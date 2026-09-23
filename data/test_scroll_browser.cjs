// Native touch-scroll regression checks. Serve the repository on port 8000.
const {chromium}=require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert=require('node:assert/strict');

async function swipe(page,cdp,direction,startY,stepSize=25){
  const start=startY ?? (direction==='down' ? 650 : 180);
  const step=direction==='down' ? -stepSize : stepSize;
  await cdp.send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[{x:190,y:start}]});
  for(let i=1;i<=18;i++){
    await cdp.send('Input.dispatchTouchEvent',{type:'touchMove',touchPoints:[{x:190,y:start+step*i}]});
    await page.waitForTimeout(17);
  }
  await cdp.send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});
  await page.waitForTimeout(100);
}

(async()=>{
  const browser=await chromium.launch({headless:true});
  try{
    for(const file of ['chiroptera-tree.html','bird-tree.html','marine-mammal-tree.html','dinosaur-tree.html']){
      const page=await browser.newPage({viewport:{width:393,height:852},deviceScaleFactor:3,isMobile:true,hasTouch:true,serviceWorkers:'block'});
      const errors=[];page.on('pageerror',e=>errors.push(e.message));
      const cdp=await page.context().newCDPSession(page);
      await cdp.send('Emulation.setCPUThrottlingRate',{rate:8});
      await page.goto('http://127.0.0.1:8000/'+file);
      await page.waitForFunction(()=>typeof CM!=='undefined' && CM);
      await page.evaluate(()=>document.fonts.ready);
      await page.waitForFunction(()=>treeLayoutFrame===null && topbarFrame===null && !svg.hasAttribute('aria-busy') && mainCtx.rowOrder.length>0);
      // Geometry must be prepared before scrolling reaches the map; attaching
      // it must not synchronously parse hundreds of country paths mid-gesture.
      await page.evaluate(()=>cmPrepareMap());
      assert.equal(await page.evaluate(()=>cmMapGeometry.isConnected),false);
      await page.evaluate(()=>{
        window.headerWrites=0;
        new MutationObserver(r=>headerWrites+=r.length).observe(document.documentElement,{attributes:true,attributeFilter:['style']});
      });
      assert.equal(await page.evaluate(()=>getComputedStyle(document.body,'::before').content),'none');
      assert.equal(await page.evaluate(()=>getComputedStyle(document.body,'::after').content),'none');
      assert.equal(await page.evaluate(()=>getComputedStyle(document.querySelector('.treebox')).overflowY),'visible');
      if(file==='chiroptera-tree.html'){
        // Repeated settled swipes over the collapsed family list, never close
        // enough to mount the map. This is distinct from startup/expand tests.
        await page.evaluate(()=>{
          window.steadyTreeWrites=0;
          window.steadyTreeObserver=new MutationObserver(records=>steadyTreeWrites+=records.length);
          steadyTreeObserver.observe(svg,{subtree:true,childList:true,attributes:true});
        });
        const renderVersion=await page.evaluate(()=>mainCtx.renderVersion);
        for(let i=0;i<3;i++){
          await swipe(page,cdp,'down',650,10);
          await swipe(page,cdp,'up',300,10);
        }
        assert.equal(await page.evaluate(()=>mainCtx.renderVersion),renderVersion,'steady scrolling never rebuilds the collapsed tree');
        assert.equal(await page.evaluate(()=>steadyTreeWrites),0,'steady scrolling does not mutate tree elements');
        assert.equal(await page.locator('#cm-map-svg :is(svg,canvas)').count(),0,'steady swipe case stays above the map');
        await page.evaluate(()=>{steadyTreeObserver.disconnect();scrollTo(0,0)});
      }
      const before=await page.evaluate(()=>({page:document.documentElement.scrollHeight,map:document.getElementById('cm-map-svg').getBoundingClientRect().height}));
      // Verify real touch events scroll the document, not a nested tree container.
      await swipe(page,cdp,'down');await swipe(page,cdp,'down');
      assert(await page.evaluate(()=>scrollY)>500,'touch swipe scrolls down');
      assert.equal(await page.evaluate(()=>document.querySelector('.treebox').scrollTop),0);
      assert(Math.abs(await page.evaluate(()=>topbar.getBoundingClientRect().top))<1,'header stays sticky');
      assert.equal(await page.evaluate(()=>headerWrites),0,'scroll does not rewrite root styles');
      const downY=await page.evaluate(()=>scrollY);
      await swipe(page,cdp,'up');
      assert(await page.evaluate(()=>scrollY)<downY,'reverse swipe scrolls up');

      // Draw the lazy map without changing its reserved height or the page length.
      await page.evaluate(()=>{if(!cmMapVisible){cmMapVisible=true;cmRenderMap()}});
      const after=await page.evaluate(()=>({page:document.documentElement.scrollHeight,map:document.getElementById('cm-map-svg').getBoundingClientRect().height}));
      assert(await page.evaluate(()=>document.querySelector('#cm-map-svg :is(svg,canvas)')===cmMapGeometry));
      assert(Math.abs(after.page-before.page)<=2,'lazy map keeps page length');
      assert(Math.abs(after.map-before.map)<=2,'map space reserved');
      // A vertical swipe starting on the map scrolls the page without first
      // moving its view or suppressing the next country-selection click.
      await page.locator('#cm-map').scrollIntoViewIfNeeded();
      const viewBefore=await page.evaluate(()=>JSON.stringify(cmView));
      const mapBox=await page.locator('#cm-map-svg :is(svg,canvas)').boundingBox();
      const startY=Math.min(550,mapBox.y+mapBox.height/2);
      const scrollBefore=await page.evaluate(()=>scrollY);
      await swipe(page,cdp,'up',startY,12);
      assert(await page.evaluate(()=>scrollY)<scrollBefore,'map swipe scrolls document');
      assert.equal(await page.evaluate(()=>JSON.stringify(cmView)),viewBefore,'vertical swipe leaves map view unchanged');
      assert.equal(await page.evaluate(()=>cmSuppressNextClick),false,'vertical swipe does not swallow the next tap');
      // Opening a drawer after scrolling must measure the current header offset.
      await page.evaluate(()=>ctxShowSpecies(mainCtx,luNiceName(luState.species[0].sciName),true));
      await page.waitForFunction(()=>luDrawer.classList.contains('open'));
      assert(await page.evaluate(()=>Math.abs(luDrawer.getBoundingClientRect().top-topbar.getBoundingClientRect().bottom)<=1),'drawer clears header');
      await page.locator('#lu-close').click();
      assert.equal(await page.evaluate(()=>document.body.classList.contains('drawer-open')),false);
      assert.deepEqual(errors,[]);
      console.log(file,'native touch scroll PASS');
      await page.close();
    }
  }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
