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

    // every family's marker is unique within its colour
    assert.ok(await page.evaluate(()=>{
      const seen = new Set();
      return plotState.fams.every(f=>{ const k = plotGroupOf(f)+(PLOT_MARK[f]||[]).join(); const ok = !seen.has(k) && PLOT_MARK[f]; seen.add(k); return ok; });
    }), 'marker shape and style unique within each colour');
    // families of ten or more species keep a marker no other family uses, so they stay apart without colour
    assert.ok(await page.evaluate(()=>{
      const big = plotState.fams.filter(f=>plotState.famCounts[f] >= 10);
      return big.every(f=>Object.keys(PLOT_MARK).every(o=>o===f || PLOT_MARK[o].join()!==PLOT_MARK[f].join()));
    }), 'large families have globally unique markers');
    // the key names every plotted family with its marker
    assert.equal(await page.locator('#plot-key .plot-key-fam').count(), await page.evaluate(()=>plotState.fams.length), 'key lists every family');

    // the line under the title says what is selected
    assert.equal(await page.textContent('#plot-sel'), 'All families, tribes, genera and diets', 'selection line, nothing narrowed');
    await page.click('#plot-fam-none');
    await page.click('label[for="plot-fam-Molossidae"]');
    assert.equal(await page.textContent('#plot-sel'), 'FamilyMolossidae', 'selection line names the one family');
    await page.click('#pf-body-diet label[data-v="ins"]');
    assert.match(await page.textContent('#plot-sel'), /FamilyMolossidae·Diets?/, 'diet joins the line once narrowed');
    await page.click('#plot-reset');
    await page.click('label[for="plot-fam-Molossidae"]');
    assert.match(await page.textContent('#plot-sel'), /^Familiesall except Molossidae$/, 'one family out reads as all except');
    await page.click('#plot-reset');
    await page.click('#pf-body-tribe label[data-v="Vespertilionidae|Pipistrellini"]');
    assert.match(await page.textContent('#plot-sel'), /^Tribesall except Pipistrellini$/, 'a tribe out is named');
    for(const v of ['Vespertilionidae|Lasiurini','Vespertilionidae|Plecotini','Phyllostomidae|Vampyrini'])
      await page.click('#pf-body-tribe label[data-v="'+v+'"]');
    assert.match(await page.textContent('#plot-sel'), /^Tribes20 of 24$/, 'many out collapses to a count');
    assert.match(await page.evaluate(()=>[...document.getElementById('plot-svg').getAttribute('aria-labelledby').split(' ')].map(id=>document.getElementById(id).textContent).join(' ')),
      /^Tribes20 of 24 Each mark/, 'the plot is named by its selection');
    if(SHOTS){ await page.click('#plot-reset'); await page.click('#plot-fam-none'); await page.click('label[for="plot-fam-Molossidae"]');
      await page.click('#pf-body-genus label[data-v="Mops"]'); await page.click('#pf-body-diet label[data-v="ins"]');
      await page.locator('#plotbox .plot-head').screenshot({path:SHOTS+'/plot-selection.png'}); }
    await page.click('#plot-reset');

    // one panel, no tabs: every row is on show at once
    for(const dim of ['fam','tribe','genus','diet'])
      assert.ok(await page.isVisible('.plot-dim[data-dim="'+dim+'"]'), dim+' row shown');
    // with every family ticked the genus list is folded behind a count
    assert.ok(await page.isVisible('#pf-genus-show'), 'a long genus list starts folded');

    // the cascade: only Molossidae ticked lists no tribes and only molossid genera
    await page.click('#plot-fam-none');
    await page.click('label[for="plot-fam-Molossidae"]');
    assert.match(await page.textContent('#pf-body-tribe'), /None of the ticked families is divided into tribes/);
    assert.ok(await page.evaluate(()=>{
      const shown = [...document.querySelectorAll('#pf-body-genus .plot-fam')].map(l=>l.dataset.v);
      const molossid = new Set(plotState.points.filter(p=>p.f==='Molossidae').map(p=>p.gn));
      return shown.length===molossid.size && shown.every(g=>molossid.has(g));
    }), 'genus row lists exactly the molossid genera');
    assert.ok(await page.evaluate(()=>plotState.geo.length > 0 && plotState.geo.every(g=>g.p.f==='Molossidae')), 'only molossids drawn');
    // a genus of that family can be left out, and focus stays on its box through the rebuild
    const gid = await page.evaluate(()=>document.querySelector('#pf-body-genus input').id);
    await page.focus('#'+gid);
    await page.keyboard.press('Space');
    assert.equal(await page.evaluate(()=>document.activeElement.id), gid, 'focus kept on the chip after the rows rebuild');
    await page.click('#plot-fam-all');
    await page.click('#plot-reset');

    // tribes narrow the genus row: Pipistrellini out removes its genera from the list
    await page.click('#plot-fam-none');
    await page.click('label[for="plot-fam-Vespertilionidae"]');
    await page.click('#pf-body-tribe label[data-v="Vespertilionidae|Pipistrellini"]');
    assert.ok(await page.evaluate(()=>plotState.geo.every(g=>g.p.t!=='Pipistrellini') && plotState.geo.some(g=>g.p.f==='Vespertilionidae')),
      'a tribe can be left out');
    assert.ok(await page.evaluate(()=>![...document.querySelectorAll('#pf-body-genus .plot-fam')].some(l=>l.dataset.v==='Pipistrellus')),
      'genera of a left-out tribe are not listed');
    assert.match(await page.textContent('#plot-fam-count'), /tribes narrowed/);
    await page.click('#plot-reset');

    // genus search: works while folded; None then acts on the matches alone
    await page.fill('#plot-find', 'Myotis');
    await page.click('#pf-genus-none');
    assert.ok(await page.evaluate(()=>plotState.geo.length > 100 && plotState.geo.every(g=>g.p.gn!=='Myotis')), 'None hits only the found genus');
    await page.fill('#plot-find', '');
    await page.click('#plot-reset');

    // diet: one guild alone, coloured by diet; the counts follow the other rows
    await page.click('#pf-diet-none');
    await page.click('#pf-body-diet label[data-v="fru"]');
    assert.ok(await page.evaluate(()=>plotState.geo.length > 0 && plotState.geo.every(g=>g.p.dts.includes('fru'))), 'diet filter keeps only fruit-eaters');
    assert.ok(await page.evaluate(()=>plotState.geo.some(g=>g.p.dts.length > 1)), 'species that also eat other foods stay in');
    assert.equal(await page.textContent('label[for="plot-fam-Vespertilionidae"] .plot-cnt'), '0', 'family counts follow the diet row');
    // marked by family, the diet row offers to show diet on the plot
    assert.ok(await page.isVisible('#pf-diet-mark'), 'diet row offers diet marking');
    await page.click('#pf-diet-mark');
    assert.equal(await page.evaluate(()=>plotState.colour), 'diet', 'the link switches the marking');
    assert.ok(!(await page.isVisible('#pf-diet-mark')), 'and then hides');
    assert.ok(await page.evaluate(()=>plotState.geo.every(g=>{ const c = 'pg'+PLOT_DIET.fru.slot; return g.el.classList.contains(c) || !!g.el.querySelector('.'+c); })), 'fruit-eaters drawn with the fruit marker');
    assert.ok(await page.evaluate(()=>plotState.geo.filter(g=>g.p.dts.length > 1).every(g=>g.el.tagName==='g' && g.el.querySelectorAll('path').length===g.p.dts.length)),
      'a species eating several foods gets one overlapping marker per food');
    // marked by diet, every diet has its own shape: one path per diet, never shared
    await page.click('#pf-diet-all');
    assert.ok(await page.evaluate(()=>{
      const byDiet = new Map();
      plotState.geo.filter(g=>g.top==null).forEach(g=>{
        const shape = JSON.stringify(PLOT_DIET[g.p.dt].mark);
        if(!byDiet.has(g.p.dt)) byDiet.set(g.p.dt, shape);
      });
      const shapes = [...byDiet.values()];
      return byDiet.size >= 5 && new Set(shapes).size === shapes.length;
    }), 'each diet drawn with its own marker');
    assert.equal(await page.locator('#plot-key li').count(), await page.evaluate(()=>new Set(plotState.points.flatMap(p=>p.dts)).size + 1), 'key lists every food, and the overlap');
    assert.equal(await page.locator('#pf-body-fam .plot-fam svg').count(), 0, 'family shapes hidden while marked by diet');
    await page.click('#pf-diet-none');
    await page.click('#pf-body-diet label[data-v="fru"]');
    if(SHOTS) await page.locator('#plotbox').screenshot({path:SHOTS+'/plot-filters.png'});
    await page.click('#plot-reset');
    assert.equal(await page.evaluate(()=>plotState.geo.length), await page.evaluate(()=>plotState.points.length), 'reset brings every species back');

    // pointing at a chip picks its species out
    await page.hover('label[for="plot-fam-Rhinolophidae"]');
    assert.ok(await page.evaluate(()=>plotSvg.classList.contains('emph') &&
      plotState.geo.every(g=>g.el.classList.contains('pl-hi')===(g.p.f==='Rhinolophidae'))), 'chip hover highlights its family');
    await page.mouse.move(5, 5);
    assert.ok(!(await page.evaluate(()=>plotSvg.classList.contains('emph'))), 'highlight clears');
    await page.click('#plot-colour-group');
    await page.click('#plot-fams summary');

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
