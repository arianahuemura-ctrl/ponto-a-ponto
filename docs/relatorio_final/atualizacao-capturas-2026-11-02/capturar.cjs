const {chromium}=require('/home/avale/Projetos/maua_bus_map/frontend/node_modules/playwright');
const fs=require('fs'),crypto=require('crypto');
const ROOT='/home/avale/Projetos/maua_bus_map-relatorio';
const OUT=ROOT+'/docs/relatorio_final/capturas/2026-11-02-interface-atual';
const CACHE=ROOT+'/.cache/setup/capturas-atuais-20261102';
const BASE='http://127.0.0.1:18082';
const run=process.argv[2]||'static';
const manifest={run,started:new Date().toISOString(),appCommit:'78e39355ce23aa545c4006978bcc59060f6db24f',baseURL:BASE,transport:'Real application; no mocked or substituted responses',research:'Declined through UI; no feedback sent',captures:[],requests:[]};
let browser;
async function context(desktop=false,theme='dark'){
 const c=await browser.newContext({viewport:desktop?{width:1366,height:1000}:{width:430,height:932},deviceScaleFactor:2,locale:'pt-BR',timezoneId:'America/Sao_Paulo',colorScheme:theme});
 const p=await c.newPage();p.setDefaultTimeout(20000);
 p.on('response',r=>{if(r.url().startsWith(BASE+'/api/'))manifest.requests.push({time:new Date().toISOString(),method:r.request().method(),url:r.url(),status:r.status()});});
 return p;
}
async function go(p,path='/'){
 await p.goto(BASE+path,{waitUntil:'domcontentloaded'});
 const decline=p.getByRole('button',{name:'Continuar sem contribuir',exact:true});
 if(await decline.isVisible())await decline.click();
 await p.locator('.leaflet-container').waitFor();await p.waitForTimeout(4500);
}
async function shot(p,name,note){
 await p.evaluate(()=>document.fonts.ready);await p.mouse.move(1,1);await p.waitForTimeout(600);
 const path=OUT+'/'+name+'.png';if(fs.existsSync(path))throw Error('Refusing overwrite '+path);
 await p.screenshot({path});
 fs.writeFileSync(CACHE+'/'+name+'.txt',await p.locator('body').innerText());
 manifest.captures.push({file:name+'.png',at:new Date().toISOString(),url:p.url(),viewport:p.viewportSize(),scale:2,note,sha256:crypto.createHash('sha256').update(fs.readFileSync(path)).digest('hex')});
 fs.writeFileSync(OUT+'/manifest-'+run+'.json',JSON.stringify(manifest,null,2)+'\n');console.log('Captured '+name);
}
async function stop(p,id){const r=await p.request.get(BASE+'/api/sptrans/stops/?id='+id);const d=await r.json();return d.stops[0];}
(async()=>{browser=await chromium.launch({headless:true,args:['--no-sandbox']});
 if(run==='static'){
  let p=await context();await p.goto(BASE);await p.getByRole('button',{name:'Continuar sem contribuir',exact:true}).waitFor();
  await shot(p,'pesquisa-inicial','Fresh browser, no previous research choice.');
  await p.getByRole('button',{name:'Continuar sem contribuir',exact:true}).click();await p.locator('.leaflet-container').waitFor();await p.waitForTimeout(5000);
  await shot(p,'sem-localizacao','Geolocation not authorized.');
  await p.getByRole('button',{name:'Configurações',exact:true}).click();
  await p.getByRole('button',{name:'Participação na pesquisa',exact:true}).click();
  await shot(p,'pesquisa-configuracoes','Research declined, settings opened; no recording.');
  await p.getByRole('button',{name:'Fechar configurações',exact:true}).click();await p.getByRole('button',{name:'Feedback',exact:true}).click();
  await shot(p,'feedback','Empty feedback form; no rating or message submitted.');await p.context().close();
  p=await context();await go(p,'/?location=-23.561326733117216,-46.65615056649423');
  await shot(p,'localizacao','Location simulated at MASP through supported URL parameter.');
  await p.getByRole('button',{name:'Mostrar embarque',exact:true}).click();await p.getByRole('button',{name:'Alterar embarque',exact:true}).click();
  await shot(p,'alterar-embarque','Manual origin selection with simulated MASP location.');await p.context().close();
  for(const theme of ['light','dark']){
   p=await context(true,theme);await go(p,'/?location=-23.561326733117216,-46.65615056649423');
   await shot(p,'ferrovia-'+theme,'Simulated MASP location; lamp on; '+theme+' theme; current rail labels.');await p.context().close();
  }
 }
 if(run==='journey'||run==='route'){
  const p=await context();await go(p,'/?stop=1211381');await p.getByRole('heading',{name:'Próximos ônibus',exact:true}).waitFor();await p.waitForTimeout(5000);
  if(run==='journey')await shot(p,'embarque','Entry through stop 1211381 URL; no physical QR reading.');
  await p.getByRole('button',{name:'Informações do ponto',exact:true}).click();await p.locator('#sp-point-info img').waitFor();await p.waitForTimeout(500);
  if(run==='journey')await shot(p,'qr-atual','Actual QR for the local development URL, not public deployment.');
  await p.getByRole('button',{name:'Ver mapa',exact:true}).click();
  const favs=[];for(const [id,label] of [['680017148','Casa'],['8210184','UNIVESP Carrão'],['600012585','Guaiaúna']]){const s=await stop(p,id);if(!s)throw Error('Missing stop '+id);favs.push({...s,favoriteLabel:label});}
  manifest.preparedFavorites=favs;
  await p.evaluate(f=>{localStorage.setItem('pap.sp.favorites',JSON.stringify(f));localStorage.setItem('pap.sp.quickDestinations',JSON.stringify({home:f[0].id}));},favs);
  await go(p,'/?stop=1211381');await p.getByRole('button',{name:'Ver mapa',exact:true}).click();await p.getByRole('button',{name:'Favoritos',exact:true}).click();
  if(run==='journey')await shot(p,'favoritos','Prepared favourites with real catalogued stops and illustrative labels; not participant data.');
  await p.getByRole('button',{name:'Usar como destino Guaiaúna',exact:true}).click();
  for(let i=0;i<12;i++){await p.waitForTimeout(10000);fs.writeFileSync(CACHE+'/route-progress-'+i+'.txt',await p.locator('body').innerText());if(await p.locator('.sp-route-option').count())break;}
  await p.screenshot({path:CACHE+'/route-debug.png'});
  await p.locator('.sp-route-option').first().waitFor({timeout:10000});await p.waitForTimeout(5000);
  await shot(p,'alternativas','Real progressive route query from 1211381 to 600012585; consult text log for displayed state.');
  await p.getByRole('button',{name:'Ver mapa',exact:true}).click();await p.waitForTimeout(4000);
  await shot(p,'viagem-completa','Selected route as calculated by actual application at capture time.');
  const select=p.getByLabel('Trecho exibido no mapa');await select.waitFor();const values=await select.locator('option').evaluateAll(es=>es.map(e=>({value:e.value,text:e.textContent})));
  manifest.segments=values;await select.selectOption(values.at(-1).value);await p.waitForTimeout(4000);
  await shot(p,'ultimo-trecho','Last segment of same selected route.');
  await p.getByRole('button',{name:'Cancelar viagem',exact:true}).click();
  await shot(p,'confirmacao','Cancellation confirmation; same journey.');await p.context().close();
 }
 if(run==='free'){
  const p=await context();await go(p,'/?stop=1211381');await p.getByRole('button',{name:'Ver mapa',exact:true}).click();
  const b=await p.locator('.leaflet-container').boundingBox();await p.mouse.move(b.x+b.width*.65,b.y+b.height*.4);await p.mouse.down();await p.waitForTimeout(1000);await p.mouse.up();
  await shot(p,'destino-livre','Long press on map opens destination and save-location actions; destination not yet confirmed.');await p.context().close();
 }
 if(run==='line'){
  const p=await context(true);await go(p,'/?stop=5614798');await p.getByRole('button',{name:'Ver trajeto da linha 6L10-41',exact:true}).first().waitFor({timeout:120000});
  await p.getByRole('button',{name:'Ver trajeto da linha 6L10-41',exact:true}).first().click();await p.waitForTimeout(10000);
  await shot(p,'linha-6L10-completa','Real 6L10-41 route from stop 5614798; availability as displayed.');await p.context().close();
 }
})().catch(e=>{manifest.error=String(e.stack);console.error(e);process.exitCode=1;}).finally(async()=>{manifest.ended=new Date().toISOString();fs.writeFileSync(OUT+'/manifest-'+run+'.json',JSON.stringify(manifest,null,2)+'\n');if(browser)await browser.close();});
