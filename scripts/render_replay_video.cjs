const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const {execFileSync} = require('child_process');
const {chromium} = require('../frontend/node_modules/playwright');
(async () => {
 const [input, output] = process.argv.slice(2);
 const events = JSON.parse(fs.readFileSync(input, 'utf8'));
 const meta = events.find(e => e.type === 4)?.data || {};
 const width = Math.max(240, Math.min(1920, Math.round(meta.width || 1280)));
 const height = Math.max(240, Math.min(1920, Math.round(meta.height || 720)));
 const browser = await chromium.launch({headless:true});
 try {
  const context = await browser.newContext({viewport:{width,height}});
  // The replay cannot call the application or arbitrary network destinations.
  await context.route('**/*', route => {
   const url = new URL(route.request().url());
   if (route.request().resourceType() === 'image' && url.protocol === 'https:' && /^(?:[abc]\.)?tile\.openstreetmap\.org$/.test(url.hostname)) return route.continue();
   return route.abort();
  });
  const page = await context.newPage();
  await page.setContent('<style>html,body{margin:0;overflow:hidden;background:#112136}.rr-player{box-shadow:none!important}</style><div id="player"></div>');
  await page.addStyleTag({path:require.resolve('../frontend/node_modules/rrweb-player/dist/style.css')});
  await page.addScriptTag({path:require.resolve('../frontend/node_modules/rrweb-player/dist/rrweb-player.umd.cjs')});
  await page.addScriptTag({path:path.join(__dirname,'../backend/transit/static/transit/replay-theme.js')});
  await page.evaluate(({events,width,height}) => {
   window.player=new (rrwebPlayer.default||rrwebPlayer)({target:document.querySelector('#player'),props:{events,autoPlay:false,showController:false,width,height,UNSAFE_replayCanvas:true}});
   papReplayTheme(player,events);
  },{events,width,height});
  const base = events[0].timestamp;
  const duration = Math.max(1, events.at(-1).timestamp-base);
  // Match the capture's 5 fps ceiling, but never iterate over idle time.
  const times = new Set([0]);
  for (const event of events) {
   const offsets = [event.timestamp-base];
   for (const position of event.data?.positions || []) offsets.push(event.timestamp-base+(position.timeOffset||0));
   for (const offset of offsets) times.add(Math.max(0,Math.min(duration,Math.ceil(offset/200)*200)));
  }
  const folder = fs.mkdtempSync(path.join(path.dirname(output),'frames-'));
  try {
   const frames=[];
   let previousHash;
   for (const time of [...times].sort((a,b)=>a-b)) {
    await page.evaluate(async time=>{
     player.goto(time+1,false);
     // Flush layout and asynchronous canvas operations without replaying wall time.
     await new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));
     const doc=document.querySelector('#player iframe')?.contentDocument;
     const images=[...(doc?.images||[])].filter(image=>!image.complete);
     if(images.length)await Promise.race([
      Promise.all(images.map(image=>image.decode().catch(()=>{}))),
      new Promise(resolve=>setTimeout(resolve,1500))
     ]);
    },time);
    const png=await page.screenshot({animations:'disabled'});
    const hash=crypto.createHash('sha256').update(png).digest('hex');
    if(hash===previousHash)continue;
    const file=`frame-${frames.length}.png`;
    fs.writeFileSync(path.join(folder,file),png);
    frames.push({file,time});previousHash=hash;
   }
   const lines=['ffconcat version 1.0'];
   for(let i=0;i<frames.length;i++){
    const end=i+1<frames.length?frames[i+1].time:duration;
    if(end<=frames[i].time)continue;
    lines.push(`file '${frames[i].file}'`,`option framerate 1000`,`duration ${(end-frames[i].time)/1000}`);
   }
   lines.push(`file '${frames.at(-1).file}'`,`option framerate 1000`);
   fs.writeFileSync(path.join(folder,'frames.txt'),lines.join('\n')+'\n');
   execFileSync('ffmpeg',['-hide_banner','-loglevel','error','-y','-safe','0','-f','concat','-i',path.join(folder,'frames.txt'),'-fps_mode','vfr','-c:v','libvpx-vp9','-deadline','realtime','-cpu-used','6','-pix_fmt','yuv420p',output],{timeout:3600000});
   console.log(JSON.stringify({durationMs:duration,rendered:times.size,uniqueFrames:frames.length}));
  } finally {fs.rmSync(folder,{recursive:true,force:true});}
  await context.close();
 } finally {await browser.close();}
})().catch(error=>{console.error(error.message);process.exit(1);});
