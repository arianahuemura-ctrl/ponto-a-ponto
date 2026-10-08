import {test,expect} from './coverage.js';
const origin={id:'1',name:'Embarque',lat:-23.55,lon:-46.64},destination={id:'2',name:'Guaiaúna',lat:-23.52,lon:-46.53};
async function setup(page,gps=false){
 await page.addInitScript(({origin,destination})=>sessionStorage.setItem('pap.sp.session',JSON.stringify({origin,destination})),{origin,destination});
 await page.route('https://tile.openstreetmap.org/**',r=>r.abort());
 await page.route('**/api/location-config/**',r=>r.fulfill({json:{position:gps?{lat:-23.57,lon:-46.70,simulated:true}:null}}));
 await page.route('**/api/sptrans/stops/**',r=>r.fulfill({json:{stops:[origin,destination]}}));
 await page.route('**/api/sptrans/trips/**',r=>r.fulfill({json:{line:{arrivals:[]}}}));
 return {id:'J',duration_minutes:90,transfers:0,walks:[],legs:[{trip_id:'T',code:'702C-10',origin,destination,boarding_index:0,geometry:[[origin.lat,origin.lon],[destination.lat,destination.lon]]}]};
}
test('busca permanece estável após 30s e recarregar inicia consulta com ampulheta',async({page})=>{
 const journey=await setup(page);const queries=[];let release;
 await page.route('**/api/sptrans/board/**',async r=>{
  queries.push(new URL(r.request().url()).searchParams);
  if(queries.length>1)await new Promise(resolve=>release=resolve);
  await r.fulfill({json:{journeys:[journey],selected_journey:'J',complete:true,lines:[]}});
 });
 await page.clock.install();await page.goto('/?stop=1');
 await page.getByRole('button',{name:'Horários de embarque',exact:true}).click();
 await expect(page.locator('.sp-route-option')).toHaveCount(1);
 await page.clock.fastForward(35000);expect(queries).toHaveLength(1);
 await expect(page.locator('.sp-route-option')).toHaveAttribute('aria-pressed','true');
 await page.getByRole('button',{name:'Reiniciar busca',exact:true}).click();
 await expect.poll(()=>queries.length).toBe(2);expect(queries[1].get('refresh')).toBe('1');
 await expect(page.getByRole('button',{name:'Carregando rotas',exact:true})).toBeDisabled();
 await expect(page.locator('.sp-loading-hourglass')).toBeVisible();
 release();await expect(page.getByRole('button',{name:'Reiniciar busca',exact:true})).toBeEnabled();
});
for(const gps of [false,true])test(`alterar embarque aproxima origem; cancelar foca destino (GPS=${gps})`,async({page})=>{
 await page.setViewportSize({width:390,height:844});
 const journey=await setup(page,gps);const areas=[];
 await page.route('**/api/sptrans/stops/**',r=>{areas.push(new URL(r.request().url()).searchParams);return r.fulfill({json:{stops:[origin,destination]}});});
 await page.route('**/api/sptrans/board/**',r=>r.fulfill({json:{journeys:[journey],selected_journey:'J',complete:true,lines:[]}}));
 await page.goto('/?stop=1');await expect(page.locator('.sp-route-bus')).toHaveCount(1);
 await page.getByRole('button',{name:'Cancelar viagem',exact:true}).click();await page.getByRole('button',{name:'Confirmar cancelamento',exact:true}).click();
 await expect(page.locator('.sp-navigation-state')).toContainText('Selecionar destino');
 await expect.poll(()=>Number(areas.at(-1)?.get('lat'))).toBeCloseTo(destination.lat,3);
 const session=await page.evaluate(()=>JSON.parse(sessionStorage.getItem('pap.sp.session')));
 expect(session.origin.id).toBe('1');expect(session.destination).toBeNull();
 await page.getByRole('button',{name:'Alterar embarque',exact:true}).click();
 await expect.poll(()=>Number(areas.at(-1)?.get('lat'))).toBeCloseTo(gps?-23.57:origin.lat,3);
 const q=areas.at(-1),width=(Number(q.get('east'))-Number(q.get('west')))*111320*Math.cos(origin.lat*Math.PI/180);
 expect(width).toBeGreaterThanOrEqual(495);expect(width).toBeLessThan(560);
 if(gps){const zoom=await page.locator('.leaflet-control-zoom').boundingBox(),loc=await page.getByRole('button',{name:'Minha localização (simulada)',exact:true}).boundingBox();expect(Math.abs(loc.width-zoom.width)).toBeLessThan(1);expect(Math.abs(loc.height-zoom.width)).toBeLessThan(1);expect(Math.abs(loc.x-zoom.x)).toBeLessThan(1);}
});
