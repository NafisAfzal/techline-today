import { t, type Locale } from '../lib/i18n';
import { useEffect, useState } from 'react';
import type { Category, Preferences as PreferenceData } from '../../../../packages/contracts';
import { defaults, LocalRepository } from '../lib/repositories';
export default function Preferences({ categories, locale='en' }: {locale?:Locale;categories: {id:Category; label:string}[]}) {
  const ui = (key:string)=>t(locale,key);
  const [value, setValue] = useState<PreferenceData>(defaults);
  const [message, setMessage] = useState(ui('Preferences stay on this device.'));
  useEffect(() => { try { setValue(new LocalRepository(localStorage).get()); } catch { setMessage(ui('Browser storage is unavailable.')); } }, []);
  const save = (next: PreferenceData) => {
    setValue(next);
    try {
      if (!new LocalRepository(localStorage).set(next)) throw new Error('Storage unavailable');
      document.documentElement.dataset.theme = next.theme === 'system' ? (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light') : next.theme;
      document.documentElement.dataset.density = next.density;
      window.dispatchEvent(new CustomEvent('ti:preferences'));
      setMessage(ui('Preferences saved on this device.'));
    } catch { setMessage(ui('Browser storage is unavailable. Changes apply to this visit.')); }
  };
  const move = (index: number, direction: number) => { const next = [...value.categories]; const swap = next[index + direction]; if (swap !== undefined) {next[index + direction] = next[index]!; next[index] = swap; save({...value, categories:next});} };
  return <div className="preferences-panel"><fieldset><legend>{ui("Put your interests first")}</legend><p>{ui("Selected categories appear first in All stories. Use the arrow buttons below to change their order.")}</p><div className="preference-categories">{categories.map(category => <label key={category.id}><input type="checkbox" checked={value.categories.includes(category.id)} onChange={() => save({...value,categories:value.categories.includes(category.id) ? value.categories.filter(id => id !== category.id) : [...value.categories, category.id]})} />{category.label}</label>)}</div></fieldset>
    <ol className="category-order">{value.categories.map((id,index) => <li key={id}><span>{categories.find(category => category.id === id)?.label}</span><button disabled={index === 0} onClick={() => move(index,-1)} aria-label={`${ui("Move up")}: ${categories.find(category=>category.id===id)?.label}`}>↑</button><button disabled={index === value.categories.length - 1} onClick={() => move(index,1)} aria-label={`${ui("Move down")}: ${categories.find(category=>category.id===id)?.label}`}>↓</button></li>)}</ol>
    <div className="preference-selects"><label>{ui("Appearance")}<select value={value.theme} onChange={event => save({...value, theme:event.target.value as PreferenceData['theme']})}><option value="system">{ui("Follow device")}</option><option value="light">{ui("Light")}</option><option value="dark">{ui("Dark")}</option></select></label>
    <label>{ui("Reading density")}<select value={value.density} onChange={event => save({...value,density:event.target.value as PreferenceData['density']})}><option value="comfortable">{ui("Comfortable")}</option><option value="compact">{ui("Compact")}</option></select></label>
    <label>{ui("Feed order")}<select value={value.sort} onChange={event => save({...value,sort:event.target.value as PreferenceData['sort']})}><option value="importance">{ui("Importance")}</option><option value="latest">{ui("Newest first")}</option></select></label></div>
    <label className="checkbox-label"><input type="checkbox" checked={value.hideRead} onChange={event => save({...value,hideRead:event.target.checked})} />{ui("Hide stories marked read")}</label>
    <button className="button" onClick={() => save({...defaults,categories:[]})}>{ui("Reset personalization")}</button><p role="status">{message}</p></div>;
}
