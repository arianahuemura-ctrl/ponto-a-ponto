import {test,expect} from './coverage.js';
for(const restored of [false,true])test(`QR abre próximos ônibus, sessão anterior=${restored}`,async({page})=>{
 const stop={id:'1',name:'Ponto do QR',lat:-23.56,lon:-46.68};
 if(restored)await page.addInitScript(stop=>sessionStorage.setItem('pap.sp.session',JSON.stringify({origin:stop,destination:{...stop,id:'2',name:'Destino antigo'}})),stop);
 await page.route('https://tile.openstreetmap.org/**',r=>r.abort());
 await page.route('**/api/location-config/**',r=>r.fulfill({json:{position:null}}));
 await page.route('**/api/sptrans/stops/**',r=>r.fulfill({json:{stops:[stop]}}));
 const queries=[];
 await page.route('**/api/sptrans/board/**',r=>{
  queries.push(new URL(r.request().url()).searchParams);
  return r.fulfill({json:{lines:[],journeys:[]}});
 });
 await page.goto('/?stop=1');
 await expect(page.getByRole('dialog')).toBeVisible();
 await expect(page.getByRole('dialog').getByRole('heading',{name:'Próximos ônibus'})).toBeVisible();
 await expect(page.getByRole('dialog')).toContainText('Ponto do QR');
 await expect.poll(()=>queries.length).toBeGreaterThan(0);
 expect(queries[0].get('destination')).toBeNull();
 expect(await page.evaluate(()=>JSON.parse(sessionStorage.getItem('pap.sp.session')).destination)).toBeNull();
 await page.getByRole('button',{name:'Selecionar destino',exact:true}).click();
 await expect(page.getByRole('dialog')).not.toBeVisible();
});
