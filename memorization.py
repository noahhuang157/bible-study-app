"""Account-scoped verse cards, daily spaced review, and deterministic practice."""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import hashlib
import json
import os
import re
import unicodedata
from storage import connect


def today():
    return datetime.now(ZoneInfo(os.getenv('SCRIPTURE_TIMEZONE', 'America/Los_Angeles'))).date()


def _schema(db):
    db.executescript('''
        CREATE TABLE IF NOT EXISTS memory_cards (
            user_id INTEGER NOT NULL REFERENCES users(id), id TEXT NOT NULL,
            reference TEXT NOT NULL, translation TEXT NOT NULL, collection TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL, due_date TEXT NOT NULL, interval_days INTEGER NOT NULL DEFAULT 0,
            reviews INTEGER NOT NULL DEFAULT 0, successes INTEGER NOT NULL DEFAULT 0,
            last_review TEXT, PRIMARY KEY(user_id,id)
        );
        CREATE TABLE IF NOT EXISTS memory_reviews (
            user_id INTEGER NOT NULL, card_id TEXT NOT NULL, token TEXT NOT NULL,
            reviewed_on TEXT NOT NULL, rating TEXT NOT NULL,
            PRIMARY KEY(user_id,token),
            FOREIGN KEY(user_id,card_id) REFERENCES memory_cards(user_id,id) ON DELETE CASCADE
        );
    ''')


def add_card(user_id, reading, collection=''):
    rows = reading['selected']
    start, end = rows[0]['verse'], rows[-1].get('verse_end', rows[-1]['verse'])
    if end-start+1 > 5:
        raise ValueError('Choose one verse or a short range of up to five verses.')
    reference = f"{reading['chapter_reference']}:{start}" + (f'–{end}' if end != start else '')
    code = reading['translation_code']
    identity = hashlib.sha256(json.dumps([reading['book'], reading['chapter_number'], start, end, code]).encode()).hexdigest()[:24]
    with connect() as db:
        _schema(db)
        existing = db.execute('SELECT id FROM memory_cards WHERE user_id=? AND id=?', (user_id,identity)).fetchone()
        db.execute('''INSERT INTO memory_cards(user_id,id,reference,translation,collection,created_at,due_date)
            VALUES(?,?,?,?,?,?,?) ON CONFLICT(user_id,id) DO UPDATE SET collection=excluded.collection''',
            (user_id,identity,reference,code,collection.strip()[:60],today().isoformat(),today().isoformat()))
    return identity, not bool(existing)


def list_cards(user_id):
    with connect() as db:
        _schema(db)
        return [dict(r) for r in db.execute('SELECT * FROM memory_cards WHERE user_id=? ORDER BY due_date,created_at,id', (user_id,))]


def remove_card(user_id, identity):
    with connect() as db:
        _schema(db)
        db.execute('DELETE FROM memory_cards WHERE user_id=? AND id=?', (user_id,identity))


def next_interval(previous, rating):
    if rating not in {'Again','Hard','Good','Easy'}:
        raise ValueError('Choose a review rating.')
    if rating == 'Again': return 1
    if rating == 'Hard': return max(1, min(30, round(previous*1.2)))
    if rating == 'Good': return 1 if previous == 0 else min(180, max(previous+1,round(previous*2.2)))
    return 3 if previous == 0 else min(180, max(previous+2,round(previous*3)))


def review_card(user_id, identity, rating, token):
    """One rating per practice attempt; retries cannot advance the schedule twice."""
    if not token or len(token)>100: raise ValueError('Start a new review attempt.')
    next_interval(0, rating)
    with connect() as db:
        _schema(db)
        db.execute('BEGIN IMMEDIATE')
        row = db.execute('SELECT * FROM memory_cards WHERE user_id=? AND id=?', (user_id,identity)).fetchone()
        if row is None: raise ValueError('This card is no longer in your deck.')
        prior = db.execute('SELECT token FROM memory_reviews WHERE user_id=? AND token=?', (user_id,token)).fetchone()
        if prior: return False
        day = today()
        interval = next_interval(row['interval_days'], rating)
        db.execute('INSERT INTO memory_reviews VALUES(?,?,?,?,?)', (user_id,identity,token,day.isoformat(),rating))
        db.execute('''UPDATE memory_cards SET interval_days=?, due_date=?, reviews=reviews+1,
            successes=successes+?, last_review=? WHERE user_id=? AND id=?''',
            (interval,(day+timedelta(days=interval)).isoformat(),int(rating in {'Good','Easy'}),day.isoformat(),user_id,identity))
    return True


def memory_stats(user_id):
    cards = list_cards(user_id)
    day = today()
    with connect() as db:
        dates = {r[0] for r in db.execute('SELECT DISTINCT reviewed_on FROM memory_reviews WHERE user_id=?', (user_id,))}
        reviewed_today = db.execute('SELECT COUNT(DISTINCT card_id) FROM memory_reviews WHERE user_id=? AND reviewed_on=?', (user_id,day.isoformat())).fetchone()[0]
    cursor = day if day.isoformat() in dates else day-timedelta(days=1)
    streak = 0
    while cursor.isoformat() in dates:
        streak += 1
        cursor -= timedelta(days=1)
    return {'total':len(cards),'due':sum(c['due_date']<=day.isoformat() for c in cards),
            'reviewed_today':reviewed_today,'streak':streak}


def export_deck(user_id):
    cards = [{k:v for k,v in c.items() if k != 'user_id'} for c in list_cards(user_id)]
    return json.dumps({'format':'scripture-memory-v1','exported_on':today().isoformat(),'cards':cards},ensure_ascii=False,indent=2)


def normalized_words(text):
    # Capitalization, punctuation and typographic apostrophes do not affect recall.
    text = unicodedata.normalize('NFKC',text).casefold().replace('’', "'")
    return re.findall(r"[^\W_]+(?:'[^\W_]+)*", text, re.UNICODE)


def check_recall(answer, expected):
    from difflib import SequenceMatcher
    actual, target = normalized_words(answer), normalized_words(expected)
    if not actual: raise ValueError('Type your attempt before checking it.')
    matcher = SequenceMatcher(a=target,b=actual,autojunk=False)
    matched = sum(block.size for block in matcher.get_matching_blocks())
    # Extra words count too. Feedback is practice assistance, never a spiritual score.
    score = round(100*2*matched/(len(target)+len(actual))) if target else 0
    return {'exact':actual==target,'score':score,'matched':matched,'expected_words':len(target)}


def hidden_words(text, level):
    """Deterministic hints that preserve punctuation and word positions."""
    counter = 0
    def replace(match):
        nonlocal counter
        counter += 1
        hide = level=='All words' or (level=='Most words' and counter%3!=1) or (level=='Some words' and counter%3==0)
        return '＿'*min(len(match.group()),8) if hide else match.group()
    return re.sub(r"[^\W_]+(?:[’'][^\W_]+)*",replace,text,flags=re.UNICODE)
