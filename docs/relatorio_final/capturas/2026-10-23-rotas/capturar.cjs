const {chromium}=require('/home/avale/Projetos/maua_bus_map/frontend/node_modules/playwright');
const fs=require('fs'),crypto=require('crypto');
const out=__dirname,base='http://127.0.0.1:8001';const records=[];
(async()=>{const browser=await chromium.launch({headless:true});
async function context(viewport){const c=await browser.newContext({viewport,deviceScaleFactor:2,colorScheme:'dark'});await c.addInitScript(()=>localStorage.setItem('pap.theme','dark'));await c.route('**/api/usability/**',r=>{throw Error('Coleta inesperada durante captura sem participação');});return c;}
async function shot(p,name){await p.waitForTimeout(1500);await p.mouse.move(0,0);await p.screenshot({path:out+'/'+name+'.png'});records.push({file:name+'.png',date:new Date().toISOString(),url:p.url(),viewport:p.viewportSize(),sha256:crypto.createHash('sha256').update(fs.readFileSync(out+'/'+name+'.png')).digest('hex'),text:await p.locator('body').innerText()});fs.writeFileSync(out+'/registro.json',JSON.stringify(records,null,2));console.log(name);}
try{
let c=await context({width:430,height:932}),p=await c.newPage();
await p.goto(base);await p.getByRole('button',{name:'Continuar sem contribuir',exact:true}).waitFor();await shot(p,'pesquisa-inicial');await p.getByRole('button',{name:'Continuar sem contribuir',exact:true}).click();await p.waitForTimeout(4000);await shot(p,'sem-localizacao');
await p.getByRole('button',{name:'Configurações',exact:true}).click();await shot(p,'pesquisa-configuracoes');await p.getByRole('button',{name:'Fechar configurações',exact:true}).click();await p.getByRole('button',{name:'Feedback',exact:true}).click();await shot(p,'feedback');await c.close();
c=await context({width:1366,height:1000});p=await c.newPage();p.setDefaultTimeout(60000);
await p.goto(base+'/?stop=5614798');await p.getByRole('button',{name:'Continuar sem contribuir',exact:true}).click();await p.getByRole('button',{name:'Ver trajeto da linha 6L10-41',exact:true}).waitFor();await shot(p,'linha-6L10-consulta');await p.getByRole('button',{name:'Ver trajeto da linha 6L10-41',exact:true}).click();await p.locator('.sp-direction-arrow').first().waitFor();await p.waitForTimeout(5000);await p.locator('.leaflet-control-zoom-out').click();await shot(p,'linha-6L10-completa');
// Ampliação real pelo controle do mapa; mantém o estado e os dados da consulta.
await p.locator('.leaflet-control-zoom-in').click();await p.waitForTimeout(500);await p.locator('.leaflet-control-zoom-in').click();await p.waitForTimeout(1500);await shot(p,'linha-6L10-detalhe');await c.close();
}finally{await browser.close();}})().catch(e=>{console.error(e);process.exitCode=1;});
