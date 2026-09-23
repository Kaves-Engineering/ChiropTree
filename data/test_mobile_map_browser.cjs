// Mobile canvas functionality and idle-rendering regression checks.
// Serve the repository on port 8000; configure PLAYWRIGHT_MODULE if needed.
const {chromium}=require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true});
 try{
  for(const file of ['chiroptera-tree.html','bird-tree.html','marine-mammal-tree.html','dinosaur-tree.html']){
   const page=await browser.newPage({viewport:{width:393,height:852},deviceScaleFactor:3,isMobile:true,hasTouch:true,serviceWorkers:'block'});
   const errors=[];page.on('pageerror',e=>errors.push(e.message));
   const cdp=await page.context().newCDPSession(page);
   await cdp.send('Emulation.setCPUThrottlingRate',{rate:8});
   await page.goto('http://127.0.0.1:8000/'+file);
   await page.waitForFunction(()=>typeof cmMapGeometry!=='undefined' && cmMapGeometry && treeLayoutFrame===null && !svg.hasAttribute('aria-busy'));
   await page.locator('#cm-map').scrollIntoViewIfNeeded();
   await page.waitForSelector('#cm-map-svg canvas');
   const settled=()=>page.waitForFunction(()=>cmCanvasFrame===null && cmViewFrame===null && treeLayoutFrame===null && !svg.hasAttribute('aria-busy'));
   await settled();
   assert.equal(await page.locator('#cm-map-svg svg').count(),0);
   assert(await page.evaluate(()=>cmMapGeometry.width<=cmMapGeometry.clientWidth*2+1),'bitmap density is capped at 2');
   assert(await page.evaluate(()=>cmCanvasPaths.length===WMBASE.length),'all country outlines retained');
   // Find an interior point using the map data, then select with a real tap.
   const target=await page.evaluate(()=>{
    const box=cmMapGeometry.getBoundingClientRect();
    for(const {key,has} of cmCanvasPaths){
     const center=WMAP.cent[key];if(!has || !center) continue;
     const x=box.x+center[0]/WMAP.w*box.width,y=box.y+center[1]/WMAP.h*box.height;
     if(y<100 || y>innerHeight-20) continue;
     if(cmCanvasCountryAt(x,y)===key) return {key,x,y};
    }
   });
   assert(target,'a country interior is clickable');
   await page.touchscreen.tap(target.x,target.y);
   await settled();
   assert.equal(await page.evaluate(()=>cmSelected),target.key);
   assert(await page.evaluate(()=>countrySpeciesSet.size>0 && cmView.scale>1),'tap filters tree and zooms map');
   assert(await page.evaluate(()=>document.querySelector('#cm-country-icon path').getAttribute('d')===WMAP.shapes[cmSelected]),'country silhouette retained');
   await page.evaluate(()=>{cmSetCountry(null);cmShowSpeciesRange(null)});await settled();
   await page.locator('#cm-map').scrollIntoViewIfNeeded();
   const beforeRange=await page.evaluate(()=>cmMapGeometry.toDataURL());
   await page.evaluate(()=>cmShowSpeciesRange(luNiceName(luState.species.find(s=>s.countryDistribution && wmResolve(s.countryDistribution).shapes && Object.keys(wmResolve(s.countryDistribution).shapes).length).sciName)));
   await settled();
   assert.notEqual(await page.evaluate(()=>cmMapGeometry.toDataURL()),beforeRange,'species ranges change painted pixels');
   const beforeTheme=await page.evaluate(()=>cmMapGeometry.toDataURL());
   await page.locator('#theme-toggle').click();await settled();
   assert.notEqual(await page.evaluate(()=>cmMapGeometry.toDataURL()),beforeTheme,'theme change repaints map');
   const island=await page.evaluate(()=>Object.keys(WMAP.dots).find(k=>CM[k]?.confirmed.length));
   if(island){await page.selectOption('#cm-country',island);await settled();assert.equal(await page.evaluate(()=>cmSelected),island);}
   await page.locator('#cm-zoom-reset').tap();await settled();
   await page.locator('#cm-zoom-in').tap();await settled();
   assert(await page.evaluate(()=>cmView.scale>1));
   const box=await page.locator('#cm-map-svg canvas').boundingBox();
   const x=box.x+box.width*.4,y=box.y+box.height*.5;
   const panBefore=await page.evaluate(()=>cmView.x);
   await cdp.send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[{x,y}]});
   for(let i=1;i<=10;i++)await cdp.send('Input.dispatchTouchEvent',{type:'touchMove',touchPoints:[{x:x+i*5,y}]});
   await cdp.send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});await settled();
   assert.notEqual(await page.evaluate(()=>cmView.x),panBefore,'horizontal touch drag pans');
   await page.locator('#cm-zoom-reset').tap();await settled();
   await page.evaluate(()=>{
    window.mapPaints=0;
    const draw=cmDrawCanvas;cmDrawCanvas=()=>{mapPaints++;draw()};
   });
   // Revisit the tree AFTER loading the map, then revisit the map. Neither
   // ordinary scrolling nor an idle page should issue a new canvas draw.
   for(const y of [0,300,0,500]){await page.evaluate(y=>scrollTo(0,y),y);await page.waitForTimeout(100);}
   await page.locator('#cm-map').scrollIntoViewIfNeeded();await page.waitForTimeout(250);
   assert.equal(await page.evaluate(()=>mapPaints),0,'scrolling and idle time do not redraw the map');
   await page.setViewportSize({width:430,height:852});await page.waitForTimeout(150);await settled();
   assert(await page.evaluate(()=>mapPaints>0 && cmMapGeometry.width===Math.round(cmMapGeometry.clientWidth*2)),'width changes resize bitmap');
   assert.deepEqual(errors,[]);
   console.log(file,'mobile canvas PASS');await page.close();
  }
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
