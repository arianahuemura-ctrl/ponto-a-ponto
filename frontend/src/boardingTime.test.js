import test from 'node:test';
import assert from 'node:assert/strict';
import {boardingMinutes} from './boardingTime.js';
const now=Date.parse('2026-10-07T06:38:00-03:00');
const prediction=(time,observed_at='2026-10-07T06:37:50-03:00')=>({time,observed_at});
test('countdown uses live arrival, not scheduled departure, and decreases',()=>{
 const arrivals=[prediction('06:45'),prediction('06:43')];
 assert.equal(boardingMinutes(arrivals,now),5);
 assert.equal(boardingMinutes(arrivals,now+60000),4);
 assert.equal(boardingMinutes([],now),null);
});
test('expired, stale and malformed predictions are omitted',()=>{
 assert.equal(boardingMinutes([prediction('06:30'),prediction('08:00','2026-10-07T06:00:00-03:00'),prediction('99:99')],now),null);
 assert.equal(boardingMinutes([prediction('06:38')],now+10000),0);
});
test('midnight is anchored to observation and does not resurrect old arrivals',()=>{
 const observation='2026-10-07T23:59:00-03:00';
 assert.equal(boardingMinutes([prediction('00:04',observation)],Date.parse(observation)),5);
 assert.equal(boardingMinutes([prediction('23:58',observation)],Date.parse('2026-10-08T00:01:00-03:00')),null);
});
test('13.5 minute access walk excludes the bus in 3 minutes and rounding does not make it reachable',()=>{
 const arrivals=[prediction('06:41'),prediction('06:51'),prediction('06:52')];
 assert.equal(boardingMinutes(arrivals,now,13.5),14);
 assert.equal(boardingMinutes(arrivals.slice(0,2),now,13.5),null);
});


test('next buses sort by live arrival; stale/missing estimates follow without mutating input',async()=>{
 const {orderedBoardLines,humanBoarding}=await import('./boardingTime.js');
 const now=Date.parse('2026-10-08T02:01:30-03:00');
 const arrival=(time,observed_at='2026-10-08T02:01:00-03:00')=>({time,observed_at,vehicle:'81614'});
 const lines=[{code:'none'},{code:'late',arrivals:[arrival('02:14'),arrival('02:10')]},
   {code:'stale',arrivals:[arrival('02:02','2026-10-08T01:50:00-03:00')]},
   {code:'early',arrivals:[arrival('02:02')]}];
 const result=orderedBoardLines(lines,now);
 assert.deepEqual(result.map(l=>l.code),['early','late','none','stale']);
 assert.equal(result[0].live[0].seconds,30);
 assert.equal(result[1].live[0].time,'02:10');
 assert.equal(lines[0].code,'none');
 assert.equal(humanBoarding(30),'Embarque em 30 s');
 assert.equal(humanBoarding(60),'Embarque em 1 min');
 assert.equal(humanBoarding(3660),'Embarque em 1 h 1 min');
 assert.equal(humanBoarding(0),'Embarque agora');
});


test('board sorts destinations alphabetically and schedules by active or upcoming dated service',async()=>{
 const {orderedBoardLines}=await import('./boardingTime.js');
 const now=Date.parse('2026-10-08T02:00:00-03:00');
 const lines=[
  {code:'4',headsign:'Zoológico',programme:[{kind:'frequency',start:'2026-10-08T01:30:00-03:00',end:'2026-10-08T02:30:00-03:00'}]},
  {code:'3',headsign:'Água',programme:[{start:'2026-10-08T05:00:00-03:00'}]},
  {code:'2',headsign:'Centro',programme:[{start:'2026-10-09T01:00:00-03:00'}]},
  {code:'1',headsign:'Bairro',programme:[{start:'invalid'},{start:'2026-10-08T01:00:00-03:00'}]},
 ];
 assert.deepEqual(orderedBoardLines(lines,now,'alphabetical').map(l=>l.code),['3','1','2','4']);
 assert.deepEqual(orderedBoardLines(lines,now,'service').map(l=>l.code),['4','3','2','1']);
 assert.equal(lines[0].code,'4');
});
