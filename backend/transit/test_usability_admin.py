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
        with tempfile.TemporaryDirectory() as folder,override_settings(PAP_USABILITY_DB=Path(folder)/'events.sqlite3'):
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
