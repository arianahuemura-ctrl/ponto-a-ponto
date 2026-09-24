import { test, expect } from "@playwright/test";
const elements = [
  {
    type: "node",
    id: 1,
    lat: -23.6676,
    lon: -46.4603,
    tags: { highway: "bus_stop", name: "Terminal" },
  },
  {
    type: "node",
    id: 2,
    lat: -23.665,
    lon: -46.456,
    tags: { highway: "bus_stop", name: "Escola" },
  },
  {
    type: "node",
    id: 3,
    lat: -23.67,
    lon: -46.456,
    tags: { highway: "bus_stop", name: "Hospital" },
  },
  ...[
    [10, 2],
    [20, 3],
  ].map(([id, end]) => ({
    type: "relation",
    id,
    tags: { route: "bus", ref: String(id) },
    members: [
      { type: "node", ref: 1, role: "stop", lat: -23.6676, lon: -46.4603 },
      {
        type: "node",
        ref: end,
        role: "stop",
        lat: end === 2 ? -23.665 : -23.67,
        lon: -46.456,
      },
    ],
  })),
];
test.beforeEach(async ({ page }) => {
  await page.route("https://tile.openstreetmap.org/**", (r) => r.abort());
  await page.route("**/api/geocode/**", (r) =>
    r.fulfill({ json: { lat: -23.6676, lon: -46.4603, label: "Mauá" } }),
  );
  await page.route("**/api/nearby/**", (r) =>
    r.fulfill({ json: { elements } }),
  );
});
test("busca, compara linhas, refina destino, desfaz e limpa", async ({
  page,
}) => {
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/explorar/");
  await page.getByRole("searchbox").fill("Mauá");
  await page.getByRole("button", { name: "Buscar endereço" }).click();
  await expect(page.getByRole("status")).toContainText("3 pontos próximos");
  await page.locator('.leaflet-marker-icon[title="Terminal"]').click();
  await expect(page.locator(".route-item")).toHaveCount(2);
  await page.locator('.leaflet-marker-icon[title="Escola"]').click();
  await expect(page.locator(".route-item")).toHaveCount(1);
  await expect(page.locator(".route-ref")).toHaveText("10");
  await page.getByRole("button", { name: "Desfazer último ponto" }).click();
  await expect(page.locator(".route-item")).toHaveCount(2);
  await page.getByRole("button", { name: "Limpar seleção" }).click();
  await expect(page.getByRole("region", { name: "Seleção atual" })).toHaveCount(
    0,
  );
  expect(errors).toEqual([]);
});
test("mostra falha da API e permite tentar novamente", async ({ page }) => {
  await page.route("**/api/nearby/**", (r) =>
    r.fulfill({ status: 502, json: { error: "OSM indisponível" } }),
  );
  await page.goto("/explorar/");
  await page.getByRole("searchbox").fill("Mauá");
  await page.getByRole("button", { name: "Buscar endereço" }).click();
  await expect(page.getByRole("status")).toContainText("OSM indisponível");
  await expect(
    page.getByRole("button", { name: "Buscar endereço" }),
  ).toBeEnabled();
});
test("legenda no celular fecha pelo botão voltar", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/explorar/");
  await page.getByRole("button", { name: "Abrir legenda" }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.goBack();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "Abrir legenda" }),
  ).toBeFocused();
});
