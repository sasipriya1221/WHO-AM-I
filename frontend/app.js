let userId=null,chapterId=null,currentPattern=null,currentStrand=null;
const $=s=>document.querySelector(s),$$=s=>[...document.querySelectorAll(s)];

async function api(path,opts={}){
  const r=await fetch(path,{headers:{'Content-Type':'application/json'},...opts});
  if(!r.ok){let body={};try{body=await r.json()}catch{};throw new Error(body.detail||r.statusText)}
  return r.json();
}
function say(x){$('#status').textContent=x}
function needUser(){if(!userId){alert('Start Mirror first.');return false}return true}
function escapeHtml(v=''){return String(v).replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#039;','"':'&quot;'}[c]))}
function setView(id){$$('nav button').forEach(x=>x.classList.toggle('active',x.dataset.view===id));$$('.view').forEach(v=>v.classList.toggle('active',v.id===id))}
$$('nav button').forEach(b=>b.onclick=()=>setView(b.dataset.view));

$('#start').onclick=async()=>{
  const name=$('#name').value||'Maya';
  const u=await api('/api/v1/users/demo',{method:'POST',body:JSON.stringify({display_name:name,email:name.toLowerCase().replace(/\s/g,'.')+'@demo.local'})});
  userId=u.id;
  $('#hello').innerHTML=`<p>Hey ${escapeHtml(name)} 👋 Tell me one thing you genuinely enjoy.</p>`;
  say('Mirror · Level 1');
};

$('#saveInterest').onclick=async()=>{
  if(!needUser())return;
  await api(`/api/v1/mirror/${userId}/interests`,{method:'POST',body:JSON.stringify({category:$('#interestType').value,name:$('#interestName').value})});
  say('Mirror remembers — entertainment only');
  await loadGame();
};
async function loadGame(){
  if(!needUser())return;
  const g=await api(`/api/v1/mirror/${userId}/game`);
  $('#game').innerHTML=`<b>${escapeHtml(g.title)}</b><p>${escapeHtml(g.question)}</p>${(g.options||[]).map(x=>`<button class="mini-answer">${escapeHtml(x)}</button>`).join('')}<p class="tiny">${escapeHtml(g.note||'')}</p>`;
}
$('#loadGame').onclick=loadGame;

$('#consent').onclick=async()=>{
  if(!needUser())return;
  await api(`/api/v1/dna/${userId}/consent`,{method:'POST',body:JSON.stringify({consent:true})});
  say('DNA · you chose to explore');
};

$$('.submitExp').forEach(b=>b.onclick=async()=>{
  if(!needUser())return;
  const type=b.dataset.exp,text=type==='empty_room'?$('#room').value:$('#future').value;
  if(!text.trim()){alert('Share a clue first.');return}
  b.disabled=true;b.textContent='Reading this clue…';
  try{
    const result=await api(`/api/v1/dna/${userId}/experiences`,{method:'POST',body:JSON.stringify({experience_type:type,input_mode:'text',response:{reflection:text},consent_for_analysis:true})});
    await refreshDNA();
    say(result.evidence_created?`${result.evidence_created} clue(s) added`:'No reliable clue extracted yet');
  }catch(err){alert(err.message)}finally{b.disabled=false;b.textContent='Add this clue'}
});

$('#refreshDNA').onclick=refreshDNA;
async function refreshDNA(){
  if(!userId)return;
  const strands=await api(`/api/v1/dna/${userId}/strands`);
  const visible=strands.filter(s=>s.status!=='retired');
  $('#revealEmpty').classList.toggle('hidden',visible.length>0);
  $('#patterns').innerHTML=visible.map(s=>{
    const label=s.user_label||s.ai_label||'Unnamed clue';
    const ownership=s.status==='user_defined'?'Defined by you':'AI hypothesis';
    return `<button class="dna-chip ${s.status==='user_defined'?'human':'ai'}" data-pattern="${s.pattern_id||''}" data-strand="${s.id}" data-label="${escapeHtml(label)}"><span>${s.status==='user_defined'?'●':'◌'}</span><b>${escapeHtml(label)}</b><small>${ownership}</small></button>`;
  }).join('');
  $$('.dna-chip').forEach(chip=>chip.onclick=()=>openReveal(chip.dataset.pattern,chip.dataset.strand,chip.dataset.label));
  if(currentStrand){const updated=visible.find(s=>s.id===currentStrand);if(updated)await openReveal(updated.pattern_id,updated.id,updated.user_label||updated.ai_label,false)}
}

async function openReveal(patternId,strandId,label,scroll=true){
  if(!patternId)return;
  currentPattern=patternId;currentStrand=strandId;
  const p=(await api(`/api/v1/dna/${userId}/patterns`)).find(x=>x.id===patternId);
  $('#revealPanel').classList.remove('hidden');
  $('#revealLabel').textContent=label||p?.label||'Possible pattern';
  $('#revealStatus').textContent=(p?.status||'emerging').replace('_',' ');
  const strand=(await api(`/api/v1/dna/${userId}/strands`)).find(s=>s.id===strandId);
  const human=strand?.status==='user_defined';
  $('#ownershipLine').textContent=human?'Defined by you. The original AI hypothesis remains traceable, but your words have authority.':'AI noticed this. It may be wrong. You decide what it means.';
  $('#revealPanel').classList.toggle('human-defined',human);
  $('#contestResult').classList.add('hidden');$('#contestResult').innerHTML='';
  $('#renameInput').value=human?(strand.user_label||''):'';
  if(scroll)$('#revealPanel').scrollIntoView({behavior:'smooth',block:'start'});
}

$('#whyBtn').onclick=async()=>{
  if(!currentPattern)return;
  const d=await api(`/api/v1/dna/${userId}/patterns/${currentPattern}/why`);
  const box=$('#contestResult');
  box.classList.remove('hidden');
  box.innerHTML=`<div class="contest-heading"><strong>Why did Mirror notice this?</strong><span>${d.supporting.length} supporting clue(s)</span></div>${d.supporting.length?d.supporting.map((x,i)=>`<div class="evidence-line support"><span>${i+1}</span><div><b>${escapeHtml(x.summary)}</b><p>${escapeHtml(x.original||'')}</p></div></div>`).join(''):'<p class="soft-copy">There is not enough supporting evidence yet.</p>'}<p class="trust-note">Every conclusion stays traceable to experiences you intentionally shared.</p>`;
};

$('#challengeBtn').onclick=async()=>{
  if(!currentPattern)return;
  const d=await api(`/api/v1/dna/${userId}/patterns/${currentPattern}/challenge`,{method:'POST'});
  const box=$('#contestResult');
  box.classList.remove('hidden');
  box.innerHTML=`<div class="contest-heading"><strong>The AI tried to prove itself wrong.</strong><span>${d.status.replace('_',' ')}</span></div>${d.contradicting.length?d.contradicting.map(x=>`<div class="evidence-line counter"><span>↔</span><div><b>${escapeHtml(x.summary)}</b><p>${escapeHtml(x.original||'')}</p><small>semantic similarity ${x.similarity}</small></div></div>`).join(''):'<div class="no-counter"><b>No meaningful counter-evidence surfaced yet.</b><p>That does not make the hypothesis true. It only means the current story is incomplete.</p></div>'}<p class="trust-note">${escapeHtml(d.message||'')}</p>`;
  $('#revealStatus').textContent=d.status.replace('_',' ');
  await refreshDNA();
};

$('#notMeBtn').onclick=async()=>{
  if(!currentPattern)return;
  const ok=confirm('Reject this AI hypothesis? It will not be treated as your identity or used by Compass.');
  if(!ok)return;
  const d=await api(`/api/v1/dna/${userId}/patterns/${currentPattern}/not-me`,{method:'POST'});
  $('#contestResult').classList.remove('hidden');
  $('#contestResult').innerHTML=`<div class="rejected-state"><b>Not you. Understood.</b><p>${escapeHtml(d.message)}</p></div>`;
  say('AI hypothesis rejected');
  currentPattern=null;currentStrand=null;
  setTimeout(async()=>{$('#revealPanel').classList.add('hidden');await refreshDNA()},600);
};

$('#renameBtn').onclick=async()=>{
  if(!currentStrand)return;
  const value=$('#renameInput').value.trim();
  if(!value){alert('Use your own words first.');return}
  const d=await api(`/api/v1/dna/${userId}/strands/${currentStrand}/rename`,{method:'POST',body:JSON.stringify({user_label:value})});
  $('#revealLabel').textContent=d.user_label;
  $('#ownershipLine').textContent=`Defined by you. Mirror originally suggested “${d.ai_label||'a different label'}”.`;
  $('#revealPanel').classList.add('human-defined');
  $('#contestResult').classList.remove('hidden');
  $('#contestResult').innerHTML=`<div class="human-win"><span>●</span><div><b>${escapeHtml(d.user_label)}</b><p>The AI's label did not become your identity. Your interpretation did.</p></div></div>`;
  say('DNA · defined by you');
  await refreshDNA();
};

$('#makeChapter').onclick=async()=>{
  if(!needUser())return;
  const c=await api(`/api/v1/compass/${userId}/chapters`,{method:'POST',body:JSON.stringify({title:$('#chapter').value||'My current chapter'})});
  chapterId=c.id;say('Compass · '+c.title);
};
$('#reflect').onclick=async()=>{
  if(!chapterId){alert('Create your current chapter first.');return}
  const r=await api(`/api/v1/compass/${userId}/reflect`,{method:'POST',body:JSON.stringify({chapter_id:chapterId,focus:{}})});
  $('#compassResult').innerHTML=`<div class="compass-question">${escapeHtml(r.text)}</div><p class="tiny">${escapeHtml(r.note||'')}</p>`;
};

$('#refreshVault').onclick=refreshVault;
async function refreshVault(){
  if(!needUser())return;
  const v=await api(`/api/v1/vault/${userId}`);
  $('#vaultData').innerHTML=`<div class="vault-group"><h3>Entertainment</h3>${v.entertainment.map(x=>`<p>${escapeHtml(x.label)} <span class="purpose-tag">${escapeHtml(x.purpose)}</span></p>`).join('')||'<p>None</p>'}</div><div class="vault-group"><h3>Self-discovery evidence</h3>${v.self_discovery.map(x=>`<div class="vault-row"><span><b>${escapeHtml(x.label)}</b><small>${escapeHtml(x.summary)}</small></span><button class="delete" data-evidence="${x.id}">Forget</button></div>`).join('')||'<p>None</p>'}</div><div class="vault-group"><h3>DNA</h3>${v.dna.map(x=>`<p>🧬 ${escapeHtml(x.label)} · ${escapeHtml(x.status.replace('_',' '))}</p>`).join('')||'<p>None</p>'}</div>`;
  $$('.delete[data-evidence]').forEach(b=>b.onclick=()=>delEvidence(b.dataset.evidence));
}
async function delEvidence(id){
  await api(`/api/v1/vault/${userId}/evidence/${id}`,{method:'DELETE'});
  await refreshVault();await refreshDNA();say('Evidence forgotten; DNA recalculated');
}
