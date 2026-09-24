import { test, expect } from "@playwright/test";
const origin = "way:1410074325";
async function selectDestination(page, name = "Trabalho") {
  await page.getByRole("button", { name: /Buscar destino.*no mapa/ }).click();
  await page
    .getByRole("button", { name: new RegExp(name + " .*Mauá") })
    .click();
  await page.getByRole("button", { name: "Confirmar destino" }).click();
  await expect(
    page.getByRole("heading", { name: "Linhas que atendem origem e destino" }),
  ).toBeVisible();
}
test.beforeEach(async ({ page }) => {
  await page.route("https://tile.openstreetmap.org/**", (r) => r.abort());
  await page.setViewportSize({ width: 390, height: 844 });
});
test("tela inicial segue mockup e não expõe controles de simulação", async ({
  page,
}) => {
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/?stop=" + origin);
  await expect(
    page.getByRole("heading", { name: "Meu Ponto", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Ponto MAU-001" }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: /Iniciar simulação|Pausar|Reiniciar/ }),
  ).toHaveCount(0);
  await expect(
    page.getByRole("navigation", { name: "Navegação principal" }),
  ).toBeVisible();
  await page.screenshot({ path: "test-results/mockup-02-home.png" });
  expect(errors).toEqual([]);
});
test("lista, destino, filtro, mapa conjunto e detalhes são telas distintas", async ({
  page,
}) => {
  await page.goto("/?stop=" + origin);
  await page.getByRole("button", { name: /Ver linhas.*deste ponto/ }).click();
  await expect(
    page.getByRole("heading", { name: "Próximos ônibus neste ponto" }),
  ).toBeVisible();
  await expect(page.locator(".line-card")).toHaveCount(4);
  await page.screenshot({ path: "test-results/mockup-03-lines.png" });
  await page
    .getByRole("button", { name: "Selecionar destino no mapa" })
    .click();
  await expect(
    page.getByRole("heading", { name: "Ponto de destino" }),
  ).toBeVisible();
  await page.getByRole("button", { name: /Trabalho .*Mauá/ }).click();
  await expect(
    page.getByRole("button", { name: "Confirmar destino" }),
  ).toBeEnabled();
  await page.screenshot({ path: "test-results/mockup-04-destination.png" });
  await page.getByRole("button", { name: "Confirmar destino" }).click();
  await expect(page.locator(".line-card").first()).toContainText("25 min");
  await page.screenshot({ path: "test-results/mockup-05-filtered.png" });
  await page.getByRole("button", { name: "Ver essas linhas no mapa" }).click();
  await expect(
    page.getByRole("heading", { name: /Veículos em tempo real/ }),
  ).toBeVisible();
  await expect(page.locator(".leaflet-overlay-pane path")).not.toHaveCount(0);
  await page.screenshot({ path: "test-results/mockup-06-vehicles.png" });
  await page.locator(".line-card").first().click();
  await expect(
    page.getByRole("tab", { name: "Horários", exact: true }),
  ).toHaveAttribute("aria-selected", "true");
  await page.screenshot({ path: "test-results/mockup-07-details.png" });
  await page.getByRole("tab", { name: "Mapa da linha", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Paradas da viagem" }),
  ).toBeVisible();
  await expect(page.locator(".transfer-label")).toContainText("307");
  const maxCommands = await page
    .locator(".leaflet-overlay-pane path")
    .evaluateAll((paths) =>
      Math.max(
        ...paths.map((p) => (p.getAttribute("d")?.match(/[ML]/g) || []).length),
      ),
    );
  expect(maxCommands).toBeGreaterThan(10);
  await page.screenshot({ path: "test-results/mockup-08-line-map.png" });
});
test("favoritos persistem e voltam ao fluxo filtrado", async ({ page }) => {
  await page.goto("/?stop=" + origin);
  await selectDestination(page);
  await page.getByRole("button", { name: "Favoritos", exact: true }).click();
  await page.getByLabel("Nome do favorito").fill("Casa");
  await page
    .getByRole("button", { name: "Salvar favorito", exact: true })
    .click();
  await page.reload();
  await page.getByRole("button", { name: "Favoritos", exact: true }).click();
  await page.getByRole("button", { name: "Voltar para casa" }).click();
  await expect(page.locator(".line-card").first()).toContainText("25 min");
  await page.getByRole("button", { name: "Favoritos", exact: true }).click();
  await page.getByRole("button", { name: "Remover favorito Casa" }).click();
  await expect(
    page.getByRole("button", { name: "Voltar para casa" }),
  ).toHaveCount(0);
});
test("QR e registro de avaliação continuam disponíveis em Mais", async ({
  page,
}) => {
  await page.goto("/?stop=" + origin);
  await page.getByRole("button", { name: "Mais", exact: true }).click();
  await page.getByRole("button", { name: "QR Code deste ponto" }).click();
  const image = page.getByRole("img", { name: "QR Code do ponto MAU-001" });
  await expect
    .poll(() => image.evaluate((e) => e.complete && e.naturalWidth > 0))
    .toBe(true);
  await page.getByText("Registrar avaliação", { exact: true }).click();
  await page
    .getByLabel("Observações")
    .fill("Avaliação automatizada das telas.");
  await page.getByRole("button", { name: "Registrar observações" }).click();
  await expect(page.getByRole("status")).toContainText("Observação registrada");
});
test("sem conexão, mapa livre e navegação voltar", async ({ page }) => {
  await page.goto("/?stop=" + origin);
  await selectDestination(page, "Parada sem conexão");
  await expect(
    page.getByText("Nenhuma conexão disponível para este destino."),
  ).toBeVisible();
  await page.goBack();
  await expect(
    page.getByRole("heading", { name: "Ponto de destino" }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth > innerWidth,
    ),
  ).toBe(false);
});
test("admin liga e desliga simulação global sem controle no passageiro", async ({
  page,
  context,
}) => {
  await page.goto("/admin/transit/simulation/1/change/");
  await expect(page.getByLabel("Usuário:")).toBeVisible();
  await page.getByLabel("Usuário:").fill("test-admin");
  await page.getByLabel("Senha:").fill("temporary-e2e-password");
  await page.getByRole("button", { name: "Acessar" }).click();
  await expect(page.getByLabel("Simulação ligada")).toBeVisible();
  const passenger = await context.newPage();
  await passenger.route("https://tile.openstreetmap.org/**", (r) => r.abort());
  await passenger.goto("/?stop=" + origin);
  await passenger
    .getByRole("button", { name: /Ver linhas.*deste ponto/ })
    .click();
  await expect(passenger.locator(".line-card")).toHaveCount(4);
  await page.getByLabel("Simulação ligada").uncheck();
  await page.locator('input[name="_save"]').click();
  await expect(
    passenger.getByText("Previsões indisponíveis no momento", { exact: true }),
  ).toBeVisible({ timeout: 10000 });
  await expect(passenger.locator(".line-card")).toHaveCount(0);
  await page.goto("/admin/transit/simulation/1/change/");
  await page.getByLabel("Simulação ligada").check();
  await page.locator('input[name="_save"]').click();
  await expect(passenger.locator(".line-card")).toHaveCount(4, {
    timeout: 10000,
  });
  await passenger.close();
});
test("favoritar linha persiste sem precisar escolher destino", async ({
  page,
}) => {
  await page.goto("/?stop=" + origin);
  await page.getByRole("button", { name: /Ver linhas.*deste ponto/ }).click();
  await page.locator(".line-card").first().click();
  await page
    .getByRole("button", { name: "Favoritar linha", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Remover linha dos favoritos" }),
  ).toHaveAttribute("aria-pressed", "true");
  await page.reload();
  await page.getByRole("button", { name: "Favoritos", exact: true }).click();
  await page.getByRole("button", { name: /Linha 405 ·/ }).click();
  await expect(
    page.getByRole("heading", { name: "Detalhes da linha", exact: true }),
  ).toBeVisible();
});


test("catálogo mostra sequência importada sem inventar localização", async ({ page }) => {
  await page.route("**/api/catalogue/?*", route => route.fulfill({ json: {
    counts: { stops: 2, located_stops: 1, variants: 1 },
    routes: [{ id: "cittamobi:test", code: "088", name: "ZAIRA", source: "cittamobi", stop_count: 2 }],
    sources: [],
  } }));
  await page.route("**/api/catalogue/routes/**", route => route.fulfill({ json: {
    id: "cittamobi:test", code: "088", name: "ZAIRA", source: "cittamobi", routable: false,
    stops: [{ id: "a", name: "Parada verificada", lat: -23.6 }, { id: "b", name: "Parada sem coordenadas", lat: null }],
  } }));
  await page.goto("/?stop=" + origin);
  await page.getByRole("button", { name: /Ver linhas.*deste ponto/ }).click();
  await page.getByRole("button", { name: "Consultar cadastro de linhas" }).click();
  await page.getByRole("textbox", { name: "Buscar linha" }).fill("088");
  await page.getByRole("button", { name: /088 — ZAIRA/ }).click();
  await expect(page.getByText("Parada sem coordenadas · localização pendente")).toBeVisible();
  await expect(page.getByText(/Sem dados suficientes para planejamento/)).toBeVisible();
});


test("mapa identifica a localização aproximada da parada", async ({ page }) => {
  await page.route("**/api/network/?*", async route => {
    const response = await route.fetch();
    const data = await response.json();
    data.stops.find(s => s.id === origin).geolocation = { status: "estimated" };
    await route.fulfill({ json: data });
  });
  await page.goto("/?stop=" + origin);
  await expect(page.locator(".map-stop-label").filter({ hasText: "posição aproximada" })).toBeVisible();
});
