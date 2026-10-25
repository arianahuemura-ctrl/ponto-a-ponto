import {test,expect} from '@playwright/test';
const KEY='pap.research.choice',VERSION='research-v6-voluntary';
const stop={id:'1',name:'Origem teste',lat:-23.5505,lon:-46.6333};
async function setup(context,{failure=null}={}){
  const requests=[],events=[];
  context.on('request',r=>{if(r.url().includes('/api/usability/'))requests.push(r);});
  await context.route('https://tile.openstreetmap.org/**',r=>r.abort());
  await context.route('**/api/location-config/**',r=>r.fulfill({json:{position:null}}));
  await context.route('**/api/sptrans/stop-catalogue/**',r=>r.fulfill({status:503,body:''}));
  await context.route('**/api/sptrans/stops/**',r=>r.fulfill({json:{stops:[stop]}}));
  await context.route('**/api/sptrans/board/**',r=>r.fulfill({json:{lines:[{trip_id:'T',code:'1000-10',headsign:'Centro',arrivals:[],programme:[]}],journeys:[],complete:true}}));
  await context.route('**/api/usability/',async r=>{
    if(failure==='network')return r.abort();
    if(failure==='get'&&r.request().method()==='GET')return r.fulfill({status:503,json:{error:'Artificial'}});
    if(r.request().method()==='POST'){events.push(...r.request().postDataJSON().events);return r.fulfill({json:{accepted:1}});}
    return r.fulfill({json:{session:'11111111-1111-4111-8111-111111111111',token:'test-only',csrf:'test-only'}});
  });
  return {requests,events};
}
async function decide(page,accept=false){await page.getByRole('button',{name:accept?'Contribuir com a pesquisa':'Continuar sem contribuir',exact:true}).click();await expect(page.locator('.sp-shell')).toBeVisible();}
async function settings(page){await page.getByRole('button',{name:'Configurações',exact:true}).click();await expect(page.getByRole('dialog',{name:'Configurações → Participação na pesquisa'})).toBeVisible();}
async function revoke(page){await settings(page);await page.getByRole('button',{name:'Interromper gravação',exact:true}).click();await page.getByRole('button',{name:'Fechar configurações'}).click();}

test('recusa: navegação, busca, tema e feedback sem sessão ou replay',async({page,context})=>{
  const {requests,events}=await setup(context);await page.setViewportSize({width:390,height:844});await page.goto('/?stop=1');await page.screenshot({path:'test-results/research-welcome-mobile.png'});await decide(page);
  await expect(page.getByRole('dialog',{name:'Próximos ônibus'})).toBeVisible();
  await page.getByRole('button',{name:'Ver mapa',exact:true}).click();
  await page.getByRole('button',{name:'Buscar endereço',exact:true}).click();await expect(page.getByRole('combobox')).toBeVisible();await page.keyboard.press('Escape');
  await page.getByRole('button',{name:'Feedback',exact:true}).click();await page.getByLabel('Seu feedback', {exact:true}).fill('Relato voluntário artificial');
  const sent=page.waitForRequest(r=>r.url().includes('/api/research/feedback/')&&r.method()==='POST');await page.getByRole('button',{name:'Enviar feedback'}).click();
  expect((await sent).postDataJSON()).not.toHaveProperty('token');await expect(page.getByText('Nenhuma gravação de navegação foi iniciada.',{exact:false})).toBeVisible();
  await page.getByRole('button',{name:'Concluir',exact:true}).click();await page.waitForTimeout(400);expect(requests).toHaveLength(0);expect(events).toHaveLength(0);
  expect(await page.evaluate(()=>sessionStorage.getItem('pap-usability-id'))).toBeNull();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  await page.screenshot({path:'test-results/research-refusal-mobile.png'});
});
test('aceitação explícita registra versão e inicia rrweb',async({page,context})=>{
 const {requests,events}=await setup(context);await page.goto('/');expect(requests).toHaveLength(0);await decide(page,true);
 await expect(page.locator('.research-status')).toContainText('Gravação ativa');
 await expect.poll(()=>events.some(e=>e.type==='trace'&&JSON.parse(e.data.payload).kind==='consent')).toBe(true);
 const consent=events.find(e=>e.type==='trace'&&JSON.parse(e.data.payload).kind==='consent');expect(JSON.parse(consent.data.payload).details.version).toBe(VERSION);
 await expect.poll(()=>events.some(e=>e.type==='trace'&&JSON.parse(e.data.payload).kind==='visual_config')).toBe(true);
 await revoke(page);
});
for(const state of ['accepted','declined'])test(`persistência, recarga e nova aba: ${state}`,async({page,context})=>{
 const {requests}=await setup(context);await page.goto('/');await decide(page,state==='accepted');
 const choice=await page.evaluate(key=>JSON.parse(localStorage.getItem(key)),KEY);expect(choice.state).toBe(state);expect(choice.version).toBe(VERSION);expect(Date.parse(choice.decidedAt)).toBeGreaterThan(0);
 await page.reload();await expect(page.locator('.sp-shell')).toBeVisible();await expect(page.getByRole('heading',{name:'Ponto a Ponto — Ajude a melhorar o transporte público'})).toHaveCount(0);
 const other=await context.newPage();await other.goto('/');await expect(other.locator('.sp-shell')).toBeVisible();
 if(state==='declined')expect(requests).toHaveLength(0);else{await expect(other.locator('.research-status')).toContainText('Gravação ativa');await revoke(page);await expect(other.locator('.research-status')).not.toContainText('Gravação ativa');}
 await other.close();
});
test('revogação limpa fila, interrompe envios e não reinicia ao recarregar',async({page,context})=>{
 const {requests}=await setup(context);await page.goto('/');await decide(page,true);await expect(page.locator('.research-status')).toContainText('Gravação ativa');await revoke(page);
 const count=requests.length;await page.mouse.move(200,300);await page.getByRole('button',{name:'Favoritos',exact:true}).click();await page.waitForTimeout(700);expect(requests).toHaveLength(count);
 expect(await page.evaluate(()=>sessionStorage.getItem('pap-usability-token'))).toBeNull();await page.reload();await expect(page.locator('.sp-shell')).toBeVisible();await page.waitForTimeout(300);expect(requests).toHaveLength(count);
});
test('mudança de versão solicita nova escolha sem capturar',async({page,context})=>{
 const {requests}=await setup(context);await page.addInitScript(({key})=>localStorage.setItem(key,JSON.stringify({state:'accepted',version:'old',decidedAt:new Date().toISOString()})),{key:KEY});await page.goto('/');await expect(page.getByRole('button',{name:'Continuar sem contribuir',exact:true})).toBeVisible();expect(requests).toHaveLength(0);
});
for(const accept of [false,true])test(`armazenamento indisponível não presume consentimento (${accept})`,async({page,context})=>{
 const {requests}=await setup(context);await page.addInitScript(()=>{Storage.prototype.getItem=()=>{throw Error('blocked')};Storage.prototype.setItem=()=>{throw Error('blocked')};});await page.goto('/');expect(requests).toHaveLength(0);await decide(page,accept);await expect(page.getByText('Não foi possível salvar sua escolha', {exact:false}).first()).toBeVisible();
 if(accept){await expect(page.locator('.research-status')).toContainText('Gravação ativa');await revoke(page);}else expect(requests).toHaveLength(0);
 await page.reload();await expect(page.getByRole('button',{name:'Continuar sem contribuir',exact:true})).toBeVisible();
});
for(const failure of ['get','network'])test(`falha ${failure} permite consulta`,async({page,context})=>{
 await setup(context,{failure});await page.goto('/?stop=1');await decide(page,true);await expect(page.locator('.research-status')).toContainText('Gravação indisponível');await expect(page.getByRole('dialog',{name:'Próximos ônibus'})).toBeVisible();
});
test('falha de rede depois do início interrompe pesquisa e preserva mapa',async({page,context})=>{
 const {requests}=await setup(context);await page.goto('/');await decide(page,true);await expect(page.locator('.research-status')).toContainText('Gravação ativa');await context.route('**/api/usability/',r=>r.abort());await page.getByRole('button',{name:'Favoritos',exact:true}).click();await expect(page.locator('.research-status')).toContainText('Gravação indisponível');const count=requests.length;await page.waitForTimeout(500);expect(requests).toHaveLength(count);await expect(page.locator('.sp-shell')).toBeVisible();
});
test('recusa pode ser alterada nas configurações e revogada em outra aba',async({page,context})=>{
 const {requests}=await setup(context);await page.goto('/');await decide(page);expect(requests).toHaveLength(0);await settings(page);await page.getByRole('button',{name:'Gravar',exact:true}).click();await page.getByRole('button',{name:'Fechar configurações'}).click();await expect(page.locator('.research-status')).toContainText('Gravação ativa');
 const other=await context.newPage();await other.goto('/');await expect(other.locator('.research-status')).toContainText('Gravação ativa');await revoke(page);await expect(other.locator('.research-status')).not.toContainText('Gravação ativa');const count=requests.length;await other.reload();await expect(other.locator('.sp-shell')).toBeVisible();await page.waitForTimeout(300);expect(requests).toHaveLength(count);await other.close();
});
test('exclusão pode ser solicitada sem criar sessão',async({page,context})=>{
 const {requests}=await setup(context);await page.goto('/');await decide(page);await settings(page);await page.screenshot({path:'test-results/research-settings.png'});await page.getByRole('combobox',{name:'Assunto',exact:true}).selectOption('deletion');await page.getByLabel('Mensagem',{exact:true}).fill('Solicitação artificial de exclusão de registros anteriores');await page.getByRole('button',{name:'Enviar solicitação'}).click();await expect(page.getByText('Solicitação recebida.',{exact:false})).toBeVisible();expect(requests).toHaveLength(0);
});
test('revogação durante inicialização não permite captura tardia',async({page,context})=>{
 const {requests}=await setup(context);let release;const wait=new Promise(r=>release=r);await context.route('**/api/usability/',async r=>{await wait;try{await r.fulfill({json:{session:'test',token:'test',csrf:'test'}});}catch{}});await page.goto('/');await decide(page,true);await revoke(page);release();await page.waitForTimeout(500);expect(requests.filter(r=>r.method()==='POST')).toHaveLength(0);await expect(page.locator('.research-status')).not.toContainText('Gravação ativa');
});


test('roteiro de transporte sem pesquisa: rota, mapa, favoritos e cancelamento',async({page,context})=>{
 const {requests}=await setup(context);
 const destination={id:'2',name:'Destino artificial',lat:-23.5515,lon:-46.6323};
 await context.route('**/api/sptrans/destination/**',r=>r.fulfill({json:{stop:destination,distance_meters:10}}));
 await context.route('**/api/sptrans/trips/**',r=>r.fulfill({json:{line:{arrivals:[]}}}));
 await context.route('**/api/sptrans/board/**',r=>r.fulfill({json:{journeys:[{id:'J',arrival:'2026-10-23T19:00:00Z',duration_minutes:10,transfers:0,walks:[],legs:[{trip_id:'T',code:'1000-10',origin:stop,destination,boarding_index:0,departure:'2026-10-23T18:50:00Z',geometry:[[stop.lat,stop.lon],[destination.lat,destination.lon]]}]}],selected_journey:'J',complete:true,lines:[]}}));
 await page.goto('/?stop=1');await decide(page);
 await page.getByRole('button',{name:'Ver mapa',exact:true}).click();
 const box=await page.locator('.sp-map').boundingBox();
 await page.mouse.move(box.x+box.width*.7,box.y+box.height*.4);await page.mouse.down();await page.waitForTimeout(800);await page.mouse.up();
 // O gesto existente suprime cliques por 1,2 s após disparar o toque longo.
 await page.waitForTimeout(1250);
 await expect(page.locator('.sp-route-option')).toHaveCount(1);
 await page.locator('.sp-route-option').click();
 await expect(page.locator('dialog[open]')).toHaveCount(0);
 await expect(page.locator('.sp-route-bus')).toHaveCount(1);
 await page.getByRole('button',{name:'Favoritos',exact:true}).click();
 await expect(page.getByRole('dialog',{name:'Pontos favoritos'})).toBeVisible();
 await page.getByRole('button',{name:'Fechar favoritos',exact:true}).click();
 await page.getByRole('button',{name:'Cancelar viagem',exact:true}).click();
 await page.getByRole('button',{name:'Confirmar cancelamento',exact:true}).click();
 await expect(page.locator('.sp-navigation-state')).toContainText('Selecionar embarque');
 expect(await page.evaluate(()=>JSON.parse(sessionStorage.getItem('pap.sp.session')))).toEqual({origin:null,destination:null});
 expect(requests).toHaveLength(0);
});
