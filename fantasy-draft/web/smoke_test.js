// Smoke test for fantasy-draft/web/dist/draft-room.html (HANDOFF §4b).
// usage: node fantasy-draft/web/smoke_test.js fantasy-draft/web/dist/draft-room.html <scratch dir>
// Expectations ($185 budget, Giannis overpays, Porter Jr. undervalued) match the 2026-10-09 board;
// if keepers or budgets change, a FAIL on those lines may be the data moving, not a bug.
const fs = require('fs'), path = require('path');
const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const [dist, dir] = process.argv.slice(2);
const wrapped = path.join(dir, 'wrapped.html');
fs.writeFileSync(wrapped, '<!doctype html><html><head><meta charset=utf8><meta name=viewport content="width=device-width,initial-scale=1"></head><body>'
  + fs.readFileSync(dist, 'utf8') + '</body></html>');
const url = 'file://' + wrapped;
let fails = 0;
const ok = (cond, msg) => { console.log((cond ? 'PASS ' : 'FAIL ') + msg); if (!cond) fails++; };

(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 1400, height: 900 } });
  const page = await ctx.newPage();
  const errors = [];
  page.on('console', (m) => { if (m.type() === 'error' || m.type() === 'warning') errors.push(m.type() + ': ' + m.text()); });
  page.on('pageerror', (e) => errors.push('pageerror: ' + e.message));
  await page.goto(url);
  await page.waitForTimeout(500);
  const text = (sel) => page.$eval(sel, (e) => e.innerText);
  const run = async (line) => {
    const t0 = Date.now();
    await page.fill('#cmd', line); await page.press('#cmd', 'Enter');
    await page.waitForTimeout(150);
    return { result: await text('#result').catch(() => ''), wall: Date.now() - t0 };
  };
  const overflow = async (w) => { await page.setViewportSize({ width: w, height: 900 }); await page.waitForTimeout(150);
    return page.evaluate(() => document.documentElement.scrollWidth - innerWidth); };

  ok((await text('#sync')).includes('This browser only'), 'no window.claude -> pill says "This browser only": ' + await text('#sync'));
  const nom0 = await text('#nom');
  ok(nom0.toLowerCase().includes('nominate early: room overpays'), 'nominate-early list present');
  ok(nom0.toLowerCase().includes('nominate late: room undervalues'), 'nominate-late list present');
  console.log('  #nom:\n' + nom0.split('\n').map((l) => '    ' + l).join('\n'));
  const me0 = await text('#me');
  ok(me0.includes('Spend plan') && me0.includes('Tyrese Maxey'), 'pre-draft spend plan present and includes Maxey');
  const total0 = (me0.match(/Total\s+\$(\d+) of \$(\d+)/) || []);
  ok(total0[2] === '185', 'plan total line reads of $185: ' + total0[0]);
  console.log('  plan:\n' + me0.split('\n').slice(0, 16).map((l) => '    ' + l).join('\n'));
  const head = await page.$$eval('#p-board thead th', (ths) => ths.map((t) => t.innerText));
  ok(head.map((h) => h.toLowerCase()).includes('room'), 'board has Room column: ' + head.join('|'));
  const row0 = await page.$$eval('#board tr', (trs) => trs.slice(0, 3).map((t) => t.innerText.replace(/\s+/g, ' ')));
  console.log('  board top 3: ' + row0.join(' / '));

  let r = await run('giannis?');
  let nm = await text('#p-nominee');
  ok(/room\s*\$\d+/i.test(nm), 'price card shows a Room box');
  ok(nm.includes('ROOM OVERPAYS'), 'Giannis -> ROOM OVERPAYS line');
  console.log('  giannis card: ' + nm.replace(/\s+/g, ' ').slice(0, 400));
  for (const w of [400, 720, 1400]) ok((await overflow(w)) <= 0, `no horizontal overflow at ${w}px with price card open (${await overflow(w)})`);

  r = await run('kevin porter?');
  nm = await text('#p-nominee');
  ok(nm.includes('ROOM UNDERVALUES'), 'Kevin Porter Jr. -> ROOM UNDERVALUES line: ' + nm.replace(/\s+/g, ' ').slice(0, 200));

  r = await run('maxey 76 me');
  console.log('  maxey 76 me -> result: ' + r.result.replace(/\s+/g, ' ').slice(0, 300) + `  [${r.wall} ms incl. 150ms wait]`);
  const me1 = await text('#me');
  const planPart = me1.slice(me1.indexOf('Spend plan'));
  ok(me1.includes('Tyrese Maxey') && /Tyrese Maxey\s+\S*\s*\$76/.test(me1.split('Spend plan')[0]), 'Maxey on my roster at $76');
  ok(!planPart.split('Total')[0].includes('Tyrese Maxey'), 'plan no longer lists Maxey');
  const total1 = (me1.match(/Total\s+\$(\d+) of \$(\d+)/) || []);
  ok(total1[2] === '109', 'plan total now of $109 (185-76): ' + total1[0]);
  ok((await text('#s-me')).includes('$109 / 9'), 'header shows $109 / 9: ' + await text('#s-me'));
  console.log('  plan after maxey:\n' + planPart.split('\n').slice(0, 14).map((l) => '    ' + l).join('\n'));

  // render cost: time a full command round-trip inside the page
  const ms = await page.evaluate(async () => {
    const inp = document.getElementById('cmd'), f = document.getElementById('cmdform');
    const t = performance.now();
    for (let i = 0; i < 5; i++) { inp.value = 'giannis?'; f.requestSubmit(); }
    return (performance.now() - t) / 5;
  });
  console.log(`  avg in-page time per command (incl. full re-render + spend plan): ${ms.toFixed(1)} ms`);
  ok(ms < 500, 'command + render under 500ms');

  // reload: state persists via localStorage
  await page.reload(); await page.waitForTimeout(400);
  ok((await text('#s-me')).includes('$109 / 9'), 'state survives reload (localStorage)');

  r = await run('undo');
  ok((await text('#s-me')).includes('$185 / 10'), 'undo restores $185 / 10');
  const me2 = await text('#me');
  ok(me2.includes('Spend plan') && /Total\s+\$\d+ of \$185/.test(me2), 'plan back to $185 after undo');

  // no-plan fallback: fill my roster with non-guards until 2 open and 0 guards
  const nonG = await page.evaluate(() => window.DRAFT_DATA.players.filter((p) => !p.kept_by && !p.pos.some((x) => x === 'PG' || x === 'SG'))
    .sort((a, b) => a.fair - b.fair).slice(0, 8).map((p) => p.name));
  for (const n of nonG) await run(`${n} 1 me`);
  const me3 = await text('#me');
  console.log('  after 8 non-guard $1 buys: ' + await text('#s-me') + ' -> ' + me3.split('Needs')[0].split('\n').slice(-3).join(' | '));
  ok(me3.includes('No spend plan fits'), 'no-plan fallback message shows when guards cannot be covered');
  for (const w of [400, 720, 1400]) ok((await overflow(w)) <= 0, `no horizontal overflow at ${w}px late state (${await overflow(w)})`);

  // reset back to clean (two-click confirm)
  await page.click('#reset'); await page.waitForTimeout(100); await page.click('#reset'); await page.waitForTimeout(200);
  const tools = await text('#tools').catch(() => '');
  console.log('  after reset clicks: ' + await text('#s-me') + ' sold ' + await text('#s-sold') + (tools ? ' tools: ' + tools.slice(0, 120) : ''));

  await page.screenshot({ path: path.join(dir, 'shot-1400.png'), fullPage: false });
  await page.setViewportSize({ width: 400, height: 900 });
  await run('giannis?');
  await page.screenshot({ path: path.join(dir, 'shot-400.png'), fullPage: false });

  ok(errors.length === 0, 'no console errors/warnings' + (errors.length ? ': ' + errors.join(' || ') : ''));
  await browser.close();
  console.log(fails ? `${fails} FAIL` : 'ALL PASS');
  process.exit(fails ? 1 : 0);
})().catch((e) => { console.error(e); process.exit(2); });
