import { test, expect } from '@playwright/test';

const point = { id: '440016922', name: 'Av. Paulista, 1578', lat: -23.5614, lon: -46.6559 };

test('falha no módulo inicial mantém uma orientação visível', async ({ page }) => {
  await page.route('**/assets/index-*.js', route => route.fulfill({ status: 404, body: '' }));
  await page.goto('/?stop=440016922');
  await expect(page.getByRole('heading', { name: 'Ponto a Ponto', exact: true })).toBeVisible();
  await expect(page.getByRole('link', { name: 'recarregue a página' })).toBeVisible();
});

test('falha de módulo após atualização permite recuperar QR e favoritos', async ({ page }) => {
  await page.route('**/api/**', route => {
    const url = route.request().url();
    return route.fulfill({ json: url.includes('/stops/') ? { stops: [point] } : url.includes('/board/') ? { lines: [], journeys: [], complete: true } : {} });
  });
  await page.route('https://tile.openstreetmap.org/**', route => route.abort());
  await page.route('**/assets/SaoPaulo-*.js', route => route.fulfill({ status: 404, body: '' }));
  await page.goto('/?stop=440016922');
  await page.evaluate(point => localStorage.setItem('pap.sp.favorites', JSON.stringify([point])), point);
  await page.getByRole('button', { name: 'Continuar sem contribuir', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Não foi possível abrir o PaP' })).toBeVisible();
  await page.unroute('**/assets/SaoPaulo-*.js');
  await page.getByRole('button', { name: 'Recarregar aplicativo' }).click();
  await expect(page).toHaveURL(/stop=440016922.*_pap_reload=/);
  await expect(page.getByRole('dialog', { name: 'Próximos ônibus' })).toBeVisible();
  await expect(page.getByRole('dialog', { name: 'Próximos ônibus' }).getByText('Av. Paulista, 1578', { exact: false })).toBeVisible();
  expect(await page.evaluate(() => JSON.parse(localStorage.getItem('pap.sp.favorites')))).toEqual([point]);
});
