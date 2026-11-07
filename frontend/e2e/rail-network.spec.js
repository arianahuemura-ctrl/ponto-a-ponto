import {test,expect} from '@playwright/test';

for(const theme of ['light','dark'])test(`rede ferroviária visível antes da rota, abaixo dos pontos (${theme})`,async({page})=>{
  await page.setViewportSize({width:390,height:844});
  await page.addInitScript(theme=>localStorage.setItem('pap.appearance',theme),theme);
  const stop={id:'bus',name:'Ônibus sobre o trilho',mode:'bus',lat:-23.5505,lon:-46.6333};
  const geometry=[[-23.56,-46.6333],[-23.5505,-46.6333],[-23.54,-46.6333]];
  await page.route('https://tile.openstreetmap.org/**',r=>r.abort());
  await page.route('**/api/location-config/**',r=>r.fulfill({json:{position:null}}));
  await page.route('**/api/sptrans/stop-catalogue/**',r=>r.fulfill({status:503,body:''}));
  await page.route('**/api/sptrans/stops/**',r=>r.fulfill({json:{stops:[stop]}}));
  await page.route('**/api/sptrans/board/**',r=>r.fulfill({json:{lines:[],journeys:[]}}));
  await page.route('**/api/sptrans/rail-network/**',r=>r.fulfill({json:{revision:'test',lines:[
    {route_id:'L1',code:'L1',mode:'metro',color:'#0455a1',geometries:[geometry]},
    {route_id:'L9',code:'L9',mode:'rail',color:'#01a9a7',geometries:[geometry.map(([lat,lon])=>[lat,lon+.003])]},
  ]}}));
  await page.goto('/');
  await page.getByRole('button',{name:'Continuar sem contribuir',exact:true}).click();
  await expect(page.locator('.sp-network-rail')).toHaveCount(2);
  await expect(page.locator('.sp-route-rail')).toHaveCount(0);
  await expect(page.locator('.sp-network-rail').first()).toHaveCSS('stroke','rgb(4, 85, 161)');
  for(const line of await page.locator('.sp-network-rail').all())await expect(line).toHaveAttribute('stroke-opacity','1');
  await expect(page.locator('.sp-network-rail-label').filter({hasText:'Metrô Linha Azul'}).first()).toBeVisible();
  await expect(page.locator('.sp-network-rail-label').filter({hasText:'CPTM Linha 9 Esmeralda'}).first()).toBeVisible();
  await expect(page.locator('.sp-network-rail-halo').first()).toHaveAttribute('stroke-opacity','1');
  await expect(page.locator('.sp-network-rail-contrast').first()).toHaveAttribute('stroke','#ffffff');
  await page.getByRole('button',{name:'Pontos transparentes',exact:true}).click();
  await expect(page.locator('.sp-map')).toHaveClass(/sp-transparent-stops/);
  await expect(page.locator('.leaflet-tile-pane')).toHaveCSS('filter',/grayscale\(1\)/);
  for(const line of await page.locator('.sp-network-rail').all())await expect(line).toHaveAttribute('stroke-opacity','1');
  const pane=page.locator('.leaflet-networkContext-pane');
  await expect(pane).toHaveCSS('pointer-events','none');
  await expect(pane).toHaveCSS('z-index','250');
  await expect(page.locator('.sp-stop-canvas')).toHaveAttribute('data-points','1');
  const canvas=await page.locator('.sp-stop-canvas').boundingBox();
  await page.mouse.click(canvas.x+canvas.width/2,canvas.y+canvas.height/2);
  await expect(page.locator('.sp-origin')).toHaveAttribute('title',/Ônibus sobre o trilho/);
  await expect(page.locator('.sp-network-rail')).toHaveCount(2);
  // Names remain useful without color, and moving the map rebuilds them in view.
  await page.getByRole('button',{name:'Zoom out',exact:true}).click();
  await expect(page.locator('.sp-network-rail-label').filter({hasText:'Metrô Linha Azul'}).first()).toBeVisible();
  await expect(page.locator('.sp-network-rail-label').filter({hasText:'CPTM Linha 9 Esmeralda'}).first()).toBeVisible();
  await page.screenshot({path:`test-results/rail-network-${theme}.png`});
});

for(const width of [390,1440])test(`passageiro acima dos pontos e nomes fora dos trilhos (${width}px)`,async({page})=>{
  await page.setViewportSize({width,height:900});
  const position={lat:-23.561326733117216,lon:-46.65615056649423,simulated:true};
  const stop={id:'masp',name:'Ponto junto ao passageiro',mode:'bus',...position};
  await page.route('https://tile.openstreetmap.org/**',r=>r.abort());
  await page.route('**/api/location-config/**',r=>r.fulfill({json:{position}}));
  await page.route('**/api/sptrans/stop-catalogue/**',r=>r.fulfill({status:503,body:''}));
  await page.route('**/api/sptrans/stops/**',r=>r.fulfill({json:{stops:[stop]}}));
  await page.route('**/api/sptrans/board/**',r=>r.fulfill({json:{lines:[],journeys:[]}}));
  await page.route('**/api/sptrans/rail-network/**',r=>r.fulfill({json:{lines:[
    {route_id:'L4',mode:'metro',geometries:[[[position.lat-.01,position.lon-.01],[position.lat+.01,position.lon+.01]]]},
    {route_id:'L2',mode:'metro',geometries:[[[position.lat-.01,position.lon+.01],[position.lat+.01,position.lon-.01]]]},
    {route_id:'L12',mode:'rail',geometries:[[[position.lat+.0007,position.lon-.01],[position.lat+.0007,position.lon+.01]]]},
  ]}}));
  await page.goto('/?location='+position.lat+','+position.lon);
  await page.getByRole('button',{name:'Continuar sem contribuir',exact:true}).click();
  const passenger=page.locator('.sp-passenger-position');await expect(passenger).toBeVisible();
  await expect(page.locator('.sp-network-rail-label').filter({hasText:'Metrô Linha Amarela'}).first()).toBeVisible();
  await expect(page.locator('.sp-network-rail-label').filter({hasText:'CPTM Linha 12 Safira'}).first()).toBeVisible();
  const check=async()=>{
    await expect.poll(async()=>{
      const names=await page.locator('.sp-network-rail-label').allTextContents();
      return names.length===new Set(names).size;
    }).toBe(true);
    await expect.poll(()=>page.evaluate(()=>{
      const canvas=document.querySelector('.sp-stop-canvas').getBoundingClientRect();
      const map=document.querySelector('.sp-map').getBoundingClientRect();
      return Math.abs(canvas.x-map.x)<1&&Math.abs(canvas.y-map.y)<1;
    })).toBe(true);
    await expect.poll(()=>page.evaluate(()=>{
      const p=document.querySelector('.sp-passenger-position').getBoundingClientRect();
      return [...document.querySelectorAll('.sp-network-rail-label')].every(el=>{
        const b=el.getBoundingClientRect();return b.right<p.left-10||b.left>p.right+10||b.bottom<p.top-10||b.top>p.bottom+10;
      });
    })).toBe(true);
    const box=await passenger.boundingBox();
    expect(await page.evaluate(({x,y})=>Boolean(document.elementFromPoint(x,y)?.closest('.sp-passenger-position')),
      {x:box.x+box.width/2,y:box.y+box.height/2})).toBe(true);
    const labels=page.locator('.leaflet-networkLabels-pane');
    await expect(labels).toHaveCSS('z-index','410');
    await expect(page.locator('.leaflet-passengerLocation-pane')).toHaveCSS('z-index','750');
  };
  await check();
  await page.getByRole('button',{name:'Zoom out',exact:true}).click();await check();
  const map=await page.locator('.sp-map').boundingBox();
  await page.mouse.move(map.x+map.width*.6,map.y+map.height*.6);await page.mouse.down();
  await page.mouse.move(map.x+map.width*.6+45,map.y+map.height*.6+30,{steps:8});await page.mouse.up();
  await check();
  await page.screenshot({path:`test-results/rail-label-passenger-${width}.png`});
});
