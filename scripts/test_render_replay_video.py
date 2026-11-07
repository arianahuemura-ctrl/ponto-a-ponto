"""Integration: real Chromium and ffmpeg, synthetic data only."""
import json
from pathlib import Path
import subprocess
import tempfile
import time
import unittest

class RenderVideoTests(unittest.TestCase):
    def test_ten_minute_idle_session_preserves_timing(self):
        events=[{'type':4,'timestamp':1000,'data':{'width':320,'height':480}},
          {'type':2,'timestamp':1001,'data':{'node':{'type':0,'id':1,'childNodes':[{'type':2,'tagName':'html','attributes':{},'id':2,'childNodes':[{'type':2,'tagName':'body','attributes':{},'id':3,'childNodes':[{'type':3,'textContent':'Início','id':4}]}]}]},'initialOffset':{'left':0,'top':0}}},
          {'type':3,'timestamp':301000,'data':{'source':0,'texts':[{'id':4,'value':'Fim'}],'attributes':[],'removes':[],'adds':[]}},
          {'type':3,'timestamp':601000,'data':{'source':0,'texts':[],'attributes':[],'removes':[],'adds':[]}}]
        with tempfile.TemporaryDirectory() as folder:
            source=Path(folder)/'events.json';output=Path(folder)/'video.webm'
            source.write_text(json.dumps(events))
            start=time.monotonic()
            subprocess.run(['node',str(Path(__file__).with_name('render_replay_video.cjs')),str(source),str(output)],check=True,capture_output=True,timeout=30)
            self.assertLess(time.monotonic()-start,30)
            result=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-show_entries','frame=pts_time','-of','json',str(output)]))
            self.assertAlmostEqual(float(result['format']['duration']),600,places=2)
            self.assertEqual([float(f['pts_time']) for f in result['frames']],[0,300,600])
            self.assertFalse(list(Path(folder).glob('frames-*')))
