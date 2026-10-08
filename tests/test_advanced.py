import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from storage import register,save_study,get_study,update_notes
from advanced_study import (semantic_search,ask_sermon,TranscriptAnswer,Evidence,
                            validate_answer,chunks,cosine)


def fake_embed(texts, task):
    return [[1.0,0.0] if any(w in t.lower() for w in ['hope','trust','future']) else [0.0,1.0] for t in texts]


class AdvancedTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory()
        self.environment=patch.dict(os.environ,{'SCRIPTURE_DATA_DIR':self.directory.name})
        self.environment.start()
        self.user=register('advanced','test-password')['id']
        self.other=register('another','test-password')['id']

    def tearDown(self):
        self.environment.stop()
        self.directory.cleanup()

    def test_semantic_cache_and_account_scope(self):
        save_study(self.user,'passage_result',{'label':'Romans 8','text':'Hope and trust for the future.'})
        save_study(self.other,'passage_result',{'label':'Private hope','text':'Not this account.'})
        with patch('advanced_study.embed',side_effect=fake_embed) as embedding:
            hits=semantic_search(self.user,'trust')
            self.assertEqual(len(hits),1)
            self.assertEqual(hits[0]['title'],'Romans 8')
            first=embedding.call_count
            semantic_search(self.user,'future')
            self.assertEqual(embedding.call_count,first+1) # Query only; reuse document vectors.
            update_notes(self.user,hits[0]['id'],'A new personal reflection')
            semantic_search(self.user,'future')
            self.assertEqual(embedding.call_count,first+2) # Notes excluded by default.
            semantic_search(self.user,'future',include_notes=True)
            self.assertEqual(embedding.call_count,first+4) # Query + changed document.

    def test_answer_evidence_and_abstention(self):
        valid=TranscriptAnswer(answer='The speaker calls for trust.',insufficient_evidence=False,evidence=[Evidence(chunk=1,quote='Trust God with the future.')])
        self.assertFalse(validate_answer(valid,{1:'Trust God with the future.'})['insufficient_evidence'])
        with self.assertRaises(ValueError): validate_answer(valid,{1:'An unrelated statement.'})
        with self.assertRaises(ValueError): validate_answer(valid,{2:'Trust God with the future.'})
        no_evidence=TranscriptAnswer(answer='Invented',insufficient_evidence=False,evidence=[])
        with self.assertRaises(ValueError): validate_answer(no_evidence,{1:'Source'})
        unknown=TranscriptAnswer(answer='Invented extra claim',insufficient_evidence=True,evidence=[])
        self.assertNotIn('Invented',validate_answer(unknown,{})['answer'])

    def test_transcript_questions_never_use_another_account(self):
        identity=save_study(self.user,'sermon_result',{'label':'Sermon','source_url':'https://www.youtube.com/watch?v=dQw4w9WgXcQ','text':'Summary','transcript':'Trust God with the future.'})
        answer=TranscriptAnswer(answer='The speaker encourages trust.',insufficient_evidence=False,evidence=[Evidence(chunk=1,quote='Trust God with the future.')])
        with patch('advanced_study.embed',side_effect=fake_embed),patch('advanced_study.generate_json',return_value=answer) as generate:
            self.assertEqual(ask_sermon(self.user,identity,'What about trust?')['evidence'][0]['chunk'],1)
            self.assertEqual(generate.call_count,1)
            with self.assertRaises(ValueError): ask_sermon(self.other,identity,'What about trust?')
            self.assertEqual(generate.call_count,1)

    def test_chunk_and_similarity_checks(self):
        self.assertGreater(len(chunks('x'*3000)),1)
        self.assertAlmostEqual(cosine([1,0],[1,0]),1)
        with self.assertRaises(ValueError): cosine([1],[1,2])


if __name__=='__main__': unittest.main()
