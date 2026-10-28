import test from 'node:test';
import assert from 'node:assert/strict';
import {apiProgressive} from './api.js';
for(const format of ['text/event-stream','application/x-ndjson']){
  test(`entrega incremental ${format} antes do encerramento`,async t=>{
    let controller,received;
    const firstReceived=new Promise(resolve=>{received=resolve;});
    const encoder=new TextEncoder(),results=[];
    const stream=new ReadableStream({start(c){controller=c;}});
    t.mock.method(globalThis,'fetch',async(url,options)=>{
      assert.match(options.headers.Accept,/text\/event-stream/);
      return new Response(stream,{headers:{'Content-Type':format}});
    });
    const running=apiProgressive('sptrans/board',{stream:1},new AbortController().signal,result=>{results.push(result);received();});
    const wrap=row=>format==='text/event-stream'?`data: ${JSON.stringify(row)}\n\n`:`${JSON.stringify(row)}\n`;
    const first=wrap({complete:false,journeys:[{mode:'walk',name:'A pé'}]});
    controller.enqueue(encoder.encode(first.slice(0,9)));
    controller.enqueue(encoder.encode(first.slice(9)));
    await firstReceived;
    assert.equal(results.length,1);assert.equal(results[0].complete,false);
    controller.enqueue(encoder.encode(wrap({complete:true,journeys:[]})));
    controller.close();await running;
    assert.equal(results[1].complete,true);
  });
}
test('erro SSE é apresentado ao consumidor',async t=>{
  t.mock.method(globalThis,'fetch',async()=>new Response('data: {"error":"Falha no cálculo"}\n\n',{headers:{'Content-Type':'text/event-stream'}}));
  await assert.rejects(apiProgressive('sptrans/board',{},new AbortController().signal,()=>{}),/Falha no cálculo/);
});
