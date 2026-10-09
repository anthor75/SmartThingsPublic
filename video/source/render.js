const { chromium } = require('/opt/node22/lib/node_modules/playwright');
(async()=>{
  const b = await chromium.launch();
  const pg = await b.newPage({viewport:{width:1280,height:720},deviceScaleFactor:1.5});
  await pg.goto('file://'+__dirname+'/built.html');
  await pg.waitForTimeout(500);
  const only = process.argv[2] ? process.argv[2].split(',').map(Number) : null;
  const FPS=30, N=450;
  const list = only ? only.map(s=>Math.round(s*FPS)) : [...Array(N).keys()];
  for (const i of list) {
    await pg.evaluate(t=>render(t), i/FPS);
    await pg.screenshot({path:`frames/f${String(i).padStart(4,'0')}.png`});
  }
  await b.close();
})();
