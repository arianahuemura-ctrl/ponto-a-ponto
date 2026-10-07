import {test,expect} from '@playwright/test';
const origin={id:'1',name:'Embarque',lat:-23.55,lon:-46.64},destination={id:'2',name:'Destino',lat:-23.551,lon:-46.63};
for(const mobile of [false,true])test(`fundo abre mapa; interior vazio mantém painel; sem seleção acidental (móvel=${mobile})`,async({browser})=>{
 const context=await browser.newContext({viewport:{width:mobile?390:1200,height:mobile?1100:900},isMobile:mobile,hasTouch:mobile});
 const page=await context.newPage();
 try{
  await page.addInitScript(({origin,destination})=>sessionStorage.setItem('pap.sp.session',JSON.stringify({origin,destination})),{origin,destination});
  await page.route('https://tile.openstreetmap.org/**',r=>r.abort());
  await page.route('**/api/location-config/**',r=>r.fulfill({json:{position:null}}));
  await page.route('**/api/sptrans/stops/**',r=>r.fulfill({json:{stops:[origin,destination]}}));
  await page.route('**/api/sptrans/trips/**',r=>r.fulfill({json:{line:{arrivals:[]}}}));
  let searches=0,selections=0;
  await page.route('**/api/sptrans/destination/**',r=>{selections++;return r.fulfill({json:{stop:destination}});});
  const journey={id:'J',duration_minutes:20,walks:[],legs:[{trip_id:'T',boarding_index:0,code:'702C-10',origin,destination,geometry:[[origin.lat,origin.lon],[destination.lat,destination.lon]]}]};
  await page.route('**/api/sptrans/board/**',r=>{searches++;return r.fulfill({json:{journeys:[journey],selected_journey:'J',complete:true,lines:[]}});});
  await page.goto('/?stop=1');
  const panel=page.getByRole('dialog',{name:'Ônibus da sua rota'}),open=()=>page.getByRole('button',{name:'Horários de embarque',exact:true}).click();
  await open();await expect(page.locator('.sp-route-option')).toHaveCount(1);
  const original=await page.evaluate(()=>sessionStorage.getItem('pap.sp.session'));
  const click=async(x,y)=>mobile?page.touchscreen.tap(x,y):page.mouse.click(x,y);
  // All four quadrants outside the panel behave like its explicit map button.
  for(const [side,vertical] of [[.3,'top'],[.7,'top'],[.3,'bottom'],[.7,'bottom']]){
   const box=await panel.boundingBox();const x=page.viewportSize().width*side,y=vertical==='top'?box.y-20:box.y+box.height+20;
   expect(y).toBeGreaterThan(0);expect(y).toBeLessThan(page.viewportSize().height);
   await click(x,y);await expect(panel).not.toBeVisible();
   await expect(page.locator('.sp-route-bus')).toHaveCount(1);
   expect(await page.evaluate(()=>sessionStorage.getItem('pap.sp.session'))).toBe(original);
   await open();await expect(panel).toBeVisible();
  }
  const box=await panel.boundingBox();
  // Dialog padding and plain text are inert, even though the dialog itself receives the click.
  await click(box.x+6,box.y+box.height/2);await expect(panel).toBeVisible();
  await panel.getByRole('heading',{name:'Ônibus da sua rota'}).click();await expect(panel).toBeVisible();
  await panel.locator('p').first().click();await expect(panel).toBeVisible();
  expect(searches).toBe(1);expect(selections).toBe(0);
  // Dragging from content onto the backdrop must not count as an outside click.
  await page.mouse.move(box.x+8,box.y+box.height/2);await page.mouse.down();await page.mouse.move(box.x-8,box.y+box.height/2,{steps:8});await page.mouse.up();await expect(panel).toBeVisible();
  await page.mouse.move(box.x+40,box.y-20);await page.mouse.down();await page.mouse.move(box.x+100,box.y-20,{steps:8});await page.mouse.up();await expect(panel).toBeVisible();
  // Existing controls retain their behavior.
  await page.getByRole('button',{name:'Ver mapa',exact:true}).click();await expect(panel).not.toBeVisible();await open();
  await page.locator('.sp-route-option').click();await expect(panel).not.toBeVisible();await open();
  await panel.getByRole('button',{name:'Cancelar viagem',exact:true}).click();await expect(page.getByRole('dialog',{name:'Cancelar viagem?'})).toBeVisible();
  await page.getByRole('button',{name:'Continuar viagem',exact:true}).click();await expect(panel).toBeVisible();
 }finally{await context.close();}
});
