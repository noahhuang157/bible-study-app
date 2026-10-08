"""Offline WEB reading snapshots and chapter navigation using bundled verse data."""
from word_study import parse_passage,connect,reference,BOOK_NAMES


def load_reading(passage,translation="WEB"):
    book,chapter,start,end=parse_passage(passage)
    with connect() as db:
        verses=[dict(r) for r in db.execute('SELECT book,chapter,verse,text FROM verses WHERE book=? AND chapter=? ORDER BY verse',(book,chapter))]
        chapters=[(r[0],r[1]) for r in db.execute('SELECT DISTINCT book,chapter FROM verses ORDER BY book,chapter')]
    from translations import TRANSLATIONS,fetch_chapter
    if translation not in TRANSLATIONS:raise ValueError('Choose a supported Bible translation.')
    provider={'copyright':'World English Bible, public domain.','provider':'Bundled WEB'}
    if translation!='WEB':
        provider=fetch_chapter(translation,book,chapter)
        verses=provider['verses']
    for row in verses:row.setdefault('reference',reference(book,chapter,row['verse']))
    selected=[r for r in verses if r.get('verse_end',r['verse'])>=start and r['verse']<=end]
    if not selected:raise ValueError('No verses are available in this translation for that selection. Textual readings may differ; no other version was substituted.')
    index=chapters.index((book,chapter))
    previous=chapters[index-1] if index else None
    following=chapters[index+1] if index+1<len(chapters) else None
    return {'reference':passage.strip(),'chapter_reference':f'{BOOK_NAMES[book-1]} {chapter}',
            'translation':TRANSLATIONS[translation]+f' ({translation})','translation_code':translation,
            'copyright':provider['copyright'],'provider':provider['provider'],'provider_meta':provider.get('provider_meta',{}),'book':book,'chapter_number':chapter,
            'selected':selected,'chapter':verses,'is_whole_chapter':len(selected)==len(verses),
            'previous_chapter':f'{BOOK_NAMES[previous[0]-1]} {previous[1]}' if previous else None,
            'next_chapter':f'{BOOK_NAMES[following[0]-1]} {following[1]}' if following else None}


def reading_text(reading,whole_chapter=False):
    return '\n'.join(f"{r['reference']}: {r['text']}" for r in reading['chapter' if whole_chapter else 'selected'])
