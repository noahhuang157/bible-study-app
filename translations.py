"""Authorized, on-demand translations. Copyrighted Bible text is not bundled."""
import json,os,re
from html import unescape
import requests
from word_study import BOOK_NAMES,reference,clean

TRANSLATIONS={'WEB':'World English Bible','ESV':'English Standard Version','NIV':'New International Version','NLT':'New Living Translation','NKJV':'New King James Version'}
API_BOOKS='GEN EXO LEV NUM DEU JOS JDG RUT 1SA 2SA 1KI 2KI 1CH 2CH EZR NEH EST JOB PSA PRO ECC SNG ISA JER LAM EZK DAN HOS JOL AMO OBA JON MIC NAM HAB ZEP HAG ZEC MAL MAT MRK LUK JHN ACT ROM 1CO 2CO GAL EPH PHP COL 1TH 2TH 1TI 2TI TIT PHM HEB JAS 1PE 2PE 1JN 2JN 3JN JUD REV'.split()


def request_json(url,headers,params=None):
    try:r=requests.get(url,headers=headers,params=params,timeout=30)
    except requests.RequestException:raise ValueError('Could not reach the Bible text provider. Check your internet connection and try again.') from None
    if r.status_code in (401,403):raise ValueError('The Bible provider denied access. Check your API key and enable this translation in your provider account.')
    if r.status_code==429:raise ValueError('The Bible text provider rate limit was reached. Please try again later.')
    if r.status_code==404:raise ValueError('This translation or chapter is unavailable for your provider account.')
    if r.status_code!=200:raise ValueError(f'The Bible text provider returned HTTP {r.status_code}. Please try again later.')
    try:return r.json()
    except ValueError:raise ValueError('The Bible text provider returned an invalid response.') from None


def choose_bible(catalog,code):
    override=os.getenv('API_BIBLE_'+code+'_ID','').strip()
    if override:
        found=[b for b in catalog if b.get('id')==override and b.get('language',{}).get('id','eng')=='eng']
        if not found:raise ValueError(f'The configured {code} Bible ID is not available for this API.Bible key.')
        if not any(str(found[0].get(k,'')).upper()==code for k in ['abbreviation','abbreviationLocal']):
            raise ValueError(f'The configured Bible ID is not labeled {code}. Check API_BIBLE_{code}_ID; a different version will not be substituted.')
        return found[0]
    found=[b for b in catalog if b.get('language',{}).get('id','eng')=='eng' and any(str(b.get(k,'')).upper()==code for k in ['abbreviation','abbreviationLocal'])]
    if not found:raise ValueError(f'{code} is not enabled for this API.Bible key. Enable it in your provider account, or choose WEB. ESV can also use ESV_API_KEY.')
    if len(found)>1:raise ValueError(f'Multiple {code} editions are available. Set API_BIBLE_{code}_ID in .env to your chosen edition ID from API.Bible.')
    return found[0]


def parse_content(content,book,chapter):
    if isinstance(content,str):
        try:content=json.loads(content)
        except ValueError:raise ValueError('Expected structured Bible text from the provider.') from None
    if not isinstance(content,list):raise ValueError('Expected structured Bible text from the provider.')
    pieces={};current=None
    def walk(node):
        nonlocal current
        if isinstance(node,list):
            for child in node:walk(child)
            return
        if not isinstance(node,dict):return
        attrs=node.get('attrs') or {};name=node.get('name','')
        if name=='note' or (name=='para' and re.match(r'^(?:s\d|ms|mt|h|r$|d$)',str(attrs.get('style','')))):return
        if name=='verse':
            number=str(attrs.get('number',''))
            match=re.fullmatch(r'(\d+)(?:[-–](\d+))?',number)
            current=(int(match[1]),int(match[2] or match[1])) if match else None
            return
        if node.get('type')=='text':
            sid=attrs.get('verseId')
            if sid:
                match=re.fullmatch(re.escape(API_BOOKS[book-1])+r'\.'+str(chapter)+r'\.(\d+)(?:-(\d+))?',sid)
                if match:current=(int(match[1]),int(match[2] or match[1]))
                else:raise ValueError('The provider returned verse text for a different chapter.')
            if current:pieces.setdefault(current,[]).append(node.get('text',''))
        for child in node.get('items',[]):walk(child)
    walk(content)
    rows=[]
    for (verse,end),parts in sorted(pieces.items()):
        text=''.join(parts).strip()
        if text:rows.append({'book':book,'chapter':chapter,'verse':verse,'verse_end':end,'text':text,'reference':reference(book,chapter,verse)+(f'–{end}' if end!=verse else '')})
    if not rows:raise ValueError('No numbered verses were returned by the Bible provider.')
    return rows


def fetch_chapter(code,book,chapter):
    if code not in TRANSLATIONS or code=='WEB':raise ValueError('Choose a supported online translation.')
    if code=='ESV' and os.getenv('ESV_API_KEY','').strip():return fetch_esv(book,chapter)
    key=os.getenv('API_BIBLE_KEY','').strip()
    if not key:raise ValueError('Add API_BIBLE_KEY to .env for NIV, NLT, CSB, NKJV, or supported ESV access. ESV can alternatively use ESV_API_KEY. WEB works without a key.')
    headers={'api-key':key}
    catalog=request_json('https://rest.api.bible/v1/bibles',headers,{'language':'eng','include-full-details':'true'}).get('data',[])
    bible=choose_bible(catalog,code);chapter_id=API_BOOKS[book-1]+'.'+str(chapter)
    response=request_json(f"https://rest.api.bible/v1/bibles/{bible['id']}/chapters/{chapter_id}",headers,{'content-type':'json','include-notes':'false','include-titles':'false','include-chapter-numbers':'false','include-verse-numbers':'true'})
    data=response.get('data',{})
    if data.get('id')!=chapter_id or data.get('bibleId',bible['id'])!=bible['id']:raise ValueError('The Bible provider returned a different chapter or edition.')
    copyright=clean(data.get('copyright') or bible.get('copyright',''))
    if not copyright:raise ValueError('The Bible provider did not include a copyright notice. This edition cannot be displayed yet.')
    return {'verses':parse_content(data.get('content'),book,chapter),'copyright':copyright,'provider':'API.Bible','bible_id':bible['id'],'provider_meta':response.get('meta',{})}


def fetch_esv(book,chapter):
    response=request_json('https://api.esv.org/v3/passage/text/',{'Authorization':'Token '+os.environ['ESV_API_KEY'].strip()}, {'q':f'{BOOK_NAMES[book-1]} {chapter}','include-passage-references':'false','include-verse-numbers':'true','include-first-verse-numbers':'true','include-footnotes':'false','include-footnote-body':'false','include-headings':'false','include-copyright':'true','include-short-copyright':'false'})
    spans=response.get('parsed',[])
    if not spans or any(int(span[0])//1000 != book*1000+chapter or int(span[1])//1000!=book*1000+chapter for span in spans):raise ValueError('ESV returned a different chapter.')
    text='\n'.join(response.get('passages',[]))
    copyright_start=text.find('The Holy Bible, English Standard Version')
    if copyright_start<0:raise ValueError('ESV did not return the requested copyright notice.')
    copyright=text[copyright_start:].strip();body=text[:copyright_start].rstrip(' \n(')
    matches=list(re.finditer(r'\[(\d+)\]',body));rows=[]
    for i,m in enumerate(matches):
        value=body[m.end():matches[i+1].start() if i+1<len(matches) else len(body)].strip()
        if value:rows.append({'book':book,'chapter':chapter,'verse':int(m[1]),'text':value,'reference':reference(book,chapter,int(m[1]))})
    if not rows:raise ValueError('No numbered ESV verses were returned.')
    return {'verses':rows,'copyright':copyright,'provider':'Crossway ESV API','bible_id':'ESV','provider_meta':{}}
