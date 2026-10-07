import {test} from 'node:test';
import assert from 'node:assert/strict';
import {mergeProgramme} from './programme.js';
const frequency=(start,end,interval_minutes=5)=>({kind:'frequency',start:'2026-10-07T'+start+':00-03:00',end:'2026-10-07T'+end+':00-03:00',interval_minutes});
test('merges adjacent equal frequencies without changing source windows',()=>{
 const source=[frequency('04:46','05:45',12),frequency('05:46','06:45'),frequency('06:46','07:45')];
 const original=structuredClone(source);
 assert.deepEqual(mergeProgramme(source),[source[0],frequency('05:46','07:45')]);
 assert.deepEqual(source,original);
});
test('preserves frequency changes, service gaps and scheduled departures',()=>{
 const source=[frequency('04:00','05:00'),frequency('05:02','06:00'),frequency('06:00','07:00',12),
 {kind:'scheduled',start:'2026-10-07T07:00:00-03:00',end:'2026-10-07T07:00:00-03:00'}];
 assert.deepEqual(mergeProgramme(source),source);
 assert.deepEqual(mergeProgramme(),[]);
});
test('uses full timestamps across midnight',()=>{
 const source=[{kind:'frequency',interval_minutes:5,start:'2026-10-07T23:00:00-03:00',end:'2026-10-07T23:59:00-03:00'},
 {kind:'frequency',interval_minutes:5,start:'2026-10-08T00:00:00-03:00',end:'2026-10-08T01:00:00-03:00'}];
 assert.equal(mergeProgramme(source).length,1);
 assert.equal(mergeProgramme(source)[0].end,source[1].end);
});
