import { test, expect } from "@playwright/test";

const origin = "/?stop=way:1410074325";
async function fits(page) {
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  expect(await page.locator('.passenger-screen').evaluate(el => el.scrollWidth <= el.clientWidth + 1)).toBe(true);
  await expect(page.getByRole('navigation', { name: 'Navegação principal' })).toBeInViewport();
}
for (const [width, height] of [[320, 640], [390, 844], [768, 1024], [1440, 900], [844, 390]]) {
  test(`fluxos responsivos e tema escuro em ${width}x${height}`, async ({ page }) => {
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.setViewportSize({ width, height });
    await page.route('https://tile.openstreetmap.org/**', r => r.abort());
    await page.goto(origin);
    await page.getByRole('button', { name: 'Ativar modo escuro' }).click();
    await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
    await fits(page);
    await page.screenshot({ path: `test-results/responsive-${width}-home-dark.png` });
    await page.getByRole('button', { name: /Buscar destino.*no mapa/ }).click();
    await fits(page);
    await page.getByRole('button', { name: /Trabalho .*Mauá/ }).click();
    await page.screenshot({ path: `test-results/responsive-${width}-destination-dark.png` });
    await page.getByRole('button', { name: 'Confirmar destino' }).click();
    await expect(page.locator('.line-card').first()).toBeVisible();
    await fits(page);
    await page.getByRole('button', { name: 'Ver essas linhas no mapa' }).click();
    await fits(page);
    await page.locator('.line-card').first().click();
    await fits(page);
    await page.getByRole('tab', { name: 'Itinerário', exact: true }).click();
    await fits(page);
    await page.getByRole('tab', { name: 'Mapa da linha' }).click();
    await fits(page);
    await page.screenshot({ path: `test-results/responsive-${width}-detail-dark.png` });
    await page.getByRole('button', { name: 'Favoritos', exact: true }).click();
    await fits(page);
    await page.getByRole('button', { name: 'Mais', exact: true }).click();
    await page.getByRole('button', { name: 'QR Code deste ponto' }).click();
    await fits(page);
    await page.reload();
    await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
    await page.getByRole('button', { name: 'Ativar modo claro' }).click();
    await expect(page.locator('html')).toHaveAttribute('data-theme', 'light');
    await page.screenshot({ path: `test-results/responsive-${width}-home-light.png` });
    await page.getByRole('button', { name: 'Horários', exact: true }).click();
    await fits(page);
    await page.getByRole('button', { name: 'Consultar cadastro de linhas' }).click();
    await expect(page.getByRole('heading', { name: 'Linhas e pontos cadastrados' })).toBeVisible();
    await fits(page);
    expect(errors).toEqual([]);
  });
}
test('tema acompanha o dispositivo, permite escolha explícita e tolera armazenamento bloqueado', async ({ page }) => {
  await page.addInitScript(() => { Storage.prototype.setItem = () => { throw new Error('bloqueado'); }; });
  await page.emulateMedia({ colorScheme: 'dark' });
  await page.goto(origin);
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
  await page.emulateMedia({ colorScheme: 'light' });
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'light');
  await page.getByRole('button', { name: 'Ativar modo escuro' }).click();
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
  await page.getByRole('button', { name: 'Mais', exact: true }).click();
  await page.getByLabel('Aparência').selectOption('system');
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'light');
});
