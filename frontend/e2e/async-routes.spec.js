import {test,expect} from './coverage.js';
test('exibe SSE parcial e mantém a escolha enquanto chegam alternativas',async({page})=>{
 const origin={id:'1',name:'Origem',lat:-23.55,lon:-46.64};
 const destination={id:'2',name:'Destino',lat:-23.57,lon:-46.64};
 await page.addInitScript(({origin,destination})=>{
  sessionStorage.setItem('pap.sp.session',JSON.stringify({origin}));
  const fetch=window.fetch;
  window.fetch=(url,options)=>{
   if(String(url).includes('/sptrans/board/')&&new URL(url,location.href).searchParams.has('destination')){
    return Promise.resolve(new Response(new ReadableStream({start(controller){
     const route=(id,minutes)=>({id,duration_minutes:minutes,walking_meters:0,transfers:0,walks:[],legs:[{trip_id:id,code:id,headsign:'Destino',mode:'bus',origin,destination,geometry:[[origin.lat,origin.lon],[destination.lat,destination.lon]]}]});
     const first=route('Materializada',30),later=route('Alternativa',20);
     const send=(journeys,complete)=>controller.enqueue(new TextEncoder().encode('data: '+JSON.stringify({journeys,complete,selected_journey:first.id,lines:[]})+'\n\n'));
     send([first],false);
     window.finishRoutes=()=>{send([later,first],true);controller.close();};
    }}),{headers:{'Content-Type':'text/event-stream'}}));
   }
   return fetch(url,options);
  };
 },{origin,destination});
 await page.route('https://tile.openstreetmap.org/**',r=>r.abort());
 await page.route('**/api/location-config/**',r=>r.fulfill({json:{position:null}}));
 await page.route('**/api/sptrans/stop-catalogue/**',r=>r.fulfill({status:503,body:''}));
 await page.route('**/api/sptrans/rail-network/**',r=>r.fulfill({json:{lines:[]}}));
 await page.route('**/api/sptrans/stops/**',r=>r.fulfill({json:{stops:[origin,destination]}}));
 await page.route('**/api/sptrans/board/**',r=>r.fulfill({json:{journeys:[],lines:[],complete:true}}));
 await page.route('**/api/sptrans/addresses/**',r=>r.fulfill({json:{suggestions:[{...destination,label:destination.name}]}}));
 await page.route('**/api/sptrans/destination/**',r=>r.fulfill({json:{stop:destination,distance_meters:0}}));
 await page.goto('/?stop=1');
 await page.getByRole('button',{name:'Continuar sem contribuir'}).click();
 await page.getByRole('button',{name:'Ver mapa',exact:true}).click();
 await page.getByRole('combobox',{name:'Endereço ou coordenadas de destino',exact:true}).fill('Destino');
 await page.getByRole('option').click();
 await page.getByRole('button',{name:'Usar como destino',exact:true}).click();
 await expect(page.locator('.sp-route-option')).toHaveCount(1);
 await expect(page.locator('.sp-route-option')).toContainText('Materializada');
 await expect(page.getByText(/As rotas aparecem conforme/)).toBeVisible();
 await page.locator('.sp-route-option').click();
 await page.evaluate(()=>window.finishRoutes());
 await page.getByRole('button',{name:'Horários de embarque',exact:true}).click();
 await expect(page.locator('.sp-route-option')).toHaveCount(2);
 await expect(page.locator('.sp-route-option').filter({hasText:'Materializada'})).toHaveAttribute('aria-pressed','true');
 await expect(page.getByText(/As rotas aparecem conforme/)).not.toBeVisible();
});
