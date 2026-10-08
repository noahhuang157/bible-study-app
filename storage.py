"""Local account and study persistence. No Streamlit dependency in this module."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
from contextlib import contextmanager

KINDS = {'passage_result', 'sermon_result', 'word_result', 'topic_result'}
ROUNDS = 600_000


def database_path():
    directory = Path(os.getenv('SCRIPTURE_DATA_DIR', str(Path.home() / '.scripture-study'))).expanduser()
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    return directory / 'studies.sqlite3'


@contextmanager
def connect():
    db = sqlite3.connect(database_path(), timeout=10)
    try:
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys = ON')
        db.executescript('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY, username TEXT NOT NULL UNIQUE,
                password_salt BLOB NOT NULL, password_hash BLOB NOT NULL
            );
            CREATE TABLE IF NOT EXISTS studies (
                user_id INTEGER NOT NULL REFERENCES users(id), id TEXT NOT NULL,
                kind TEXT NOT NULL, title TEXT NOT NULL, payload TEXT NOT NULL,
                notes TEXT NOT NULL DEFAULT '', bookmarked INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                PRIMARY KEY (user_id, id)
            );
            CREATE TABLE IF NOT EXISTS embedding_cache (
                user_id INTEGER NOT NULL, study_id TEXT NOT NULL, model TEXT NOT NULL,
                fingerprint TEXT NOT NULL, chunk_index INTEGER NOT NULL,
                excerpt TEXT NOT NULL, vector TEXT NOT NULL,
                PRIMARY KEY (user_id,study_id,model,fingerprint,chunk_index),
                FOREIGN KEY (user_id,study_id) REFERENCES studies(user_id,id)
            );
        ''')
        with db:
            yield db
    finally:
        db.close()


def _password_hash(password, salt):
    return hashlib.pbkdf2_hmac('sha256', password.encode(), salt, ROUNDS)


def register(username, password):
    username = username.strip().lower()
    if not re.fullmatch(r'[a-z0-9._-]{3,32}', username):
        raise ValueError('Use a username with 3–32 letters, numbers, dots, underscores, or hyphens.')
    if len(password) < 8 or len(password) > 256:
        raise ValueError('Choose a password between 8 and 256 characters.')
    salt = secrets.token_bytes(32)
    with connect() as db:
        try:
            cursor = db.execute('INSERT INTO users(username,password_salt,password_hash) VALUES(?,?,?)',
                                (username, salt, _password_hash(password, salt)))
        except sqlite3.IntegrityError:
            raise ValueError('That username is already taken. Choose another or sign in.') from None
        return {'id': cursor.lastrowid, 'username': username}


def authenticate(username, password):
    with connect() as db:
        user = db.execute('SELECT * FROM users WHERE username=?', (username.strip().lower(),)).fetchone()
    # Equal work for an unknown username avoids a fast username-existence check.
    salt = user['password_salt'] if user else bytes(32)
    candidate = _password_hash(password, salt)
    if user and hmac.compare_digest(candidate, user['password_hash']):
        return {'id': user['id'], 'username': user['username']}
    return None


def study_identity(kind, result):
    identity = {'kind': kind, 'label': result.get('label', result.get('query', '')),
                'source': result.get('source_url', ''), 'passage': result.get('passage', '')}
    if kind == 'word_result' and result.get('word_version', 0) >= 2:
        identity['lemma'] = result.get('entry', {}).get('lemma_id', '')
    return hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()[:24]


def saved_payload(result):
    # Keep licensed text in the active session only. Persist references, tags,
    # generated explanations and notes; reopen fetches authorized text again.
    payload=json.loads(json.dumps(result))
    for field in ('reader','passage_data'):
        material=payload.get(field)
        if material and material.get('translation_code','WEB')!='WEB':
            for key in ('selected','chapter','provider_meta'):material.pop(key,None)
            material['requires_fetch']=True
    return payload


def save_study(user_id, kind, result):
    if kind not in KINDS:
        raise ValueError('Unknown study type.')
    identity = study_identity(kind, result)
    title = result.get('label', result.get('query', 'Study'))
    now = datetime.now(timezone.utc).isoformat()
    with connect() as db:
        db.execute('''INSERT INTO studies(user_id,id,kind,title,payload,created_at,updated_at)
            VALUES(?,?,?,?,?,?,?) ON CONFLICT(user_id,id) DO UPDATE SET
            payload=excluded.payload, title=excluded.title, updated_at=excluded.updated_at''',
            (user_id,identity,kind,title,json.dumps(saved_payload(result),ensure_ascii=False),now,now))
    return identity


def _record(row):
    if row is None:
        return None
    record = dict(row)
    record['payload'] = json.loads(record['payload'])
    record['bookmarked'] = bool(record['bookmarked'])
    return record


def get_study(user_id, identity):
    with connect() as db:
        return _record(db.execute('SELECT * FROM studies WHERE user_id=? AND id=?', (user_id,identity)).fetchone())


def list_studies(user_id, query='', kind='', bookmarked_only=False):
    # Parameterized SQL; filtering never changes the current account scope.
    sql = 'SELECT * FROM studies WHERE user_id=?'
    values = [user_id]
    if query.strip():
        sql += ' AND (instr(lower(title),lower(?))>0 OR instr(lower(notes),lower(?))>0)'
        values += [query.strip(),query.strip()]
    if kind:
        sql += ' AND kind=?'
        values.append(kind)
    if bookmarked_only:
        sql += ' AND bookmarked=1'
    sql += ' ORDER BY updated_at DESC, id'
    with connect() as db:
        return [_record(row) for row in db.execute(sql,values).fetchall()]


def update_notes(user_id, identity, notes):
    with connect() as db:
        db.execute('UPDATE studies SET notes=?, updated_at=? WHERE user_id=? AND id=?',
                   (notes,datetime.now(timezone.utc).isoformat(),user_id,identity))


def set_bookmark(user_id, identity, bookmarked):
    with connect() as db:
        db.execute('UPDATE studies SET bookmarked=? WHERE user_id=? AND id=?', (int(bookmarked),user_id,identity))


def export_backup(user_id):
    # Only the signed-in account's studies. Passwords and API keys are excluded.
    records = list_studies(user_id)
    for record in records:
        record.pop('user_id',None)
    from memorization import export_deck
    memory = json.loads(export_deck(user_id))
    return json.dumps({'format':'scripture-study-backup','version':1,'studies':records,'memory_deck':memory},ensure_ascii=False,indent=2)


def cached_embeddings(user_id, identity, model, fingerprint):
    with connect() as db:
        return [dict(r) for r in db.execute('SELECT * FROM embedding_cache WHERE user_id=? AND study_id=? AND model=? AND fingerprint=? ORDER BY chunk_index',
                (user_id,identity,model,fingerprint)).fetchall()]


def save_embeddings(user_id, identity, model, fingerprint, chunks, vectors):
    if len(chunks) != len(vectors):
        raise ValueError('Embedding count did not match source chunks.')
    with connect() as db:
        db.execute('DELETE FROM embedding_cache WHERE user_id=? AND study_id=? AND model=?', (user_id,identity,model))
        db.executemany('INSERT INTO embedding_cache VALUES(?,?,?,?,?,?,?)',
            [(user_id,identity,model,fingerprint,i,text,json.dumps(vector)) for i,(text,vector) in enumerate(zip(chunks,vectors))])
