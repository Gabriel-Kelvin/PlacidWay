const $=s=>document.querySelector(s);
let busy=false,sourceData=null,disclaimerShown=false;
const el=(tag,cls,text)=>{const x=document.createElement(tag);if(cls)x.className=cls;if(text!==undefined)x.textContent=text;return x;};
const date=v=>v?new Date(v).toLocaleString(undefined,{month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'}):'Not available';
function external(url,label,cls){const a=el('a',cls,label);a.href=url;a.target='_blank';a.rel='noopener noreferrer';return a;}
function renderView(name){$('#chat-view').classList.toggle('hidden',name!=='chat');$('#sources-view').classList.toggle('hidden',name!=='sources');$('#nav-chat').classList.toggle('active',name==='chat');$('#nav-sources').classList.toggle('active',name==='sources');$('#page-title').textContent=name==='chat'?'Care assistant':'Knowledge sources';}
// Native browser history records module changes, without trapping users on the site.
function routeName(){return location.hash==='#sources'?'sources':'chat';}
function showView(name){if(routeName()!==name)history.pushState({module:name},'',`#${name}`);renderView(name);}
if(!['#chat','#sources'].includes(location.hash))history.replaceState({module:'chat'},'','#chat');
renderView(routeName());
window.addEventListener('popstate',()=>renderView(routeName()));
window.addEventListener('hashchange',()=>renderView(routeName()));
$('.brand').onclick=e=>{e.preventDefault();showView('chat');};
function showEvidence(data){$('#evidence-panel').classList.remove('hidden');const root=$('#evidence-content');root.replaceChildren();if(data.outcome!=='answered')root.append(el('p','evidence-summary','For refusals or missing information, the source below provides scope or contact guidance. It does not prove that an absent fact is false.'));
 for(const c of data.citations||[]){const card=el('div','evidence-card');card.append(external(c.url,`${c.title} ↗`),el('blockquote','',c.quote),el('small','',`Line ${c.line}`));root.append(card);}
 $('#close-evidence').focus();
}
function formatAnswer(root){const text=root.textContent;root.replaceChildren();let table=null;for(const line of text.split('\n')){if(!line.trim()){table=null;continue;}if(line.includes(' | ')){if(!table){const wrap=el('div','answer-table-wrap');table=el('table','answer-table');wrap.append(table);root.append(wrap);}const row=el('tr');for(const cell of line.split(' | '))row.append(el(line.startsWith('Program Type')?'th':'td','',cell));table.append(row);}else{table=null;const heading=/^(Included in the|Optional Specialized|Excluded Services)/.test(line);root.append(el(heading?'h3':'p',heading?'answer-subheading':'answer-paragraph',line));}}}
function finishMessage(container,data){const meta=el('div','answer-meta');const why=el('button','trace-button','How did I get this answer?');why.onclick=()=>showEvidence(data);meta.append(why);container.append(meta);
 if(data.language!=='en')container.append(el('p','translation-note','Translated answer · Original English evidence available in citations'));
 if(data.disclaimer&&!disclaimerShown){container.append(el('div','disclaimer',data.disclaimer));disclaimerShown=true;}
 if(['unknown','booking','quote','recovery','unavailable'].includes(data.intent))container.append(external(data.quote_url,'Request a free quote from PlacidWay ↗','quote-link'));

 if(data.warnings?.length)container.append(el('p','warning','Some sources could not be refreshed. This answer uses the last successful snapshot.'));
 if(data.followups?.length){const follow=el('div','followups');for(const q of data.followups.slice(0,3)){const b=el('button','',q+' ↗');b.onclick=()=>send(q);follow.append(b);}container.append(follow);}
}
async function send(question){if(busy||!question.trim())return;busy=true;showView('chat');$('#welcome').classList.add('hidden');$('#send').disabled=true;$('#message').value='';const root=$('#messages');const user=el('div','message user',question);user.dir='auto';root.append(user);const assistant=el('article','message assistant');const label=el('div','assistant-label');label.append(el('span','mini-brand','✳'),el('span','','CARE NAVIGATOR'));const text=el('div','answer-text');text.dir='auto';const status=el('div','answer-status','Finding the right source…');assistant.append(label,status,text);root.append(assistant);assistant.scrollIntoView({behavior:'smooth',block:'start'});let data=null;
 try{const response=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:question})});if(!response.ok){const d=await response.json();throw Error(typeof d.detail==='string'?d.detail:'Please try again shortly.');}const reader=response.body.getReader();const decoder=new TextDecoder();let buffer='';let completed=false;
 const process=packet=>{let type='',payload='';for(const line of packet.split('\n')){if(line.startsWith('event: '))type=line.slice(7);if(line.startsWith('data: '))payload+=line.slice(6);}if(!payload)return;const event=JSON.parse(payload);if(type==='status')status.textContent=event.text;if(type==='validated'){data=event;status.remove();text.lang=event.language;if(['ar','he','fa','ur'].includes(event.language))text.dir='rtl';}if(type==='delta')text.textContent+=event.text;if(type==='done')completed=true;if(type==='error')throw Error(event.text);};
 while(true){const {value,done}=await reader.read();if(done)break;buffer+=decoder.decode(value,{stream:true});let i;while((i=buffer.indexOf('\n\n'))!==-1){process(buffer.slice(0,i));buffer=buffer.slice(i+2);}}
 if(!completed)throw Error('The connection was interrupted. Please try again.');formatAnswer(text);if(data)finishMessage(assistant,data);
 }catch(err){status.remove();assistant.append(el('p','error-text',err.message));}finally{busy=false;$('#send').disabled=false;$('#message').focus();}
}
$('#chat-form').onsubmit=e=>{e.preventDefault();send($('#message').value);};$('#message').onkeydown=e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();send(e.currentTarget.value);}};
document.querySelectorAll('[data-question]').forEach(b=>b.onclick=()=>send(b.dataset.question));
$('#new-chat').onclick=async()=>{if(busy)return;const response=await fetch('/api/chat/reset',{method:'POST'});if(!response.ok)return;disclaimerShown=false;$('#messages').replaceChildren();$('#welcome').classList.remove('hidden');$('#evidence-panel').classList.add('hidden');showView('chat');$('#message').focus();};
$('#nav-chat').onclick=()=>showView('chat');$('#nav-sources').onclick=$('#inline-sources').onclick=()=>showView('sources');$('#close-evidence').onclick=()=>$('#evidence-panel').classList.add('hidden');$('#privacy-open').onclick=$('#privacy-mobile').onclick=()=>$('#privacy-dialog').showModal();$('.dialog-close').onclick=()=>$('#privacy-dialog').close();document.addEventListener('keydown',e=>{if(e.key==='Escape')$('#evidence-panel').classList.add('hidden');});
fetch('/api/sources').then(r=>r.json()).then(data=>{sourceData=data;$('#updated').textContent='Sources checked '+date(data.last_refresh);const list=$('#source-list');data.sources.forEach((s,i)=>{const row=el('article','source-row');const body=el('div');const h=el('h3');h.append(external(s.url,s.title+' ↗'));body.append(h,el('p','',s.heading),el('p','',`Content updated ${date(s.fetched_at)} · Last checked ${date(s.checked_at)}`));row.append(el('span','source-number',String(i+1).padStart(2,'0')),body,el('span','source-ok',s.status==='ok'?'✓ Available':'⚠ Cached'));if(s.warning)body.append(el('p','warning',s.warning));list.append(row);});}).catch(()=>$('#updated').textContent='Source status unavailable');
