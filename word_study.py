"""Offline lexical search and concordance using the bundled STEP Bible index."""
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path
import gzip
import hashlib
import json
import os
import re
import sqlite3
import tempfile
import unicodedata
from html import unescape
from html.parser import HTMLParser

DATA=Path(__file__).resolve().parent/'data'
BOOK_CODES='Gen Exo Lev Num Deu Jos Jdg Rut 1Sa 2Sa 1Ki 2Ki 1Ch 2Ch Ezr Neh Est Job Psa Pro Ecc Sng Isa Jer Lam Ezk Dan Hos Jol Amo Oba Jon Mic Nam Hab Zep Hag Zec Mal Mat Mrk Luk Jhn Act Rom 1Co 2Co Gal Eph Php Col 1Th 2Th 1Ti 2Ti Tit Phm Heb Jas 1Pe 2Pe 1Jn 2Jn 3Jn Jud Rev'.split()
BOOK_NAMES='Genesis|Exodus|Leviticus|Numbers|Deuteronomy|Joshua|Judges|Ruth|1 Samuel|2 Samuel|1 Kings|2 Kings|1 Chronicles|2 Chronicles|Ezra|Nehemiah|Esther|Job|Psalms|Proverbs|Ecclesiastes|Song of Solomon|Isaiah|Jeremiah|Lamentations|Ezekiel|Daniel|Hosea|Joel|Amos|Obadiah|Jonah|Micah|Nahum|Habakkuk|Zephaniah|Haggai|Zechariah|Malachi|Matthew|Mark|Luke|John|Acts|Romans|1 Corinthians|2 Corinthians|Galatians|Ephesians|Philippians|Colossians|1 Thessalonians|2 Thessalonians|1 Timothy|2 Timothy|Titus|Philemon|Hebrews|James|1 Peter|2 Peter|1 John|2 John|3 John|Jude|Revelation'.split('|')

class PlainText(HTMLParser):
    def __init__(self):super().__init__();self.parts=[];self.skip=0
    def handle_starttag(self,tag,attrs):
        if tag in ('script','style'):self.skip+=1
        if tag in ('br','p','div','li'):self.parts.append('\n')
    def handle_endtag(self,tag):
        if tag in ('script','style'):self.skip=max(0,self.skip-1)
    def handle_data(self,data):
        if not self.skip:self.parts.append(data)

def clean(value):
    p=PlainText();p.feed(str(value or ''))
    return re.sub(r'\n[ \t]*\n+', '\n\n', unescape(''.join(p.parts)).replace('__','')).strip()

def normalize(value):
    return ''.join(c for c in unicodedata.normalize('NFD',value.casefold()) if unicodedata.category(c)!='Mn')

@lru_cache(maxsize=1)
def database_path():
    manifest=json.loads((DATA/'word_sources.json').read_text())
    digest=manifest['database_sha256']
    folder=Path(os.getenv('SCRIPTURE_DATA_DIR',str(Path.home()/'.scripture-study'))).expanduser()/'word-data'
    folder.mkdir(parents=True,exist_ok=True)
    path=folder/(digest[:16]+'.sqlite3')
    if not path.exists():
        # Atomic replace avoids a partial database if a second session opens the app.
        with tempfile.NamedTemporaryFile(dir=folder,delete=False) as out:
            temp=Path(out.name)
            try:
                with gzip.open(DATA/'words.sqlite3.gz','rb') as inp:
                    import shutil;shutil.copyfileobj(inp,out)
                out.flush()
                if hashlib.sha256(temp.read_bytes()).hexdigest()!=digest:
                    raise ValueError('The word data is incomplete. Extract the full app ZIP again.')
                os.replace(temp,path)
            finally:temp.unlink(missing_ok=True)
    return path

@contextmanager
def connect():
    db=sqlite3.connect(database_path().as_uri()+'?mode=ro',uri=True)
    db.row_factory=sqlite3.Row
    try:yield db
    finally:db.close()

def reference(book,chapter,verse):return f'{BOOK_NAMES[book-1]} {chapter}:{verse}'

def parse_passage(value):
    """Single chapter or same-chapter verse span. Do not guess unsupported ranges."""
    m=re.fullmatch(r'\s*(.+?)\s+(\d+)(?::(\d+)(?:\s*[-–—]\s*(\d+))?)?\s*',value)
    if not m:raise ValueError('Use a single chapter or verse range, such as John 15 or John 15:9–17.')
    name=re.sub(r'[ .]','',m[1]).casefold()
    aliases={}
    for i,(code,full) in enumerate(zip(BOOK_CODES,BOOK_NAMES),1):
        for alias in [code,full,full.replace('1 ','I ').replace('2 ','II ').replace('3 ','III ')]:
            aliases[re.sub(r'[ .]','',alias).casefold()]=i
    aliases.update({'jn':43,'psalm':19,'ps':19,'songofsongs':22,'song':22,'jude':65,'ezek':26,'phil':50,'1cor':46,'2cor':47,'1tim':54,'2tim':55,'rev':66})
    book=aliases.get(name)
    if not book:raise ValueError('Book not recognized. Try its full name, such as John or 1 Corinthians.')
    chapter=int(m[2]);start=int(m[3]) if m[3] else 0;end=int(m[4]) if m[4] else start or 999
    if chapter<1 or end<start or (m[3] and start<1):raise ValueError('Check the chapter and verse range.')
    with connect() as db:
        verses=db.execute('SELECT verse FROM verses WHERE book=? AND chapter=? ORDER BY verse',(book,chapter)).fetchall()
    if not verses or (start and (start not in {r[0] for r in verses} or end not in {r[0] for r in verses})):
        raise ValueError('That chapter or verse range is not available. Check the reference.')
    return book,chapter,start,end

def entry_from_row(row):
    return {'topic':row['base'][0]+str(int(row['base'][1:])), 'lemma_id':row['id'],
            'lexeme':row['lexeme'],'transliteration':row['transliteration'],
            'short_definition':row['gloss'],'definition':row['definition'],
            'grammar':row['grammar'],'source':row['origin'],
            'transliteration_scope':'attested form' if 'corpus glossary' in row['origin'] else 'dictionary lemma'}

def search_entries(query,passage='',limit=150):
    if not query.strip():return [],0
    q=normalize(query.strip());strong=re.fullmatch(r'([gh])0*(\d+)([a-z]*)',q)
    with connect() as db:
        if strong:
            base=strong[1].upper()+strong[2].zfill(4)
            rows=db.execute('SELECT * FROM lexicon WHERE base=? ORDER BY id',(base,)).fetchall()
            if strong[3]:rows=[r for r in rows if r['id'].casefold()==(base+strong[3]).casefold()]
        else:
            rows=db.execute('SELECT * FROM lexicon WHERE instr(search,?)>0 ORDER BY id',(q,)).fetchall()
        entries=[entry_from_row(r) for r in rows]
        counts={}
        if passage:
            book,chapter,start,end=parse_passage(passage)
            counts={r['lemma']:r['n'] for r in db.execute('SELECT g.lemma,COUNT(DISTINCT t.id) n FROM tokens t JOIN tags g ON g.token_id=t.id WHERE book=? AND chapter=? AND verse BETWEEN ? AND ? GROUP BY g.lemma',(book,chapter,start,end))}
        for e in entries:e['passage_matches']=counts.get(e['lemma_id'],0)
        entries.sort(key=lambda e:(-e['passage_matches'],0 if normalize(e['short_definition'])==q or normalize(e['transliteration'])==q else 1,len(e['short_definition']),e['lemma_id']))
        return entries[:limit],len(entries)

def get_word_definition(word):
    # Compatibility for earlier callers. The UI explicitly asks users to choose.
    entries,_=search_entries(word);return entries[0] if entries else None

def passage_material(passage,entry,translation="WEB"):
    book,chapter,start,end=parse_passage(passage)
    with connect() as db:
        chapter_verses=[dict(r) for r in db.execute('SELECT book,chapter,verse,text FROM verses WHERE book=? AND chapter=? ORDER BY verse',(book,chapter))]
        selected=[r for r in chapter_verses if start<=r['verse']<=end]
        # Retain the entire chapter for interpretation; matching only within the user's range.
        lemma=entry.get('lemma_id')
        base=entry['topic'][0]+entry['topic'][1:].zfill(4)
        field,value=('lemma',lemma) if lemma else ('base',base)
        matches=[dict(r) for r in db.execute(f'SELECT DISTINCT t.* FROM tokens t JOIN tags g ON g.token_id=t.id WHERE g.{field}=? AND book=? AND chapter=? AND verse BETWEEN ? AND ? ORDER BY verse,position',(value,book,chapter,start,end))]
    for row in chapter_verses:row['reference']=reference(book,chapter,row['verse'])
    for row in matches:row['reference']=reference(book,chapter,row['verse'])
    from bible_reader import load_reading
    reading=load_reading(passage,translation)
    return {'reference':passage,'translation':reading['translation'],'translation_code':translation,
            'copyright':reading.get('copyright',''),'provider':reading.get('provider',''),
            'provider_meta':reading.get('provider_meta',{}),'selected':reading['selected'],'chapter':reading['chapter'],'matches':matches,'verified':bool(matches),'edition':'STEP TAGNT / NA28' if book>39 else 'STEP TAHOT primary L/Q/R','matching_scope':'extended lexical ID' if lemma else 'Strong’s number (legacy study; may group distinct words)'}

def occurrences(entry,book=None,offset=0,limit=20):
    lemma=entry.get('lemma_id');base=entry['topic'][0]+entry['topic'][1:].zfill(4)
    field,value=('lemma',lemma) if lemma else ('base',base)
    condition=f'g.{field}=?';params=[value]
    with connect() as db:
        books=[{'book':r['book'],'name':BOOK_NAMES[r['book']-1],'tokens':r['n'],'verses':r['v']} for r in db.execute(f'SELECT t.book,COUNT(DISTINCT t.id) n,COUNT(DISTINCT t.chapter || ":" || t.verse) v FROM tokens t JOIN tags g ON g.token_id=t.id WHERE {condition} GROUP BY t.book ORDER BY t.book',params)]
        if book:condition+=' AND t.book=?';params.append(book)
        total=db.execute(f'SELECT COUNT(DISTINCT t.id) FROM tokens t JOIN tags g ON g.token_id=t.id WHERE {condition}',params).fetchone()[0]
        count=db.execute(f'SELECT COUNT(*) FROM (SELECT t.book,t.chapter,t.verse FROM tokens t JOIN tags g ON g.token_id=t.id WHERE {condition} GROUP BY t.book,t.chapter,t.verse)',params).fetchone()[0]
        rows=db.execute(f'SELECT t.book,t.chapter,t.verse,group_concat(DISTINCT t.surface) forms FROM tokens t JOIN tags g ON g.token_id=t.id WHERE {condition} GROUP BY t.book,t.chapter,t.verse ORDER BY t.book,t.chapter,t.verse LIMIT ? OFFSET ?',params+[limit,offset]).fetchall()
        previews=[]
        for row in rows:
            verse=db.execute('SELECT text FROM verses WHERE book=? AND chapter=? AND verse=?',(row['book'],row['chapter'],row['verse'])).fetchone()
            previews.append({**dict(row),'reference':reference(row['book'],row['chapter'],row['verse']),'text':verse[0] if verse else 'No WEB preview for this STEP reference.'})
    return {'tokens':total,'verse_count':count,'books':books,'verses':previews,'scope':'extended lexical ID' if lemma else 'Strong’s number (legacy)'}

def greek_morphology(code):
    """Conservative decoder for common Robinson noun/adjective and finite verb tags."""
    parts=code.split('-');pos={'N':'noun','A':'adjective','T':'article','V':'verb','CONJ':'conjunction','ADV':'adverb','PREP':'preposition','INJ':'interjection'}
    name=pos.get(parts[0],'See source grammar code')
    if parts[0] in ('N','A','T') and len(parts)>1 and len(parts[1])==3:
        c,n,g=parts[1]
        return ', '.join([name,{'N':'nominative','G':'genitive','D':'dative','A':'accusative','V':'vocative'}.get(c,c),{'S':'singular','P':'plural'}.get(n,n),{'M':'masculine','F':'feminine','N':'neuter'}.get(g,g)])
    if parts[0]=='V' and len(parts)>2 and len(parts[1])==3 and re.fullmatch('[123][SP]',parts[2]):
        t,v,m=parts[1]
        return ', '.join([name,{'P':'present','I':'imperfect','F':'future','A':'aorist','R':'perfect','L':'pluperfect'}.get(t,t),{'A':'active','M':'middle','P':'passive','E':'middle/passive','D':'middle deponent','O':'passive deponent','N':'middle/passive deponent'}.get(v,v),{'I':'indicative','S':'subjunctive','O':'optative','M':'imperative'}.get(m,m),parts[2][0]+' person',{'S':'singular','P':'plural'}[parts[2][1]]])
    return name+' · '+code
