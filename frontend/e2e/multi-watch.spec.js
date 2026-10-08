import {test,expect} from './coverage.js';
for(const touch of [false,true])test(`seleção múltipla sem arrastar: ${touch?'toque':'mouse'}`,async({page})=>{
 await page.setViewportSize({width:touch?390:1200,height:850});
 const now='2026-10-08T02:01:00-03:00';
 await page.clock.install({time:new Date(now)});
 const stop={id:'1',name:'Brasil C/B',lat:-23.56,lon:-46.68};
 const lines=['A','B'].map(trip_id=>({trip_id,code:trip_id,headsign:'Centro',arrivals:[{time:'02:10',observed_at:now,vehicle:trip_id,accessible:true}]}));
 await page.route('https://tile.openstreetmap.org/**',r=>r.abort());
 await page.route('**/api/location-config/**',r=>r.fulfill({json:{position:null}}));
 await page.route('**/api/sptrans/stops/**',r=>r.fulfill({json:{stops:[stop]}}));
 await page.route('**/api/sptrans/board/**',r=>r.fulfill({json:{lines,journeys:[]}}));
 const calls={A:0,B:0};
 await page.route('**/api/sptrans/trips/**',r=>{
  const url=new URL(r.request().url()),id=url.pathname.split('/').filter(Boolean).at(-1);
  expect(url.searchParams.get('next')).toBe('1');expect(url.searchParams.get('origin')).toBe('1');
  calls[id]++;
  return r.fulfill({json:{approach:id==='B'&&calls[id]>1?null:{vehicle:{id:id+calls[id],code:id,lat:-23.561,lon:id==='A'?-46.685:-46.675,observed_at:now},geometry:[[-23.561,id==='A'?-46.685:-46.675],[-23.56,-46.68]]}}});
 });
 await page.goto('/?stop=1');
 const first=page.locator('.sp-selectable-line').first();await expect(first).toBeVisible();
 const pointer={pointerId:1,isPrimary:true,pointerType:touch?'touch':'mouse',button:0,clientX:100,clientY:400};
 await first.dispatchEvent('pointerdown',pointer);
 await first.dispatchEvent('pointermove',{...pointer,clientY:430});
 await page.clock.runFor(700);await first.dispatchEvent('pointerup',pointer);
 await expect(page.getByRole('checkbox')).toHaveCount(0);
 if(touch){
  await first.dispatchEvent('pointerdown',pointer);await page.clock.runFor(700);
  await first.dispatchEvent('pointerup',pointer);await first.dispatchEvent('click');
 }else{
  const box=await first.getByRole('heading').boundingBox();
  await page.mouse.move(box.x+20,box.y+10);await page.mouse.down();
  await page.clock.runFor(700);await page.mouse.up();
 }
 await expect(page.getByRole('checkbox',{name:'Acompanhar linha A · Centro'})).toBeChecked();
 await page.locator('.sp-selectable-line').nth(1).getByRole('heading').click();
 await expect(page.getByRole('checkbox',{name:'Acompanhar linha B · Centro'})).toBeChecked();
 await page.getByRole('button',{name:'Ver mapa',exact:true}).click();
 await expect(page.locator('.sp-live-bus')).toHaveCount(2);
 await expect(page.locator('.sp-watch-panel')).toContainText('2 linhas acompanhadas');
 await page.clock.fastForward(5000);
 await expect.poll(()=>calls.A).toBe(2);await expect.poll(()=>calls.B).toBe(2);
 await expect(page.locator('.sp-live-bus')).toHaveCount(1);
 await expect(page.locator('.sp-watch-panel')).toContainText('veículo A2');
 await page.getByRole('button',{name:'Voltar aos próximos ônibus'}).click();
 await expect(page.getByRole('checkbox',{name:'Acompanhar linha B · Centro'})).toBeChecked();
 await page.getByRole('checkbox',{name:'Acompanhar linha B · Centro'}).uncheck();
 await page.getByRole('button',{name:'Ver mapa',exact:true}).click();
 await expect(page.locator('.sp-watch-panel')).toContainText('1 linhas acompanhadas');
 await expect.poll(()=>calls.A).toBe(3);expect(calls.B).toBe(2);
});
