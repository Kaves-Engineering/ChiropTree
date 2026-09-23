// Run after build.sh, with the repository served on port 8000.
const {chromium}=require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert=require('node:assert/strict');
(async()=>{
  const browser=await chromium.launch({headless:true});
  try{
    const context=await browser.newContext({viewport:{width:360,height:740},isMobile:true,hasTouch:true});
    const page=await context.newPage();
    await page.goto('http://127.0.0.1:8000/public/index.html');
    // Production registers automatically; local development deliberately opts out.
    await page.evaluate(async()=>{
      await navigator.serviceWorker.register('service-worker.js');
      await navigator.serviceWorker.ready;
    });
    await page.waitForFunction(()=>!!navigator.serviceWorker.controller);
    await context.setOffline(true);
    for(const file of ['index.html','birds.html','marine.html','dinosaurs.html']){
      await page.goto('http://127.0.0.1:8000/public/'+file);
      await page.waitForFunction(()=>typeof CM!=='undefined' && CM && luState.ready && treeLayoutFrame===null && !svg.hasAttribute('aria-busy'));
      assert(await page.locator('#tree [role=treeitem]').count()>0);
      await page.locator('#cm-map').scrollIntoViewIfNeeded();
      await page.waitForSelector('#cm-map-svg svg');
      await page.locator('#cm-zoom-in').tap();
      await page.waitForFunction(()=>cmView.scale>1);
      console.log(file,'offline load and map zoom PASS');
    }
  }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
