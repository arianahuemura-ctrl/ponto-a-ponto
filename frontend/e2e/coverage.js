import {test as base, expect} from '@playwright/test';
import {mkdir, writeFile} from 'node:fs/promises';
import {randomUUID} from 'node:crypto';

async function instrument(context) {
  const save = async coverage => {
    if (!coverage) return;
    await mkdir('.nyc_output', {recursive:true});
    await writeFile(`.nyc_output/browser-${randomUUID()}.json`, JSON.stringify(coverage));
  };
  await context.exposeFunction('__papSaveCoverage', save);
  await context.addInitScript(() => {
    window.addEventListener('beforeunload', () => window.__papSaveCoverage(window.__coverage__));
  });
  const close = context.close.bind(context);
  context.close = async (...args) => {
    for (const page of context.pages()) {
      if (!page.isClosed()) await save(await page.evaluate(() => window.__coverage__));
    }
    return close(...args);
  };
  return context;
}

// Cobre tanto a página padrão de teste quanto os contextos explícitos de celular/computador.
// Nada é injetado ou coletado em testes comuns ou compilações de produção.
export const test = base.extend({
  browser: [async ({browser}, use) => {
    if (process.env.PAP_COVERAGE !== '1') { await use(browser); return; }
    const newContext = browser.newContext.bind(browser);
    browser.newContext = async (...args) => instrument(await newContext(...args));
    try { await use(browser); } finally { browser.newContext = newContext; }
  }, {scope:'worker'}],
});
export {expect};
