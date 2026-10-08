import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from datetime import date
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from storage import register,export_backup
from memorization import (add_card,list_cards,remove_card,review_card,memory_stats,
                          check_recall,hidden_words,export_deck,next_interval)


def reading(code='WEB'):
    return {'selected':[{'verse':8,'text':'Secret licensed text.'}], 'chapter_reference':'Acts 1',
            'translation_code':code,'book':44,'chapter_number':1}

class MemoryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.env=patch.dict(os.environ,{'SCRIPTURE_DATA_DIR':self.temp.name});self.env.start()
        self.day=patch('memorization.today',return_value=date(2026,10,8));self.day.start()
        self.user=register('memory','test-password')['id']
        self.other=register('other','test-password')['id']
    def tearDown(self):
        self.day.stop();self.env.stop();self.temp.cleanup()
    def test_duplicate_retains_progress_and_versions_are_distinct(self):
        identity,created=add_card(self.user,reading(),'Witness');self.assertTrue(created)
        review_card(self.user,identity,'Good','attempt1')
        repeated,created=add_card(self.user,reading(),'Mission');self.assertFalse(created)
        self.assertEqual(identity,repeated)
        row=list_cards(self.user)[0]
        self.assertEqual(row['reviews'],1);self.assertEqual(row['due_date'],'2026-10-09')
        self.assertEqual(row['collection'],'Mission')
        self.assertNotEqual(add_card(self.user,reading('NIV'))[0],identity)
    def test_account_isolation_and_idempotent_review(self):
        identity,_=add_card(self.user,reading())
        self.assertEqual(list_cards(self.other),[])
        with self.assertRaises(ValueError):review_card(self.other,identity,'Easy','attempt1')
        remove_card(self.other,identity);self.assertEqual(len(list_cards(self.user)),1)
        self.assertTrue(review_card(self.user,identity,'Easy','attempt1'))
        self.assertFalse(review_card(self.user,identity,'Easy','attempt1'))
        self.assertEqual(list_cards(self.user)[0]['reviews'],1)
        self.assertEqual(list_cards(self.user)[0]['due_date'],'2026-10-11')
    def test_streak_due_and_removal(self):
        identity,_=add_card(self.user,reading())
        self.assertEqual(memory_stats(self.user)['due'],1)
        review_card(self.user,identity,'Again','attempt1')
        self.assertEqual(memory_stats(self.user),{'total':1,'due':0,'reviewed_today':1,'streak':1})
        with patch('memorization.today',return_value=date(2026,10,9)):
            self.assertEqual(memory_stats(self.user)['streak'],1)
            self.assertEqual(memory_stats(self.user)['due'],1)
            review_card(self.user,identity,'Good','attempt2')
            self.assertEqual(memory_stats(self.user)['streak'],2)
        with patch('memorization.today',return_value=date(2026,10,11)):
            self.assertEqual(memory_stats(self.user)['streak'],0)
        remove_card(self.user,identity)
        self.assertEqual(memory_stats(self.user)['total'],0)
        self.assertEqual(memory_stats(self.user)['reviewed_today'],0)
    def test_licensed_text_never_persisted_or_exported(self):
        add_card(self.user,reading('NIV'))
        data=export_deck(self.user)
        self.assertNotIn('Secret licensed text',data);self.assertNotIn('user_id',data)
        backup=json.loads(export_backup(self.user))
        self.assertEqual(backup['memory_deck']['cards'][0]['translation'],'NIV')
        self.assertEqual(json.loads(export_deck(self.other))['cards'],[])
    def test_short_ranges_and_bridge(self):
        r=reading();r['selected']=[{'verse':8,'verse_end':10,'text':'bridge'}]
        identity,_=add_card(self.user,r)
        self.assertEqual(list_cards(self.user)[0]['reference'],'Acts 1:8–10')
        r['selected']=[{'verse':8,'verse_end':13}]
        with self.assertRaises(ValueError):add_card(self.user,r)
    def test_recall_and_hints(self):
        self.assertTrue(check_recall('You ARE my witnesses!', 'You are my witnesses.')['exact'])
        self.assertTrue(check_recall("Don't fear",'Don’t fear.')['exact'])
        self.assertFalse(check_recall('You are witnesses','You are my witnesses')['exact'])
        self.assertLess(check_recall('You are my witnesses extra','You are my witnesses')['score'],100)
        with self.assertRaises(ValueError):check_recall('   ','Verse')
        self.assertEqual(hidden_words('One two three, four.', 'Some words'),'One two ＿＿＿＿＿, four.')
        self.assertNotIn('One',hidden_words('One two three.','All words'))
    def test_intervals_are_bounded_and_unknown_rating_rejected(self):
        self.assertEqual(next_interval(14,'Again'),1)
        self.assertLess(next_interval(14,'Hard'),next_interval(14,'Good'))
        self.assertLess(next_interval(14,'Good'),next_interval(14,'Easy'))
        self.assertEqual(next_interval(100,'Easy'),180)
        with self.assertRaises(ValueError):next_interval(0,'Unknown')

if __name__=='__main__':unittest.main()
