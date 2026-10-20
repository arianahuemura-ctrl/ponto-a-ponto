import json,unittest
from export_replay import reconstruct
class ReconstructionTests(unittest.TestCase):
    def test_reassembles_out_of_order_fragments_and_reports_incomplete(self):
        value=json.dumps({'kind':'visual','details':{'type':2,'timestamp':1000,'data':{'node':'teste'}}})
        def row(seq,id,index,total,text):return (seq,0,'trace',json.dumps({'payload':json.dumps({'kind':'chunk','id':id,'index':index,'total':total,'text':text})}))
        rows=[row(3,'ok',1,2,value[20:]),row(2,'ok',0,2,value[:20]),row(4,'missing',0,2,'x')]
        events,missing=reconstruct(rows)
        self.assertEqual(events,[{'seq':2,**json.loads(value)}]);self.assertEqual(missing,['missing'])
    def test_preserves_basic_and_trace_in_sequence(self):
        rows=[(2,1,'trace',json.dumps({'payload':json.dumps({'kind':'input','details':{'value':'São Paulo'}})})),(1,0,'action',json.dumps({'target':'lamp'}))]
        events,missing=reconstruct(rows)
        self.assertEqual([e['seq'] for e in events],[1,2]);self.assertEqual(events[1]['details']['value'],'São Paulo');self.assertFalse(missing)
if __name__=='__main__':unittest.main()
