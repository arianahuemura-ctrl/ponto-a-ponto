import json
import sqlite3
import tempfile
import time
import uuid
from pathlib import Path
from unittest.mock import patch
from django.core import signing
from django.test import SimpleTestCase, Client, override_settings
from transit.research import PROOF_SALT
from transit.usability import SALT

class ResearchTests(SimpleTestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory();self.addCleanup(self.folder.cleanup)
        self.root=Path(self.folder.name)
        self.override=override_settings(PAP_USABILITY_DB=self.root/'events.sqlite3',PAP_RESEARCH_DB=self.root/'messages.sqlite3')
        self.override.enable();self.addCleanup(self.override.disable)
    def post(self,path,data,client=None,**kw):return (client or self.client).post('/api/research/'+path+'/',json.dumps(data),content_type='application/json',**kw)
    def feedback(self,**kw):return {'id':str(uuid.uuid4()),'category':'problema','message':'Exemplo artificial',**kw}
    def test_feedback_without_research_creates_no_telemetry_database(self):
        data=self.feedback();self.assertEqual(self.post('feedback',data).status_code,201)
        self.assertFalse((self.root/'events.sqlite3').exists())
        with sqlite3.connect(self.root/'messages.sqlite3') as db:
            stored=json.loads(db.execute('SELECT data FROM messages').fetchone()[0])
        self.assertEqual(stored,{'category':'problema','message':'Exemplo artificial','session':None})
    def test_idempotency_and_collision(self):
        data=self.feedback();self.assertEqual(self.post('feedback',data).status_code,201)
        self.assertEqual(self.post('feedback',data).status_code,200)
        self.assertEqual(self.post('feedback',{**data,'message':'Outro'}).status_code,409)
    def test_csrf_and_info_do_not_start_session(self):
        c=Client(enforce_csrf_checks=True);info=c.get('/api/research/info/').json()
        self.assertNotIn('session',info);self.assertFalse((self.root/'events.sqlite3').exists())
        self.assertFalse((self.root/'messages.sqlite3').exists())
        self.assertEqual(self.post('feedback',self.feedback(),c).status_code,403)
        self.assertEqual(self.post('feedback',self.feedback(),c,HTTP_X_CSRFTOKEN=info['csrf']).status_code,201)
    def test_feedback_links_only_verified_session(self):
        session=str(uuid.uuid4());token=signing.dumps(session,salt=SALT)
        r=self.post('feedback',self.feedback(token=token));self.assertTrue(r.json()['linked'])
        from transit.research import linked_feedback
        self.assertEqual(len(linked_feedback(session)),1)
        self.assertEqual(self.post('feedback',self.feedback(token='forged')).status_code,400)
    def test_privacy_request_is_not_a_delete_and_proofs_cannot_read_data(self):
        info=self.client.get('/api/usability/').json()
        self.client.post('/api/usability/',json.dumps({'token':info['token'],'events':[{'seq':1,'type':'action','data':{'target':'lamp'}}]}),content_type='application/json')
        request={'id':str(uuid.uuid4()),'kind':'deletion','message':'Excluir sessão artificial','proofs':[info['deletion_proof']]}
        self.assertEqual(self.post('requests',request).status_code,201)
        self.assertEqual(self.post('requests',request).status_code,200)
        with sqlite3.connect(self.root/'events.sqlite3') as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM events').fetchone()[0],1)
        self.assertEqual(self.post('requests',{**request,'id':str(uuid.uuid4()),'proofs':[info['session']]}).status_code,400)
        self.assertEqual(self.client.get('/admin/research/').status_code,302)
    def test_validation_limits_and_storage_failure(self):
        for changes in [{'id':42},{'id':[]},{'token':{}},{'message':''},{'message':'x'*2001},{'category':'other'},{'extra':True}]:self.assertEqual(self.post('feedback',self.feedback(**changes)).status_code,400)
        with override_settings(PAP_RESEARCH_MESSAGES_PER_MINUTE=1):
            self.assertEqual(self.post('feedback',self.feedback()).status_code,201)
            self.assertEqual(self.post('feedback',self.feedback()).status_code,429)
        with patch('transit.research.connect',side_effect=sqlite3.OperationalError):self.assertEqual(self.post('feedback',self.feedback()).status_code,503)
    def test_public_instance_has_contact_but_not_admin(self):
        with override_settings(ROOT_URLCONF='mbm.public_urls'):
            self.assertEqual(self.client.get('/api/research/info/').status_code,200)
            self.assertEqual(self.client.get('/admin/research/').status_code,404)
    def test_retention_contract_on_artificial_records_only(self):
        from transit.usability import connection
        from scripts.telemetry_storage import encode,collect,block_size
        session=str(uuid.uuid4());db=connection()
        with db:
            db.execute('INSERT INTO events VALUES (?,?,?,?,?)',(session,1,time.time()-31*86400,'trace',encode(db,session,'x'*3000)))
            db.execute('INSERT INTO events VALUES (?,?,?,?,?)',(session,2,time.time(),'action','{"target":"lamp"}'))
            db.execute('DELETE FROM events WHERE received<?',(time.time()-30*86400,));collect(db)
        self.assertGreater(block_size(db,session),0)  # documented: blocks survive a partially expired session
        cache=self.root/'exports'/session;cache.mkdir(parents=True);(cache/'fake.webm').write_bytes(b'artificial')
        with db:db.execute('DELETE FROM events WHERE session=?',(session,));collect(db)
        self.assertEqual(block_size(db,session),0);self.assertTrue((cache/'fake.webm').exists())
        db.close()  # cache isn't removed by ingest; notice must not promise otherwise

    @patch('transit.research.admin.site.each_context',return_value={})
    def test_admin_message_review_requires_confirmation_and_can_remove_message(self,context):
        from django.test import RequestFactory
        from django.contrib.auth.models import User
        from transit.research import inbox
        data=self.feedback(message='<script>exemplo artificial</script>');self.post('feedback',data)
        def request(method='get',payload=None):
            r=getattr(RequestFactory(),method)('/admin/research/',data=payload or {})
            r.user=User(is_active=True,is_staff=True,is_superuser=True);r._dont_enforce_csrf_checks=True
            return r
        self.assertContains(inbox(request()),'&lt;script&gt;')
        self.assertEqual(inbox(request('post',{'id':data['id']})).status_code,400)
        self.assertContains(inbox(request('post',{'id':data['id'],'confirm':'yes'})),'Analisada')
        self.assertContains(inbox(request('post',{'id':data['id'],'confirm':'yes','action':'delete'})),'Nenhuma mensagem.')
        self.assertFalse((self.root/'events.sqlite3').exists())
