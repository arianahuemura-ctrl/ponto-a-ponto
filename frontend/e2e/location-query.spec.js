import {test, expect} from './coverage.js';

async function isolateMap(page) {
  await page.route('https://tile.openstreetmap.org/**',r=>r.abort());
  await page.route('**/api/sptrans/stops/**',r=>r.fulfill({json:{stops:[]}}));
}

test('coordenadas da URL chegam ao backend e sobrevivem à troca de embarque e recarga',async({page})=>{
  await isolateMap(page);
  const response=page.waitForResponse(r=>r.url().includes('/api/location-config/'));
  await page.goto('/?latitude=-23.57&longitude=-46.70');
  expect((await (await response).json()).position).toMatchObject({lat:-23.57,lon:-46.70,simulated:true});
  await expect(page.locator('.sp-passenger-position')).toBeVisible();
  await expect(page.locator('.sp-navigation-state')).toContainText('Selecionar destino');
  await page.getByRole('button',{name:'Alterar embarque',exact:true}).click();
  expect(new URL(page.url()).searchParams.get('latitude')).toBe('-23.57');
  expect(new URL(page.url()).searchParams.get('longitude')).toBe('-46.70');
  await page.reload();
  await expect(page.locator('.sp-passenger-position')).toBeVisible();
});

test('URL com coordenada incompleta informa erro sem inventar uma posição',async({page})=>{
  await isolateMap(page);
  await page.goto('/?latitude=-23.57');
  await expect(page.locator('.passenger-notice')).toContainText('Coordenadas simuladas inválidas');
  await expect(page.locator('.sp-passenger-position')).toHaveCount(0);
  await expect(page.locator('.sp-navigation-state')).toContainText('Selecionar local de embarque');
});

test('sem parâmetros usa GPS; remover parâmetros retoma a localização do aparelho',async({page,context})=>{
  await isolateMap(page);
  await context.grantPermissions(['geolocation']);
  await context.setGeolocation({latitude:-23.58,longitude:-46.71});
  await page.goto('/?latitude=-23.57&longitude=-46.70');
  await expect(page.locator('.sp-passenger-position')).toBeVisible();
  const response=page.waitForResponse(r=>r.url().includes('/api/location-config/'));
  await page.goto('/');
  expect((await (await response).json()).position).toBeNull();
  await expect.poll(()=>page.evaluate(()=>JSON.parse(sessionStorage.getItem('pap.sp.session'))?.origin?.lat)).toBe(-23.58);
});

test('coordenadas copiadas do Maps mantêm precisão após navegação e recarga',async({page})=>{
  await isolateMap(page);
  const value='-23.561902423411315, -46.680757605637645';
  const response=page.waitForResponse(r=>r.url().includes('/api/location-config/'));
  await page.goto('/?location='+value);
  expect((await (await response).json()).position).toMatchObject({lat:-23.561902423411315,lon:-46.680757605637645});
  await expect(page.locator('.sp-passenger-position')).toBeVisible();
  await page.getByRole('button',{name:'Alterar embarque',exact:true}).click();
  expect(new URL(page.url()).searchParams.get('location')).toBe(value);
  await page.reload();
  await expect(page.locator('.sp-passenger-position')).toBeVisible();
});
