import {test,expect} from './coverage.js';
const stops=[{id:'1',name:'Origem teste',lat:-23.5505,lon:-46.6333},{id:'2',name:'Destino teste',lat:-23.5515,lon:-46.6323}];
test.beforeEach(async({page})=>{
 await page.route('https://tile.openstreetmap.org/**',r=>r.abort());
 await page.route('**/api/usability/',r=>r.fulfill({json:{session:'test',token:'test',csrf:'test'}}));
 await page.route('**/api/sptrans/stop-catalogue/**',r=>r.fulfill({status:503,body:''}));
 await page.route('**/api/location-config/**',r=>r.fulfill({json:{position:null}}));
 await page.route('**/api/sptrans/stops/**',r=>r.fulfill({json:{stops:new URL(r.request().url()).searchParams.has('id')?[stops[0]]:stops}}));
 await page.route('**/api/sptrans/board/**',r=>r.fulfill({json:{lines:[],journeys:[]}}));
});
for(const long of [false,true])test(`origem permanece no mapa e destino abre rotas (clique longo=${long})`,async({page})=>{
 let requests=0,boards=[];
 await page.route('**/api/sptrans/destination/**',r=>r.fulfill({json:{stop:stops[requests++],distance_meters:10}}));
 await page.route('**/api/sptrans/board/**',r=>{boards.push(new URL(r.request().url()).searchParams);return r.fulfill({json:{lines:[],journeys:[]}});});
 await page.goto('/');await page.getByRole('button',{name:'Concordo e continuar'}).click();
 await expect(page.locator('.sp-navigation-state')).toContainText('Selecionar embarque');
 const select=async(index)=>{
  if(!long){
   // Ordinary stops are canvas dots: click their projected map coordinates.
   await page.waitForTimeout(500);
   const box=await page.locator('.sp-map').boundingBox(),zoom=index?16:15;
   const project=p=>{const sin=Math.sin(p.lat*Math.PI/180),scale=256*2**zoom;return {x:(p.lon+180)/360*scale,y:(.5-Math.log((1+sin)/(1-sin))/(4*Math.PI))*scale};};
   const center=project(stops[0]),point=project(stops[index]);
   await page.mouse.click(box.x+box.width/2+point.x-center.x,box.y+box.height/2+point.y-center.y);return;
  }
  const box=await page.locator('.sp-map').boundingBox();
  await page.mouse.move(box.x+box.width*.7,box.y+box.height*.4);
  await page.mouse.down();await page.waitForTimeout(800);await page.mouse.up();
 };
 await select(0);
 await expect(page.locator('.sp-navigation-state')).toContainText('Selecionar destino');
 await expect(page.locator('dialog[open]')).toHaveCount(0);
 expect(boards).toHaveLength(0);
 await select(1);
 await expect(page.getByRole('dialog').getByRole('heading',{name:'Ônibus da sua rota'})).toBeVisible();
 await expect.poll(()=>boards.length).toBeGreaterThan(0);
 expect(boards[0].get('origin')).toBe('1');expect(boards[0].get('destination')).toBe('2');
});
test('link direto abre próximos ônibus',async({page})=>{
 await page.goto('/?stop=1');await page.getByRole('button',{name:'Concordo e continuar'}).click();
 await expect(page.getByRole('dialog',{name:'Próximos ônibus'})).toBeVisible();
});
