const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const FPS=24;
(async()=>{
  const [,, port, from, to, outdir, list] = process.argv;
  const b = await chromium.launch({args:['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist']});
  const pg = await b.newPage({viewport:{width:1920,height:1080}});
  pg.on('console',m=>{if(m.type()==='error')console.log('ERR',m.text())});
  pg.on('pageerror',e=>console.log('PAGEERR',e.message));
  await pg.goto(`http://127.0.0.1:${port}/index.html`);
  await pg.waitForFunction(()=>window.READY===true,{timeout:120000});
  const frames = list ? list.split(',').map(s=>Math.round(parseFloat(s)*FPS)) : Array.from({length:+to-+from},(_,i)=>+from+i);
  for (const i of frames) {
    const t0=Date.now();
    await pg.evaluate(t=>render(t), i/FPS);
    await pg.screenshot({path:`${outdir}/f${String(i).padStart(4,'0')}.png`});
    if(list) console.log(i, Date.now()-t0,'ms');
  }
  await b.close();
})();
