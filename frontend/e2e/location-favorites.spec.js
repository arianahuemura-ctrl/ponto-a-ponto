import {test,expect} from './coverage.js';
const stop={id:'1',name:'Parada próxima',lat:-23.55,lon:-46.63};
const saved={lat:-23.551234,lon:-46.631234};
const moved={lat:-23.561234,lon:-46.641234};
const button=(page,name)=>page.getByRole('button',{name,exact:true});
const favorites=page=>page.evaluate(()=>JSON.parse(localStorage.getItem('pap.sp.favorites'))||[]);
async function setup(page,position=saved){
 await page.route('**/api/location-config/**',r=>r.fulfill({json:{position:position?{...position,simulated:true}:null}}));
 await page.route('https://tile.openstreetmap.org/**',r=>r.abort());
 await page.route('**/api/sptrans/stops/**',r=>r.fulfill({json:{stops:[stop]}}));
 await page.route('**/api/sptrans/destination/**',r=>r.fulfill({json:{stop,distance_meters:100}}));
 await page.route('**/api/sptrans/board/**',r=>r.fulfill({json:{lines:[],journeys:[],complete:true}}));
 await page.goto('/');await button(page,'Continuar sem contribuir').click();
 await expect(page.locator('.sp-map')).toBeVisible();
 await expect.poll(()=>page.evaluate(()=>sessionStorage.getItem('pap.sp.session')!==null)).toBe(true);
 if(position)await expect.poll(()=>page.evaluate(()=>JSON.parse(sessionStorage.getItem('pap.sp.session'))?.origin?.useLocation)).toBe(true);
}
async function nameFavorite(page,name){
 const dialog=page.getByRole('dialog',{name:'Nome do favorito'});
 await dialog.getByRole('textbox',{name:'Nome do favorito'}).fill(name);
 await button(dialog,'Salvar favorito').click();
}
for(const width of [390,1440])test(`GPS salvo é fixo e Casa preserva caminhada após mudar localização ${width}`,async({page})=>{
 await page.setViewportSize({width,height:900});await setup(page);
 await button(page,'Favoritos').click();await button(page,'Salvar minha localização').click();await nameFavorite(page,'Meu local');
 const first=(await favorites(page))[0];expect(first).toMatchObject({kind:'location',...saved,favoriteLabel:'Meu local'});expect(first.useLocation).toBeUndefined();
 await expect(button(page,'Ver próximos ônibus Meu local')).toHaveCount(0);
 await button(page,'Configurar Casa').click();await button(page,'Usar favorito existente').click();await page.getByRole('combobox',{name:'Local de Casa',exact:true}).selectOption(first.id);await button(page,'Salvar atalho').click();
 await page.route('**/api/location-config/**',r=>r.fulfill({json:{position:{...moved,simulated:true}}}));
 await page.reload();await expect(button(page,'Ir para Casa')).toBeVisible();
 const request=page.waitForRequest(r=>r.url().includes('/board/')&&new URL(r.url()).searchParams.has('to_lat'));
 await button(page,'Ir para Casa').click();const q=new URL((await request).url()).searchParams;
 expect(Number(q.get('from_lat'))).toBe(moved.lat);expect(Number(q.get('from_lon'))).toBe(moved.lon);
 expect(Number(q.get('to_lat'))).toBe(saved.lat);expect(Number(q.get('to_lon'))).toBe(saved.lon);expect(q.get('destination')).toBe(stop.id);
 await expect(button(page,'Remover favorito')).toBeVisible();expect(await favorites(page)).toEqual([first]);
 await button(page,'Ver mapa').click();await button(page,'Favoritos').click();
 await page.screenshot({path:`/tmp/pap-geo-favorites-${width}.png`});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 await button(page,'Renomear favorito Meu local').click();await nameFavorite(page,'Local renomeado');
 await page.reload();await expect(button(page,'Ir para Casa')).toHaveAttribute('title','Casa: Local renomeado');
 await button(page,'Favoritos').click();await button(page,'Remover favorito Local renomeado').click();await button(page.getByRole('dialog',{name:'Remover favorito?'}),'Remover favorito').click();
 expect(await favorites(page)).toEqual([]);await expect(button(page,'Configurar Casa')).toBeVisible();
});
test('dois endereços da mesma parada permanecem favoritos independentes',async({page})=>{
 await setup(page);
 const places=[{...saved,id:'a',name:'Endereço A',label:'Endereço A'},{lat:saved.lat+.0001,lon:saved.lon,id:'b',name:'Endereço B',label:'Endereço B'}];
 await page.route('**/api/sptrans/addresses/**',r=>r.fulfill({json:{suggestions:places}}));
 for(const place of places){
  await button(page,'Buscar endereço').click();await page.getByRole('combobox',{name:'Endereço'}).fill(place.name);
  await page.getByRole('option').filter({hasText:place.name}).click();await button(page,'Usar como destino').click();
  await button(page,'Adicionar local aos favoritos').click();await nameFavorite(page,place.name);
  await button(page,'Ver mapa').click();
 }
 const entries=await favorites(page);expect(entries).toHaveLength(2);expect(entries[0].id).not.toBe(entries[1].id);
 for(let i=0;i<2;i++)expect(entries[i]).toMatchObject({kind:'location',lat:places[i].lat,lon:places[i].lon});
 await page.reload();expect(await favorites(page)).toEqual(entries);
});
test('local do mapa mantém coordenadas ao ser reutilizado como origem',async({page})=>{
 await setup(page);const request=page.waitForRequest(r=>r.url().includes('/destination/'));
 const map=await page.locator('.sp-map').boundingBox();await page.mouse.move(map.x+map.width*.6,map.y+map.height*.45);await page.mouse.down();await page.waitForTimeout(850);await page.mouse.up();
 await button(page,'Usar como destino').click();
 const coords=new URL((await request).url()).searchParams;
 await page.waitForTimeout(1250);await button(page,'Adicionar local aos favoritos').click();await nameFavorite(page,'Local no mapa');
 const entry=(await favorites(page))[0];expect(entry.lat).toBe(Number(coords.get('lat')));expect(entry.lon).toBe(Number(coords.get('lon')));
 await button(page,'Ver mapa').click();await button(page,'Favoritos').click();await button(page,'Usar como origem Local no mapa').click();
 await expect.poll(()=>page.evaluate(()=>JSON.parse(sessionStorage.getItem('pap.sp.session'))?.origin?.addressCoordinates)).toEqual({lat:entry.lat,lon:entry.lon});
 await button(page,'Favoritos').click();const board=page.waitForRequest(r=>r.url().includes('/board/')&&new URL(r.url()).searchParams.has('to_lat'));
 await button(page,'Minha localização como destino').click();const q=new URL((await board).url()).searchParams;
 expect(Number(q.get('from_lat'))).toBe(entry.lat);expect(Number(q.get('from_lon'))).toBe(entry.lon);
});
test('falha de resolução não altera viagem nem perde favorito',async({page})=>{
 await page.addInitScript(entry=>localStorage.setItem('pap.sp.favorites',JSON.stringify([entry])),{kind:'location',id:`location:${saved.lat},${saved.lon}`,name:'Local salvo',...saved});
 await setup(page);const before=await page.evaluate(()=>JSON.parse(sessionStorage.getItem('pap.sp.session')));
 await page.route('**/api/sptrans/destination/**',r=>r.fulfill({status:503,json:{error:'Serviço indisponível no teste'}}));
 await button(page,'Favoritos').click();await button(page,'Usar como destino Local salvo').click();await expect(page.getByRole('status').filter({hasText:'Serviço indisponível no teste'})).toBeVisible();
 expect(await page.evaluate(()=>JSON.parse(sessionStorage.getItem('pap.sp.session')))).toEqual(before);expect(await favorites(page)).toHaveLength(1);
});

test('sem GPS guarda localização de destino até selecionar embarque',async({page})=>{
 const location={kind:'location',id:`location:${saved.lat},${saved.lon}`,name:'Local salvo',...saved};
 await page.addInitScript(entries=>localStorage.setItem('pap.sp.favorites',JSON.stringify(entries)),[location,stop]);
 await setup(page,null);await button(page,'Favoritos').click();await button(page,'Usar como destino Local salvo').click();
 await expect(page.getByRole('status').filter({hasText:'Selecione o local de embarque.'})).toBeVisible();
 const state=await page.evaluate(()=>JSON.parse(sessionStorage.getItem('pap.sp.session')));
 expect(state.origin).toBeNull();expect(state.destination.addressCoordinates).toEqual(saved);
 await button(page,'Favoritos').click();await button(page,'Usar como embarque Parada próxima').click();
 await button(page,'Horários de embarque').click();
 await expect(page.getByRole('dialog',{name:'Próximos ônibus'})).toBeVisible();
 await expect(page.locator('.sp-origin')).toHaveCount(1);await expect(page.locator('.sp-destination')).toHaveCount(1);
 await expect(page.getByText('Origem e destino são o mesmo ponto.')).toHaveCount(0);
 expect(await page.evaluate(()=>JSON.parse(sessionStorage.getItem('pap.sp.session')).destination.addressCoordinates)).toEqual(saved);
});

for(const [role,label] of [['home','Casa'],['work','Trabalho']])test(`${label} vazio abre endereço e salva localização sem alterar viagem`,async({page})=>{
 await setup(page);
 const before=await page.evaluate(()=>JSON.parse(sessionStorage.getItem('pap.sp.session')));
 let nearby=0;await page.route('**/api/sptrans/destination/**',r=>{nearby++;return r.fulfill({status:503,json:{error:'Não deve consultar ao salvar'}});});
 await page.route('**/api/sptrans/addresses/**',r=>r.fulfill({json:{suggestions:[{id:'a',name:'MASP',label:'MASP, Avenida Paulista',...saved}]}}));
 await button(page,`Configurar ${label}`).click();await expect(page.getByRole('heading',{name:`Endereço de ${label}`})).toBeVisible();
 await page.getByRole('combobox').fill('MASP');await page.getByRole('option').filter({hasText:'MASP'}).click();await button(page,`Salvar ${label}`).click();
 const entry=(await favorites(page))[0];expect(entry).toMatchObject({kind:'location',...saved,favoriteLabel:label});
 expect(await page.evaluate(()=>JSON.parse(sessionStorage.getItem('pap.sp.session')))).toEqual(before);expect(nearby).toBe(0);
 expect(await page.evaluate(()=>JSON.parse(localStorage.getItem('pap.sp.quickDestinations')))).toEqual({[role]:entry.id});
 await button(page,'Buscar endereço').click();await expect(page.getByRole('heading',{name:'Para onde você vai?'})).toBeVisible();await expect(page.getByRole('combobox')).toHaveValue('');await button(page,'Fechar busca de endereço').click();
 await page.reload();await expect(button(page,`Ir para ${label}`)).toBeVisible();
});
for(const [name,role] of [['casa','home'],['Casa','home'],['trabalho','work'],['Trabalho','work']])test(`nome ${name} associa atalho vazio ao salvar`,async({page})=>{
 await setup(page);await button(page,'Favoritos').click();await button(page,'Salvar minha localização').click();await nameFavorite(page,name);
 const entry=(await favorites(page))[0];expect(await page.evaluate(()=>JSON.parse(localStorage.getItem('pap.sp.quickDestinations')))).toEqual({[role]:entry.id});
});
test('estrela do toque longo salva sem GPS e sem alterar a viagem',async({page})=>{
 await setup(page,null);let lookups=0;await page.route('**/api/sptrans/destination/**',r=>{lookups++;return r.fulfill({status:503,json:{error:'Sem serviço'}});});
 const before=await page.evaluate(()=>JSON.parse(sessionStorage.getItem('pap.sp.session')));
 const map=await page.locator('.sp-map').boundingBox();
 const press=async()=>{await page.mouse.move(map.x+map.width*.65,map.y+map.height*.45);await page.mouse.down();await page.waitForTimeout(750);await page.mouse.up();};
 await press();const star=button(page,'Adicionar local aos favoritos');await expect(star).toHaveAttribute('aria-pressed','false');await star.click();await nameFavorite(page,'casa');
 expect(lookups).toBe(0);expect(await page.evaluate(()=>JSON.parse(sessionStorage.getItem('pap.sp.session')))).toEqual(before);
 expect((await favorites(page))[0].kind).toBe('location');await expect(button(page,'Ir para Casa')).toBeVisible();
 await press();await expect(button(page,'Remover favorito deste local')).toHaveAttribute('aria-pressed','true');
 await page.screenshot({path:'/tmp/pap-location-star.png'});
});
test('salvar outro favorito chamado Casa não substitui Casa já definida',async({page})=>{
 await page.addInitScript(entry=>{localStorage.setItem('pap.sp.favorites',JSON.stringify([entry]));localStorage.setItem('pap.sp.quickDestinations',JSON.stringify({home:entry.id}));},stop);
 await setup(page);await button(page,'Favoritos').click();await button(page,'Salvar minha localização').click();await nameFavorite(page,' CASA ');
 expect(await favorites(page)).toHaveLength(2);expect(await page.evaluate(()=>JSON.parse(localStorage.getItem('pap.sp.quickDestinations')).home)).toBe(stop.id);
});
