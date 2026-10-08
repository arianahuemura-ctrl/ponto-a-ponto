import test from 'node:test';
import assert from 'node:assert/strict';
import {operationalArrival} from './useJourneyForecast.js';
const now=Date.parse('2026-10-08T09:00:00-03:00');
const stamp=t=>`2026-10-08T${t}:00-03:00`;
const forecast=(...times)=>({arrivals:times.map(time=>({time,observed_at:stamp('09:00')}))});
const trip={legs:[{departure:stamp('09:00'),arrival:stamp('09:10')},{departure:stamp('09:20'),arrival:stamp('09:30')}],walks:[{accessType:'transfer',before_leg:1,duration_minutes:5},{accessType:'destination',duration_minutes:3}]};
test('usa caminhada pré-calculada no acesso e na transferência para escolher veículos alcançáveis',()=>{
 assert.equal(operationalArrival(trip,{0:forecast('09:02','09:06'),1:forecast('09:20','09:23')},now,5),Date.parse(stamp('09:36')));
});
test('não publica chegada operacional quando nenhuma previsão permite concluir a caminhada',()=>{
 assert.equal(operationalArrival(trip,{0:forecast('09:06'),1:forecast('09:20')},now,5),null);
});
test('aguarda os trechos ainda sem previsão',()=>{
 assert.equal(operationalArrival(trip,{0:forecast('09:06')},now,5),null);
});
