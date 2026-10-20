import {test,expect} from './coverage.js';
test.use({viewport:{width:390,height:844},isMobile:true,hasTouch:true});
test('toque prolongado escolhe coordenadas; toque curto, arrasto e dois dedos não escolhem',async({page,context})=>{
  await page.route('https://tile.openstreetmap.org/**',r=>r.abort());
  await page.route('**/api/location-config/**',r=>r.fulfill({json:{position:{lat:-23.55,lon:-46.63,accuracy:0,simulated:true}}}));
  await page.route('**/api/sptrans/stops/**',r=>r.fulfill({json:{stops:[]}}));
  const destinations=[],boards=[];
  await page.route('**/api/sptrans/destination/**',r=>{
    destinations.push(new URL(r.request().url()).searchParams);
    return r.fulfill({json:{stop:{id:'2',name:'Parada próxima',lat:-23.551,lon:-46.631},distance_meters:100}});
  });
  await page.route('**/api/sptrans/board/**',r=>{
    boards.push(new URL(r.request().url()).searchParams);
    return r.fulfill({json:{lines:[],journeys:[]}});
  });
  await page.goto('/');
  await expect(page.locator('.sp-passenger-position')).toBeVisible();
  const box=await page.locator('.sp-map').boundingBox();
  const x=Math.round(box.x+box.width*.7),y=Math.round(box.y+box.height*.4);
  const cdp=await context.newCDPSession(page);
  const touch=(type,points)=>cdp.send('Input.dispatchTouchEvent',{type,touchPoints:points});
  const point={x,y,id:1};
  await page.touchscreen.tap(x,y);
  await page.waitForTimeout(750);
  expect(destinations).toHaveLength(0);
  await touch('touchStart',[point]);
  await touch('touchMove',[{...point,x:x-60}]);
  await page.waitForTimeout(750);
  await touch('touchEnd',[]);
  expect(destinations).toHaveLength(0);
  await touch('touchStart',[point]);
  await touch('touchStart',[point,{x:x-80,y,id:2}]);
  await page.waitForTimeout(750);
  await touch('touchEnd',[]);
  expect(destinations).toHaveLength(0);
  await touch('touchStart',[point]);
  await page.waitForTimeout(750);
  await touch('touchEnd',[]);
  await expect.poll(()=>destinations.length).toBe(1);
  await expect.poll(()=>boards.length).toBe(1);
  expect(boards[0].get('to_lat')).toBe(destinations[0].get('lat'));
  expect(boards[0].get('to_lon')).toBe(destinations[0].get('lon'));
  expect(boards[0].get('to_lat')).not.toBe('-23.551');
  await expect(page.getByRole('dialog')).toContainText('Local selecionado no mapa');
  const previousDestination=Object.fromEntries(['destination','to_lat','to_lon'].map(key=>[key,boards[0].get(key)]));
  // Alterar embarque em uma rota já selecionada deve preservar o destino.
  await page.waitForTimeout(1250);
  await page.getByRole('button',{name:'Ver mapa',exact:true}).click();
  await page.getByRole('button',{name:'Alterar embarque',exact:true}).click();
  await touch('touchStart',[{...point,x:x-30}]);
  await page.waitForTimeout(750);
  await touch('touchEnd',[]);
  await expect.poll(()=>destinations.length).toBe(2);
  await expect.poll(()=>boards.length).toBe(2);
  expect(boards[1].get('from_lat')).toBe(destinations[1].get('lat'));
  expect(boards[1].get('from_lon')).toBe(destinations[1].get('lon'));
  for(const [key,value] of Object.entries(previousDestination))expect(boards[1].get(key)).toBe(value);
  const session=await page.evaluate(()=>JSON.parse(sessionStorage.getItem('pap.sp.session')));
  expect(session.origin.manualBoarding).toBe(true);
  expect(session.destination.addressCoordinates.lat).toBe(Number(previousDestination.to_lat));
  expect(session.destination.addressCoordinates.lon).toBe(Number(previousDestination.to_lon));
});

test('clique longo com pequena oscilação do mouse seleciona o local',async({browser})=>{
  const context=await browser.newContext({viewport:{width:1200,height:900},isMobile:false,hasTouch:false});
  const page=await context.newPage();
  await page.route('https://tile.openstreetmap.org/**',r=>r.abort());
  await page.route('**/api/location-config/**',r=>r.fulfill({json:{position:{lat:-23.55,lon:-46.63,accuracy:0,simulated:true}}}));
  await page.route('**/api/sptrans/stops/**',r=>r.fulfill({json:{stops:[]}}));
  let selections=0;
  await page.route('**/api/sptrans/destination/**',r=>{selections++;return r.fulfill({json:{stop:{id:'2',name:'Destino',lat:-23.551,lon:-46.631}}});});
  await page.route('**/api/sptrans/board/**',r=>r.fulfill({json:{lines:[],journeys:[]}}));
  await page.goto('/');
  await expect(page.locator('.sp-passenger-position')).toBeVisible();
  const box=await page.locator('.sp-map').boundingBox(),x=box.x+box.width*.7,y=box.y+box.height*.4;
  await page.mouse.move(x,y);await page.mouse.down();await page.waitForTimeout(100);
  await page.mouse.move(x+5,y+2,{steps:2});await page.waitForTimeout(800);await page.mouse.up();
  await expect.poll(()=>selections).toBe(1);
  await context.close();
});

for(const restored of [false,true]) test(`mapa conserva embarque ao escolher destino no computador (restaurado=${restored})`,async({browser})=>{
  const context=await browser.newContext({viewport:{width:1200,height:900},isMobile:false,hasTouch:false});
  const page=await context.newPage();
  const origin={id:'1',name:'Embarque definido',lat:-23.55,lon:-46.63,manualBoarding:true,addressCoordinates:{lat:-23.5501,lon:-46.6301}};
  if(restored)await page.addInitScript(origin=>sessionStorage.setItem('pap.sp.session',JSON.stringify({origin,destination:null})),origin);
  await page.route('https://tile.openstreetmap.org/**',r=>r.abort());
  await page.route('**/api/location-config/**',r=>r.fulfill({json:{position:null}}));
  await page.route('**/api/sptrans/stops/**',r=>r.fulfill({json:{stops:[origin]}}));
  await page.route('**/api/sptrans/destination/**',r=>r.fulfill({json:{stop:{id:'2',name:'Destino',lat:-23.551,lon:-46.631}}}));
  await page.route('**/api/sptrans/board/**',r=>r.fulfill({json:{lines:[],journeys:[]}}));
  await page.goto('/?stop=1');
  if(!restored){await expect(page.getByRole('dialog')).toBeVisible();await page.getByRole('button',{name:'Ver mapa',exact:true}).click();}
  await expect(page.locator('.sp-navigation-state')).toContainText('Selecionar destino');
  const box=await page.locator('.sp-map').boundingBox();await page.mouse.move(box.x+box.width*.7,box.y+box.height*.4);
  await page.mouse.down();await page.waitForTimeout(800);await page.mouse.up();
  await expect.poll(async()=>page.evaluate(()=>JSON.parse(sessionStorage.getItem('pap.sp.session')).destination?.id)).toBe('2');
  const session=await page.evaluate(()=>JSON.parse(sessionStorage.getItem('pap.sp.session')));
  expect(session.origin.id).toBe('1');
  if(restored)expect(session.origin.addressCoordinates).toEqual(origin.addressCoordinates);
  await context.close();
});

test('sem geolocalização nem embarque, primeiro clique longo define origem e segundo define destino',async({browser})=>{
  const context=await browser.newContext({viewport:{width:1200,height:900},isMobile:false,hasTouch:false});
  const page=await context.newPage();
  await page.route('https://tile.openstreetmap.org/**',r=>r.abort());
  await page.route('**/api/location-config/**',r=>r.fulfill({json:{position:null}}));
  await page.route('**/api/sptrans/stops/**',r=>r.fulfill({json:{stops:[]}}));
  let selections=0;
  await page.route('**/api/sptrans/destination/**',r=>{selections++;return r.fulfill({json:{stop:{id:String(selections),name:'Local '+selections,lat:-23.551,lon:-46.631}}});});
  await page.route('**/api/sptrans/board/**',r=>r.fulfill({json:{lines:[],journeys:[]}}));
  await page.goto('/');
  await expect(page.locator('.sp-navigation-state')).toContainText('Selecionar embarque');
  const hold=async()=>{const box=await page.locator('.sp-map').boundingBox();await page.mouse.move(box.x+box.width*.7,box.y+box.height*.4);await page.mouse.down();await page.waitForTimeout(800);await page.mouse.up();};
  await hold();
  await expect(page.locator('.sp-navigation-state')).toContainText('Selecionar destino');
  const origin=await page.evaluate(()=>JSON.parse(sessionStorage.getItem('pap.sp.session')).origin);
  expect(origin.id).toBe('1');
  await hold();
  await expect.poll(async()=>page.evaluate(()=>JSON.parse(sessionStorage.getItem('pap.sp.session')).destination?.id)).toBe('2');
  expect(await page.evaluate(()=>JSON.parse(sessionStorage.getItem('pap.sp.session')).origin)).toEqual(origin);
  await context.close();
});

for(const gps of [true,false]) test(`URL vazia ignora viagem antiga da sessão (GPS=${gps})`,async({page})=>{
  const old={id:'600012613',name:'Embarque antigo',lat:-23.52,lon:-46.53};
  await page.addInitScript(old=>{
    sessionStorage.setItem('pap.sp.session',JSON.stringify({origin:old,destination:{...old,id:'2'}}));
    localStorage.setItem('pap.sp.favorites',JSON.stringify([old]));
  },old);
  await page.route('https://tile.openstreetmap.org/**',r=>r.abort());
  await page.route('**/api/location-config/**',r=>r.fulfill({json:{position:gps?{lat:-23.55,lon:-46.63,accuracy:0,simulated:true}:null}}));
  await page.route('**/api/sptrans/stops/**',r=>r.fulfill({json:{stops:[]}}));
  let boardRequests=0;
  await page.route('**/api/sptrans/board/**',r=>{boardRequests++;return r.fulfill({json:{lines:[],journeys:[]}});});
  await page.goto('/');
  await expect(page.locator('.sp-navigation-state')).toContainText(gps?'Selecionar destino':'Selecionar embarque');
  const session=await page.evaluate(()=>JSON.parse(sessionStorage.getItem('pap.sp.session')));
  expect(session.origin?.id??null).toBe(gps?'passenger-location':null);
  expect(session.destination).toBeNull();
  expect(boardRequests).toBe(0);
  expect(await page.evaluate(()=>JSON.parse(localStorage.getItem('pap.sp.favorites')).length)).toBe(1);
});
