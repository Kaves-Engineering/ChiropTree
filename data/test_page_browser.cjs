// Serve the repository on port 8000. Use PLAYWRIGHT_MODULE for an external install.
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert = require('node:assert/strict');

(async()=>{
  const browser = await chromium.launch({headless:true});
  try {
    for(const mobile of [false,true]){
      for(const file of ['chiroptera-tree.html','bird-tree.html','marine-mammal-tree.html','dinosaur-tree.html']){
        const page = await browser.newPage({
          viewport:mobile ? {width:393,height:852} : {width:1440,height:1000},
          deviceScaleFactor:mobile ? 3 : 1, isMobile:mobile, hasTouch:mobile,
          serviceWorkers:'block'
        });
        const errors=[];
        page.on('pageerror',e=>errors.push(e.message));
        await page.addInitScript(()=>{
          window.svgTextMeasurements=0;
          const measure=SVGTextContentElement.prototype.getComputedTextLength;
          SVGTextContentElement.prototype.getComputedTextLength=function(){svgTextMeasurements++;return measure.call(this)};
        });
        await page.goto('http://127.0.0.1:8000/'+file);
        await page.waitForFunction(()=>typeof CM!=='undefined' && CM && luState.ready);
        await page.evaluate(()=>document.fonts.ready);
        await page.waitForFunction(()=>treeLayoutFrame===null && !svg.hasAttribute('aria-busy') && mainCtx.rowOrder.length>0);
        const initialRows=await page.evaluate(()=>mainCtx.rowOrder.length);
        assert(initialRows>0);
        if(mobile) assert.equal(await page.locator('#cm-map-svg svg').count(),0,'offscreen map is deferred');

        // The arrow keys must still expand a row and preserve its focus after a redraw.
        const row=page.locator('#tree [role="treeitem"]').first();
        const key=await row.getAttribute('data-key');
        await row.focus();await page.keyboard.press('ArrowRight');
        assert.equal(await page.evaluate(()=>document.activeElement.dataset.key),key);
        assert.equal(await row.getAttribute('aria-expanded'),'true');
        await page.keyboard.press('ArrowLeft');
        assert.equal(await row.getAttribute('aria-expanded'),'false');

        await page.locator('#t-toggle').click();
        await page.waitForFunction(()=>!svg.hasAttribute('aria-busy'));
        assert(await page.evaluate(()=>mainCtx.rowOrder.length)>initialRows);
        assert(await page.locator('#tree [role="treeitem"]').count()<=128,'only nearby tree rows are mounted');
        await page.locator('#t-toggle').click();
        assert.equal(await page.evaluate(()=>mainCtx.rowOrder.length),initialRows);

        await page.evaluate(()=>{
          // Cached search must return exactly the same records as the original fields.
          for(const q of ['a','myotis','whale','rex','æ','pter','nonexistent-zzz']){
            const expected=luState.species.filter(s=>{
              const dk=luState.danish[s.id];
              return [luNiceName(s.sciName),s.mainCommonName||'',s.otherCommonNames||'',s.genus,s.family,
                ...(dk ? dk.allNames : [])].some(value=>value.toLowerCase().includes(q));
            }).map(s=>s.id);
            luInput.value=q;luApplyFilter();
            if(JSON.stringify(expected)!==JSON.stringify(luState.filtered.map(s=>s.id)))throw Error('Search mismatch: '+q);
          }
          luInput.value='';luCloseResults();
          // Text measurement should agree with the rendered font, including letter spacing.
          const {measures}=treeTextMetrics(mainCtx,matchMedia('(max-width:620px)').matches);
          for(const cls of Object.keys(measures)){
            const sample=el('text',{class:cls},'Myotis testing species');svg.appendChild(sample);
            const canvasWidth=measures[cls](sample.textContent);
            const svgWidth=sample.getBBox().width;sample.remove();
            if(Math.abs(canvasWidth-svgWidth)>3)throw Error(cls+' text width mismatch: '+canvasWidth+' / '+svgWidth);
          }
        });
        const query=await page.evaluate(()=>luNiceName(luState.species[0].sciName));
        await page.locator('input[role="combobox"]').fill(query);
        await page.locator('input[role="combobox"]').press('ArrowDown');
        await page.locator('input[role="combobox"]').press('Enter');
        if(mobile){
          await page.waitForFunction(()=>luDrawer.classList.contains('open'));
          await page.locator('#lu-close').click();
        } else {
          assert(await page.locator('#card-body').innerText());
          await page.evaluate(()=>{window.treeRowBeforeClose=svg.querySelector('[role="treeitem"]')});
          await page.locator('#card-close').click();
          assert.equal(await page.evaluate(()=>treeRowBeforeClose===svg.querySelector('[role="treeitem"]') && !svg.querySelector('.active')),true);
        }
        await page.locator('#cm-map').scrollIntoViewIfNeeded();
        await page.waitForSelector('#cm-map-svg svg');
        if(mobile) await page.locator('#cm-zoom-in').tap(); else await page.locator('#cm-zoom-in').click();
        await page.waitForFunction(()=>cmView.scale>1);
        await page.waitForFunction(()=>cmViewFrame===null && cmMotionTimer===null && !document.getElementById('cm-zoom-g').classList.contains('cm-moving'));
        assert.equal(await page.evaluate(()=>cmHatchScale===cmView.scale),true,'hatch scale restored');
        assert.equal(await page.evaluate(()=>getComputedStyle(document.querySelector('.cm-c.has:not(.range):not(.sel)')).fill.includes('cm-hatch')),true);
        assert.equal(await page.evaluate(()=>svgTextMeasurements),0,'tree uses no synchronous SVG text measurements');
        assert.deepEqual(errors,[]);
        console.log(file,mobile?'mobile':'desktop','PASS');
        await page.close();
      }
    }
  } finally { await browser.close(); }
})().catch(error=>{console.error(error);process.exitCode=1});
