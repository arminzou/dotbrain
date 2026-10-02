// With docs dev server running:
// playwright-cli open http://localhost:5173/dotbrain/
// playwright-cli run-code --filename=tests/browser/mermaid-theme.js
async (page) => {
  const base = page.url().split('/dotbrain/')[0] + '/dotbrain/';
  for (const name of ['', 'getting-started', 'configuration', 'architecture']) {
    await page.goto(`${base}${name}`);
    await page.locator('.tree-view').first().waitFor();
    for (const dark of [true, false, true]) {
      const toggle = page.locator('.VPSwitchAppearance').first();
      if ((await toggle.getAttribute('aria-checked')) !== String(dark)) await toggle.click();
      await page.waitForFunction(() => !!document.querySelector('.tree-view'));
      await page.evaluate(() => {
        const rgb = color => color.match(/[\d.]+/g).slice(0, 3).map(Number);
        const luminance = color => rgb(color).map(v => {
          v /= 255;
          return v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
        }).reduce((sum, v, i) => sum + v * [0.2126, 0.7152, 0.0722][i], 0);
        const bg = luminance(getComputedStyle(document.body).backgroundColor);
        const elements = [...document.querySelectorAll('.tree-view text, .tree-view path, .tree-view line')]
          .filter(e => e.getBoundingClientRect().width > 0);
        if (!elements.some(e => e.tagName === 'text')) throw new Error('No tree labels rendered');
        for (const el of elements) {
          const style = getComputedStyle(el);
          const fg = luminance(el.tagName === 'line' ? style.stroke : style.fill);
          const ratio = (Math.max(bg, fg) + 0.05) / (Math.min(bg, fg) + 0.05);
          const minimum = el.tagName === 'text' ? 4.5 : 3;
          if (ratio < minimum) throw new Error(`${el.getAttribute('class') || el.tagName}: contrast ${ratio.toFixed(2)} < ${minimum}`);
        }
      });
    }
  }
  return 'Tree labels, descriptions, icons, and connectors pass contrast checks through dark/light/dark toggles on all four tree pages.';
}
