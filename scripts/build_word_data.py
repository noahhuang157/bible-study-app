"""Build the bundled index from downloaded STEP Bible TSV files and Bolls WEB.json.
Usage: python scripts/build_word_data.py SOURCE_DIRECTORY
Sources and transformations are recorded in data/word_sources.json.
"""
import gzip, hashlib, json, re, sqlite3, sys, unicodedata
from pathlib import Path
from html.parser import HTMLParser
BOOK_CODES='Gen Exo Lev Num Deu Jos Jdg Rut 1Sa 2Sa 1Ki 2Ki 1Ch 2Ch Ezr Neh Est Job Psa Pro Ecc Sng Isa Jer Lam Ezk Dan Hos Jol Amo Oba Jon Mic Nam Hab Zep Hag Zec Mal Mat Mrk Luk Jhn Act Rom 1Co 2Co Gal Eph Php Col 1Th 2Th 1Ti 2Ti Tit Phm Heb Jas 1Pe 2Pe 1Jn 2Jn 3Jn Jud Rev'.split()

def normalize(value):
    return ''.join(c for c in unicodedata.normalize('NFD',value.casefold()) if unicodedata.category(c) != 'Mn')

class Text(HTMLParser):
    def __init__(self): super().__init__();self.parts=[]
    def handle_data(self,d):self.parts.append(d)

def plain(value):
    p=Text();p.feed(value);return ''.join(p.parts)

def build(source, output):
    output.mkdir(exist_ok=True,parents=True)
    path=output/'words.sqlite3'
    if path.exists():path.unlink()
    db=sqlite3.connect(path)
    db.executescript('''
    PRAGMA journal_mode=OFF; PRAGMA synchronous=OFF;
    CREATE TABLE lexicon(id TEXT PRIMARY KEY, base TEXT, lexeme TEXT, transliteration TEXT, grammar TEXT, gloss TEXT, definition TEXT, search TEXT, origin TEXT);
    CREATE TABLE tokens(id INTEGER PRIMARY KEY,book INTEGER,chapter INTEGER,verse INTEGER,position TEXT,surface TEXT,transliteration TEXT,gloss TEXT,morphology TEXT,source_ref TEXT);
    CREATE TABLE tags(token_id INTEGER,lemma TEXT,base TEXT);
    CREATE TABLE verses(book INTEGER,chapter INTEGER,verse INTEGER,text TEXT,PRIMARY KEY(book,chapter,verse));
    ''')
    files=[]
    corpus_entries={}
    for p in sorted(source.glob('*.txt')):
        if not p.name.startswith(('TBESG','TBESH','TAGNT','TAHOT')):continue
        files.append({'name':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
        greek=p.name.startswith(('TBESG','TAGNT'))
        if p.name.startswith(('TBESG','TBESH')):
            for line in p.read_text(encoding='utf-8-sig').splitlines():
                f=line.split('\t')
                if len(f)<8 or not re.fullmatch('[GH][0-9]{4}[a-z]*',f[0]):continue
                # Use the disambiguated ID, not unified IDs (which can combine words).
                match=re.match(r'[GH]\d{4}[A-Za-z]*',f[1])
                if not match:continue
                lemma=match[0];definition=f[7] if greek else ''
                values=(lemma,f[0][:5],f[3],f[4],f[5],f[6],definition,normalize(' '.join([f[0],lemma,f[3],f[4],f[6]])), 'STEP Bible TBESG' if greek else 'STEP Bible Hebrew glossary (TBESH metadata)')
                db.execute('INSERT OR IGNORE INTO lexicon VALUES(?,?,?,?,?,?,?,?,?)',values)
        else:
            for line in p.read_text(encoding='utf-8-sig').splitlines():
                f=line.split('\t')
                if len(f)<6:continue
                m=re.match(r'([123]?[A-Za-z]{2,3})\.(\d+)\.(\d+)(.*?)#([^=]+)=(.+)',f[0])
                if not m or m[1] not in BOOK_CODES:continue
                if greek and not re.search(r'\bNA28\b',f[5]):continue
                if not greek and m[6][0] not in 'LQR':continue
                if greek:
                    surface=f[1].rsplit(' (',1)[0];translit=f[1].rsplit(' (',1)[-1].rstrip(')')
                    gloss=f[2];tag_text,morph=f[3].split('=',1) if '=' in f[3] else (f[3],'')
                else:surface,translit,gloss,tag_text,morph=f[1:6]
                tags=list(dict.fromkeys(re.findall(r'[GH]\d{4}[A-Za-z]*',tag_text)))
                if not tags:continue
                for tag in tags:
                    if greek:
                        form,brief=f[4].split('=',1) if '=' in f[4] else (surface,gloss)
                        roman=translit
                    else:
                        lexical=re.search(re.escape(tag)+r'=([^=]+)=([^}/\\]+)',f[11]) if len(f)>11 else None
                        form=lexical[1] if lexical else surface
                        brief=lexical[2].split('»')[0] if lexical else gloss
                        roman=translit
                    corpus_entries.setdefault(tag,(tag,tag[:5],form,roman,'',brief,'',normalize(' '.join([tag,form,roman,brief])),'STEP Bible corpus glossary (TAGNT/TAHOT)'))
                row=(BOOK_CODES.index(m[1])+1,int(m[2]),int(m[3]),m[5],surface,translit,gloss,morph,f[0])
                tid=db.execute('INSERT INTO tokens(book,chapter,verse,position,surface,transliteration,gloss,morphology,source_ref) VALUES(?,?,?,?,?,?,?,?,?)',row).lastrowid
                db.executemany('INSERT INTO tags VALUES(?,?,?)',[(tid,t,t[:5]) for t in tags])
        db.commit()
    # A few corpus IDs are absent from the separate brief lexicon. Preserve them
    # as corpus-glossary entries instead of guessing a disambiguated dictionary ID.
    db.executemany('INSERT OR IGNORE INTO lexicon VALUES(?,?,?,?,?,?,?,?,?)',corpus_entries.values())
    p=source/'WEB.json'
    for row in json.loads(p.read_text()):
        if 1<=row['book']<=66:
            db.execute('INSERT OR REPLACE INTO verses VALUES(?,?,?,?)',(row['book'],row['chapter'],row['verse'],plain(row['text'])))
    files.append({'name':'WEB.json','sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
    db.executescript('CREATE INDEX tags_lemma ON tags(lemma,token_id); CREATE INDEX token_ref ON tokens(book,chapter,verse); CREATE INDEX lexicon_base ON lexicon(base);')
    db.commit();counts={t:db.execute('SELECT COUNT(*) FROM '+t).fetchone()[0] for t in ['tokens','tags','lexicon','verses']};db.close()
    with path.open('rb') as inp,gzip.open(output/'words.sqlite3.gz','wb',compresslevel=9) as out:
        import shutil;shutil.copyfileobj(inp,out)
    path.unlink()
    manifest={'built':'2026-10-07','sources':files,'counts':counts,'database_sha256':hashlib.sha256(gzip.decompress((output/'words.sqlite3.gz').read_bytes())).hexdigest(),'edition':'TAGNT words marked NA28; TAHOT primary L/Q/R rows (no X additions or alternate rows)','transformations':'TSV subset to SQLite; primary word-level lexical tags only; no alternate tagging; missing lexicon IDs exposed using corpus glossary metadata (transliteration from an attested form); references use STEP English/NRSV versification. Hebrew lexicon columns 0-6 only: full TBESH definitions excluded because source header requests Online Bible permission. HTML removed from WEB verse text.'}
    (output/'word_sources.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False))
    print(counts,'compressed bytes:',(output/'words.sqlite3.gz').stat().st_size)

if __name__=='__main__':build(Path(sys.argv[1]),Path(__file__).resolve().parents[1]/'data')
