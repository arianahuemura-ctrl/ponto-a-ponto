import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readSession, readFavorites, favoriteStop, readQuickDestinations, save, sessionKey, favoritesKey } from './spSession.js';
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


test('favoritos de endereços preservam coordenadas, sem contexto de viagem',()=>{
 const point={...stop,favoriteLabel:'Casa',manualBoarding:true,addressCoordinates:{lat:1,lon:2},destinationAddress:'Rua antiga',trip_id:'T'};
 const storage={getItem:()=>JSON.stringify([point,point])};
 assert.deepEqual(readFavorites(storage),[{kind:'location',id:'location:1,2',name:'Rua antiga',lat:1,lon:2,favoriteLabel:'Casa'}]);
});


test('localizações diferentes próximas da mesma parada não se confundem',()=>{
 const a=favoriteStop({...stop,addressCoordinates:{lat:-23.551,lon:-46.631}});
 const b=favoriteStop({...stop,addressCoordinates:{lat:-23.552,lon:-46.631}});
 assert.notEqual(a.id,b.id);
 assert.notEqual(a.id,stop.id);
 const storage={getItem:()=>JSON.stringify([stop,a,b,a])};
 assert.deepEqual(readFavorites(storage),[stop,a,b]);
});
test('GPS é salvo como coordenada fixa, sem acompanhar o passageiro',()=>{
 const saved=favoriteStop({id:'passenger-location',name:'Minha localização',lat:1,lon:2,addressCoordinates:{lat:1,lon:2},useLocation:true});
 assert.deepEqual(saved,{kind:'location',id:'location:1,2',name:'Minha localização',lat:1,lon:2});
 assert.deepEqual(favoriteStop(saved),saved);
 assert.deepEqual(readQuickDestinations({getItem:()=>JSON.stringify({home:saved.id})},[saved]),{home:saved.id});
});
test('não substitui uma coordenada inválida pela parada próxima',()=>{
 for(const point of [{lat:91,lon:1},{lat:0,lon:181},{lat:'1',lon:2},{lat:NaN,lon:2},{lat:1,lon:Infinity}]){
  assert.equal(favoriteStop({...stop,addressCoordinates:point}),null);
  assert.equal(favoriteStop({kind:'location',name:'Local',...point}),null);
 }
});
