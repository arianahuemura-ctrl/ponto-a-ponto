import json,os,unittest
from types import SimpleNamespace
from unittest.mock import patch
import public_instance as public

class DiscoveryTests(unittest.TestCase):
    def output(self,*args):
        if args[0]=='ps':return SimpleNamespace(stdout='abc\n',stderr='')
        if args[0]=='inspect':return SimpleNamespace(stdout=json.dumps('cloudflare/cloudflared:latest')+'|'+json.dumps(['tunnel','--url','http://127.0.0.1:8001'])+'|2026-10-20T00:00:00Z',stderr='')
        return SimpleNamespace(stdout='',stderr='URL https://new-test.trycloudflare.com')
    @patch.object(public,'docker_output')
    def test_running_tunnel(self,docker):
        docker.side_effect=self.output
        self.assertEqual(public.discover_host(),'new-test.trycloudflare.com')
        self.assertIn('--since',docker.call_args.args)
    @patch.object(public,'docker_output')
    def test_ignores_development_tunnel(self,docker):
        docker.side_effect=lambda *args: SimpleNamespace(stdout=self.output(*args).stdout.replace('8001','8000'),stderr='')
        self.assertIsNone(public.discover_host())
    @patch.dict(os.environ,{'PAP_PUBLIC_HOST':'chosen.example.com'})
    @patch.object(public,'discover_host')
    def test_explicit_host_wins(self,discover):
        self.assertEqual(public.desired_host(None),'chosen.example.com');discover.assert_not_called()
    @patch.dict(os.environ,{'PAP_PUBLIC_HOST':'https://invalid.example/'})
    def test_invalid_host_rejected(self):
        with self.assertRaises(SystemExit):public.desired_host(None)
    @patch.dict(os.environ,{'PAP_PUBLIC_HOST':''})
    @patch.object(public,'running_host',return_value='old.example.com')
    @patch.object(public,'discover_host',return_value='new.trycloudflare.com')
    def test_new_tunnel_replaces_old_host(self,*mocks):
        self.assertEqual(public.desired_host({}),'new.trycloudflare.com')
    @patch.object(public,'docker_output')
    def test_missing_url_fails_without_guessing(self,docker):
        docker.side_effect=lambda *args:self.output(*args) if args[0]!='logs' else SimpleNamespace(stdout='',stderr='')
        with self.assertRaises(SystemExit):public.discover_host()
if __name__=='__main__':unittest.main()
