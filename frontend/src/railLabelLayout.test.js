import test from 'node:test';
import assert from 'node:assert/strict';
import {placeRailLabels,crossesBox,overlaps,labelBox} from './railLabelLayout.js';
import {railMapLabel} from './railStyle.js';

test('map names identify metro colors and numbered CPTM lines, including legacy codes',()=>{
  assert.equal(railMapLabel({route_id:'L4',mode:'metro'}),'Metrô Linha Amarela');
  assert.equal(railMapLabel({code:'METRÔ L2',mode:'metro'}),'Metrô Linha Verde');
  assert.equal(railMapLabel({code:'CPTM L012',mode:'rail'}),'CPTM Linha 12 Safira');
  assert.equal(railMapLabel({route_id:'opaque-id',code:'CPTM L012',mode:'rail'}),'CPTM Linha 12 Safira');
  assert.equal(railMapLabel({code:'LX',mode:'metro'}),'LX');
});

test('labels and their leaders leave the passenger clear at a rail crossing',()=>{
  const geometry=[{x:10,y:10},{x:790,y:590}];
  const passenger=labelBox({x:400,y:300},68,68);
  const placed=placeRailLabels([{width:160,geometries:[geometry]}],{width:800,height:600,obstacles:[passenger]});
  assert.ok(placed.length);
  for(const item of placed){
    assert.equal(overlaps(item.box,passenger),false);
    assert.equal(crossesBox(...geometry,item.box),false);
    assert.equal(crossesBox(item.anchor,item.edge,passenger),false);
  }
});

test('parallel lines retain distinct, unclipped names on a narrow viewport',()=>{
  const lines=[160,260].map(x=>({width:126,height:46,geometries:[[{x,y:-400},{x,y:1200}]]}));
  const placed=placeRailLabels(lines,{width:390,height:600});
  assert.equal(new Set(placed.map(p=>p.line)).size,2);
  for(const p of placed){
    assert.ok(p.box.left>=12&&p.box.right<=378&&p.box.top>=16&&p.box.bottom<=584);
    for(const line of lines)assert.equal(crossesBox(...line.geometries[0],p.box),false);
  }
  for(let i=0;i<placed.length;i++)for(let j=i+1;j<placed.length;j++)assert.equal(overlaps(placed[i].box,placed[j].box),false);
});

test('an obstructed viewport omits labels instead of covering a point or control',()=>{
  const placed=placeRailLabels([{width:150,geometries:[[{x:0,y:150},{x:300,y:150}]]}],
    {width:300,height:300,obstacles:[{left:0,right:300,top:0,bottom:300}]});
  assert.deepEqual(placed,[]);
});

test('a long line and repeated branches receive only one name in the viewport',()=>{
  const yellow={label:'Metrô Linha Amarela',width:160,geometries:[[{x:0,y:180},{x:1200,y:180}],[{x:0,y:220},{x:1200,y:220}]]};
  const green={label:'Metrô Linha Verde',width:150,geometries:[[{x:0,y:550},{x:1200,y:550}]]};
  const placed=placeRailLabels([yellow,{...yellow},green],{width:1200,height:800});
  assert.deepEqual(placed.map(p=>p.line.label).sort(),[yellow.label,green.label].sort());
});

test('all known rail numbers use the same display format',()=>{
  for(const [n,name] of [[1,'Azul'],[2,'Verde'],[3,'Vermelha'],[4,'Amarela'],[5,'Lilás'],[6,'Laranja'],[15,'Prata'],[17,'Ouro']])
    assert.equal(railMapLabel({route_id:`L${n}`,mode:'metro'}),`Metrô Linha ${name}`);
  for(const [n,name] of [[7,'Rubi'],[8,'Diamante'],[9,'Esmeralda'],[10,'Turquesa'],[11,'Coral'],[12,'Safira'],[13,'Jade']])
    assert.equal(railMapLabel({route_id:`L${n}`,mode:'rail'}),`CPTM Linha ${n} ${name}`);
});
