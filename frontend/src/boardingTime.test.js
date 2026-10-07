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
