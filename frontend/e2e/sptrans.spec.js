import { test, expect } from '@playwright/test';
const stop={id:'1',name:'Origem A',lat:-23.55,lon:-46.6333,directions:[{bearing:90,code:'1000-10',headsign:'Destino',kind:'departure'},{bearing:270,code:'1000-10',headsign:'Destino',kind:'arrival'}]};
async function setup(page) {
  await page.route('https://tile.openstreetmap.org/**',r=>r.abort());
  await page.route('**/api/sptrans/stops/**',r=>r.fulfill({json:{stops:[stop]}}));
  await page.route('**/api/sptrans/destination/**',r=>{const q=new URL(r.request().url()).searchParams;return r.fulfill({json:{stop:q.has('target')?stop:{id:'2',name:'Destino B',lat:Number(q.get('lat')),lon:Number(q.get('lon'))},max_transfers:2,direction_checked:true}});});
  await page.route('**/api/sptrans/board/**',r=>r.fulfill({json:{lines:[{trip_id:'T',code:'1000-10',headsign:'Centro',arrivals:[{time:'08:10',vehicle:123}],programme:[]}],journeys:[]}}));
}
for(const width of [390,1440]) {
  test(`mapa limpo atualiza ao arrastar sem recentrar em ${width}px`,async({page})=>{
    await page.setViewportSize({width,height:900});
    await setup(page);
    const requests=[];const errors=[];
    page.on('request',r=>{if(r.url().includes('/api/sptrans/'))requests.push(r.url());});
    page.on('pageerror',e=>errors.push(e.message));
    await page.goto('/sao-paulo/');
    await expect(page.locator('.sp-stop')).toHaveCount(1);
    await expect(page.locator('.sp-heading')).toHaveCount(1);
    await expect(page.getByRole('region',{name:'Navegação corrente'})).toHaveCount(0);
    await expect(page.getByRole('button',{name:'Buscar pontos nesta área'})).toHaveCount(0);
    const box=await page.locator('.sp-map').boundingBox();
    expect(box.width).toBeGreaterThan(width-25);expect(box.height).toBeGreaterThan(550);
    const previous=requests.length;
    const next=page.waitForRequest(r=>r.url().includes('/api/sptrans/stops/'));
    await page.mouse.move(box.x+box.width*.65,box.y+box.height*.6);
    await page.mouse.down();await page.mouse.move(box.x+box.width*.35,box.y+box.height*.6,{steps:15});await page.mouse.up();
    const query=new URL((await next).url()).searchParams;
    expect(Number(query.get('lon'))).not.toBeCloseTo(-46.6333,4);
    await expect(page.getByText('Atualizando pontos…')).toHaveCount(0);
    const location=await page.locator('.sp-stop').getAttribute('style');
    await page.waitForTimeout(900);
    expect(await page.locator('.sp-stop').getAttribute('style')).toBe(location);
    expect(requests.length-previous).toBe(1);
    expect(requests.every(u=>u.includes('/stops/'))).toBe(true);
    await page.getByRole('button',{name:'Ativar modo escuro'}).click();
    await page.screenshot({path:`test-results/sp-clean-map-${width}.png`});
    expect(errors).toEqual([]);
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  });
  test(`seleção no mapa e favoritos continuam acessíveis em ${width}px`,async({page})=>{
    await page.setViewportSize({width,height:900});await setup(page);await page.goto('/sao-paulo/');
    await page.locator('.sp-stop').click();
    await expect(page.getByRole('dialog')).toBeVisible();
    await page.getByRole('button',{name:'Adicionar embarque aos favoritos'}).click();
    await page.getByRole('textbox',{name:'Nome do favorito',exact:true}).fill('');
    await page.getByRole('textbox',{name:'Nome do favorito',exact:true}).fill('Origem A');
    await page.getByRole('button',{name:'Salvar favorito',exact:true}).click();
    await page.getByRole('button',{name:'Ver mapa'}).click();
    await page.getByRole('button',{name:'Favoritos',exact:true}).click();
    await expect(page.getByRole('button',{name:'Origem A · Origem A · 1',exact:true})).toBeVisible();
    await page.getByRole('button',{name:'Navegação',exact:true}).click();
    await page.locator('.sp-stop').click();
    await expect(page.locator('.sp-origin')).toHaveCount(1);
    expect(await page.evaluate(()=>JSON.parse(sessionStorage.getItem('pap.sp.session')).origin.id)).toBe('1');
  });
}
test('falha ao atualizar informa o erro e mantém os pontos anteriores',async({page})=>{
  await setup(page);await page.goto('/sao-paulo/');await expect(page.locator('.sp-stop')).toHaveCount(1);
  await page.route('**/api/sptrans/stops/**',r=>r.fulfill({status:503,json:{error:'Serviço indisponível'}}));
  const map=page.locator('.sp-map');await map.click({position:{x:200,y:200}});await page.keyboard.press('ArrowRight');
  await expect(page.getByRole('alert')).toBeVisible();await expect(page.locator('.sp-stop')).toHaveCount(1);
});

for(const width of [390,1440]) test(`autocomplete distingue bairros em ${width}px`,async({page})=>{
  await page.setViewportSize({width,height:900});await setup(page);
  const destination={id:'2',name:'Parada do destino',lat:-23.551,lon:-46.634};
  let searches=0;
  await page.route('**/api/sptrans/addresses/**',r=>{searches++;return r.fulfill({json:{suggestions:['Centro','Bela Vista'].map((district,i)=>({id:String(i),name:'Rua de teste',district,city:'São Paulo',label:'Rua de teste, '+district,lat:-23.551,lon:-46.634}))}});});
  await page.route('**/api/sptrans/destination/**',r=>r.fulfill({json:{stop:destination,distance_meters:12}}));
  await page.goto('/sao-paulo/');await page.locator('.sp-stop').click();
  await page.getByRole('button',{name:'Selecionar destino',exact:true}).click();
  await page.getByRole('button',{name:'Buscar endereço',exact:true}).click();
  const input=page.getByRole('combobox');
  await input.fill('Ru');await page.waitForTimeout(600);expect(searches).toBe(0);
  await input.fill('Rua de teste');await expect(page.getByRole('option')).toHaveCount(2);
  await expect(page.getByRole('option').last()).toContainText('Bela Vista');
  await page.screenshot({path:`test-results/sp-autocomplete-${width}.png`});
  await input.press('ArrowUp');await input.press('Enter');
  await expect(page.getByRole('dialog')).toContainText('Rua de teste, Bela Vista');
  await expect(page.getByRole('dialog')).toContainText('Parada do destino');
  await page.getByRole('button',{name:'Usar como destino'}).click();
  await expect(page.getByRole('dialog')).toContainText('Ônibus da sua rota');
  expect(await page.evaluate(()=>JSON.parse(sessionStorage.getItem('pap.sp.session')).destination.id)).toBe('2');
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
});
test('busca trata ausência de sugestões e falha do provedor',async({page})=>{
  await setup(page);await page.route('**/api/sptrans/addresses/**',r=>r.fulfill({json:{suggestions:[]}}));
  await page.goto('/sao-paulo/');await page.getByRole('button',{name:'Buscar endereço',exact:true}).click();
  await page.getByRole('combobox').fill('Não existe');await expect(page.getByRole('dialog')).toContainText('Nenhum endereço encontrado');
  await page.route('**/api/sptrans/addresses/**',r=>r.fulfill({status:502,json:{error:'Não foi possível buscar endereços agora.'}}));
  await page.getByRole('combobox').fill('Outra rua');await expect(page.getByRole('dialog').getByRole('alert')).toContainText('Não foi possível');
});

test('zoom e redimensionamento consultam os limites visíveis',async({page})=>{
  await setup(page);const queries=[];
  page.on('request',r=>{if(r.url().includes('/api/sptrans/stops/'))queries.push(new URL(r.url()).searchParams);});
  await page.goto('/sao-paulo/');await expect(page.locator('.sp-stop')).toHaveCount(1);
  const initial=queries.at(-1);
  for(const key of ['south','west','north','east'])expect(initial.has(key)).toBe(true);
  const zoomRequest=page.waitForRequest(r=>r.url().includes('/api/sptrans/stops/'));
  await page.getByRole('button',{name:'Zoom in',exact:true}).click();
  const zoomed=new URL((await zoomRequest).url()).searchParams;
  expect(Number(zoomed.get('north'))-Number(zoomed.get('south'))).toBeLessThan(Number(initial.get('north'))-Number(initial.get('south')));
  const resizedRequest=page.waitForRequest(r=>r.url().includes('/api/sptrans/stops/'));
  await page.setViewportSize({width:600,height:800});
  const resized=new URL((await resizedRequest).url()).searchParams;
  expect(Number(resized.get('east'))-Number(resized.get('west'))).not.toBe(Number(zoomed.get('east'))-Number(zoomed.get('west')));
});

test('mostra o primeiro lote sem aguardar as bordas e reutiliza marcadores',async({page})=>{
  await setup(page);
  let release;const gate=new Promise(resolve=>{release=resolve;});
  const edge={...stop,id:'2',name:'Borda',lat:-23.551};
  await page.route('**/api/sptrans/stops/**',async r=>{
    const offset=Number(new URL(r.request().url()).searchParams.get('offset'));
    if(offset)await gate;
    await r.fulfill({json:{stops:offset?[edge]:[stop],next_offset:offset?null:1,revision:'v1'}});
  });
  await page.goto('/sao-paulo/');
  await expect(page.locator('.sp-stop')).toHaveCount(1);
  await expect(page.getByText('Atualizando pontos…')).toBeVisible();
  await page.locator('.sp-stop').evaluate(el=>{window.firstMarker=el;});
  release();
  await expect(page.locator('.sp-stop')).toHaveCount(2);
  await expect(page.getByText('Atualizando pontos…')).toHaveCount(0);
  expect(await page.evaluate(()=>window.firstMarker.isConnected)).toBe(true);
});
test('voltar à área já carregada reutiliza cache do navegador',async({page})=>{
  await setup(page);let count=0;
  page.on('request',r=>{if(r.url().includes('/api/sptrans/stops/'))count++;});
  await page.goto('/sao-paulo/');await expect(page.locator('.sp-stop')).toHaveCount(1);
  await page.getByRole('button',{name:'Zoom in',exact:true}).click();
  await expect.poll(()=>count).toBe(2);
  await expect(page.getByText('Atualizando pontos…')).toHaveCount(0);
  await page.getByRole('button',{name:'Zoom out',exact:true}).click();
  await page.waitForTimeout(1000);
  expect(count).toBe(2);
  await expect(page.locator('.sp-stop')).toHaveCount(1);
});

for(const width of [390,1440]) test(`embarque, lista filtrada e cancelamento em ${width}px`,async({page})=>{
  await page.setViewportSize({width,height:900});await setup(page);
  const other={...stop,id:'2',name:'Destino B',lat:-23.551,lon:-46.634};
  await page.route('**/api/sptrans/stops/**',r=>r.fulfill({json:{stops:[stop,other]}}));
  const leg={origin:stop,destination:other,stops:[stop,other],color:'#1372db',code:'1000-10',headsign:'Centro'};
  await page.route('**/api/sptrans/board/**',r=>{
    const q=new URL(r.request().url()).searchParams,filtered=q.get('destination')==='2';
    if(filtered)expect(q.get('route_only')).toBe('1');
    return r.fulfill({json:{lines:[{trip_id:'T',code:'1000-10',headsign:'Centro',arrivals:[{time:'08:10',vehicle:123}],...(filtered?{origin:stop,destination:other}:{})},...(!filtered?[{trip_id:'X',code:'2000-10',headsign:'Outra linha',arrivals:[]}]:[])],journeys:filtered?[{legs:[leg]}]:[]}});
  });
  const state=page.getByRole('region',{name:'Estado da navegação'});
  await page.goto('/sao-paulo/');await expect(state).toContainText('Selecionar local de embarque');
  await page.getByRole('button',{name:'Ativar modo escuro'}).click();await page.locator('.sp-stop').first().click();
  const dialog=page.getByRole('dialog');
  await expect(dialog).toContainText('Próximos ônibus');await expect(dialog).toContainText('2000-10');
  await page.screenshot({path:`test-results/sp-board-${width}.png`});
  await page.getByRole('button',{name:'Selecionar destino',exact:true}).click();
  await expect(dialog).not.toBeVisible();await expect(state).toContainText('Selecionar destino');
  await page.getByRole('button',{name:'Cancelar seleção'}).click();await expect(dialog).toBeVisible();
  await page.getByRole('button',{name:'Selecionar destino',exact:true}).click();await page.locator('.sp-stop:not(.sp-origin)').click();
  await expect(dialog).toContainText('Ônibus da sua rota');await expect(dialog).toContainText('08:10');await expect(dialog).not.toContainText('2000-10');
  await page.screenshot({path:`test-results/sp-route-${width}.png`});
  await dialog.getByRole('button',{name:'Cancelar viagem',exact:true}).click();
  await page.getByRole('button',{name:'Confirmar cancelamento'}).click();
  await expect(dialog).not.toBeVisible();await expect(state).toContainText('Selecionar local de embarque');
  expect(await page.evaluate(()=>JSON.parse(sessionStorage.getItem('pap.sp.session')).origin)).toBeNull();
  expect(new URL(page.url()).searchParams.has('stop')).toBe(false);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
});

test('rua sem número enquadra suas paradas e aguarda escolha no mapa',async({page})=>{
  await setup(page);
  const far={...stop,id:'8',name:'Rua Augusta, 800',lat:-23.57,lon:-46.64};
  await page.route('**/api/sptrans/addresses/**',r=>r.fulfill({json:{suggestions:[{id:'a',name:'Rua Augusta',street:'Rua Augusta',kind:'street',label:'Rua Augusta, São Paulo',lat:-23.55,lon:-46.63}]}}));
  await page.route('**/api/sptrans/destination/**',r=>{
    expect(new URL(r.request().url()).searchParams.get('street')).toBe('Rua Augusta');
    return r.fulfill({json:{stops:[stop,far]}});
  });
  await page.goto('/sao-paulo/');await page.getByRole('button',{name:'Buscar endereço',exact:true}).click();
  await page.getByRole('combobox').fill('Rua Augusta');await page.getByRole('option').click();
  await expect(page.getByRole('dialog')).not.toBeVisible();
  await expect(page.locator('.sp-stop')).toHaveCount(2);
  await expect(page.getByRole('region',{name:'Estado da navegação'})).toContainText('Selecionar local de embarque');
  const map=await page.locator('.sp-map').boundingBox();
  for(const marker of await page.locator('.sp-stop').all()){
    const box=await marker.boundingBox();expect(box.x).toBeGreaterThan(map.x);expect(box.x).toBeLessThan(map.x+map.width);expect(box.y).toBeGreaterThan(map.y);expect(box.y).toBeLessThan(map.y+map.height);
  }
  expect(await page.evaluate(()=>JSON.parse(sessionStorage.getItem('pap.sp.session')).origin)).toBeNull();
  await page.locator('.sp-stop').last().click();await expect(page.getByRole('dialog')).toContainText('Próximos ônibus');
});

test('ônibus sólido e caminhada tracejada têm contraste nos dois temas',async({page})=>{
  await setup(page);
  const destination={id:'2',name:'Destino',lat:-23.551,lon:-46.634,addressCoordinates:{lat:-23.5512,lon:-46.6342}};
  const geometry=[[stop.lat,stop.lon],[-23.55,-46.634],[destination.lat,destination.lon]];
  await page.addInitScript(({stop,destination})=>sessionStorage.setItem('pap.sp.session',JSON.stringify({origin:stop,destination})),{stop,destination});
  await page.route('**/api/sptrans/board/**',r=>r.fulfill({json:{lines:[],journeys:[{legs:[{origin:stop,destination,stops:[stop,destination],geometry}]}]}}));
  await page.route('**/api/sptrans/walk/**',r=>r.fulfill({json:{available:true,geometry:[[destination.lat,destination.lon],[-23.5511,-46.634],[-23.5512,-46.6342]]}}));
  await page.goto('/sao-paulo/');await page.getByRole('button',{name:'Ver próximos ônibus'}).click();
  await expect(page.locator('.sp-route-bus')).toHaveCount(1);
  await expect(page.locator('.sp-route-walk')).toHaveCount(1);
  await page.getByRole('button',{name:'Ver mapa'}).click();
  await expect(page.locator('.sp-route-bus')).not.toHaveAttribute('stroke-dasharray',/.+/);
  await expect(page.locator('.sp-route-walk')).toHaveAttribute('stroke-dasharray','9 10');
  for(const dark of [false,true]){
    if(dark)await page.getByRole('button',{name:'Ativar modo escuro'}).click();
    expect(await page.locator('.sp-route-bus').evaluate(el=>getComputedStyle(el).stroke)).toBe(dark?'rgb(66, 200, 255)':'rgb(0, 118, 237)');
    expect(await page.locator('.sp-route-walk').evaluate(el=>getComputedStyle(el).stroke)).toBe(dark?'rgb(255, 121, 203)':'rgb(213, 44, 148)');
    await page.screenshot({path:`test-results/sp-routes-${dark?'dark':'light'}.png`});
  }
});

test('rota selecionada mostra só extremos e restaura pontos ao alterar destino',async({page})=>{
  await setup(page);
  const destination={...stop,id:'2',name:'Destino',lat:-23.551};
  const transfer={...stop,id:'3',name:'Troca',lat:-23.5505};
  const extra={...stop,id:'4',name:'Outra parada',lat:-23.5508,lon:-46.634};
  await page.route('**/api/sptrans/stops/**',r=>r.fulfill({json:{stops:[stop,destination,transfer,extra]}}));
  await page.addInitScript(({stop,destination})=>sessionStorage.setItem('pap.sp.session',JSON.stringify({origin:stop,destination})),{stop,destination});
  const legs=[{origin:stop,destination:transfer,stops:[stop,transfer],geometry:[[stop.lat,stop.lon],[transfer.lat,transfer.lon]]},{origin:transfer,destination,stops:[transfer,destination],geometry:[[transfer.lat,transfer.lon],[destination.lat,destination.lon]]}];
  await page.route('**/api/sptrans/board/**',r=>r.fulfill({json:{lines:[],journeys:[{legs}]}}));
  await page.goto('/sao-paulo/');await expect(page.locator('.sp-stop')).toHaveCount(3);
  await page.getByRole('button',{name:'Ver próximos ônibus'}).click();
  await expect(page.locator('.sp-stop')).toHaveCount(3);
  await expect(page.locator('.sp-origin')).toHaveCount(1);await expect(page.locator('.sp-destination')).toHaveCount(1);
  await expect(page.locator('.sp-route-bus')).toHaveCount(2);
  await page.getByRole('button',{name:'Ver mapa'}).click();await expect(page.locator('.sp-stop')).toHaveCount(3);
  await page.getByRole('button',{name:'Ver próximos ônibus'}).click();
  await page.getByRole('button',{name:'Alterar destino',exact:true}).click();await expect(page.locator('.sp-stop')).toHaveCount(4);
  await expect(page.locator('.sp-route-bus')).toHaveCount(0);
  await page.getByRole('button',{name:'Cancelar seleção'}).click();
  await expect(page.locator('.sp-stop')).toHaveCount(3);
  await page.getByRole('button',{name:'Ver mapa'}).click();
  await expect(page.locator('.sp-stop')).toHaveCount(3);
  await page.getByRole('button',{name:'Cancelar viagem',exact:true}).click();await page.getByRole('button',{name:'Confirmar cancelamento'}).click();await expect(page.locator('.sp-stop')).toHaveCount(4);
  await expect(page.locator('.sp-route-bus')).toHaveCount(0);
});

test('fechar lista antes da resposta não cancela rota nem reexibe paradas',async({page})=>{
  await setup(page);
  const destination={...stop,id:'2',name:'Destino',lat:-23.551};
  const extra={...stop,id:'3',name:'Outro ponto',lat:-23.5505,lon:-46.634};
  await page.route('**/api/sptrans/stops/**',r=>r.fulfill({json:{stops:[stop,destination,extra]}}));
  let release;const gate=new Promise(resolve=>release=resolve);
  await page.route('**/api/sptrans/board/**',async r=>{
    const selected=new URL(r.request().url()).searchParams.has('destination');
    if(selected)await gate;
    await r.fulfill({json:{lines:[],journeys:selected?[{legs:[{origin:stop,destination,stops:[stop,destination],geometry:[[stop.lat,stop.lon],[destination.lat,destination.lon]]}]}]:[]}});
  });
  await page.goto('/sao-paulo/');await page.locator('.sp-stop').first().click();
  await page.getByRole('button',{name:'Selecionar destino',exact:true}).click();
  await page.locator('.sp-stop[title^="Destino ·"]').click();
  await page.getByRole('button',{name:'Ver mapa'}).click();
  await expect(page.locator('.sp-stop')).toHaveCount(2);
  await expect(page.getByText('Calculando rota…',{exact:true})).toBeVisible();
  release();await expect(page.locator('.sp-route-bus')).toHaveCount(1);
  await expect(page.locator('.sp-stop')).toHaveCount(2);
  await page.locator('.sp-origin').click();await expect(page.getByRole('dialog')).toContainText('Ônibus da sua rota');
});

test('nome do favorito persiste e pode ser alterado sem mudar a parada',async({page})=>{
  await setup(page);await page.goto('/sao-paulo/');await page.locator('.sp-stop').click();
  await page.getByRole('button',{name:'Adicionar embarque aos favoritos'}).click();
  await page.getByRole('textbox',{name:'Nome do favorito',exact:true}).fill('Casa');
  await page.getByRole('button',{name:'Salvar favorito',exact:true}).click();
  await page.getByRole('button',{name:'Ver mapa'}).click();
  await page.reload();await page.getByRole('button',{name:'Ver mapa'}).click();
  await page.getByRole('button',{name:'Favoritos',exact:true}).click();
  await expect(page.getByRole('button',{name:'Casa · Origem A · 1',exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Renomear favorito Casa'}).click();
  await page.getByRole('textbox',{name:'Nome do favorito',exact:true}).fill('Trabalho');
  await page.getByRole('button',{name:'Salvar favorito',exact:true}).click();
  const stored=await page.evaluate(()=>JSON.parse(localStorage.getItem('pap.sp.favorites')));
  expect(stored).toHaveLength(1);expect(stored[0].favoriteLabel).toBe('Trabalho');expect(stored[0].name).toBe('Origem A');expect(stored[0].id).toBe('1');
});


test('selecionar destino oferece favoritos e preserva a referência para calcular alternativas',async({page})=>{
  await setup(page);
  const saved={id:'8',name:'Lado de retorno',favoriteLabel:'Casa',lat:-23.551,lon:-46.634};
  await page.addInitScript(saved=>localStorage.setItem('pap.sp.favorites',JSON.stringify([saved])),saved);
  await page.route('**/api/sptrans/destination/**',r=>{
    const query=new URL(r.request().url()).searchParams;
    if(query.has('target'))return r.fulfill({json:{stop,max_transfers:2}});
    expect(query.get('origin')).toBe('1');
    return r.fulfill({json:{stop:{...saved,id:'9',name:'Lado adequado'},max_transfers:0,direction_checked:true}});
  });
  await page.route('**/api/sptrans/walk/**',r=>r.fulfill({json:{available:false,message:'Sem percurso'}}));
  await page.goto('/sao-paulo/');await page.locator('.sp-stop').click();
  await page.getByRole('button',{name:'Selecionar destino',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Pontos favoritos'})).toBeVisible();
  await page.getByRole('button',{name:'Buscar no mapa'}).click();
  await expect(page.locator('.sp-map')).toBeVisible();
  await page.getByRole('button',{name:'Favoritos',exact:true}).click();
  await page.getByRole('button',{name:'Casa · Lado de retorno · 8',exact:true}).click();
  await expect(page.getByRole('dialog',{name:'Ônibus da sua rota'})).toContainText('Lado de retorno');
  const data=await page.evaluate(()=>({session:JSON.parse(sessionStorage.getItem('pap.sp.session')),favorites:JSON.parse(localStorage.getItem('pap.sp.favorites'))}));
  expect(data.session.destination.id).toBe('8');expect(data.favorites[0].id).toBe('8');
});

test('seleciona trecho na lista e no mapa e fechar mostra viagem completa',async({page})=>{
  await setup(page);
  const middle={...stop,id:'2',name:'Troca',lat:-23.551};
  const end={...stop,id:'3',name:'Fim',lat:-23.552};
  const legs=[[stop,middle],[middle,end]].map(([origin,destination],i)=>({trip_id:'T'+i,code:'L'+i,headsign:'Fim',origin,destination,stops:[origin,destination],geometry:[[origin.lat,origin.lon],[destination.lat,destination.lon]]}));
  await page.addInitScript(({stop,end})=>sessionStorage.setItem('pap.sp.session',JSON.stringify({origin:stop,destination:end})),{stop,end});
  await page.route('**/api/sptrans/board/**',r=>r.fulfill({json:{lines:legs,journeys:[{legs}]}}));
  await page.goto('/sao-paulo/');await page.getByRole('button',{name:'Ver próximos ônibus'}).click();
  await page.getByRole('button',{name:'Ver trecho 2: L1 no mapa'}).click();
  await expect(page.getByRole('dialog')).not.toBeVisible();
  await expect(page.locator('.sp-route-bus')).toHaveCount(1);
  await expect(page.locator('.sp-transfer-stop')).toHaveAttribute('title',/Troca/);
  await page.getByLabel('Trecho exibido no mapa').selectOption('all');
  await expect(page.locator('.sp-route-bus')).toHaveCount(2);
  await page.getByLabel('Trecho exibido no mapa').selectOption('0');
  await expect(page.locator('.sp-route-bus')).toHaveCount(1);
  await page.getByRole('button',{name:'Ver próximos ônibus'}).click();
  await page.getByRole('button',{name:'Ver mapa'}).click();
  await expect(page.locator('.sp-route-bus')).toHaveCount(2);
});

test('baldeações B e C mantêm identificação na viagem e nos trechos',async({page})=>{
  await setup(page);
  const points=Array.from({length:4},(_,i)=>({...stop,id:String(i+1),name:'Ponto '+i,lat:stop.lat-i*.001}));
  const legs=points.slice(0,3).map((origin,i)=>({trip_id:'T'+i,code:'L'+i,origin,destination:points[i+1],stops:[origin,points[i+1]],geometry:[[origin.lat,origin.lon],[points[i+1].lat,points[i+1].lon]]}));
  await page.addInitScript(points=>sessionStorage.setItem('pap.sp.session',JSON.stringify({origin:points[0],destination:points[3]})),points);
  await page.route('**/api/sptrans/board/**',r=>r.fulfill({json:{lines:legs,journeys:[{legs}]}}));
  await page.goto('/sao-paulo/');
  await expect(page.locator('.sp-stop')).toHaveCount(4);
  expect(await page.locator('.sp-stop').allTextContents()).toEqual(expect.arrayContaining(['A','B','C','★']));
  for(const [index,labels] of [['0',['A','B']],['1',['B','C']],['2',['C','★']]]){
    await page.getByLabel('Trecho exibido no mapa').selectOption(index);
    await expect(page.locator('.sp-stop')).toHaveCount(2);
    expect(await page.locator('.sp-stop').allTextContents()).toEqual(expect.arrayContaining(labels));
  }
  await page.getByLabel('Trecho exibido no mapa').selectOption('all');
  await expect(page.locator('.sp-stop')).toHaveCount(4);
});

test('horários reabrem pelo mapa após trecho, fechar e Escape',async({page})=>{
  await setup(page);
  const destination={...stop,id:'2',lat:-23.551};
  const legs=[{trip_id:'T',code:'1000-10',origin:stop,destination,stops:[stop,destination],geometry:[[stop.lat,stop.lon],[destination.lat,destination.lon]],arrivals:[{time:'08:10',vehicle:123}]}];
  await page.addInitScript(({stop,destination})=>sessionStorage.setItem('pap.sp.session',JSON.stringify({origin:stop,destination})),{stop,destination});
  await page.route('**/api/sptrans/board/**',r=>r.fulfill({json:{lines:legs,journeys:[{legs}]}}));
  await page.goto('/sao-paulo/');await page.getByRole('button',{name:'Ver próximos ônibus'}).click();
  await page.getByRole('button',{name:'Ver trecho 1: 1000-10 no mapa'}).click();
  await page.getByRole('button',{name:'Horários de embarque',exact:true}).click();
  await expect(page.getByRole('dialog',{name:'Ônibus da sua rota'})).toContainText('08:10');
  await page.keyboard.press('Escape');
  await expect(page.getByRole('dialog')).not.toBeVisible();
  await page.getByRole('button',{name:'Ver próximos ônibus'}).click();
  await expect(page.getByRole('dialog')).toContainText('08:10');
  await page.getByRole('button',{name:'Ver mapa'}).click();
  await page.locator('.sp-origin').click();
  await expect(page.getByRole('dialog')).toContainText('08:10');
});

test('trechos preservam caminhadas de embarque e destino correspondentes',async({page})=>{
  await setup(page);
  const origin={...stop,addressCoordinates:{lat:-23.5498,lon:stop.lon}};
  const middle={...stop,id:'2',lat:-23.551};
  const destination={...stop,id:'3',lat:-23.552,addressCoordinates:{lat:-23.5522,lon:stop.lon}};
  const legs=[[origin,middle],[middle,destination]].map(([origin,destination],i)=>({trip_id:'T'+i,origin,destination,stops:[origin,destination],geometry:[[origin.lat,origin.lon],[destination.lat,destination.lon]]}));
  await page.addInitScript(({origin,destination})=>sessionStorage.setItem('pap.sp.session',JSON.stringify({origin,destination})),{origin,destination});
  await page.route('**/api/sptrans/board/**',r=>r.fulfill({json:{lines:[],journeys:[{legs}]}}));
  let queries=0;
  await page.route('**/api/sptrans/walk/**',r=>{queries++;const boarding=new URL(r.request().url()).searchParams.has('from_lat');return r.fulfill({json:{available:true,geometry:boarding?[[-23.5498,stop.lon],[origin.lat,origin.lon]]:[[destination.lat,destination.lon],[-23.5522,stop.lon]]}});});
  await page.goto('/sao-paulo/');await expect(page.locator('.sp-route-walk')).toHaveCount(2);
  await page.getByLabel('Trecho exibido no mapa').selectOption('1');await expect(page.locator('.sp-route-walk')).toHaveCount(1);
  const last=await page.locator('.sp-route-walk').getAttribute('d');
  await page.getByLabel('Trecho exibido no mapa').selectOption('0');await expect(page.locator('.sp-route-walk')).toHaveCount(1);
  expect(await page.locator('.sp-route-walk').getAttribute('d')).not.toBe(last);
  await page.getByLabel('Trecho exibido no mapa').selectOption('all');await expect(page.locator('.sp-route-walk')).toHaveCount(2);
  expect(queries).toBe(2);
});

test('estrela salva confirma remoção e cancelar preserva o favorito',async({page})=>{
  await setup(page);
  await page.addInitScript(stop=>{if(localStorage.getItem('pap.sp.favorites')===null)localStorage.setItem('pap.sp.favorites',JSON.stringify([{...stop,favoriteLabel:'Casa'}]));},stop);
  await page.goto('/sao-paulo/');await page.locator('.sp-stop').click();
  await page.getByRole('button',{name:'Remover favorito',exact:true}).click();
  const confirmation=page.getByRole('dialog',{name:'Remover favorito?'});
  await expect(confirmation).toContainText('Casa');
  await expect(page.getByRole('textbox',{name:'Nome do favorito'})).not.toBeVisible();
  await confirmation.getByRole('button',{name:'Cancelar',exact:true}).click();
  expect(await page.evaluate(()=>JSON.parse(localStorage.getItem('pap.sp.favorites')).length)).toBe(1);
  await page.getByRole('button',{name:'Remover favorito',exact:true}).click();
  await confirmation.getByRole('button',{name:'Remover favorito',exact:true}).click();
  await expect(page.getByRole('button',{name:'Adicionar embarque aos favoritos'})).toBeVisible();
  expect(await page.evaluate(()=>JSON.parse(localStorage.getItem('pap.sp.favorites')))).toEqual([]);
  expect(await page.evaluate(()=>JSON.parse(sessionStorage.getItem('pap.sp.session')).origin.id)).toBe('1');
  await page.reload();await expect(page.getByRole('button',{name:'Adicionar embarque aos favoritos'})).toBeVisible();
});

for(const width of [390,756]) test(`etapa no topo e cancelamento confirmado em ${width}px`,async({page})=>{
  await page.setViewportSize({width,height:900});await setup(page);await page.goto('/sao-paulo/');
  const brand=await page.locator('.sp-header-brand').boundingBox(),state=await page.getByRole('region',{name:'Estado da navegação'}).boundingBox();
  expect(state.y).toBeLessThan(brand.y+brand.height);expect(state.x).toBeGreaterThan(brand.x);
  await page.locator('.sp-stop').click();await page.getByRole('button',{name:'Ver mapa',exact:true}).click();
  await page.getByRole('button',{name:'Cancelar viagem',exact:true}).click();
  await page.getByRole('button',{name:'Continuar viagem'}).click();
  expect(await page.evaluate(()=>JSON.parse(sessionStorage.getItem('pap.sp.session')).origin.id)).toBe('1');
  await page.getByRole('button',{name:'Ver próximos ônibus'}).click();
  await page.getByRole('dialog',{name:'Próximos ônibus'}).getByRole('button',{name:'Cancelar viagem'}).click();
  await page.getByRole('button',{name:'Confirmar cancelamento'}).click();
  expect(await page.evaluate(()=>JSON.parse(sessionStorage.getItem('pap.sp.session')).origin)).toBeNull();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
});


test('três rotas mais rápidas, expansão e escolha preservam caminhada na baldeação',async({page})=>{
  await setup(page);
  const end={...stop,id:'8',name:'Destino',lat:-23.553};
  const transfer={...stop,id:'3',name:'Desembarque',lat:-23.551};
  const boarding={...stop,id:'4',name:'Plataforma próxima',lat:-23.5515};
  const journeys=Array.from({length:5},(_,i)=>({id:'route-'+i,duration_minutes:20+i,transfers:1,walking_meters:100,walking_minutes:1.5,
    legs:[{trip_id:'A'+i,code:'A'+i,origin:stop,destination:transfer,geometry:[[stop.lat,stop.lon],[transfer.lat,transfer.lon]],departure:'2026-10-06T08:00:00-03:00'},
          {trip_id:'B'+i,code:'B'+i,origin:boarding,destination:end,geometry:[[boarding.lat,boarding.lon],[end.lat,end.lon]],departure:'2026-10-06T08:10:00-03:00'}],
    walks:[{available:true,accessType:'transfer',before_leg:1,origin:transfer,destination:boarding,distance_meters:100,duration_minutes:1.5,geometry:[[transfer.lat,transfer.lon],[boarding.lat,boarding.lon]]}]}));
  await page.addInitScript(({stop,end})=>sessionStorage.setItem('pap.sp.session',JSON.stringify({origin:stop,destination:end})),{stop,end});
  await page.route('**/api/sptrans/board/**',r=>{
    const query=new URL(r.request().url()).searchParams;
    expect(query.get('nearby')).toBe('1');
    const chosen=journeys.find(j=>j.id===query.get('journey'))||journeys[0];
    return r.fulfill({json:{journeys,selected_journey:chosen.id,lines:chosen.legs.map(l=>({...l,headsign:'Destino',arrivals:[],planned_departure:l.departure}))}});
  });
  await page.goto('/sao-paulo/');
  await page.getByRole('button',{name:'Ver próximos ônibus',exact:true}).click();
  const options=page.getByRole('region',{name:'Alternativas de viagem'});
  await expect(options.locator('.sp-route-option')).toHaveCount(3);
  await page.getByRole('button',{name:'Mostrar todas as 5 rotas calculadas'}).click();
  await expect(options.locator('.sp-route-option')).toHaveCount(5);
  await options.locator('.sp-route-option').nth(4).click();
  await expect(page.getByRole('button',{name:'Ver trecho 1: A4 no mapa'})).toBeVisible();
  await expect(page.getByRole('region',{name:'Caminhadas da rota'})).toContainText('100 m · 1.5 min');
  await page.getByRole('button',{name:'Ver trecho 2: B4 no mapa'}).click();
  await expect(page.locator('path.sp-route-walk')).not.toHaveCount(0);
  await page.getByRole('button',{name:'Ver próximos ônibus',exact:true}).click();
  await expect(options.locator('.sp-route-option').nth(4)).toHaveAttribute('aria-pressed','true');
  await page.getByRole('button',{name:'Mostrar apenas as três mais rápidas'}).click();
  await expect(options.locator('.sp-route-option')).toHaveCount(3);
});


test('stream mostra a primeira rota antes do fim e preserva escolha com novas alternativas',async({page})=>{
  await setup(page);
  const end={...stop,id:'8',name:'Destino',lat:-23.553};
  await page.addInitScript(({stop,end})=>{
    sessionStorage.setItem('pap.sp.session',JSON.stringify({origin:stop,destination:end}));
    const originalFetch=window.fetch;
    window.fetch=(url,options)=>{
      if(String(url).includes('/sptrans/board/')){
        return Promise.resolve(new Response(new ReadableStream({start(controller){
          const route=(id,minutes)=>({id,duration_minutes:minutes,transfers:0,walks:[],legs:[{trip_id:id,code:id,origin:stop,destination:end,geometry:[[stop.lat,stop.lon],[end.lat,end.lon]]}]});
          const first=route('Primeira',30),later=route('Mais rápida',20);
          const send=(journeys,complete)=>controller.enqueue(new TextEncoder().encode(JSON.stringify({journeys,complete,selected_journey:journeys[0].id,lines:journeys[0].legs.map(l=>({...l,arrivals:[]}))})+'\n'));
          send([first],false);
          window.finishRoutes=()=>{send([later,first],true);controller.close();};
        }}),{headers:{'Content-Type':'application/x-ndjson'}}));
      }
      return originalFetch(url,options);
    };
  },{stop,end});
  await page.goto('/sao-paulo/');await page.getByRole('button',{name:'Ver próximos ônibus',exact:true}).click();
  const options=page.getByRole('region',{name:'Alternativas de viagem'});
  await expect(options.locator('.sp-route-option')).toHaveCount(1);
  await expect(page.getByText(/As rotas aparecem conforme/)).toBeVisible();
  await options.locator('.sp-route-option').click();
  await page.evaluate(()=>window.finishRoutes());
  await expect(options.locator('.sp-route-option')).toHaveCount(2);
  await expect(options.locator('.sp-route-option').first()).toContainText('Mais rápida');
  await expect(options.locator('.sp-route-option').last()).toHaveAttribute('aria-pressed','true');
  await expect(page.getByRole('button',{name:'Ver trecho 1: Primeira no mapa'})).toBeVisible();
  await expect(page.getByText(/As rotas aparecem conforme/)).not.toBeVisible();
});
