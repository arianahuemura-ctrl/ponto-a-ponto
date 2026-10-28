import {test,expect} from './coverage.js';
const points=[{id:'1',name:'Ponto A',favoriteLabel:'Meu ponto',lat:-23.55,lon:-46.63},{id:'2',name:'Ponto B',favoriteLabel:'Outro ponto',lat:-23.56,lon:-46.64}];
const position={lat:-23.552,lon:-46.632,simulated:true};
const button=(page,name)=>page.getByRole('button',{name,exact:true});
async function setup(page,gps=true){
 await page.addInitScript(points=>{if(!localStorage.getItem('pap.sp.favorites'))localStorage.setItem('pap.sp.favorites',JSON.stringify(points));},points);
 await page.route('**/api/location-config/**',r=>r.fulfill({json:{position:gps?position:null}}));
 await page.route('https://tile.openstreetmap.org/**',r=>r.abort());
 await page.route('**/api/sptrans/stops/**',r=>r.fulfill({json:{stops:points}}));
 await page.route('**/api/sptrans/board/**',r=>r.fulfill({json:{lines:[],journeys:[],complete:true}}));
 await page.goto('/');
 await page.getByRole('button',{name:'Continuar sem contribuir',exact:true}).click();
 await expect(button(page,'Configurar Casa')).toBeVisible();
 if(gps)await expect.poll(()=>page.evaluate(()=>JSON.parse(sessionStorage.getItem('pap.sp.session'))?.origin?.useLocation)).toBe(true);
}
async function assign(page,role,id){
 await button(page,`Configurar ${role}`).click();await button(page,'Usar favorito existente').click();
 await page.getByRole('combobox',{name:`Local de ${role}`,exact:true}).selectOption(id);
 await button(page,'Salvar atalho').click();
}
for(const width of [390,1440])test(`Casa e Trabalho persistem e selecionam destino em um toque ${width}`,async({page})=>{
 await page.setViewportSize({width,height:850});await setup(page);
 await assign(page,'Casa','1');await assign(page,'Trabalho','2');await page.reload();
 for(const [role,id] of [['Casa','1'],['Trabalho','2']]){
  const request=page.waitForRequest(r=>r.url().includes('/sptrans/board/')&&new URL(r.url()).searchParams.get('destination')===id);
  await button(page,`Ir para ${role}`).click();const q=new URL((await request).url()).searchParams;
  expect(Number(q.get('from_lat'))).toBe(position.lat);expect(Number(q.get('from_lon'))).toBe(position.lon);
  await page.goto('/');
 }
 expect(await page.evaluate(()=>JSON.parse(localStorage.getItem('pap.sp.favorites')))).toEqual(points);
 await expect(button(page,'Ir para Casa')).toBeVisible();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 await page.screenshot({path:`test-results/quick-destinations-${width}.png`});
 await button(page,'Ativar modo escuro').click();await page.screenshot({path:`test-results/quick-destinations-dark-${width}.png`});
});
test('alterar, retirar atalho e remover favorito não deixam destino obsoleto',async({page})=>{
 await setup(page);await assign(page,'Casa','1');
 await button(page,'Favoritos').click();await button(page,'Alterar atalho Casa').click();
 await page.getByRole('combobox',{name:'Local de Casa',exact:true}).selectOption('2');await button(page,'Cancelar').click();
 expect(await page.evaluate(()=>JSON.parse(localStorage.getItem('pap.sp.quickDestinations')))).toEqual({home:'1'});
 await button(page,'Favoritos').click();await button(page,'Alterar atalho Casa').click();
 await page.getByRole('combobox',{name:'Local de Casa',exact:true}).selectOption('2');await button(page,'Salvar atalho').click();
 await button(page,'Favoritos').click();await button(page,'Alterar atalho Casa').click();
 await page.getByRole('combobox',{name:'Local de Casa',exact:true}).selectOption('');await button(page,'Salvar atalho').click();
 expect(await page.evaluate(()=>JSON.parse(localStorage.getItem('pap.sp.favorites')).length)).toBe(2);
 await assign(page,'Trabalho','2');await button(page,'Favoritos').click();await button(page,'Remover favorito Outro ponto').click();
 await page.getByRole('dialog',{name:'Remover favorito?'}).getByRole('button',{name:'Remover favorito',exact:true}).click();
 await page.reload();await expect(button(page,'Configurar Trabalho')).toBeVisible();
 expect(await page.evaluate(()=>JSON.parse(localStorage.getItem('pap.sp.quickDestinations')))).toEqual({});
});
test('atalho sem localização guarda destino e exige embarque, preservando QR quando existe',async({page})=>{
 await setup(page,false);await assign(page,'Casa','2');await button(page,'Ir para Casa').click();
 await expect.poll(()=>page.evaluate(()=>JSON.parse(sessionStorage.getItem('pap.sp.session'))?.destination?.id)).toBe('2');
 expect(await page.evaluate(()=>JSON.parse(sessionStorage.getItem('pap.sp.session')).origin)).toBeNull();
 await expect(page.getByRole('status').filter({hasText:'Selecione o local de embarque.'})).toBeVisible();
 await page.goto('/?stop=1');await button(page,'Ver mapa').click();
 const request=page.waitForRequest(r=>r.url().includes('/sptrans/board/')&&new URL(r.url()).searchParams.get('destination')==='2');
 await button(page,'Ir para Casa').click();expect(new URL((await request).url()).searchParams.get('origin')).toBe('1');
});
