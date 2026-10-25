import {test,expect} from '@playwright/test';
const stops=[{id:'1',name:'Primeiro',lat:-23.55,lon:-46.64},{id:'2',name:'Embarque',lat:-23.55,lon:-46.63},{id:'3',name:'Terminal',lat:-23.55,lon:-46.62}];
const geometry=stops.map(s=>[s.lat,s.lon]);
for(const live of [false,true,"single","mismatch"])test(`linha completa com veículos disponíveis=${live}`,async({page})=>{
 await page.setViewportSize({width:390,height:844});
 const now=new Date();await page.clock.install({time:now});
 const line={trip_id:'T',code:'6L10-41',headsign:'Terminal',arrivals:[]};let calls=0,fail=false;
 if(live==='single')line.arrivals=[{vehicle:'10',observed_at:now.toISOString(),time:new Intl.DateTimeFormat('pt-BR',{timeZone:'America/Sao_Paulo',hour:'2-digit',minute:'2-digit'}).format(new Date(+now+600000)),accessible:true}];
 await page.route('https://tile.openstreetmap.org/**',r=>r.abort());
 await page.route('**/api/location-config/**',r=>r.fulfill({json:{position:null}}));
 await page.route('**/api/sptrans/stops/**',r=>r.fulfill({json:{stops:[stops[1]]}}));
 await page.route('**/api/sptrans/board/**',r=>r.fulfill({json:{lines:[line],journeys:[]}}));
 await page.route('**/api/sptrans/trips/**',r=>{
  calls++;if(fail)return r.abort();
  return r.fulfill({json:{line,approach:live?{label:'Veículo artificial',vehicle:{id:'10',code:line.code,lat:-23.55,lon:-46.635,observed_at:now.toISOString()},geometry:[[-23.55,-46.635],geometry[1]]}:null,itinerary:{geometry,before:geometry.slice(0,2),after:geometry.slice(1),terminal:stops[2],...(live==="mismatch"?{terminal_mismatch:true,endpoint:{kind:"shape",lat:-23.55,lon:-46.62}}:{}),split_available:true,boarding_index:1}}});
 });
 await page.goto('/?stop=2');await page.getByRole('button',{name:'Continuar sem contribuir',exact:true}).click();
 await page.getByRole('button',{name:live==='single'?'Ver veículo 10 da linha 6L10-41 no mapa':'Ver trajeto da linha 6L10-41',exact:true}).click();
 await expect(page.locator('dialog[open]')).toHaveCount(0);
 await expect(page.locator('.sp-line-start')).toHaveAttribute('title','Início do traçado da linha 6L10-41');
 await expect(page.locator('.sp-line-before')).toHaveCount(1);await expect(page.locator('.sp-line-after')).toHaveCount(1);
 await expect(page.locator('.sp-line-before')).toHaveAttribute('stroke-dasharray','5 8');
 await expect(page.locator('.sp-line-terminal')).toHaveAttribute('title',live==='mismatch'?'Fim do traçado GTFS da linha 6L10-41 · última parada cadastrada divergente':'Último ponto da linha 6L10-41 · Terminal · 3');
 await expect(page.locator('.sp-live-bus')).toHaveCount(live?1:0);
 expect(await page.evaluate(()=>JSON.parse(sessionStorage.getItem('pap.sp.session')).destination)).toBeNull();
 // Sem atualização de posições, o traçado estático não desaparece.
 fail=true;await page.clock.fastForward(16000);await expect.poll(()=>calls).toBeGreaterThan(1);
 await expect(page.locator('.sp-line-after')).toHaveCount(1);await expect(page.locator('.sp-line-terminal')).toHaveCount(1);
 await page.screenshot({path:`test-results/line-itinerary-${live}.png`});
});
