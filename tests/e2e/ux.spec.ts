import { expect, test } from '@playwright/test';

const widths=[320,390,834,1280,1366,1440];
for(const width of widths) {
test(`readable typography, comfortable controls and no overflow at ${width}px`,async({page})=>{
  await page.goto('/');
  const detail=await page.locator('[data-variant="lead"] h2 a').getAttribute('href');
  const routes=['/','/all/','/category/ai/','/category/chips/',detail!,'/digests/','/models/','/freebies/','/saved/','/settings/','/about/','/archives/','/missing-page/'];
    await page.setViewportSize({width,height:900});
    for(const route of routes) {
      await page.goto(route);
      await page.waitForFunction(()=>!document.querySelector('astro-island[ssr]'));
      const failures=await page.evaluate(()=>{
        const visible=(element:Element)=>{
          const closed=element.closest('details:not([open])');
          return element.getClientRects().length && getComputedStyle(element).visibility!=='hidden' && (!closed || closed.querySelector(':scope > summary')?.contains(element));
        };
        const text=[...document.querySelectorAll('body *')].filter(element=>visible(element) && !element.closest('[aria-hidden="true"]') && [...element.childNodes].some(node=>node.nodeType===Node.TEXT_NODE && node.textContent?.trim()));
        const tiny=text.filter(element=>parseFloat(getComputedStyle(element).fontSize)<12).map(element=>element.textContent?.trim().slice(0,60));
        // Inline prose links are deliberately excluded. Checkbox labels provide the hit area.
        const controls=[...document.querySelectorAll('button:not(:disabled),.category-nav>a,.more-nav>summary,.more-menu a,.category-tag,.saved-link,.category-index-grid>a,.briefing-arrow,.control-link,.citation,.breadcrumb a,.preference-categories label,.checkbox-label')].filter(visible);
        const small=controls.filter(element=>{const bounds=element.getBoundingClientRect();return bounds.width<43.9 || bounds.height<43.9;}).map(element=>({text:element.textContent?.trim(),width:element.getBoundingClientRect().width,height:element.getBoundingClientRect().height}));
        return {overflow:document.documentElement.scrollWidth>innerWidth,tiny,small};
      });
      expect(failures,`${route} at ${width}px`).toEqual({overflow:false,tiny:[],small:[]});
    }
});
}

test('computed text and visible brand contrast in both themes, including More and saved states',async({page})=>{
  for(const theme of ['light','dark']) {
    await page.goto('/');
    await page.evaluate(value=>{document.documentElement.dataset.theme=value;},theme);
    await page.locator('[data-bookmark]').first().click();
    await page.getByText('More',{exact:true}).click();
    const failures=await page.evaluate(()=>{
      const rgb=(value:string)=>value.match(/[\d.]+/g)?.map(Number) || [];
      const luminance=(values:number[])=>values.slice(0,3).map(value=>{const c=value/255;return c<=.04045?c/12.92:((c+.055)/1.055)**2.4;}).reduce((sum,c,i)=>sum+c*[.2126,.7152,.0722][i]!,0);
      const background=(element:Element|null):number[]=>{
        if(!element) return [255,255,255];
        const value=rgb(getComputedStyle(element).backgroundColor);
        const alpha=value[3]??1;
        const parent=alpha<1?background(element.parentElement):[0,0,0];
        return value.slice(0,3).map((c,i)=>c*alpha+parent[i]!*(1-alpha));
      };
      const elements=[...document.querySelectorAll('body *')].filter(element=>element.getClientRects().length && getComputedStyle(element).visibility!=='hidden' && !element.closest('button:disabled') && [...element.childNodes].some(node=>node.nodeType===Node.TEXT_NODE && node.textContent?.trim()));
      return elements.flatMap(element=>{
        const style=getComputedStyle(element),fg=luminance(rgb(style.color)),bg=luminance(background(element));
        const ratio=(Math.max(fg,bg)+.05)/(Math.min(fg,bg)+.05);
        const size=parseFloat(style.fontSize),large=size>=24 || (size>=18.66 && parseInt(style.fontWeight)>=700);
        return ratio+.01<(large?3:4.5)?[{text:element.textContent?.trim().slice(0,70),ratio}]:[];
      });
    });
    expect(failures,theme).toEqual([]);
  }
});

test('lead, briefing and feed have distinct semantics and labelled mobile facts',async({page})=>{
  await page.setViewportSize({width:320,height:844});await page.goto('/');
  await expect(page.locator('[data-variant="lead"]')).toHaveCount(1);
  await expect(page.locator('[data-variant="briefing"]')).toHaveCount(4);
  const lead=page.locator('[data-variant="lead"]');
  expect(await lead.evaluate(element=>element.getBoundingClientRect().top)).toBeLessThan(650);
  await expect(lead.locator('.story-index')).toHaveCount(0);
  await page.goto('/all/');
  expect(await page.locator('[data-variant="feed"]').count()).toBeGreaterThan(5);
  await expect(page.locator('.story-index,.verification,.why')).toHaveCount(0);
  for(const label of await page.locator('.chip-label').all()) {await expect(label).toBeVisible();expect((await label.textContent())?.trim()).not.toBe('');}
  expect(await page.locator('.chips').count()).toBeGreaterThan(0);
  for(const chip of await page.locator('.chips').all()) expect(await chip.locator(':scope > span').count()).toBeLessThanOrEqual(2);
});

test('primary navigation and More are keyboard and touch usable; credit routes are distinct',async({page})=>{
  await page.goto('/');const nav=page.getByRole('navigation',{name:'Main navigation'});
  await expect(nav.locator(':scope > a')).toHaveText(['Home','AI','Chips','Security','Free credit']);
  const more=nav.locator('summary');await more.focus();await page.keyboard.press('Enter');
  await expect(nav.getByRole('link',{name:'Research',exact:true})).toBeVisible();
  await expect(nav.getByRole('link',{name:'Freebie stories',exact:true})).toHaveAttribute('href','/category/freebies/');
  await expect(nav.getByRole('link',{name:'Free credit',exact:true})).toHaveAttribute('href','/freebies/');
  await page.keyboard.press('Enter');await expect(nav.locator('.more-menu')).not.toBeVisible();
  await more.click();await nav.getByRole('link',{name:'Freebie stories',exact:true}).click();
  await expect(page.locator('h1')).toHaveText('Freebie stories');
});

test('search is ready before accepting interaction, traps focus and restores it',async({page})=>{
  await page.goto('/',{waitUntil:'domcontentloaded'});
  const trigger=page.getByRole('button',{name:'Search stories'});await trigger.click();
  const input=page.getByLabel('Search the intelligence archive');await expect(input).toBeFocused();await input.fill('Meridian');
  await expect(page.locator('.search-results strong').first()).toContainText('Meridian');
  for(let i=0;i<12;i++){await page.keyboard.press('Tab');expect(await page.evaluate(()=>Boolean(document.activeElement?.closest('dialog')))).toBe(true);}
  for(let i=0;i<12;i++){await page.keyboard.press('Shift+Tab');expect(await page.evaluate(()=>Boolean(document.activeElement?.closest('dialog')))).toBe(true);}
  await page.keyboard.press('Escape');await expect(trigger).toBeFocused();
  await expect(page.locator('dialog h2')).toHaveCount(0);
});

test('blocked save reports the error beside its control and preserves accessible state names',async({page})=>{
  await page.addInitScript(()=>Object.defineProperty(window,'localStorage',{get(){throw Error('Unavailable');}}));
  await page.goto('/');const lead=page.locator('[data-variant="lead"]');await lead.locator('[data-bookmark]').click();
  await expect(lead.locator('[data-action-status]')).toContainText('Browser storage is unavailable');
  await expect(lead.locator('[data-bookmark]')).toHaveAttribute('aria-label',/^Save story:/);
});

test('404 recovery offers useful destinations and tracker absence has explicit semantics',async({page})=>{
  await page.goto('/missing-page/');await expect(page.locator('h1')).toHaveText('This story took another turn.');
  await page.getByRole('link',{name:'Browse all stories'}).click();await expect(page.locator('h1')).toHaveText('All stories.');
  await page.goto('/freebies/');await expect(page.locator('[data-missing]').first()).toBeVisible();
  expect(await page.locator('[data-missing]').first().evaluate(element=>getComputedStyle(element).fontStyle)).toBe('italic');
});

test('an unavailable saved record has honest copy and a working recovery route',async({page})=>{
  await page.goto('/');await page.locator('[data-bookmark]').first().click();
  await page.route('**/data/story-index.json',route=>route.fulfill({json:{}}));
  await page.goto('/saved/');
  await expect(page.getByRole('heading',{name:'This saved story is unavailable in this edition.'})).toBeVisible();
  await page.getByRole('link',{name:'Browse all stories'}).click();
  await expect(page.locator('h1')).toHaveText('All stories.');
});
