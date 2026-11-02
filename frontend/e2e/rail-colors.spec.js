import {test,expect} from '@playwright/test';

const stops=Array.from({length:5},(_,i)=>({id:String(i+1),name:`Estação ${i+1}`,lat:-23.55,lon:-46.64+i*.005}));
for(const theme of ['light','dark'])for(const [code,mode,color,rgb,label] of [
  ['METRÔ L1','metro','#0455A1','rgb(4, 85, 161)','Metrô Linha Azul'],
  ['METRÔ L4','metro','#FFFF00','rgb(255, 255, 0)','Metrô Linha Amarela'],
  ['CPTM L09','rail','#01A9A7','rgb(1, 169, 167)','CPTM Linha 9 Esmeralda'],
])test(`${code} mantém sua cor no tema ${theme}`,async({page})=>{
  await page.setViewportSize({width:390,height:844});
  await page.addInitScript(theme=>localStorage.setItem('pap.appearance',theme),theme);
  const line={trip_id:'T',code,mode,color,headsign:'Terminal',arrivals:[],programme:[]};
  const geometry=stops.map(s=>[s.lat,s.lon]);
  await page.route('https://tile.openstreetmap.org/**',r=>r.abort());
  await page.route('**/api/location-config/**',r=>r.fulfill({json:{position:null}}));
  await page.route('**/api/sptrans/stop-catalogue/**',r=>r.fulfill({status:503,body:''}));
  await page.route('**/api/sptrans/stops/**',r=>r.fulfill({json:{stops:[{...stops[2],mode,directions:[{bearing:90,kind:'departure'},{bearing:270,kind:'departure'}]}]}}));
  await page.route('**/api/sptrans/board/**',r=>r.fulfill({json:{lines:[line],journeys:[]}}));
  await page.route('**/api/sptrans/trips/**',r=>r.fulfill({json:{line,stops,itinerary:{mode,color,code,geometry,before:geometry.slice(0,3),after:geometry.slice(2),terminal:stops[4],split_available:true,boarding_index:2}}}));
  await page.goto('/?stop=3');await page.getByRole('button',{name:'Continuar sem contribuir',exact:true}).click();
  await expect(page.locator('.sp-rail-badge')).toHaveCSS('border-left-color',rgb);
  await expect(page.locator('.sp-rail-badge')).toContainText(label);
  await page.getByRole('button',{name:`Ver trajeto da linha ${label}`,exact:true}).click();
  await expect(page.locator('.sp-line-before')).toHaveCSS('stroke',rgb);
  await expect(page.locator('.sp-line-after')).toHaveCSS('stroke',rgb);
  await expect(page.locator('.sp-line-before')).toHaveAttribute('stroke-dasharray','6 9 1 9');
  await expect(page.locator('.sp-line-after')).toHaveAttribute('stroke-dasharray','12 10 1 10');
  await expect(page.locator('.sp-origin')).toHaveClass(/sp-station/);
  await expect(page.locator('.sp-origin .sp-station-symbol')).toHaveCount(1);
  await expect(page.locator('.sp-origin .sp-heading')).toHaveCount(0);
  await expect(page.locator('.sp-route-station')).toHaveCount(3);
  await expect(page.locator('.sp-direction-arrow span').first()).toHaveCSS('color',rgb);
  await expect(page.locator('.sp-route-stop > span').first()).toHaveCSS('border-top-color',rgb);
  const key=page.locator('.sp-itinerary-legend .sp-rail-key');
  await expect(key).toHaveText(label);
  expect(await key.evaluate(el=>getComputedStyle(el,'::before').backgroundImage)).toContain(rgb);
  await page.screenshot({path:`test-results/rail-colors-${code.replace(/\W/g,'')}-${theme}.png`});
});
