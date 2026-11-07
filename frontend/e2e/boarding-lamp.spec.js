import {test,expect} from './coverage.js';

test('OK do aviso sem localização acende a lâmpada para selecionar embarque',async({page})=>{
  await page.route('https://tile.openstreetmap.org/**',r=>r.abort());
  await page.route('**/api/location-config/**',r=>r.fulfill({json:{position:null}}));
  await page.route('**/api/sptrans/stops/**',r=>r.fulfill({json:{stops:[]}}));
  await page.addInitScript(()=>{
    localStorage.setItem('pap-stop-transparency','97');
    navigator.geolocation.watchPosition=(_success,error)=>{error({code:1,message:'Permissão negada'});return 1;};
  });
  await page.goto('/');
  const lamp=page.getByRole('button',{name:'Pontos transparentes',exact:true});
  for(let attempt=0;attempt<2;attempt++){
    await lamp.click();
    await expect(lamp).toHaveAttribute('aria-pressed','true');
    const dialogPromise=page.waitForEvent('dialog');
    const click=page.getByRole('button',{name:'Selecionar destino',exact:true}).click();
    const dialog=await dialogPromise;
    expect(dialog.message()).toContain('Sua localização não está disponível');
    await dialog.accept();await click;
    await expect(lamp).toHaveAttribute('aria-pressed','false');
    await expect(page.locator('.sp-map')).not.toHaveClass(/sp-transparent-stops/);
    await expect(page.getByRole('button',{name:'Selecionar embarque',exact:true})).toHaveAttribute('aria-pressed','true');
  }
  expect(await page.evaluate(()=>localStorage.getItem('pap-stop-transparency'))).toBe('97');
});
