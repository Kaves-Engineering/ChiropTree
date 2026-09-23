// Performance and virtualization budgets at 8x CPU slowdown, 360x740, DPR 2.
// Serve this repository on port 8000; set PLAYWRIGHT_MODULE if installed elsewhere.
const {chromium}=require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert=require('node:assert/strict');

(async()=>{
  const browser=await chromium.launch({headless:true});
  try{
    for(const name of ['chiroptera-tree.html','bird-tree.html','marine-mammal-tree.html','dinosaur-tree.html']){
      const page=await browser.newPage({viewport:{width:360,height:740},deviceScaleFactor:2,isMobile:true,hasTouch:true,serviceWorkers:'block'});
      const errors=[],fonts=[];page.on('pageerror',e=>errors.push(e.message));
      page.on('request',r=>{if(r.resourceType()==='font')fonts.push(r.url())});
      const cdp=await page.context().newCDPSession(page);
      await cdp.send('Emulation.setCPUThrottlingRate',{rate:8});
      await page.addInitScript(()=>{
        window.longTasks=[];
        new PerformanceObserver(list=>longTasks.push(...list.getEntries().map(e=>({start:e.startTime,duration:e.duration})))).observe({type:'longtask'});
      });
      await page.goto('http://127.0.0.1:8000/'+name,{waitUntil:'domcontentloaded'});
      await page.waitForFunction(()=>typeof CM!=='undefined' && CM && treeLayoutFrame===null);
      await page.evaluate(()=>document.fonts.ready);
      await page.waitForFunction(()=>treeLayoutFrame===null && !svg.hasAttribute('aria-busy') && mainCtx.rowOrder.length>0);
      const result=await page.evaluate(async()=>{
        const frame=()=>new Promise(requestAnimationFrame);
        await frame();await frame();
        const collapsed=mainCtx.rowOrder.length;
        const start=performance.now();
        document.getElementById('t-toggle').click();
        const inputMs=performance.now()-start;
        let heartbeat=0;
        while(svg.hasAttribute('aria-busy')){await frame();heartbeat++}
        await frame();await frame();
        const totalMs=performance.now()-start;
        const worstTask=Math.max(0,...longTasks.filter(t=>t.start>=start).map(t=>t.duration));
        return {collapsed,logicalRows:mainCtx.rowOrder.length,mounted:svg.querySelectorAll('[role=treeitem]').length,
          nodes:document.querySelectorAll('*').length,inputMs:Math.round(inputMs),totalMs:Math.round(totalMs),worstTask:Math.round(worstTask),heartbeat};
      });
      assert(result.logicalRows>result.collapsed);
      assert(result.mounted<=128,'mounted row budget exceeded');
      assert(result.nodes<=2500,'page DOM budget exceeded');
      assert(result.inputMs<100,'expand button blocks input for 100 ms');
      assert(result.worstTask<200,'tree operation contains a task longer than 200 ms at 8x slowdown');
      if(result.logicalRows>500) assert(result.heartbeat>1,'large layout must yield to the browser');
      assert.deepEqual(fonts,[],'touch layout downloads no web fonts');

      // Scrolling alone (without keyboard materialization) must mount content.
      await page.evaluate(()=>scrollTo(0,scrollY+svg.getBoundingClientRect().top+svg.getBoundingClientRect().height/2));
      await page.waitForFunction(()=>[...svg.querySelectorAll('[role=treeitem]')].some(row=>{
        const rect=row.getBoundingClientRect();return rect.top>100 && rect.bottom<innerHeight;
      }));
      assert(await page.locator('#tree [role=treeitem]').count()<=128);

      // Keyboard navigation must reach rows that have never been mounted.
      const lastKey=await page.evaluate(()=>mainCtx.rowOrder.at(-1).key);
      await page.locator('#tree [tabindex="0"]').focus();
      await page.keyboard.press('End');
      assert.equal(await page.evaluate(()=>document.activeElement.dataset.key),lastKey);
      await page.waitForTimeout(100);
      assert(await page.locator('#tree [role=treeitem]').count()<=128);
      await page.keyboard.press('Home');
      assert.equal(await page.evaluate(()=>document.activeElement.dataset.key),await page.evaluate(()=>mainCtx.rowOrder[0].key));
      await page.waitForTimeout(100);
      assert.equal(await page.locator('#tree [tabindex="0"]').count(),1);

      // Cancel a pending expand-all with a newer collapse: stale work must not commit.
      await page.evaluate(()=>{
        document.getElementById('t-toggle').click();
        document.getElementById('t-toggle').click();
        document.getElementById('t-toggle').click();
      });
      await page.waitForFunction(()=>!svg.hasAttribute('aria-busy'));
      await page.waitForTimeout(100);
      assert.equal(await page.evaluate(()=>mainCtx.rowOrder.length),result.collapsed);
      assert.equal(await page.evaluate(()=>allFamiliesOpen()),false);

      // Search can open a species at the far end of the logical tree.
      await page.evaluate(()=>luSelectSpecies(luState.species.at(-1).id,true));
      assert.equal(await page.evaluate(()=>mainCtx.selectedSp),await page.evaluate(()=>luNiceName(luState.species.at(-1).sciName)));
      assert.equal(await page.locator('#tree .species.active').count(),1);
      await page.locator('#lu-close').click();
      await page.evaluate(()=>cmSetCountry(Object.keys(CM).find(key=>CM[key].confirmed.length)));
      await page.waitForFunction(()=>treeLayoutFrame===null && !svg.hasAttribute('aria-busy'));
      assert(await page.evaluate(()=>mainCtx.rowOrder.every(row=>row.key.startsWith('f:')
        ? countryLive.liveFamilies.has(row.key.slice(2)) : countryLive.live.has(row.key))),'virtual tree respects country pruning');
      assert.deepEqual(errors,[]);
      console.log(name,'PASS',result);
      await page.close();
    }
  }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
