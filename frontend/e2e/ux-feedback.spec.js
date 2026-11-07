import {test,expect} from '@playwright/test';

const stop={id:'1',name:'Parada de teste',lat:-23.5505,lon:-46.6333,directions:[{bearing:90,kind:'departure'}]};
const place={id:'address',name:'Rua de teste, 123',label:'Rua de teste, 123, Centro',district:'Centro',lat:stop.lat,lon:stop.lon};
async function setup(page,context,{locationError=false}={}) {
  await context.route('https://tile.openstreetmap.org/**',r=>r.abort());
  await context.route('**/api/location-config/**',r=>r.fulfill(locationError?{status:503,json:{error:'Localização indisponível. Escolha o embarque no mapa.'}}:{json:{position:{lat:stop.lat,lon:stop.lon,simulated:true}}}));
  await context.route('**/api/sptrans/stop-catalogue/**',r=>r.fulfill({status:503,body:''}));
  await context.route('**/api/sptrans/stops/**',r=>r.fulfill({json:{stops:[stop]}}));
  await context.route('**/api/sptrans/addresses/**',r=>r.fulfill({json:{suggestions:[place]}}));
  await context.route('**/api/sptrans/destination/**',r=>r.fulfill({json:{stop,distance_meters:15}}));
  await context.route('**/api/sptrans/board/**',r=>r.fulfill({json:{lines:[],journeys:[],complete:true}}));
  await page.goto('/');
  await page.getByRole('button',{name:'Continuar sem contribuir',exact:true}).click();
  await expect(page.locator('.sp-map')).toBeVisible();
}

for(const width of [320,390,1440]) test(`busca direta, confirmação e aparência em ${width}px`,async({page,context})=>{
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.clock.install();
  await page.setViewportSize({width,height:850});await setup(page,context);
  await expect(page.locator('.sp-navigation-state')).toContainText('Selecionar destino');
  const input=page.getByRole('combobox',{name:'Endereço ou coordenadas de destino',exact:true});
  await expect(input).toBeVisible();
  await input.fill('Rua de teste, 123');
  await expect(page.getByRole('option')).toContainText(place.name);
  await expect(page.locator('dialog[open]')).toHaveCount(0);
  await page.screenshot({path:`test-results/ux-inline-search-${width}.png`});
  await input.press('ArrowDown');await input.press('Enter');
  const confirm=page.getByRole('button',{name:'Usar como destino',exact:true});
  await expect(confirm).toBeFocused();await expect(confirm).toBeInViewport();
  await confirm.click();
  await expect.poll(()=>page.evaluate(()=>JSON.parse(sessionStorage.getItem('pap.sp.session')).destination?.id)).toBe('1');
  await page.getByRole('button',{name:'Ver mapa',exact:true}).click();
  await expect(page.getByRole('button',{name:'Recolher aviso de rota',exact:true})).toBeVisible();
  await page.clock.fastForward(8100);
  await expect(page.getByRole('button',{name:'Mostrar aviso de rota',exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Configurações',exact:true}).click();
  await page.getByRole('combobox',{name:'Aparência',exact:true}).selectOption('dark');
  await expect(page.locator('html')).toHaveAttribute('data-theme','dark');
  await page.getByRole('button',{name:'Fechar configurações',exact:true}).click();
  await expect(page.getByRole('button',{name:'Configurações',exact:true})).toBeFocused();
  await page.screenshot({path:`test-results/ux-map-dark-${width}.png`});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  await page.reload();await expect(page.locator('html')).toHaveAttribute('data-theme','dark');
  expect(errors).toEqual([]);
});

test('busca mantém texto após falha, permite retentar e fecha com Escape',async({page,context})=>{
  await setup(page,context);
  await context.route('**/api/sptrans/addresses/**',r=>r.fulfill({status:503,json:{error:'Busca indisponível.'}}));
  const input=page.getByRole('combobox');await input.fill('Rua de teste');
  await expect(page.getByRole('alert')).toContainText('Busca indisponível');
  await expect(input).toHaveValue('Rua de teste');
  await context.route('**/api/sptrans/addresses/**',r=>r.fulfill({json:{suggestions:[place]}}));
  await page.getByRole('button',{name:'Tentar novamente',exact:true}).click();
  await expect(page.getByRole('option')).toContainText(place.name);
  await input.press('Escape');await expect(page.locator('.sp-search-popover')).toHaveCount(0);
  await expect(input).toBeVisible();await input.click();
  await expect(page.getByRole('option')).toContainText(place.name);
  await page.locator('.sp-map').click({position:{x:350,y:300}});
  await expect(page.locator('.sp-search-popover')).toHaveCount(0);
});

test('aviso recolhe após oito segundos e continua disponível pelo ícone',async({page,context})=>{
  await page.clock.install();await setup(page,context,{locationError:true});
  const notice=page.locator('.sp-collapsible-notice').filter({hasText:'Localização indisponível.'});
  await expect(notice.getByRole('status')).toBeVisible();
  await page.clock.fastForward(8100);
  await expect(notice.getByRole('status')).toBeHidden();
  await page.getByRole('button',{name:'Mostrar aviso de localização',exact:true}).click();
  await expect(notice.getByRole('status')).toContainText('Escolha o embarque no mapa');
  await page.clock.fastForward(8100);
  await expect(page.getByRole('button',{name:'Recolher aviso de localização',exact:true})).toBeFocused();
  await expect(notice.getByRole('status')).toBeVisible();
});

test('tela cheia está no canto do mapa e falhas geram aviso',async({page,context})=>{
  await page.addInitScript(()=>{
    Object.defineProperty(document,'fullscreenEnabled',{value:true,configurable:true});
    Element.prototype.requestFullscreen=async()=>{throw new Error('Indisponível');};
  });
  await setup(page,context);
  const fullscreen=page.locator('.sp-map-fullscreen').getByRole('button',{name:'Entrar em tela cheia'});
  await expect(fullscreen).toBeVisible();
  const map=await page.locator('.sp-map').boundingBox(),button=await fullscreen.boundingBox();
  expect(button.x+button.width).toBeGreaterThan(map.x+map.width-20);expect(button.y-map.y).toBeLessThan(20);
  const attribution=await page.locator('.leaflet-control-attribution').boundingBox();
  expect(attribution.x+attribution.width).toBeLessThan(button.x);
  await fullscreen.click();
  await expect(page.getByRole('status').filter({hasText:'Não foi possível ativar ou sair da tela cheia'})).toBeVisible();
});

test('pontos redesenhados continuam selecionáveis pelo teclado',async({page,context})=>{
  await setup(page,context,{locationError:true});
  const canvas=page.locator('.sp-stop-canvas');
  await expect(canvas).toHaveAttribute('data-points','1');
  await canvas.focus();await canvas.press('ArrowRight');await canvas.press('Enter');
  await expect(page.locator('.sp-origin')).toBeVisible();
  await expect.poll(()=>page.evaluate(()=>JSON.parse(sessionStorage.getItem('pap.sp.session')).origin?.id)).toBe('1');
});
