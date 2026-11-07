import test from 'node:test';
import assert from 'node:assert/strict';
import {trackLocation, boardingCoordinates, locationOrigin, locationParams, withLocationParams} from './location.js';
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

test('embarque explícito preserva suas coordenadas apesar do GPS',()=>{
 const origin={id:'stop',lat:10,lon:20,addressCoordinates:{lat:11,lon:21}};
 assert.deepEqual(boardingCoordinates({lat:0,lon:0,simulated:true},origin),{from_lat:11,from_lon:21});
 assert.deepEqual(boardingCoordinates({lat:-23.5,lon:-46.6},origin),{from_lat:11,from_lon:21});
 assert.deepEqual(boardingCoordinates(null,origin),{from_lat:11,from_lon:21});
 assert.deepEqual(boardingCoordinates(null,{id:'stop',lat:10,lon:20}),{});
});

test('automatic origin needs no stop and manual boarding overrides live GPS',()=>{
 const gps={lat:-23.5,lon:-46.6};
 assert.equal(locationOrigin(gps).useLocation,true);
 assert.deepEqual(boardingCoordinates(gps,{id:'123',manualBoarding:true}),{});
 assert.deepEqual(boardingCoordinates(gps,{id:'440016922',lat:-23.56,lon:-46.65}),{});
 assert.deepEqual(boardingCoordinates(gps,{manualBoarding:true,addressCoordinates:{lat:1,lon:2}}),{from_lat:1,from_lon:2});
 assert.deepEqual(boardingCoordinates(gps,locationOrigin(gps)),{from_lat:gps.lat,from_lon:gps.lon});
});

test('URL test coordinates are forwarded without silently filling missing values',()=>{
 assert.deepEqual(locationParams('?latitude=0&longitude=-46.63&stop=123'),{latitude:'0',longitude:'-46.63'});
 assert.deepEqual(locationParams('?latitude='),{latitude:''});
 assert.deepEqual(locationParams('?stop=123'),{});
});
test('navigation preserves test location but removes the old stop',()=>{
 const query='?latitude=-23.55&longitude=-46.63&stop=old';
 assert.equal(withLocationParams('/',query),'/?latitude=-23.55&longitude=-46.63');
 assert.equal(withLocationParams('/?stop=new',query),'/?stop=new&latitude=-23.55&longitude=-46.63');
 assert.equal(withLocationParams('/','?stop=old'),'/');
});

test('copied Maps coordinates survive navigation and URL encoding',()=>{
 const value='-23.561902423411315, -46.680757605637645';
 assert.deepEqual(locationParams('?location='+value),{location:value});
 const next=withLocationParams('/?stop=new','?location='+value+'&stop=old');
 assert.equal(new URL(next,'http://localhost').searchParams.get('location'),value);
 assert.deepEqual(locationParams(new URL(next,'http://localhost').search),{location:value});
});
