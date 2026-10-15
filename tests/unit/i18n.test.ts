import { describe, expect, it } from 'vitest';
import en from '../../apps/web/src/i18n/en.json';
import bn from '../../apps/web/src/i18n/bn.json';
import { localeFor, localizedPath, localizedStory, storyCount, t } from '../../apps/web/src/lib/i18n';
import type { Story } from '../../packages/contracts';
describe('static localization',()=>{
  it('keeps dictionaries aligned and Unicode intact',()=>{
    expect(Object.keys(en).sort()).toEqual(Object.keys(bn).sort());
    for(const value of Object.values(bn)) {expect(value.trim()).not.toBe('');expect(value).not.toMatch(/[<>\uFFFD]/);expect(value).not.toContain(String.fromCharCode(0));}
    expect(t('bn','Summary')).toBe('সারসংক্ষেপ');expect(t('en','Summary')).toBe('Summary');
  });
  it('uses explicit routes and stable slugs without flags or geographical redirects',()=>{
    expect(localeFor('/bn/story/example/')).toBe('bn');expect(localeFor('/bn-other/')).toBe('en');
    expect(localizedPath('/story/example/?period=week#source','bn')).toBe('/bn/story/example/?period=week#source');
    expect(localizedPath('/bn/story/example/','en')).toBe('/story/example/');
    expect(localizedPath('/data/stories/example.json','bn')).toBe('/data/stories/example.json');
    expect(localizedPath('//unsafe.example/','bn')).toBe('/bn/');
  });
  it('falls back to the identical canonical record when a translation is missing',()=>{
    const story={headline:'Canonical English',language:'en'} as Story;
    expect(localizedStory(story,'bn')).toBe(story);expect(localizedStory(story,'en')).toBe(story);
  });
  it('preserves source references, number values and evidence when translating presentation',()=>{
    const story={headline:'English',language:'en',evidence_state:'primary-confirmed',source_ids:['source'],key_facts:[{text:'English fact',source_ids:['source'],status:'uncertain'}],key_numbers:[{value:'128K',label:'Context',source_ids:['source'],context:'English context'}],translations:{bn:{content:{headline:'বাংলা শিরোনাম',summary_bullets:['প্রথম','দ্বিতীয়','তৃতীয়'],why_it_matters:'কেন গুরুত্বপূর্ণ',broader_summary:'বিস্তারিত',key_fact_texts:['বাংলা তথ্য'],number_labels:['ধারণক্ষমতা'],number_contexts:['বাংলা প্রেক্ষাপট'],limitations:['সীমাবদ্ধতা']}}}} as unknown as Story;
    const translated=localizedStory(story,'bn');
    expect(translated.headline).toBe('বাংলা শিরোনাম');expect(translated.key_numbers[0]?.value).toBe('128K');
    expect(translated.source_ids).toBe(story.source_ids);expect(translated.key_facts[0]?.status).toBe('uncertain');
    expect(story.headline).toBe('English');expect(translated.evidence_state).toBe(story.evidence_state);
  });
  it('formats counts and preserves action arrows',()=>{
    expect(storyCount(1,'en')).toBe('1 story');expect(storyCount(2,'bn')).toBe('২টি খবর');
    expect(t('bn','Browse digests →')).toBe('সংকলন দেখুন →');
  });
  it('keeps new language, trust and freshness indicators in readable Bangla',()=>{
    for (const key of ['English content','Primary source','Preprint','Coverage and freshness','Technology news & research','supported']) {
      expect(t('bn',key)).toMatch(/[\u0980-\u09ff]/u);
    }
    for (const value of Object.values(bn)) expect(value).not.toMatch(/\?{2,}|\uFFFD/u);
  });
});
