import {test} from 'node:test';
import assert from 'node:assert/strict';
import {parseCoordinates} from './coordinates.js';
test('coordenadas copiadas e separadores usuais',()=>{
 for(const s of ['-23.55900998451958, -46.73154360716584',' -23.55900998451958 -46.73154360716584 ','-23.55900998451958;-46.73154360716584'])assert.deepEqual(parseCoordinates(s),{lat:-23.55900998451958,lon:-46.73154360716584});
 assert.deepEqual(parseCoordinates('0, 0'),{lat:0,lon:0});
});
test('não interpreta endereços como coordenadas',()=>{
 for(const s of ['Av. Paulista, 171','Rua 25 de Março','-23.55',''])assert.equal(parseCoordinates(s),null);
});
test('rejeita coordenadas fora dos limites',()=>{
 for(const s of ['91, 0','0, -181','-90.1, 20'])assert.ok(parseCoordinates(s).error);
 assert.deepEqual(parseCoordinates('-90, 180'),{lat:-90,lon:180});
});
