import {test,expect} from '@playwright/test';

const position={lat:-23.55,lon:-46.63,simulated:true};
const destination={id:'2',name:'Av. Paulo Guilguer Reimberg, 1234 — endereço completo',lat:-23.551,lon:-46.631};
const replacement={id:'3',name:'Novo local escolhido',lat:-23.552,lon:-46.632};
const currentSession=page=>page.evaluate(()=>JSON.parse(sessionStorage.getItem('pap.sp.session')));
async function setup(page,context,gps=true){
  const boards=[],dialogs=[];
  page.on('dialog',async d=>{dialogs.push(d.message());await d.dismiss();});
  await context.route('https://tile.openstreetmap.org/**',r=>r.abort());
  await context.route('**/api/location-config/**',r=>r.fulfill({json:{position:gps?position:null}}));
  await context.route('**/api/sptrans/stop-catalogue/**',r=>r.fulfill({status:503,body:''}));
  await context.route('**/api/sptrans/stops/**',r=>r.fulfill({json:{stops:[destination,replacement]}}));
  await context.route('**/api/sptrans/addresses/**',r=>r.fulfill({json:{suggestions:[{...destination,label:destination.name}]}}));
  await context.route('**/api/sptrans/destination/**',r=>r.fulfill({json:{stop:destination,distance_meters:12}}));
  await context.route('**/api/sptrans/board/**',r=>{boards.push(Object.fromEntries(new URL(r.request().url()).searchParams));return r.fulfill({json:{lines:[],journeys:[],complete:true}});});
  await page.goto('/');await page.getByRole('button',{name:'Continuar sem contribuir',exact:true}).click();
  await expect(page.locator('.sp-map')).toBeVisible();
  if(gps)await expect.poll(async()=>(await currentSession(page)).origin?.useLocation).toBe(true);
  return {boards,dialogs};
}
async function chooseAddress(page,role){
  const input=page.getByRole('combobox',{name:`Endereço ou coordenadas de ${role}`,exact:true});
  await input.fill('Av. Paulo Guilguer');await page.getByRole('option').click();
  await page.getByRole('button',{name:`Usar como ${role}`,exact:true}).click();
}

for(const mobile of [true,false])test.describe(mobile?'toque no celular':'teclado no computador',()=>{
  test.use({viewport:mobile?{width:390,height:844}:{width:1280,height:900},hasTouch:mobile});
  const activate=async locator=>{if(mobile)await locator.tap();else {await locator.focus();await locator.press('Enter');}};

  test('GPS é definido; primeiro toque mostra e segundo seleciona sem apagar locais',async({page,context})=>{
    const {boards,dialogs}=await setup(page,context);
    const controls=page.locator('.sp-map-point-controls'),origin=controls.locator('[data-kind="origin"]');
    await expect(origin).toHaveAttribute('data-state','set');
    await expect(origin).toHaveAttribute('aria-expanded','false');
    await expect(origin).toHaveCSS('border-top-style','solid');
    await expect(origin.locator('.sp-point-symbol')).toHaveCSS('animation-name','none');
    await expect(origin).toHaveCSS('width','44px');
    await expect(controls.locator('[data-kind="destination"]')).toHaveAttribute('aria-expanded','false');
    await chooseAddress(page,'destino');await page.getByRole('button',{name:'Ver mapa',exact:true}).click();
    const before=await currentSession(page),queryCount=boards.length;
    const dest=controls.locator('[data-kind="destination"]');
    await expect(dest).toHaveAttribute('aria-expanded','false');
    await activate(origin);
    await expect(origin).toHaveAttribute('aria-expanded','true');
    await expect(origin).toContainText('Minha localização');
    expect(await currentSession(page)).toEqual(before);expect(boards).toHaveLength(queryCount);
    await expect(page.locator('.sp-navigation-state')).toContainText('Rota selecionada');
    await activate(origin);
    await expect(page.locator('.sp-navigation-state')).toContainText('Selecionar embarque');
    await expect(origin).toHaveAttribute('data-selecting','true');
    await expect(origin).toHaveCSS('border-top-style','solid');
    expect(await currentSession(page)).toEqual(before);
    await context.route('**/api/sptrans/destination/**',r=>r.fulfill({json:{stop:replacement,distance_meters:10}}));
    await chooseAddress(page,'embarque');
    await expect(page.locator('.sp-board-dialog[open]').getByRole('heading',{name:'Opções da sua rota'})).toBeVisible();
    await expect.poll(async()=>(await currentSession(page)).origin?.id).toBe('3');
    expect((await currentSession(page)).destination).toEqual(before.destination);
    await expect.poll(()=>boards.at(-1)?.origin).toBe('3');
    expect(boards.at(-1).destination).toBe('2');
    await page.getByRole('button',{name:'Ver mapa',exact:true}).click();
    await expect(origin).toHaveAttribute('aria-expanded','false');
    const withNewOrigin=await currentSession(page);
    await activate(dest);await expect(dest).toHaveAttribute('aria-expanded','true');
    await expect(dest.locator('small')).toHaveText(destination.name);
    await expect(dest.locator('small')).toHaveCSS('white-space','normal');
    await page.screenshot({path:`test-results/point-details-${mobile?'mobile':'desktop'}.png`});
    expect(await currentSession(page)).toEqual(withNewOrigin);
    await activate(dest);
    await expect(page.locator('.sp-navigation-state')).toContainText('Selecionar destino');
    expect(await currentSession(page)).toEqual(withNewOrigin);
    await chooseAddress(page,'destino');
    await expect.poll(async()=>(await currentSession(page)).destination?.id).toBe('3');
    expect((await currentSession(page)).origin).toEqual(withNewOrigin.origin);
    expect(dialogs).toEqual([]);
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  });

  test('detalhes recolhem como avisos e o GPS continua definido',async({page,context})=>{
    await page.clock.install();await setup(page,context);
    const origin=page.locator('.sp-map-point-controls [data-kind="origin"]');
    await activate(origin);await expect(origin).toHaveAttribute('aria-expanded','true');
    await page.mouse.move(385,800);await origin.evaluate(button=>button.blur());
    await page.clock.fastForward(8100);
    await expect(origin).toHaveAttribute('aria-expanded','false');
    await expect(origin).toHaveAttribute('data-state','set');
    await expect(page.locator('.sp-navigation-state')).toContainText('Selecionar destino');
    await activate(origin);await origin.press('Escape');
    await expect(origin).toHaveAttribute('aria-expanded','false');
    expect((await currentSession(page)).origin.useLocation).toBe(true);
  });
});

test('locais ainda não definidos recolhem inclusive durante a seleção',async({page,context})=>{
  await setup(page,context,false);
  const origin=page.locator('.sp-map-point-controls [data-kind="origin"]');
  const destination=page.locator('.sp-map-point-controls [data-kind="destination"]');
  await expect(origin).toHaveAttribute('data-state','empty');
  await expect(origin).toHaveAttribute('aria-expanded','false');
  await expect(destination).toHaveAttribute('aria-expanded','false');
  await expect(origin).toHaveCSS('width','44px');
  await expect(destination).toHaveCSS('width','44px');
  await expect(origin).toHaveCSS('border-top-style','dotted');
  await origin.click();await expect(origin).toHaveAttribute('aria-expanded','true');
  await origin.click();await expect(page.locator('.sp-navigation-state')).toContainText('Selecionar embarque');
  await expect(origin).toHaveAttribute('aria-expanded','false');
  await origin.click();await expect(origin).toHaveAttribute('aria-expanded','true');
  await page.locator('.sp-navigation-state').click();
  await expect(origin).toHaveAttribute('aria-expanded','false');
});
