import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readSession, readFavorites, save, sessionKey, favoritesKey } from './spSession.js';
const stop={id:'1',name:'Ponto',lat:-23.5,lon:-46.6};
test('sessão e favoritos ficam em espaços separados e toleram corrupção',()=>{
  const values=new Map();const storage={getItem:key=>values.get(key),setItem:(key,value)=>values.set(key,value)};
  assert.equal(save(storage,sessionKey,{origin:stop,destination:stop}),true);
  assert.equal(readSession(storage).destination.id,'1');
  save(storage,favoritesKey,[stop,{id:'invalid'}]);
  assert.deepEqual(readFavorites(storage),[stop]);
  values.set(sessionKey,'invalid');assert.equal(readSession(storage).destination,null);
});
test('armazenamento bloqueado não interrompe navegação',()=>{
  const storage={getItem(){throw Error();},setItem(){throw Error();}};
  assert.equal(readSession(storage).origin,null);
  assert.deepEqual(readFavorites(storage),[]);
  assert.equal(save(storage,sessionKey,{}),false);
});
test('limite de trocas é restaurado e valores inválidos usam o padrão',()=>{
  const storage={getItem:()=>JSON.stringify({origin:stop,destination:stop,maxTransfers:1})};
  assert.equal(readSession(storage).maxTransfers,1);
  assert.equal(readSession({getItem:()=>JSON.stringify({maxTransfers:99})}).maxTransfers,2);
});
test('URL sem stop prevalece sobre origem e destino da sessão',()=>{
 const storage={getItem:()=>JSON.stringify({origin:stop,destination:{...stop,id:'2'},maxTransfers:1})};
 for(const url of ['', '?', '?stop=', '?outro=1', '?stop=99']){
  const session=readSession(storage,url);
  assert.equal(session.origin,null);
  assert.equal(session.destination,null);
 }
 assert.equal(readSession(storage,'?stop=1').origin.id,'1');
 assert.equal(readSession(storage,'?stop=1').destination,null);
});


test('favoritos guardam apenas pontos únicos, sem contexto de viagem',()=>{
 const point={...stop,favoriteLabel:'Casa',manualBoarding:true,addressCoordinates:{lat:1,lon:2},destinationAddress:'Rua antiga',trip_id:'T'};
 const storage={getItem:()=>JSON.stringify([point,point])};
 assert.deepEqual(readFavorites(storage),[{...stop,favoriteLabel:'Casa'}]);
});
