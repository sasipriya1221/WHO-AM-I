let judgeDemo=null;
let judgeStep=0;
const demoSteps=['Experience','DNA','Challenge','Rename','Compass','Delete','DNA weakens'];

function demoEl(id){return document.getElementById(id)}
function setJudgeStep(step){
  judgeStep=step;
  document.querySelectorAll('.demo-dot').forEach((el,i)=>{
    el.classList.toggle('done',i<step);
    el.classList.toggle('active',i===step);
  });
  document.querySelectorAll('.demo-card').forEach((el,i)=>{
    el.classList.toggle('visible',i===step);
    el.classList.toggle('done',i<step);
  });
}
function demoOwnership(ai,user){
  return `<div class="ownership-demo"><div class="node"><span>AI NOTICED</span><strong>${escapeHtml(ai)}</strong></div>${user?`<div class="demo-arrow">→</div><div class="node human"><span>YOU DEFINED</span><strong>${escapeHtml(user)}</strong></div>`:''}</div>`;
}

async function startJudgeDemo(){
  const btn=demoEl('startJudgeDemo');btn.disabled=true;btn.textContent='Seeding demo…';
  try{
    judgeDemo=await api('/api/v1/demo/seed',{method:'POST'});
    userId=judgeDemo.user.id;
    currentPattern=judgeDemo.pattern.id;
    currentStrand=judgeDemo.strand.id;
    chapterId=judgeDemo.chapter.id;
    compassStrandId=null;
    demoEl('demoMaya').textContent=judgeDemo.user.display_name;
    demoEl('demoExperiences').innerHTML=judgeDemo.experiences.map(x=>`<div class="demo-exp"><span>${escapeHtml(x.type.replace('_',' '))}</span><b>${escapeHtml(x.label)}</b><small>consented self-discovery evidence</small></div>`).join('');
    demoEl('demoEntertainment').innerHTML=`Mirror also remembers <b>${escapeHtml(judgeDemo.entertainment.label)}</b> — <code>purpose=${judgeDemo.entertainment.purpose}</code>, <code>dna_allowed=${judgeDemo.entertainment.dna_allowed}</code>. It is not part of this inference.`;
    setJudgeStep(0);
    demoEl('demoStartState').classList.remove('hidden');
    say('Judge Demo · seeded Maya');
  }catch(err){alert(err.message)}finally{btn.disabled=false;btn.textContent='Reset & seed Maya'}
}

async function demoRevealDNA(){
  const why=await api(`/api/v1/dna/${userId}/patterns/${currentPattern}/why`);
  const p=(await api(`/api/v1/dna/${userId}/patterns`)).find(x=>x.id===currentPattern);
  demoEl('demoDnaOwnership').innerHTML=demoOwnership(p.label,null);
  demoEl('demoDnaState').textContent=`${p.status.toUpperCase()} · ${p.support} independent supporting clues`;
  demoEl('demoWhyEvidence').innerHTML=why.supporting.map((x,i)=>`<div class="demo-evidence"><b>${i+1}. ${escapeHtml(x.summary)}</b><small>${escapeHtml(x.original||'')}</small></div>`).join('');
  setJudgeStep(1);say('Judge Demo · DNA revealed');
}

async function demoChallenge(){
  const d=await api(`/api/v1/dna/${userId}/patterns/${currentPattern}/challenge`,{method:'POST'});
  demoEl('demoChallengeState').textContent=d.status.replace('_',' ');
  demoEl('demoCounters').innerHTML=d.contradicting.length?d.contradicting.map(x=>`<div class="demo-counter"><b>${escapeHtml(x.summary)}</b><p>${escapeHtml(x.original||'')}</p><small>Counter-evidence found by semantic retrieval</small></div>`).join(''):'<div class="demo-counter">No counter-evidence surfaced.</div>';
  setJudgeStep(2);say('Judge Demo · AI challenged itself');
}

async function demoRename(){
  const label='Having control over my own choices';
  const d=await api(`/api/v1/dna/${userId}/strands/${currentStrand}/rename`,{method:'POST',body:JSON.stringify({user_label:label})});
  demoEl('demoRenameOwnership').innerHTML=demoOwnership(d.ai_label,d.user_label);
  demoEl('demoRenameMessage').textContent='The AI’s original label stays traceable. The user’s words now have authority.';
  compassStrandId=currentStrand;
  setJudgeStep(3);say('Judge Demo · defined by Maya');
}

async function demoCompass(){
  const r=await api(`/api/v1/compass/${userId}/reflect`,{method:'POST',body:JSON.stringify({chapter_id:chapterId,strand_id:currentStrand,focus:{}})});
  demoEl('demoCompassOwnership').innerHTML=demoOwnership(r.ai_original_label,r.user_defined_label);
  demoEl('demoCompassQuestion').textContent=r.text;
  demoEl('demoCompassBoundary').textContent=r.boundary||r.note;
  setJudgeStep(4);say('Judge Demo · one question, then silence');
}

async function demoPreviewDelete(){
  const id=judgeDemo.delete_candidate_evidence_id;
  const impact=await api(`/api/v1/vault/${userId}/evidence/${id}/impact`);
  demoEl('demoDeleteEvidence').innerHTML=`<b>${escapeHtml(impact.evidence.summary)}</b><p>${escapeHtml(impact.evidence.original||'')}</p>`;
  const affected=impact.affected_patterns.find(x=>x.pattern_id===currentPattern)||impact.affected_patterns[0];
  demoEl('demoDeleteImpact').innerHTML=affected?`${demoOwnership(affected.ai_label,affected.user_label)}<p>This reflection currently contributes <b>${escapeHtml(affected.relationship)}</b> evidence to a <b>${escapeHtml(affected.pattern_status)}</b> pattern with <b>${affected.support_count}</b> supporting clues.</p>`:'<p>No affected pattern.</p>';
  setJudgeStep(5);say('Judge Demo · deletion impact preview');
}

async function demoDeleteAndWeaken(){
  const id=judgeDemo.delete_candidate_evidence_id;
  const d=await api(`/api/v1/vault/${userId}/evidence/${id}/with-impact`,{method:'DELETE'});
  const change=d.changes.find(x=>x.pattern_id===currentPattern)||d.changes[0];
  if(!change){throw new Error('No pattern change was returned')}
  demoEl('demoWeakenOwnership').innerHTML=demoOwnership(change.after.ai_label,change.after.user_label);
  demoEl('demoBeforeStatus').textContent=change.before.pattern_status;
  demoEl('demoBeforeSupport').textContent=`${change.before.support_count} supporting clues`;
  demoEl('demoAfterStatus').textContent=change.after.pattern_status;
  demoEl('demoAfterSupport').textContent=`${change.after.support_count} supporting clues`;
  demoEl('demoWeakenMessage').textContent=change.message;
  demoEl('demoOwnershipPreserved').textContent=change.ownership_preserved?'Your definition stayed yours; only the AI evidence state changed.':'Ownership state changed.';
  setJudgeStep(6);say('Judge Demo · DNA recalculated');
}

demoEl('startJudgeDemo').onclick=startJudgeDemo;
demoEl('demoRevealBtn').onclick=demoRevealDNA;
demoEl('demoChallengeBtn').onclick=demoChallenge;
demoEl('demoRenameBtn').onclick=demoRename;
demoEl('demoCompassBtn').onclick=demoCompass;
demoEl('demoDeletePreviewBtn').onclick=demoPreviewDelete;
demoEl('demoDeleteBtn').onclick=demoDeleteAndWeaken;
