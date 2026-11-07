import json,tempfile,uuid
from pathlib import Path
from unittest.mock import patch
from django.test import SimpleTestCase,RequestFactory,override_settings
from django.contrib.auth.models import User,AnonymousUser
from transit import usability_admin as views
from transit.usability import connection

class AdminNavigationTests(SimpleTestCase):
    def test_authentication_and_staff_required(self):
        for user in [AnonymousUser(),User(is_active=True,is_staff=False),User(is_active=False,is_staff=True)]:
            request=RequestFactory().get('/admin/usability/');request.user=user
            response=views.sessions(request)
            self.assertEqual(response.status_code,302)
            self.assertIn('/admin/login/',response.url)
    @patch("transit.usability_admin.admin.site.each_context",return_value={"available_apps":[],"site_header":"Administração PaP","site_title":"PaP","has_permission":True})
    def test_list_details_player_and_missing_metadata(self,context):
        sid=uuid.uuid4()
        with tempfile.TemporaryDirectory() as folder,override_settings(PAP_USABILITY_DB=Path(folder)/'events.sqlite3',PAP_RESEARCH_DB=Path(folder)/'messages.sqlite3'):
            with connection() as db:
                db.execute('INSERT INTO events VALUES (?,?,?,?,?)',(str(sid),1,1,'session_start',json.dumps({'width':390,'height':844})))
                for seq,event in enumerate([{'type':4,'timestamp':1000,'data':{'width':390,'height':844}},{'type':2,'timestamp':1100,'data':{'node':{}}}],2):
                    db.execute('INSERT INTO events VALUES (?,?,?,?,?)',(str(sid),seq,seq,'trace',json.dumps({'payload':json.dumps({'kind':'visual','details':event})})))
            request=RequestFactory().get('/admin/usability/');request.user=User(is_active=True,is_staff=True,is_superuser=True)
            response=views.sessions(request);self.assertContains(response,str(sid));self.assertIn('no-store',response['Cache-Control'])
            response=views.detail(request,sid);self.assertContains(response,'não foram coletados');self.assertContains(response,'390');self.assertContains(response,'iframe')
            response=views.player(request,sid);self.assertContains(response,'rrwebPlayer');self.assertIn("connect-src 'none'",response['Content-Security-Policy'])
    @override_settings(ROOT_URLCONF='mbm.public_urls')
    def test_public_routes_excluded(self):
        from django.urls import resolve,Resolver404
        for path in ['/admin/usability/','/admin/usability/assets/player.js',f'/admin/usability/{uuid.uuid4()}/']:
            with self.assertRaises(Resolver404):resolve(path)

class SessionActionsTests(SimpleTestCase):
    @patch('transit.usability_admin.admin.site.each_context',return_value={})
    def test_export_confirmation_and_scoped_delete(self,context):
        import sqlite3
        sid,other=uuid.uuid4(),uuid.uuid4()
        with tempfile.TemporaryDirectory() as folder,override_settings(PAP_USABILITY_DB=Path(folder)/'events.sqlite3',PAP_RESEARCH_DB=Path(folder)/'messages.sqlite3'):
            with connection() as db:
                for identifier in [sid,other]:db.execute('INSERT INTO events VALUES (?,?,?,?,?)',(str(identifier),1,1,'action',json.dumps({'target':'lamp'})))
            def req(method='get',data=None,csrf=True):
                request=getattr(RequestFactory(),method)('/admin/usability/',data=data or {})
                request.user=User(is_active=True,is_staff=True,is_superuser=True)
                request._dont_enforce_csrf_checks=csrf
                return request
            response=views.export_json(req(),sid)
            self.assertEqual(json.loads(b''.join(response.streaming_content))['session'],str(sid))
            self.assertIn('attachment;',response['Content-Disposition'])
            with patch.object(views,'reconstruct',side_effect=AssertionError('cache não utilizado')):
                cached=views.export_json(req(),sid)
                self.assertEqual(json.loads(b''.join(cached.streaming_content))['session'],str(sid))
            self.assertContains(views.export_video(req(),sid),'Exportar vídeo WebM')
            self.assertContains(views.delete_session(req(),sid),'Confirmar exclusão')
            self.assertEqual(views.delete_session(req('post',{'confirm':'yes'},False),sid).status_code,403)
            self.assertEqual(views.delete_session(req('post'),sid).status_code,400)
            self.assertEqual(len(views.rows_for(sid)),1)
            self.assertEqual(views.delete_session(req('post',{'confirm':'yes'}),sid).status_code,302)
            with self.assertRaises(views.Http404):views.rows_for(sid)
            self.assertEqual(len(views.rows_for(other)),1)
    def test_actions_require_staff(self):
        for action in [views.export_json,views.export_video,views.delete_session]:
            request=RequestFactory().get('/admin/usability/');request.user=AnonymousUser()
            self.assertEqual(action(request,uuid.uuid4()).status_code,302)

    def test_video_job_authorization_and_csrf(self):
        from transit import replay_video
        sid=uuid.uuid4()
        def request(method='get',data=None,pk=1):
            r=getattr(RequestFactory(),method)('/admin/usability/',data=data or {})
            r.user=User(pk=pk,is_active=True,is_staff=True)
            return r
        self.assertEqual(views.export_video(request('post'),sid).status_code,403)
        r=request('post');r._dont_enforce_csrf_checks=True
        visual=[{'kind':'visual','details':{'type':2,'timestamp':1000,'data':{}}},{'kind':'visual','details':{'type':3,'timestamp':2000,'data':{}}}]
        with patch.object(views,'rows_for',return_value=[]),patch.object(views,'reconstruct',return_value=(visual,[])),patch.object(replay_video,'start',return_value='token') as start:
            response=views.export_video(r,sid)
            self.assertEqual(response.status_code,202)
            self.assertEqual(start.call_args.args[1],('1',str(sid)))
        with patch.object(views,'rows_for',return_value=[]),patch.dict(replay_video._jobs,{'a'*64:{'owner':('1',str(sid)),'state':'running'}},clear=True):
            self.assertEqual(json.loads(views.export_video(request(data={'job':'a'*64}),sid).content)['state'],'running')
            with self.assertRaises(views.Http404):views.export_video(request(data={'job':'a'*64},pk=2),sid)

    def test_video_cache_and_duplicate_job(self):
        from transit import replay_video as video
        with tempfile.TemporaryDirectory() as folder,override_settings(PAP_USABILITY_DB=Path(folder)/'events.sqlite3',PAP_RESEARCH_DB=Path(folder)/'messages.sqlite3'),patch.dict(video._jobs,{},clear=True),patch.object(video.threading,'Thread') as thread:
            owner=('1',str(uuid.uuid4()));key='version1'
            token=video.start([],owner,key)
            self.assertEqual(video.start([],owner,key),token)
            self.assertEqual(thread.call_count,1)
            job=video._jobs[token]
            job['destination'].write_bytes(b'webm')
            job['temp'].cleanup();video._jobs.clear()
            self.assertEqual(video.start([],owner,key),token)
            self.assertEqual(thread.call_count,1)
            self.assertEqual(video.get(token,owner)['state'],'ready')
            self.assertNotEqual(video.token_for(owner,'version2'),token)
