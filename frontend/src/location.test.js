import test from 'node:test';
import assert from 'node:assert/strict';
import {trackLocation, boardingCoordinates, locationOrigin} from './location.js';
test('simulated coordinates bypass GPS even on HTTP',()=>{
 const p={lat:0,lon:0,simulated:true};let actual;
 trackLocation(p,{},false,v=>actual=v,()=>assert.fail());assert.equal(actual,p);
});
test('GPS streams updates, reports denial and clears watcher',()=>{
 let success,error,cleared,position,message;
 const geo={watchPosition(s,e){success=s;error=e;return 7;},clearWatch(id){cleared=id;}};
 const stop=trackLocation(null,{geolocation:geo},true,v=>position=v,e=>message=e);
 success({coords:{latitude:1,longitude:2,accuracy:10}});assert.equal(position.lat,1);
 success({coords:{latitude:3,longitude:4,accuracy:5}});assert.equal(position.lat,3);
 error({code:1});assert.equal(position,null);assert.match(message,/negada/);
 stop();assert.equal(cleared,7);
});
test('HTTP cannot start GPS',()=>{
 let error;trackLocation(null,{},false,()=>assert.fail(),v=>error=v);assert.match(error,/HTTPS/);
});

test('boarding walk starts at passenger including simulated coordinates',()=>{
 const origin={id:'stop',lat:10,lon:20,addressCoordinates:{lat:11,lon:21}};
 assert.deepEqual(boardingCoordinates({lat:0,lon:0,simulated:true},origin),{from_lat:0,from_lon:0});
 assert.deepEqual(boardingCoordinates({lat:-23.5,lon:-46.6},origin),{from_lat:-23.5,from_lon:-46.6});
 assert.deepEqual(boardingCoordinates(null,origin),{from_lat:11,from_lon:21});
 assert.deepEqual(boardingCoordinates(null,{id:'stop',lat:10,lon:20}),{});
});

test('automatic origin needs no stop and manual boarding overrides live GPS',()=>{
 const gps={lat:-23.5,lon:-46.6};
 assert.equal(locationOrigin(gps).useLocation,true);
 assert.deepEqual(boardingCoordinates(gps,{id:'123',manualBoarding:true}),{});
 assert.deepEqual(boardingCoordinates(gps,{manualBoarding:true,addressCoordinates:{lat:1,lon:2}}),{from_lat:1,from_lon:2});
 assert.deepEqual(boardingCoordinates(gps,locationOrigin(gps)),{from_lat:gps.lat,from_lon:gps.lon});
});
