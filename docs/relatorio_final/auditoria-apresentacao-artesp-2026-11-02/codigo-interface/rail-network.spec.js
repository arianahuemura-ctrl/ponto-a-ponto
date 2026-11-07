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
  await expect(page.locator('.sp-network-rail-label').filter({hasText:'Metrô 1'}).first()).toBeVisible();
  await expect(page.locator('.sp-network-rail-label').filter({hasText:'Trem 9'}).first()).toBeVisible();
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
  await expect(page.locator('.sp-network-rail-label').filter({hasText:'Metrô 1'}).first()).toBeVisible();
  await expect(page.locator('.sp-network-rail-label').filter({hasText:'Trem 9'}).first()).toBeVisible();
  await page.screenshot({path:`test-results/rail-network-${theme}.png`});
});
