import {test,expect} from './coverage.js';
const origin={id:'1',name:'Plataforma A',lat:-23.55,lon:-46.64};
const destination={id:'2',name:'Plataforma B',lat:-23.55005,lon:-46.64002};
for(const available of [true,false])test(`caminhada materializada aparece antes do traçado (disponível=${available})`,async({page})=>{
 await page.addInitScript(({origin,destination})=>{
  sessionStorage.setItem('pap.sp.session',JSON.stringify({origin,destination}));
 },{origin,destination});
 await page.route('https://tile.openstreetmap.org/**',r=>r.abort());
 await page.route('**/api/location-config/**',r=>r.fulfill({json:{position:null}}));
 await page.route('**/api/usability/',r=>r.fulfill({json:{session:'test',token:'test',csrf:'test'}}));
 await page.route('**/api/sptrans/stop-catalogue/**',r=>r.fulfill({status:503,body:''}));
 await page.route('**/api/sptrans/rail-network/**',r=>r.fulfill({json:{lines:[]}}));
 await page.route('**/api/sptrans/stops/**',r=>r.fulfill({json:{stops:[origin,destination]}}));
 const foot={id:'walk-test',mode:'walk',materialized:true,legs:[],transfers:0,transfer_cost_units:0,
  walking_meters:13,walking_minutes:13/75,duration_minutes:13/75,
  walks:[{origin,destination,materialized:true,geometry:[],geometry_pending:true,max_meters:300,
          distance_meters:13,duration_minutes:13/75,accessType:'destination'}]};
 await page.route('**/api/sptrans/board/**',r=>r.fulfill({json:{journeys:[foot],selected_journey:foot.id,complete:true,lines:[]}}));
 let release;
 const ready=new Promise(resolve=>{release=resolve;});
 let requests=0;
 await page.route('**/api/sptrans/walk/**',async r=>{
  requests++;await ready;
  await r.fulfill({json:available?{available:true,distance_meters:13,geometry:[[origin.lat,origin.lon],[destination.lat,destination.lon]]}:{available:false,message:'Traçado indisponível no teste.'}});
 });
 await page.route('**/api/sptrans/addresses/**',r=>r.fulfill({json:{suggestions:[{...destination,label:destination.name}]}}));
 await page.route('**/api/sptrans/destination/**',r=>r.fulfill({json:{stop:destination,distance_meters:0}}));
 await page.goto('/?stop=1');
 const consent=page.getByRole('button',{name:'Continuar sem contribuir'});
 if(await consent.isVisible())await consent.click();
 await page.getByRole('button',{name:'Ver mapa',exact:true}).click();
 await page.getByRole('combobox',{name:'Endereço ou coordenadas de destino',exact:true}).fill(destination.name);
 await page.getByRole('option').click();
 await page.getByRole('button',{name:'Usar como destino',exact:true}).click();
 await expect(page.locator('.sp-route-option')).toContainText('Somente a pé');
 await expect(page.locator('.sp-route-option')).toContainText('13 m a pé');
 await page.locator('.sp-route-option').click();
 await expect.poll(()=>requests).toBeGreaterThan(0);
 await expect(page.locator('.sp-route-walk')).toHaveCount(0);
 release();
 if(available)await expect(page.locator('.sp-route-walk')).toHaveCount(1);
 else{
  await expect(page.getByText('Traçado indisponível no teste.',{exact:true})).toBeVisible();
  await expect(page.locator('.sp-route-walk')).toHaveCount(0);
 }
});
