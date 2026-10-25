import {test} from 'node:test';
import assert from 'node:assert/strict';
import {directedPath} from './routeDirection.js';
test('ida e volta ocupam lados distintos e apontam em sentidos opostos',()=>{
 const a=directedPath([{x:0,y:0},{x:200,y:0}]);
 const b=directedPath([{x:200,y:0},{x:0,y:0}]);
 assert.equal(a.path[0].y,4);assert.equal(b.path[0].y,-4);
 assert.equal(a.arrows[0].angle,0);assert.equal(Math.abs(b.arrows[0].angle),180);
 assert.equal(a.arrows.length,2);
});
test('pontos repetidos não produzem valores inválidos',()=>{
 const r=directedPath([{x:0,y:0},{x:0,y:0},{x:0,y:200}]);
 assert.ok(r.path.every(p=>Number.isFinite(p.x)&&Number.isFinite(p.y)));
 assert.equal(r.arrows[0].angle,90);
});
