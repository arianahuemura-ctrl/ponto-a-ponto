import {test, expect} from './coverage.js';

test.use({viewport:{width:390,height:844},isMobile:true,hasTouch:true});
test('dimmer mantém o toque durante o arrasto e confirma somente ao soltar',async({page})=>{
  await page.route('https://tile.openstreetmap.org/**',r=>r.abort());
  await page.route('**/api/location-config/**',r=>r.fulfill({json:{position:null}}));
  await page.route('**/api/sptrans/stops/**',r=>r.fulfill({json:{stops:[]}}));
  await page.goto('/');
  const lamp=page.getByRole('button',{name:'Pontos transparentes',exact:true});
  await expect(lamp).toBeVisible();
  const box=await lamp.boundingBox();
  const client=await page.context().newCDPSession(page);
  const x=box.x+box.width/2,y=box.y+box.height/2;
  await client.send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[{x,y}]});
  const slider=page.getByRole('slider',{name:'Transparência dos pontos'});
  await expect(slider).toBeVisible();
  const bar=await slider.boundingBox();
  // Subir e depois descer, atravessando a região dos demais controles do mapa.
  let previous=y;
  for(const fraction of [.15,.85]){
    const target=bar.y+bar.height*fraction;
    for(let i=1;i<=12;i++){
      await client.send('Input.dispatchTouchEvent',{type:'touchMove',touchPoints:[{x,y:previous+(target-previous)*i/12}]});
      await page.waitForTimeout(30);
    }
    await expect(lamp).toHaveAttribute('aria-expanded','true');
    await expect(slider).toHaveAttribute('aria-valuenow',String(Math.round(fraction*100)));
    previous=target;
  }
  await client.send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});
  await expect(lamp).toHaveAttribute('aria-expanded','false');
  expect(await page.evaluate(()=>localStorage.getItem('pap-stop-transparency'))).toBe('85');
});
