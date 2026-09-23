// Run against the local HTTP server on port 8000. Requires Playwright and Chromium.
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert = require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true});
 for(const file of ['chiroptera-tree.html','marine-mammal-tree.html','bird-tree.html','dinosaur-tree.html']){
  const page=await browser.newPage({viewport:{width:1440,height:1000},serviceWorkers:'block'});
  const errors=[]; page.on('pageerror',e=>errors.push(e.message));
  await page.goto('http://127.0.0.1:8000/'+file);
  await page.waitForFunction(()=>typeof CM!=='undefined' && CM && cmReady);
  await page.waitForSelector('#cm-map-svg svg');
  const result=await page.evaluate(async()=>{
   const check=(v,msg)=>{if(!v) throw Error(msg)};
   const svg=document.querySelector('#cm-map-svg svg');
   const shape=svg.querySelector('.cm-c');
   const frame=()=>new Promise(requestAnimationFrame);
   const key=Object.keys(CM).find(k=>!k.startsWith('d:') && CM[k].confirmed.length);
   document.getElementById('cm-country').value=key;
   document.getElementById('cm-country').dispatchEvent(new Event('change'));
   await frame(); await frame();
   check(cmSelected===key && countrySpeciesSet.size>0,'country filter');
   check(svg.querySelector('.cm-c.sel').dataset.key===key,'selected country');
   check(cmView.scale>=3,'country zoom');
   const oldView=JSON.stringify(cmView);
   const species=CM[key].confirmed[0];
   cmShowSpeciesRange(luNiceName(species.sciName));
   check(JSON.stringify(cmView)===oldView,'range preserves view');
   check(svg===document.querySelector('#cm-map-svg svg') && shape===svg.querySelector('.cm-c'),'geometry preserved');
   for(const el of svg.querySelectorAll('[data-key]')){
    const bag=el.dataset.key.startsWith('d:') ? speciesRange.dots : speciesRange.shapes;
    check(el.classList.contains('range')===(el.dataset.key in bag),'range coverage');
   }
   const small=WMAP.small.find(k=>CM[k]);
   if(small){cmSetCountry(small);check(svg.querySelector('.cm-ring').getAttribute('display')==='','island ring');}
   const dot=Object.keys(WMAP.dots).find(k=>CM[k]);
   if(dot){cmSetCountry(dot);check(svg.querySelector('.cm-d.sel').dataset.key===dot,'island selection');}
   cmShowSpeciesRange(null); cmSetCountry(null);
   check(!svg.querySelector('.range') && !svg.querySelector('.sel'),'clear highlights');
   check(countrySpeciesSet===null,'clear tree filter');
   await frame(); await frame();
   let transforms=0, hatchWrites=0;
   const observer=new MutationObserver(records=>{
    transforms+=records.filter(r=>r.attributeName==='transform').length;
    hatchWrites+=records.filter(r=>r.attributeName==='patternTransform').length;
   });
   observer.observe(svg,{attributes:true,subtree:true});
   for(let i=1;i<=100;i++) cmSetView({scale:1,x:i,y:i},false);
   await frame(); await frame();
   check(transforms===1,'pan updates batched into one frame');
   check(hatchWrites===0,'panning does not rebuild hatch');
   check(cmView.x===100 && cmView.y===100,'latest pan applied');
   transforms=0;
   cmSetView({scale:1,x:100,y:100},false);
   await frame(); await frame();
   check(transforms===0 && cmViewFrame===null,'unchanged view stays idle');
   observer.disconnect();
   cmResetView(false); await frame();
   return {key,small,dot};
  });
  await page.locator('#cm-zoom-in').click();
  await page.waitForFunction(()=>cmView.scale>1);
  const svg=page.locator('#cm-map-svg svg'); const box=await svg.boundingBox();
  const x=box.x+box.width/2,y=box.y+box.height/2;
  await page.mouse.move(x,y); await page.mouse.down();
  await page.mouse.move(x+60,y+25,{steps:12}); await page.mouse.up();
  assert.equal(await page.evaluate(()=>cmDrag===null && cmSelected===null),true);
  await page.locator('#cm-zoom-reset').click();
  await page.waitForFunction(()=>cmView.scale===1 && cmView.x===0);
  await page.mouse.move(x,y); await page.keyboard.down('Control'); await page.mouse.wheel(0,-100); await page.keyboard.up('Control');
  await page.waitForFunction(()=>cmView.scale>1);
  await page.setViewportSize({width:390,height:844});
  await page.locator('[data-workspace-target="country-map"]').click();
  await page.selectOption('#cm-country', result.key);
  assert.equal(await page.evaluate(()=>cmSelected),result.key);
  assert.deepEqual(errors,[]);
  console.log(file, 'PASS',result); await page.close();
 }
 await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
