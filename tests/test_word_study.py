import os,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from word_study import search_entries,passage_material,occurrences,parse_passage,greek_morphology,clean,database_path,connect
from word_explanation import generate_word_explanation,PassageWordGuide,ExplanationSection,SECTIONS
from storage import study_identity,register,save_study,update_notes,get_study

class WordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory=tempfile.TemporaryDirectory()
        cls.env=patch.dict(os.environ,{'SCRIPTURE_DATA_DIR':cls.directory.name});cls.env.start();database_path.cache_clear()
    @classmethod
    def tearDownClass(cls):
        database_path.cache_clear();cls.env.stop();cls.directory.cleanup()
    def entry(self,q):return search_entries(q)[0][0]
    def test_actual_corpus_and_lexical_disambiguation(self):
        entries,total=search_entries('love','John 15:9-17')
        matching={e['lemma_id']:e['passage_matches'] for e in entries if e['passage_matches']}
        self.assertEqual(matching,{'G0025':5,'G0026':4})
        e=self.entry('G26');o=occurrences(e)
        self.assertEqual(o['tokens'],116);self.assertEqual(o['verse_count'],106)
        self.assertEqual(search_entries('agape')[0][0]['lemma_id'],'G0026')
        self.assertTrue(any(e['lemma_id']=='G0026' for e in search_entries('ἀγάπη')[0]))
        self.assertFalse(passage_material('John 3:16',e)['verified']) # G25 occurs, not G26.
        self.assertEqual(passage_material('John 15:9',e)['matches'][0]['morphology'],'N-DSF')
        self.assertTrue(all(e['topic']=='G2' for e in search_entries('G2')[0]))
    def test_hebrew_split_entries_and_gloss_only(self):
        entries,_=search_entries('H1254','Genesis 1:1')
        self.assertEqual(entries[0]['lemma_id'],'H1254A')
        self.assertTrue(passage_material('Gen 1:1',entries[0])['verified'])
        self.assertFalse(entries[0]['definition'])
        self.assertFalse(passage_material('Genesis 1:1',next(e for e in entries if e['lemma_id']=='H1254B'))['verified'])
    def test_pagination_is_complete_and_filtered(self):
        e=self.entry('G26');allrows=occurrences(e,limit=1000)
        first=occurrences(e,limit=15);second=occurrences(e,offset=15,limit=15)
        self.assertFalse({r['reference'] for r in first['verses']} & {r['reference'] for r in second['verses']})
        self.assertEqual(len(allrows['verses']),allrows['verse_count'])
        filtered=occurrences(e,book=43,limit=1000)
        self.assertTrue(all(r['book']==43 for r in filtered['verses']))
        self.assertEqual(sum(b['tokens'] for b in allrows['books']),allrows['tokens'])
    def test_reference_validation_and_safe_rendering(self):
        self.assertEqual(parse_passage('1 Corinthians 13:1–13')[:2],(46,13))
        for value in ['John 999:1','John 15:99','John 15:17-9','John 15:1-16:1','nonsense']:
            with self.assertRaises(ValueError):parse_passage(value)
        self.assertIn('dative',greek_morphology('N-DSF'))
        self.assertIn('aorist',greek_morphology('V-AAI-3S'))
        self.assertEqual(clean('<script>bad</script><b>love</b><br>goodwill'),'love\ngoodwill')
    def test_generated_reference_validation_and_absent_word_block(self):
        e=self.entry('G26');result={'entry':e,'passage_data':passage_material('John 15:9',e),'reader_question':'What does remain mean here?'}
        section=ExplanationSection(text='The sentence locates love in a relationship.',references=['John 15:9'])
        guide=PassageWordGuide(**{key:section for key,_ in SECTIONS},questions=['How does the sentence develop?'])
        with patch('word_explanation.generate_json',return_value=guide) as gen:
            answer=generate_word_explanation(result)
            self.assertIn('Meaning in this passage',answer['markdown'])
            self.assertIn('What does remain mean here?',gen.call_args.args[0])
            guide.meaning.references=['Invented 1:1']
            with self.assertRaises(ValueError):generate_word_explanation(result)
        with patch('word_explanation.generate_json') as gen:
            with self.assertRaises(ValueError):generate_word_explanation({'entry':e,'passage_data':passage_material('John 3:16',e)})
            gen.assert_not_called()
    def test_new_lemmas_separate_notes_without_changing_legacy_identity(self):
        user=register('wordtests','test-password')['id']
        old={'query':'love','passage':'John 15','entry':{'topic':'G26'}}
        identity=save_study(user,'word_result',old);update_notes(user,identity,'Keep this note')
        enriched={**old,'passage_data':{'verified':True}}
        self.assertEqual(study_identity('word_result',enriched),identity)
        first={**old,'word_version':2,'entry':{'topic':'G26','lemma_id':'G0026'}}
        second={**first,'entry':{'topic':'G25','lemma_id':'G0025'}}
        self.assertNotEqual(study_identity('word_result',first),study_identity('word_result',second))
        save_study(user,'word_result',first)
        self.assertEqual(get_study(user,identity)['notes'],'Keep this note')

if __name__=='__main__':unittest.main()
