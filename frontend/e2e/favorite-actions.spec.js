import {test,expect} from './coverage.js';
const a={id:'1',name:'Parada Casa',favoriteLabel:'Casa',lat:-23.55,lon:-46.63};
const b={id:'2',name:'Parada Trabalho',favoriteLabel:'Trabalho',lat:-23.56,lon:-46.64};
const position={lat:-23.552,lon:-46.632,simulated:true};
async function setup(page){
 await page.addInitScript(stops=>localStorage.setItem('pap.sp.favorites',JSON.stringify(stops)),[a,b]);
 await page.route('**/api/location-config/**',r=>r.fulfill({json:{position}}));
 await page.route('https://tile.openstreetmap.org/**',r=>r.abort());
 await page.route('**/api/sptrans/stops/**',r=>r.fulfill({json:{stops:[a,b]}}));
 await page.route('**/api/sptrans/destination/**',r=>r.fulfill({json:{stop:{id:'3',name:'Ponto próximo',lat:position.lat,lon:position.lon}}}));
 await page.route('**/api/sptrans/board/**',r=>r.fulfill({json:{lines:[],journeys:[],complete:true}}));
 await page.goto('/');
 await expect.poll(()=>page.evaluate(()=>JSON.parse(sessionStorage.getItem('pap.sp.session'))?.origin?.useLocation)).toBe(true);
}
const btn=(p,name)=>p.getByRole('button',{name,exact:true});
const session=p=>p.evaluate(()=>JSON.parse(sessionStorage.getItem('pap.sp.session')));
for(const width of [390,1440])test(`favoritos: atalhos, consulta independente e geolocalização ${width}`,async({page})=>{
 await page.setViewportSize({width,height:900});const errors=[];page.on('pageerror',e=>errors.push(e.message));page.on('dialog',d=>{throw Error('Confirmação inesperada: '+d.message());});await setup(page);
 await btn(page,'Favoritos').click();const dialog=page.getByRole('dialog',{name:'Pontos favoritos'});await expect(dialog).toBeVisible();await expect(btn(dialog,'Usar como embarque Casa').locator('.sp-point-control-image')).toBeVisible();
 expect(await dialog.locator('.sp-favorite-card').first().getByRole('button').evaluateAll(nodes=>nodes.map(n=>n.getAttribute('aria-label')))).toEqual(['Usar como destino Casa','Usar como embarque Casa','Ver próximos ônibus Casa','Renomear favorito Casa','Remover favorito Casa']);
 await btn(page,'Usar como destino Casa').click();await expect.poll(async()=>(await session(page)).destination?.id).toBe('1');expect((await session(page)).origin.useLocation).toBe(true);
 await btn(page,'Ver mapa').click();await btn(page,'Favoritos').click();await btn(page,'Usar como destino Trabalho').click();await expect.poll(async()=>(await session(page)).destination?.id).toBe('2');
 await btn(page,'Ver mapa').click();await btn(page,'Favoritos').click();const before=await session(page);await btn(page,'Ver próximos ônibus Casa').click();await expect(page.getByRole('dialog',{name:'Próximos ônibus'})).toBeVisible();expect(await session(page)).toEqual(before);
 await btn(page,'Ver mapa').click();await expect(dialog).toBeVisible();await btn(page,'Usar como embarque Trabalho').click();await expect.poll(async()=>(await session(page)).origin?.id).toBe('2');
 await btn(page,'Ver mapa').click();await btn(page,'Favoritos').click();const request=page.waitForRequest(r=>r.url().includes('/sptrans/board/')&&new URL(r.url()).searchParams.has('to_lat'));
 await btn(dialog,'Minha localização como destino').click();const q=new URL((await request).url()).searchParams;expect(q.get('origin')).toBe('2');expect(Number(q.get('to_lat'))).toBe(position.lat);expect(Number(q.get('to_lon'))).toBe(position.lon);expect((await session(page)).destination.useLocation).toBe(true);expect(errors).toEqual([]);
 await btn(page,'Ver mapa').click();await btn(page,'Favoritos').click();await page.screenshot({path:`test-results/favorites-dialog-${width}.png`});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);await btn(dialog,'Fechar favoritos').click();await btn(page,'Ativar modo escuro').click();await btn(page,'Favoritos').click();await expect(btn(dialog,'Usar como embarque Casa').locator('.sp-point-dark-image')).toBeVisible();await expect(btn(dialog,'Usar como embarque Casa').locator('.sp-point-control-image')).toBeHidden();await page.screenshot({path:`test-results/favorites-dark-${width}.png`});
});
