import {test,expect} from './coverage.js';

test('próximos ônibus destacam embarque, ocultam frequências e reordenam previsões expiradas',async({page})=>{
 const observed_at='2026-10-08T02:01:00-03:00';
 const stop={id:'1',name:'Brasil C/B',lat:-23.56,lon:-46.68};
 const programme=[{kind:'frequency',interval_minutes:30,start:'2026-10-08T01:00:00-03:00',end:'2026-10-08T03:00:00-03:00'}];
 const lines=[{trip_id:'none',code:'SEM',headsign:'Sem previsão',programme},
  {trip_id:'late',code:'715M-10',headsign:'Tardio',programme,arrivals:[{time:'02:14',observed_at,vehicle:'81250'}]},
  {trip_id:'early',code:'778R-10',headsign:'Próximo',programme,arrivals:[{time:'02:02',observed_at,vehicle:'81614',accessible:true}]}];
 await page.clock.install({time:new Date('2026-10-08T02:01:30-03:00')});
 await page.route('https://tile.openstreetmap.org/**',r=>r.abort());
 await page.route('**/api/location-config/**',r=>r.fulfill({json:{position:null}}));
 await page.route('**/api/sptrans/stops/**',r=>r.fulfill({json:{stops:[stop]}}));
 await page.route('**/api/sptrans/board/**',r=>r.fulfill({json:{lines,journeys:[],queried_at:observed_at}}));
 await page.goto('/?stop=1');
 const cards=page.locator('.sp-lines article');
 await expect(cards).toHaveCount(3);
 await expect(cards.nth(0)).toContainText('778R-10');
 await expect(cards.nth(0)).toContainText('Embarque em 30 s');
 await expect(cards.nth(0)).toContainText('No veículo 81614 — acessível');
 await expect(cards.nth(0)).not.toContainText('A cada');
 await expect(cards.nth(1)).toContainText('Embarque em 13 min');
 await expect(cards.nth(2)).toContainText('A cada 30 min');
 await page.clock.fastForward(91000);
 await expect(cards.nth(0)).toContainText('715M-10');
 const expired=cards.filter({hasText:'778R-10'});
 await expect(expired).toContainText('A cada 30 min');
 await expect(expired).not.toContainText('Embarque em');
 await page.getByLabel('Ordenar por').selectOption('alphabetical');
 await expect(cards.nth(0)).toContainText('Próximo');
 await expect(cards.nth(1)).toContainText('Sem previsão');
 await expect(cards.nth(2)).toContainText('Tardio');
 await page.getByLabel('Ordenar por').selectOption('service');
 await expect(cards.nth(0)).toContainText('Próximo');
 await page.getByLabel('Ordenar por').selectOption('arrival');
 await expect(cards.nth(0)).toContainText('715M-10');
});
