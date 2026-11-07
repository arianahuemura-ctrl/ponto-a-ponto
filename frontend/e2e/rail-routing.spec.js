import {test,expect} from '@playwright/test';

test('compara ônibus com Verde–Amarela, mostra a troca de linha e mantém as cores ferroviárias',async({page})=>{
  await page.setViewportSize({width:390,height:844});
  const origin={id:'1',name:'Trianon–Masp',mode:'metro',lat:-23.561,lon:-46.656};
  const middle={id:'3',name:'Consolação / Paulista',mode:'metro',lat:-23.565,lon:-46.66};
  const destination={id:'5',name:'Destino',mode:'rail',lat:-23.57,lon:-46.67};
  const railLeg=(code,mode,a,b,color)=>({trip_id:code,code,mode,color,headsign:b.name,origin:a,destination:b,
    boarding_index:0,stops:[a,b],geometry:[[a.lat,a.lon],[b.lat,b.lon]],wait_minutes:2,ride_minutes:8,
    departure:'2026-11-02T08:02:00-03:00',arrival:'2026-11-02T08:10:00-03:00',
    timing_detail:{estimated:true,intermediate_stations:3,station_dwell_seconds:90,motion_available:true}});
  const metro={id:'metro',duration_minutes:20,arrival:'2026-11-02T08:20:00-03:00',transfers:1,transfer_cost:1/3,transfer_cost_units:1,internal_rail_transfers:1,walking_minutes:0,walking_meters:0,walks:[],
    legs:[railLeg('L2','metro',origin,middle,'#008061'),railLeg('L4','metro',middle,destination,'#ffff00')]};
  const bus={...metro,id:'bus',duration_minutes:35,arrival:'2026-11-02T08:35:00-03:00',transfers:0,transfer_cost:0,transfer_cost_units:0,internal_rail_transfers:0,
    legs:[{...railLeg('715M','bus',origin,destination,'#0076ed'),timing_detail:undefined}]};
  await page.addInitScript(({origin,destination})=>sessionStorage.setItem('pap.sp.session',JSON.stringify({origin,destination})),{origin,destination});
  const trainRequests=[];
  await page.route('https://tile.openstreetmap.org/**',r=>r.abort());
  await page.route('**/api/location-config/**',r=>r.fulfill({json:{position:null}}));
  await page.route('**/api/sptrans/rail-network/**',r=>r.fulfill({json:{revision:'test',lines:metro.legs.map(leg=>({...leg,geometries:[[[leg.origin.lat+.01,leg.origin.lon+.01],...leg.geometry,[leg.destination.lat-.01,leg.destination.lon-.01]]]}))}}));
  await page.route('**/api/sptrans/stop-catalogue/**',r=>r.fulfill({status:503,body:''}));
  await page.route('**/api/sptrans/stops/**',r=>r.fulfill({json:{stops:[origin,middle,destination]}}));
  await page.route('**/api/sptrans/trips/**',r=>{
    if(!r.request().url().includes('715M'))trainRequests.push(r.request().url());
    return r.fulfill({json:{line:{arrivals:[]}}});
  });
  await page.route('**/api/sptrans/addresses/**',r=>r.fulfill({json:{suggestions:[{...destination,label:destination.name}]}}));
  await page.route('**/api/sptrans/destination/**',r=>r.fulfill({json:{stop:destination,distance_meters:0}}));
  const boardRequests=[];
  await page.route('**/api/sptrans/board/**',r=>{boardRequests.push(new URL(r.request().url()).searchParams);return r.fulfill({json:{journeys:new URL(r.request().url()).searchParams.has('destination')?[metro,bus]:[],selected_journey:'metro',complete:true,lines:[],transfer_policy:{minimum_found:0,maximum_allowed:1,ceiling:4}}});});
  await page.goto('/?stop=1');await page.getByRole('button',{name:'Continuar sem contribuir',exact:true}).click();
  await page.getByRole('button',{name:'Ver mapa',exact:true}).click();
  await page.getByRole('combobox',{name:'Endereço ou coordenadas de destino',exact:true}).fill('Destino');
  await page.getByRole('option').click();await page.getByRole('button',{name:'Usar como destino',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Opções da sua rota'})).toBeVisible();
  const options=page.locator('.sp-route-option');
  await expect(options.first()).toContainText('🚇 Metrô Linha Verde → 🚇 Metrô Linha Amarela');
  await expect(options.first()).toContainText('Custo de baldeações: ⅓');
  expect(boardRequests.filter(p=>p.has('destination')).every(p=>p.get('max_transfers')==='4')).toBe(true);
  await expect(page.getByRole('region',{name:'Trocas entre linhas'})).toContainText('Troque de Metrô Linha Verde para Metrô Linha Amarela');
  await expect(page.getByRole('region',{name:'Trocas entre linhas'})).toContainText('Consolação / Paulista');
  await page.getByText('Tempos estimados por trecho',{exact:true}).click();
  await expect(page.locator('.sp-rail-details')).toContainText('Espera antes de embarcar: 2 min');
  await expect(page.locator('.sp-rail-details')).toContainText('aceleração, circulação e frenagem');
  await expect(page.locator('.sp-rail-details')).toContainText('paradas incluídas: 1 min 30 s');
  await expect(options.first()).toContainText('sem previsão ao vivo');
  await page.getByRole('combobox',{name:'Ordenar rotas por'}).selectOption('transfers');
  await expect(options.first()).toContainText('715M');
  await page.getByRole('combobox',{name:'Ordenar rotas por'}).selectOption('fastest');
  await expect(options.first()).toContainText('Metrô Linha Verde');
  await options.first().click();
  await expect(page.locator('.sp-route-rail')).toHaveCount(2);
  await expect(page.locator('.sp-route-rail').first()).toHaveAttribute('stroke','#008061');
  await expect(page.locator('.sp-route-rail').first()).not.toHaveAttribute('stroke-dasharray',/.+/);
  await expect(page.locator('.sp-route-rail').first()).toHaveAttribute('stroke-opacity','1');
  await expect(page.locator('.sp-network-rail')).toHaveCount(2);
  await expect(page.locator('.sp-network-rail').first()).toHaveAttribute('stroke-dasharray','12 10 1 10');
  await expect(page.locator('.sp-network-rail').first()).toHaveAttribute('stroke-opacity','1');
  await expect(page.locator('.sp-transfer-stop')).toHaveClass(/sp-station/);
  await expect(page.locator('.sp-transfer-stop .sp-station-symbol')).toHaveCount(1);
  await expect(page.locator('.sp-transfer-stop .sp-heading')).toHaveCount(0);
  expect(trainRequests).toEqual([]);
  await page.screenshot({path:'test-results/rail-routing.png'});
});
