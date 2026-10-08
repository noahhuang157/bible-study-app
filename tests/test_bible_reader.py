import os,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from bible_reader import load_reading,reading_text
from word_study import database_path
from storage import register,save_study,get_study,update_notes,set_bookmark

class ReaderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.env=patch.dict(os.environ,{'SCRIPTURE_DATA_DIR':cls.temp.name});cls.env.start();database_path.cache_clear()
    @classmethod
    def tearDownClass(cls):
        database_path.cache_clear();cls.env.stop();cls.temp.cleanup()
    def test_selection_context_and_navigation(self):
        reading=load_reading('John 15:9–17')
        self.assertEqual([r['verse'] for r in reading['selected']],list(range(9,18)))
        self.assertGreater(len(reading['chapter']),len(reading['selected']))
        self.assertEqual(reading['previous_chapter'],'John 14');self.assertEqual(reading['next_chapter'],'John 16')
        self.assertIn('John 15:9:',reading_text(reading));self.assertNotIn('John 15:1:',reading_text(reading))
        self.assertIn('John 15:1:',reading_text(reading,whole_chapter=True))
        self.assertTrue(load_reading('John 15')['is_whole_chapter'])
    def test_book_boundaries_and_canon_ends(self):
        self.assertIsNone(load_reading('Genesis 1')['previous_chapter'])
        self.assertEqual(load_reading('Genesis 50')['next_chapter'],'Exodus 1')
        self.assertEqual(load_reading('Exodus 1')['previous_chapter'],'Genesis 50')
        self.assertIsNone(load_reading('Revelation 22')['next_chapter'])
        self.assertEqual(load_reading('Revelation 22')['previous_chapter'],'Revelation 21')
    def test_invalid_selection(self):
        for value in ['John 15:999','John 15:17–9','John 15–16','John 15:9–16:1']:
            with self.assertRaises(ValueError):load_reading(value)
    def test_reading_can_be_saved_before_generation_without_losing_notes(self):
        user=register('reader','test-password')['id']
        old={'label':'John 15:9–17','text':'Existing context','sources':[]}
        identity=save_study(user,'passage_result',old);update_notes(user,identity,'A durable observation');set_bookmark(user,identity,True)
        save_study(user,'passage_result',{**old,'reader':load_reading(old['label'])})
        row=get_study(user,identity);self.assertEqual(row['notes'],'A durable observation');self.assertTrue(row['bookmarked'])
        new=save_study(user,'passage_result',{'label':'John 16','text':'','reader':load_reading('John 16')})
        self.assertFalse(get_study(user,new)['payload']['text']);self.assertEqual(get_study(user,new)['notes'],'')

if __name__=='__main__':unittest.main()
