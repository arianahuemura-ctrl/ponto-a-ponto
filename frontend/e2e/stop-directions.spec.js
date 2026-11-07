import {test,expect} from '@playwright/test';

test.use({viewport:{width:390,height:844},deviceScaleFactor:2});
for(const theme of ['light','dark'])test(`setas de embarque ficam visíveis fora do símbolo no tema ${theme}`,async({page,context})=>{
  const departure=bearing=>({bearing,kind:'departure'});
  const stops=[
    {id:'north',name:'Norte',lat:-23.5475,lon:-46.6363,directions:[departure(0),{bearing:180,kind:'arrival'}]},
    {id:'east',name:'Leste',lat:-23.5475,lon:-46.6303,directions:[departure(90)]},
    {id:'south',name:'Sul',lat:-23.5535,lon:-46.6363,directions:[departure(180)]},
    {id:'west',name:'Oeste',lat:-23.5535,lon:-46.6303,directions:[departure(270)]},
    {id:'unknown',name:'Sem sentido cadastrado',lat:-23.5505,lon:-46.6333,directions:[]},
    {id:'metro',name:'Estação de metrô',mode:'metro',lat:-23.5505,lon:-46.6363,directions:[departure(0),departure(180)]},
    {id:'rail',name:'Estação de trem',mode:'rail',lat:-23.5505,lon:-46.6303,directions:[departure(90),departure(270)]},
  ];
  let viewport;
  await page.addInitScript(theme=>localStorage.setItem('pap.appearance',theme),theme);
  await context.route('https://tile.openstreetmap.org/**',r=>r.abort());
  await context.route('**/api/location-config/**',r=>r.fulfill({json:{position:null}}));
  await context.route('**/api/sptrans/stop-catalogue/**',r=>r.fulfill({status:503,body:''}));
  await context.route('**/api/sptrans/stops/**',r=>{
    viewport=Object.fromEntries([...new URL(r.request().url()).searchParams].map(([k,v])=>[k,Number(v)]));
    return r.fulfill({json:{stops}});
  });
  await page.goto('/');await page.getByRole('button',{name:'Continuar sem contribuir',exact:true}).click();
  const canvas=page.locator('.sp-stop-canvas');
  await expect(canvas).toHaveAttribute('data-points','7');
  const pixels=await canvas.evaluate((canvas,{stops,viewport})=>{
    const ctx=canvas.getContext('2d'),scale=canvas.width/canvas.clientWidth;
    const mercator=lat=>Math.log(Math.tan(Math.PI/4+lat*Math.PI/360));
    return stops.map(stop=>{
      const x=(stop.lon-viewport.west)/(viewport.east-viewport.west)*canvas.width;
      const y=(mercator(viewport.north)-mercator(stop.lat))/(mercator(viewport.north)-mercator(viewport.south))*canvas.height;
      const quadrants={north:0,east:0,south:0,west:0};
      // Only inspect pixels well beyond the bus sign, where the direction must be visible.
      for(let dx=-26;dx<=26;dx++)for(let dy=-26;dy<=26;dy++){
        const radius=Math.hypot(dx,dy);if(radius<18||radius>25)continue;
        const [r,g,b,a]=ctx.getImageData(Math.round(x+dx*scale),Math.round(y+dy*scale),1,1).data;
        if(a>200&&Math.max(r,g,b)-Math.min(r,g,b)>40){
          const direction=Math.abs(dx)>Math.abs(dy)?(dx>0?'east':'west'):(dy>0?'south':'north');
          quadrants[direction]++;
        }
      }
      return {id:stop.id,quadrants};
    });
  },{stops,viewport});
  await page.screenshot({path:`test-results/stop-directions-${theme}.png`});
  for(const {id,quadrants} of pixels){
    for(const [direction,count] of Object.entries(quadrants)){
      if(direction===id)expect(count,`${id}: seta visível`).toBeGreaterThan(10);
      else expect(count,`${id}: sem seta inventada para ${direction}`).toBe(0);
    }
  }
});
