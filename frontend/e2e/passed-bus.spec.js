import {test,expect} from './coverage.js';
for(const width of [390,1200])test(`próximo e ônibus após o ponto coexistem em ${width}px`,async({page})=>{
 await page.setViewportSize({width,height:850});
 const now='2026-10-08T02:01:00-03:00';await page.clock.install({time:new Date(now)});
 const stop={id:'1',name:'Brasil C/B',lat:-23.56,lon:-46.68};
 await page.route('https://tile.openstreetmap.org/**',r=>r.abort());
 await page.route('**/api/location-config/**',r=>r.fulfill({json:{position:null}}));
 await page.route('**/api/sptrans/stops/**',r=>r.fulfill({json:{stops:[stop]}}));
 await page.route('**/api/sptrans/board/**',r=>r.fulfill({json:{lines:[{trip_id:'T',code:'778R-10',headsign:'Centro',arrivals:[{time:'02:10',observed_at:now,vehicle:'81614'}]}],journeys:[]}}));
 let calls=0;
 const vehicle=(id,lon)=>({id,code:'778R-10',lat:-23.56,lon,observed_at:now});
 await page.route('**/api/sptrans/trips/T/**',r=>{
  calls++;
  return r.fulfill({json:{line:{arrivals:[]},approach:{label:'Próximo ônibus',vehicle:vehicle('81615',-46.685),geometry:[[-23.56,-46.685],[-23.56,-46.68]]},
    passed_approaches:calls===1?[{label:'Já passou do embarque · 200 m após o ponto',selection:'passed',vehicle:vehicle('81614',-46.678),geometry:[]}]:[]}});
 });
 await page.goto('/?stop=1');
 await page.getByRole('button',{name:'Ver veículo 81614 da linha 778R-10 no mapa'}).click();
 await expect(page.locator('.sp-live-bus')).toHaveCount(2);
 await expect(page.locator('.sp-live-bus[title*="Já passou"]')).toHaveCount(1);
 await expect(page.locator('.sp-live-bus[title*="Já passou"]')).toHaveCSS('opacity','0.4');
 await expect(page.locator('.sp-live-bus[title*="Próximo ônibus"]')).toHaveCSS('opacity','1');
 await expect(page.locator('.leaflet-busApproach-pane path')).toHaveCount(1);
 await page.clock.fastForward(5000);
 await expect.poll(()=>calls).toBeGreaterThan(1);
 await expect(page.locator('.sp-live-bus')).toHaveCount(1);
 await expect(page.locator('.sp-live-bus[title*="Já passou"]')).toHaveCount(0);
});
