import test from 'node:test';
import assert from 'node:assert/strict';
import {retainLive} from './liveRetention.js';
test('preserva duas falhas, descarta na terceira e reinicia após sucesso',()=>{
 const keep=retainLive(),a={observed_at:'original'},empty={arrivals:[]};
 assert.equal(keep(a,true),a);
 assert.equal(keep(empty,false),a);
 assert.equal(keep(empty,false),a);
 assert.equal(keep(empty,false),empty);
 assert.equal(keep(a,true),a);
 assert.equal(keep(empty,false),a);
 assert.equal(a.observed_at,'original');
});
test('contagens são independentes e não inventam dados antes do primeiro sucesso',()=>{
 const first=retainLive(),second=retainLive();
 assert.equal(first(null,false),null);
 first('ok',true);
 assert.equal(second(null,false),null);
 assert.equal(first(null,false),'ok');
});
