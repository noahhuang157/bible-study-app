"""Run with: python -m unittest discover -s tests -v"""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from storage import (register,authenticate,save_study,get_study,list_studies,
                     update_notes,set_bookmark,export_backup,connect)


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.environment = patch.dict(os.environ,{'SCRIPTURE_DATA_DIR':self.directory.name})
        self.environment.start()
        self.user = register('noah','a-test-password')
        self.other = register('another','another-password')
        self.result = {'label':'Romans 8:28','text':'Background','sources':[]}

    def tearDown(self):
        self.environment.stop()
        self.directory.cleanup()

    def test_passwords_and_authentication(self):
        self.assertEqual(authenticate('NOAH','a-test-password'),self.user)
        self.assertIsNone(authenticate('noah','wrong-password'))
        self.assertIsNone(authenticate('unknown','a-test-password'))
        with self.assertRaises(ValueError): register('noah','different-password')
        with connect() as db:
            rows = db.execute('SELECT password_salt,password_hash FROM users').fetchall()
        self.assertNotEqual(rows[0]['password_salt'],rows[1]['password_salt'])
        self.assertNotEqual(rows[0]['password_hash'],b'a-test-password')

    def test_account_isolation(self):
        identity=save_study(self.user['id'],'passage_result',self.result)
        self.assertIsNone(get_study(self.other['id'],identity))
        update_notes(self.other['id'],identity,'Should not overwrite')
        set_bookmark(self.other['id'],identity,True)
        self.assertEqual(get_study(self.user['id'],identity)['notes'],'')
        self.assertFalse(get_study(self.user['id'],identity)['bookmarked'])
        self.assertEqual(list_studies(self.other['id']),[])
        self.assertEqual(json.loads(export_backup(self.other['id']))['studies'],[])

    def test_regeneration_retains_notes_and_bookmarks(self):
        identity=save_study(self.user['id'],'passage_result',self.result)
        update_notes(self.user['id'],identity,'My reflection')
        set_bookmark(self.user['id'],identity,True)
        save_study(self.user['id'],'passage_result',{**self.result,'text':'Updated background'})
        record=get_study(self.user['id'],identity)
        self.assertEqual(record['notes'],'My reflection')
        self.assertTrue(record['bookmarked'])
        self.assertEqual(record['payload']['text'],'Updated background')
        self.assertEqual(len(list_studies(self.user['id'])),1)

    def test_search_filters_and_export(self):
        identity=save_study(self.user['id'],'passage_result',self.result)
        update_notes(self.user['id'],identity,'Faith and hope')
        set_bookmark(self.user['id'],identity,True)
        save_study(self.user['id'],'word_result',{'query':'love','entry':{},'passage':'John 15'})
        self.assertEqual(len(list_studies(self.user['id'],query='hope')),1)
        self.assertEqual(len(list_studies(self.user['id'],kind='word_result')),1)
        self.assertEqual(len(list_studies(self.user['id'],bookmarked_only=True)),1)
        self.assertEqual(list_studies(self.user['id'],query="' OR 1=1 --"),[])
        backup=export_backup(self.user['id'])
        self.assertEqual(len(json.loads(backup)['studies']),2)
        self.assertNotIn('password',backup)
        self.assertNotIn('user_id',backup)


if __name__ == '__main__':
    unittest.main()
