import json,os,sys,threading,unittest
from pathlib import Path
from unittest.mock import patch
import httpx
from google import genai
from google.genai.types import HttpOptions
from pydantic import BaseModel
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from advanced_study import generate_json,embed
from service_errors import describe_error
from word_study import search_entries,occurrences,connect,passage_material
from word_alignment import aligned_html
from word_explanation import ClearWordMeaning,MeaningEvidence,generate_word_meaning

class Answer(BaseModel):
    text:str

class ClientLifecycleTests(unittest.TestCase):
    def test_real_sdk_in_worker_thread_makes_requests_and_closes_afterwards(self):
        original=genai.Client
        requests=[];clients=[];errors=[]
        def handle(request):
            requests.append(request)
            if 'EmbedContents' in request.url.path:
                return httpx.Response(200,json={'embeddings':[{'values':[1.0,0.0]}]})
            return httpx.Response(200,json={'candidates':[{'content':{'role':'model','parts':[{'text':'{"text":"Success"}'}]}}]})
        def factory(**kwargs):
            self.assertFalse(kwargs['vertexai'])
            self.assertEqual(kwargs['http_options'].timeout,90000)
            c=original(api_key=kwargs['api_key'],vertexai=False,http_options=HttpOptions(
                client_args={'transport':httpx.MockTransport(handle),'trust_env':False},
                async_client_args={'trust_env':False}))
            # Keep HTTP transport for inspection, without retaining the parent Client.
            clients.append(c._api_client._httpx_client)
            return c
        def task():
            try:
                self.assertEqual(generate_json('test',Answer).text,'Success')
                self.assertEqual(generate_json('test again',Answer).text,'Success')
                self.assertEqual(embed(['test'],'RETRIEVAL_QUERY'),[[1.0,0.0]])
            except BaseException as e:errors.append(e)
        with patch.dict(os.environ,{'GEMINI_API_KEY':'dummy-test-key','GOOGLE_GENAI_USE_VERTEXAI':'true'}),patch('gemini_service.genai.Client',side_effect=factory):
            thread=threading.Thread(target=task);thread.start();thread.join()
        if errors:raise errors[0]
        self.assertEqual(len(requests),3)
        self.assertTrue(all(c.is_closed for c in clients))
    def test_missing_key_and_safe_runtime_diagnostic(self):
        with patch.dict(os.environ,{'GEMINI_API_KEY':''}):
            with self.assertRaisesRegex(ValueError,'Streamlit'):generate_json('test',Answer)
        with patch.dict(os.environ,{'GEMINI_API_KEY':'secret-credential'}):
            _,details=describe_error(RuntimeError('Cannot send a request, as the client has been closed. secret-credential https://example.test/?key=private'))
        self.assertIn('client has been closed',details)
        self.assertNotIn('secret-credential',details)
        self.assertNotIn('https://',details)

class WordClarityTests(unittest.TestCase):
    def guide(self,material):
        return ClearWordMeaning(plain_meaning='A person who tells others what they know or have experienced, giving testimony about it.',
            contextual_meaning='The disciples are assigned to testify about Jesus.',why_this_meaning='The commission connects their testimony with the promised power.',
            other_senses=[],caution='The word alone does not establish martyrdom.',references=['Acts 1:8'],
            simple_example='A person describing an event they know about gives testimony.',
            evidence=[MeaningEvidence(reference='Acts 1:8',quote=material['selected'][0]['text'])])
    def test_clarity_prompt_and_checked_evidence(self):
        entry=search_entries('G3144')[0][0];material=passage_material('Acts 1:8',entry);guide=self.guide(material)
        with patch('word_explanation.generate_json',return_value=guide) as generate:
            result=generate_word_meaning({'entry':entry,'passage_data':material,'reader_question':'Explain without theological jargon.'})
            self.assertEqual(result['meaning_version'],2)
            self.assertIn('without theological jargon',generate.call_args.args[0])
            guide.evidence[0].quote='An invented quotation not in the chapter.'
            with self.assertRaisesRegex(ValueError,'excerpt'):generate_word_meaning({'entry':entry,'passage_data':material})
            guide.evidence=[]
            with self.assertRaisesRegex(ValueError,'excerpts'):generate_word_meaning({'entry':entry,'passage_data':material})
    def test_one_word_or_repetitive_definition_rejected(self):
        entry=search_entries('G3144')[0][0];material=passage_material('Acts 1:8',entry);guide=self.guide(material)
        guide.plain_meaning='witness '*15
        with patch('word_explanation.generate_json',return_value=guide):
            with self.assertRaisesRegex(ValueError,'repetitive'):generate_word_meaning({'entry':entry,'passage_data':material})
    def test_alignment_is_tag_based_not_english_matching(self):
        entry=search_entries('G3144')[0][0]
        rows=occurrences(entry,book=44,limit=15,aligned=True)['verses']
        self.assertTrue(rows)
        for row in rows:
            matched=[t for t in row['aligned_tokens'] if t['matched']]
            self.assertTrue(matched)
            with connect() as db:
                for t in matched:
                    self.assertTrue(db.execute('SELECT 1 FROM tags WHERE token_id=? AND lemma=?',(t['id'],entry['lemma_id'])).fetchone())
            self.assertEqual(aligned_html(row['aligned_tokens']).count('<mark '),len(matched))
        fake=[{'surface':'λόγος','gloss':'a saying','matched':True},{'surface':'ἄλλος','gloss':'word','matched':False}]
        html=aligned_html(fake)
        self.assertIn('a saying</span></mark>',html)
        self.assertIn('word</span></span>',html)
        self.assertNotIn('word</span></mark>',html)
    def test_hebrew_gloss_pairing_and_html_escaping(self):
        entry=search_entries('H530')[0][0]
        row=occurrences(entry,limit=1,aligned=True)['verses'][0]
        self.assertTrue(any(t['matched'] for t in row['aligned_tokens']))
        self.assertIn('dir="rtl"',aligned_html(row['aligned_tokens'],hebrew=True))
        html=aligned_html([{'surface':'<script>','gloss':'<img>','matched':True}])
        self.assertNotIn('<script>',html);self.assertIn('&lt;script&gt;',html)

if __name__=='__main__':unittest.main()
