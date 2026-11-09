// Run against the local HTTP server on port 8000. Requires Playwright and Chromium.
// Checks the call plot on the bat page (desktop and phone) and that the clone
// pages, which have no size data, never offer it.
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert = require('node:assert/strict');
const SHOTS = process.env.PLOT_SHOTS || '';

async function open(browser, file, viewport, scheme){
  const page = await browser.newPage({viewport, serviceWorkers:'block', colorScheme:scheme || 'dark', hasTouch:viewport.width < 621});
  const errors = [];
  page.on('pageerror', e=>errors.push(e.message));
  await page.goto('http://127.0.0.1:8000/'+file);
  await page.waitForFunction(()=>typeof luState!=='undefined' && luState.ready);
  return {page, errors};
}

(async()=>{
  const browser = await chromium.launch({headless:true});

  // ---- desktop ----
  {
    const {page, errors} = await open(browser, 'chiroptera-tree.html', {width:1440, height:1000});
    await page.waitForFunction(()=>plotState.points && plotState.points.length > 400);
    assert.ok(await page.isVisible('#view-switch'), 'view switch shown on the bat page');
    await page.click('#view-switch button[data-view="plot"]');
    assert.ok(await page.isVisible('#plotbox'), 'plot shown');
    assert.ok(!(await page.isVisible('#tree')), 'tree hidden behind the plot');
    const marks = await page.locator('#plot-svg .pl-pt, #plot-svg .pl-rng').count();
    const points = await page.evaluate(()=>plotState.points.length);
    assert.equal(marks, points, 'one mark per point');
    assert.ok(await page.evaluate(()=>plotState.points.every(p=>!luSizeOf(p.n).fa.est)), 'no estimated forearms');

    // a click opens the record in the card, with the plot strip
    const target = await page.evaluate(()=>{
      const g = plotState.geo.find(z=>z.p.n==='Pipistrellus pygmaeus');
      const r = plotSvg.getBoundingClientRect(), k = r.width / +plotSvg.getAttribute('width');
      return {x:r.left + g.x*k, y:r.top + g.y*k};
    });
    await page.mouse.move(target.x, target.y);
    assert.ok(await page.isVisible('#plot-tip'), 'tooltip on hover');
    await page.mouse.click(target.x, target.y);
    await page.waitForSelector('#card-body .plot-strip');
    assert.match(await page.textContent('#card-body .lu-d-sci'), /Pipistrellus pygmaeus/);
    assert.equal(await page.evaluate(()=>plotState.sel), 'Pipistrellus pygmaeus', 'ring on the picked mark');
    if(SHOTS) await page.screenshot({path:SHOTS+'/plot-desktop.png'});

    // "Show in tree" goes back with the species row selected
    await page.click('#card-body .plot-jump');
    await page.waitForFunction(()=>plotState.view==='tree' && document.querySelector('g.trow.species.active'));
    assert.ok(await page.isVisible('#tree'), 'tree back');
    assert.match(await page.textContent('#card-body .plot-jump'), /Show in call plot/);
    await page.click('#card-body .plot-jump');
    await page.waitForFunction(()=>plotState.view==='plot');

    // keyboard: arrows move a cursor, Enter opens the record
    await page.focus('#plot-svg');
    await page.keyboard.press('Home');
    await page.keyboard.press('ArrowRight');
    const cursor = await page.evaluate(()=>plotState.cursor);
    assert.ok(cursor, 'arrow keys move the cursor');
    await page.keyboard.press('Enter');
    await page.waitForFunction(name=>document.querySelector('#card-body .lu-d-sci') &&
      document.querySelector('#card-body .lu-d-sci').textContent.includes(name), cursor);

    // families: clear all leaves an explained empty plot, include all restores
    await page.click('#plot-fams summary');
    await page.click('#plot-fam-none');
    assert.equal(await page.locator('#plot-svg .pl-pt').count(), 0, 'nothing drawn with no families');
    assert.match(await page.textContent('#plot-svg .pl-note'), /No families included/);
    await page.click('#plot-fam-all');
    await page.click('label[for="plot-fam-Molossidae"]');
    assert.ok(await page.evaluate(()=>plotState.geo.every(g=>g.p.f!=='Molossidae')), 'a family can be left out');
    await page.click('#plot-fam-all');

    // the country filter applies to the plot
    await page.waitForFunction(()=>cmReady && CM);
    await page.evaluate(()=>cmSetCountry(Object.keys(CM).find(k=>CM[k].name==='Denmark')));
    await page.waitForFunction(()=>/Denmark/.test(document.getElementById('plot-status').textContent));
    const shown = await page.evaluate(()=>plotState.geo.length);
    const inDk = await page.evaluate(()=>plotState.geo.filter(g=>countrySpeciesSet.has(g.p.n)).length);
    assert.equal(shown, inDk, 'filter mode shows only the country');
    await page.click('#plot-mode-dim');
    assert.ok(await page.evaluate(()=>plotState.geo.some(g=>g.dim)), 'All mode dims the rest');
    await page.evaluate(()=>cmSetCountry(null));
    await page.evaluate(()=>{ try { localStorage.removeItem(PLOT_KEY); } catch (_) {} });

    // a search while the plot is up keeps the plot and rings the species
    await page.fill('#lu-search', 'Nyctalus noctula');
    await page.waitForSelector('.lu-row');
    await page.keyboard.press('ArrowDown');
    await page.keyboard.press('Enter');
    await page.waitForFunction(()=>plotState.sel==='Nyctalus noctula');
    assert.equal(await page.evaluate(()=>plotState.view), 'plot', 'search keeps the plot');
    assert.deepEqual(errors, [], 'no page errors on desktop');
    console.log('chiroptera-tree.html desktop plot PASS', {points, marks});
    await page.close();
  }

  // ---- phone, light theme ----
  {
    const {page, errors} = await open(browser, 'chiroptera-tree.html', {width:390, height:844}, 'light');
    await page.evaluate(()=>applyTheme('light'));
    await page.waitForFunction(()=>plotState.points);
    assert.ok(!(await page.isVisible('#view-switch')), 'phone uses the workspace buttons');
    await page.click('.mobile-workspace button[data-view="plot"]');
    await page.waitForFunction(()=>plotState.view==='plot');
    const sw = await page.evaluate(()=>document.documentElement.scrollWidth);
    assert.equal(sw, 390, 'no sideways scroll');
    if(SHOTS) await page.screenshot({path:SHOTS+'/plot-phone.png'});
    const target = await page.evaluate(()=>{
      const g = plotState.geo.find(z=>z.p.n==='Nyctalus noctula');
      const r = plotSvg.getBoundingClientRect(), k = r.width / +plotSvg.getAttribute('width');
      return {x:r.left + g.x*k, y:r.top + g.y*k};
    });
    await page.touchscreen.tap(target.x, target.y);
    await page.waitForSelector('#lu-drawer.open .plot-strip');
    if(SHOTS) await page.screenshot({path:SHOTS+'/plot-phone-record.png'});
    assert.deepEqual(errors, [], 'no page errors on phone');
    console.log('chiroptera-tree.html phone plot PASS');
    await page.close();
  }

  // ---- clone pages never offer the plot ----
  for(const file of ['marine-mammal-tree.html','bird-tree.html','dinosaur-tree.html']){
    const {page, errors} = await open(browser, file, {width:1280, height:900});
    assert.ok(!(await page.isVisible('#view-switch')), file+': no view switch');
    assert.equal(await page.evaluate(()=>PLOT_ON), false, file+': plot off');
    assert.deepEqual(errors, [], file+': no page errors');
    console.log(file, 'no plot PASS');
    await page.close();
  }
  await browser.close();
})().catch(e=>{ console.error(e); process.exit(1); });
