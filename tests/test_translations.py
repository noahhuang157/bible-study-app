import json,os,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch,Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from translations import parse_content,choose_bible,fetch_chapter,request_json
from bible_reader import load_reading
from storage import saved_payload
from word_study import database_path,search_entries,passage_material
from word_explanation import generate_word_meaning,ClearWordMeaning

CONTENT=[{'name':'para','type':'tag','attrs':{'style':'p'},'items':[{'name':'verse','attrs':{'number':'9'}},{'type':'text','text':'A synthetic verse about testimony. ','attrs':{'verseId':'JHN.15.9'}},{'name':'char','items':[{'type':'text','text':'Its sentence continues.'}]}]}]
CATALOG=[{'id':'edition-1','abbreviation':'NIV','language':{'id':'eng'},'copyright':'Synthetic copyright'}]

class TranslationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.env=patch.dict(os.environ,{'SCRIPTURE_DATA_DIR':cls.temp.name});cls.env.start();database_path.cache_clear()
    @classmethod
    def tearDownClass(cls):database_path.cache_clear();cls.env.stop();cls.temp.cleanup()
    def test_parse_nested_text_and_bridge_without_guessing(self):
        rows=parse_content(CONTENT,43,15);self.assertEqual(rows[0]['verse'],9);self.assertEqual(rows[0]['text'],'A synthetic verse about testimony. Its sentence continues.')
        bridged=[{'name':'verse','attrs':{'number':'9-10'}},{'type':'text','text':'One combined verse span.'}]
        self.assertEqual(parse_content(bridged,43,15)[0]['verse_end'],10)
        with self.assertRaises(ValueError):parse_content([{'type':'text','text':'Wrong chapter','attrs':{'verseId':'JHN.16.9'}}],43,15)
    def test_catalog_access_and_ambiguous_editions(self):
        self.assertEqual(choose_bible(CATALOG,'NIV')['id'],'edition-1')
        with self.assertRaises(ValueError):choose_bible(CATALOG,'NLT')
        with self.assertRaises(ValueError):choose_bible(CATALOG*2,'NIV')
        with patch.dict(os.environ,{'API_BIBLE_NIV_ID':'edition-1'}):self.assertEqual(choose_bible(CATALOG,'NIV')['id'],'edition-1')
        with patch.dict(os.environ,{'API_BIBLE_CSB_ID':'edition-1'}):
            with self.assertRaises(ValueError):choose_bible(CATALOG,'CSB')
    def test_online_reader_and_copyright_no_fallback(self):
        chapter={'data':{'id':'JHN.15','bibleId':'edition-1','content':CONTENT,'copyright':'Synthetic copyright'},'meta':{'fumsToken':'test-token'}}
        with patch.dict(os.environ,{'API_BIBLE_KEY':'private-key'}),patch('translations.request_json',side_effect=[{'data':CATALOG},chapter]) as fetch:
            reader=load_reading('John 15:9','NIV');self.assertEqual(reader['translation_code'],'NIV');self.assertIn('synthetic',reader['selected'][0]['text']);self.assertEqual(fetch.call_count,2)
        with patch.dict(os.environ,{'API_BIBLE_KEY':''}):
            with self.assertRaises(ValueError):load_reading('John 15:9','NIV')
        with patch('translations.fetch_chapter',return_value={'verses':[],'copyright':'Notice','provider':'Test'}):
            with self.assertRaises(ValueError):load_reading('John 15:9','NIV')
    def test_esv_direct_text_and_copyright(self):
        response={'parsed':[[43015001,43015002]],'passages':['[1] First synthetic verse. [2] Second synthetic verse.\n\n(The Holy Bible, English Standard Version. Synthetic publisher notice.)']}
        with patch.dict(os.environ,{'ESV_API_KEY':'test-key'}),patch('translations.request_json',return_value=response) as request:
            reading=fetch_chapter('ESV',43,15)
            self.assertEqual(len(reading['verses']),2);self.assertNotIn('publisher',reading['verses'][-1]['text'])
            self.assertIn('publisher',reading['copyright']);self.assertEqual(reading['provider'],'Crossway ESV API')
            self.assertEqual(request.call_args.args[1]['Authorization'],'Token test-key')

    def test_auth_errors_are_safe(self):
        with patch('translations.requests.get',return_value=Mock(status_code=403)):
            with self.assertRaises(ValueError) as error:request_json('https://example.test',{'api-key':'never-show-this'})
            self.assertNotIn('never-show-this',str(error.exception))
    def test_copyrighted_text_not_written_into_studies(self):
        material={'translation_code':'NIV','selected':[{'text':'Licensed text'}],'chapter':[{'text':'Licensed text'}],'provider_meta':{'fumsToken':'token'},'matches':[{'gloss':'testimony'}]}
        result={'text':'My explanation','reader':material,'passage_data':material}
        stored=saved_payload(result)
        self.assertNotIn('Licensed text',json.dumps(stored));self.assertTrue(stored['reader']['requires_fetch']);self.assertEqual(stored['passage_data']['matches'],material['matches'])
        self.assertIn('selected',result['reader']) # Don't mutate active session.
    def test_clear_definition_and_context_validation(self):
        entry=search_entries('G3144')[0][0]
        material=passage_material('Acts 1:8',entry)
        result={'entry':entry,'passage_data':material}
        guide=ClearWordMeaning(plain_meaning='A person who gives testimony to what they know or have experienced.',contextual_meaning='The sentence assigns the disciples a role in testifying.',why_this_meaning='It connects their testimony with the promised power.',other_senses=[],caution='This use does not by itself mean dying for the testimony.',references=['Acts 1:8','Lexical entry'])
        with patch('word_explanation.generate_json',return_value=guide) as generate:
            meaning=generate_word_meaning(result);self.assertGreater(len(meaning['plain_meaning']),40);self.assertIn('witness',generate.call_args.args[0])
            guide.references=['Invented 99:1']
            with self.assertRaises(ValueError):generate_word_meaning(result)
            guide.references=['Lexical entry']
            with self.assertRaises(ValueError):generate_word_meaning({'entry':entry})

if __name__=='__main__':unittest.main()
