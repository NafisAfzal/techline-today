import {localeFor,t} from './i18n';
type FocusItem={id:string;title:string;href:string;language:string};
const interval=8000;

export function initNewsFocus() {
  const root=document.querySelector<HTMLElement>('[data-news-focus]');
  const link=root?.querySelector<HTMLAnchorElement>('[data-focus-link]');
  const data=root?.querySelector<HTMLScriptElement>('[data-focus-items]');
  const position=root?.querySelector<HTMLElement>('[data-focus-position]');
  const state=root?.querySelector<HTMLElement>('[data-focus-state]');
  if(!root || !link || !data || !position || !state || root.dataset.ready) return;
  const items=[...new Map((JSON.parse(data.textContent || '[]') as FocusItem[]).map(item=>[item.id,item])).values()];
  if(!items.length) return;
  const locale=localeFor(location.pathname),ui=(key:string)=>t(locale,key);
  const number=new Intl.NumberFormat(locale);
  const controls=root.querySelector<HTMLElement>('.focus-controls');
  const button=root.querySelector<HTMLButtonElement>('[data-focus-toggle]');
  const label=root.querySelector<HTMLElement>('[data-focus-toggle-label]');
  const previous=root.querySelector<HTMLButtonElement>('[data-focus-previous]');
  const next=root.querySelector<HTMLButtonElement>('[data-focus-next]');
  const progress=root.querySelector<HTMLElement>('[data-focus-progress]');
  const announcement=root.querySelector<HTMLElement>('[data-focus-announcement]');
  const reduced=matchMedia('(prefers-reduced-motion: reduce)');
  let index=0,manual=false,hovered=false,onScreen=true,running=false;
  let remaining=interval,startedAt=0,timer:ReturnType<typeof setTimeout>|undefined;
  const focused=()=>root.contains(document.activeElement) && document.activeElement instanceof HTMLElement && document.activeElement.matches(':focus-visible');
  const pauseReason=()=>items.length<2?'single':reduced.matches?'reduced':manual?'manual':document.querySelector('dialog[open]')?'modal':document.hidden?'hidden':!onScreen?'offscreen':focused()?'focus':hovered?'hover':'';
  const stop=()=>{
    if(!running) return;
    remaining=Math.max(0,remaining-(performance.now()-startedAt));
    clearTimeout(timer);timer=undefined;running=false;
  };
  const restartProgress=()=>{
    if(!progress) return;
    progress.style.animationName='none';void progress.offsetWidth;progress.style.animationName='';
  };
  const render=()=>{
    const item=items[index]!;
    link.textContent=item.title;link.href=item.href;link.lang=item.language;link.title=item.title;
    root.dataset.story=item.id;
    position.textContent=`${number.format(index+1)} / ${number.format(items.length)}`;
    position.setAttribute('aria-label',ui('Headline {position} of {total}').replace('{position}',number.format(index+1)).replace('{total}',number.format(items.length)));
  };
  const advance=(direction:number,requested=false)=>{
    stop();remaining=interval;index=(index+direction+items.length)%items.length;
    render();restartProgress();link.classList.remove('is-entering');
    if(!requested && !reduced.matches) {void link.offsetWidth;link.classList.add('is-entering');}
    if(requested && announcement) announcement.textContent=items[index]!.title;
    sync();
  };
  const sync=()=>{
    const reason=pauseReason();
    root.dataset.motion=reason?'paused':'running';root.dataset.pauseReason=reason;
    root.dataset.manualPause=String(manual);
    state.textContent=ui(reason==='single'?'One headline':reason==='reduced'?'Motion off':reason?'Paused':'Playing');
    state.title=ui(reason==='modal'?'Paused while search is open':reason==='focus'?'Paused while focused':reason==='hover'?'Paused while reading':reason==='reduced'?'Headline rotation is off with reduced motion':reason==='single'?'Only one headline in this edition.':reason?'Paused':'Automatically advances every eight seconds.');
    if(button && label) {
      button.disabled=items.length<2 || reduced.matches;
      button.setAttribute('aria-pressed',String(manual || reduced.matches));
      button.setAttribute('aria-label',ui(reduced.matches?'Headline rotation is off with reduced motion':manual?'Resume headline rotation':'Pause headline rotation'));
      label.textContent=ui(reduced.matches?'Paused':manual?'Resume':'Pause');
    }
    if(reason) {stop();link.classList.remove('is-entering');return;}
    if(!running) {
      running=true;startedAt=performance.now();
      timer=setTimeout(()=>{running=false;timer=undefined;remaining=interval;advance(1);},remaining);
    }
  };
  root.dataset.mode=items.length>1?'rotating':'static';
  if(controls) controls.hidden=items.length<2;
  if(previous) previous.disabled=items.length<2;
  if(next) next.disabled=items.length<2;
  if(items.length<2) root.querySelector<HTMLElement>('.focus-meter')?.setAttribute('hidden','');
  previous?.addEventListener('click',()=>advance(-1,true));
  next?.addEventListener('click',()=>advance(1,true));
  button?.addEventListener('click',()=>{
    manual=!manual;sync();
    if(announcement) announcement.textContent=ui(manual?'Headline rotation paused.':focused()?'Automatic headlines resume after focus leaves this strip.':'Headline rotation resumed.');
  });
  // Protect reading anywhere in the strip; pointer playback controls remain usable.
  root.addEventListener('pointerover',event=>{
    if(event.pointerType==='touch') return;
    hovered=!(event.target instanceof Element && event.target.closest('.focus-controls'));
    sync();
  });
  root.addEventListener('pointerleave',()=>{hovered=false;sync();});
  root.addEventListener('focusin',sync);
  root.addEventListener('focusout',()=>queueMicrotask(sync));
  link.addEventListener('animationend',()=>link.classList.remove('is-entering'));
  document.addEventListener('visibilitychange',sync);
  const dialogs=new MutationObserver(sync);
  document.querySelectorAll('dialog').forEach(dialog=>dialogs.observe(dialog,{attributes:true,attributeFilter:['open']}));
  reduced.addEventListener('change',()=>{stop();remaining=interval;restartProgress();sync();});
  const observer=new IntersectionObserver(entries=>{onScreen=entries[0]?.isIntersecting ?? false;sync();});
  observer.observe(root);render();root.dataset.ready='true';sync();
}
