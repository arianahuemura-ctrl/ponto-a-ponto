const {chromium}=require('/home/avale/Projetos/maua_bus_map/frontend/node_modules/playwright');
const fs=require('fs');const P='/tmp/pap-artesp-academico-20261102';
(async()=>{
 const q=JSON.parse(fs.readFileSync(P+'/planning-queries.json')).queries.find(q=>q.scenario==='onibus_trem');
 const browser=await chromium.launch({headless:true,args:['--no-sandbox']});
 const context=await browser.newContext({viewport:{width:1920,height:1080},deviceScaleFactor:1,locale:'pt-BR',timezoneId:'America/Sao_Paulo'});
 const page=await context.newPage();const responses=[];
 page.on('response',async r=>{if(r.url().includes('/api/sptrans/board/')){try{responses.push({url:r.url(),status:r.status(),text:await r.text()});}catch{}}});
 await page.addInitScript(({origin,destination})=>localStorage.setItem('pap.sp.favorites',JSON.stringify([destination])),q);
 const begun=new Date().toISOString();
 await page.goto('http://127.0.0.1:8001/?stop='+encodeURIComponent(q.origin.id),{waitUntil:'domcontentloaded'});
 try{await page.getByRole('button',{name:'Continuar sem contribuir',exact:true}).click({timeout:10000});}catch{}
 await page.getByRole('button',{name:'Ver mapa',exact:true}).click();
 await page.getByRole('button',{name:'Favoritos',exact:true}).click();
 await page.getByRole('button',{name:'Usar como destino Brás',exact:true}).click();
 await page.locator('.sp-route-option').first().waitFor({state:'visible',timeout:60000});
 await page.waitForTimeout(3000);
 await page.screenshot({path:P+'/captura-maua-bras-consulta.png'});
 const body=await page.locator('body').innerText();fs.writeFileSync(P+'/captura-maua-bras-texto.txt',body);
 const options=await page.locator('.sp-route-option').allTextContents();
 let selected=page.locator('.sp-route-option').filter({hasText:'157'}).filter({hasText:'10'}).first();
 if(await selected.count())await selected.click();
 try{await page.getByRole('button',{name:'Ver mapa',exact:true}).click({timeout:5000});}catch{}
 await page.waitForTimeout(2500);await page.screenshot({path:P+'/captura-maua-bras-mapa.png'});
 fs.writeFileSync(P+'/live-capture.json',JSON.stringify({begun,finished:new Date().toISOString(),origin:q.origin,destination:q.destination,options,responses,note:'Real public application queried at actual server time; no route, timetable or response interception. Recording consent declined. Local address is not a remotely accessible QR destination.'},null,2));
 console.log(JSON.stringify({begun,options,screenshots:['captura-maua-bras-consulta.png','captura-maua-bras-mapa.png']}));
 await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
