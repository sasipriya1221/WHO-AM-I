let judgeDemo=null;
let judgeStep=0;
const demoSteps=['Experience','Happiness DNA','Prove It Wrong','Look Again','Compass','Vault','DNA weakens'];
const demoScenes=['experience','dna','challenge','rename','compass','delete','weakens'];
const demoActionIds=['demoRevealBtn','demoChallengeBtn','demoRenameBtn','demoCompassBtn','demoDeletePreviewBtn','demoDeleteBtn'];

function demoEl(id){return document.getElementById(id)}

function setJudgeActionAvailability(step){
  demoActionIds.forEach((id,index)=>{
    const control=demoEl(id);
    control.disabled=!judgeDemo||index!==step;
  });
}

function setJudgeStep(step,{focus=true}={}){
  judgeStep=step;
  document.querySelectorAll('.demo-dot').forEach((item,index)=>{
    item.classList.toggle('done',index<step);
    item.classList.toggle('active',index===step);
    if(index===step)item.setAttribute('aria-current','step');
    else item.removeAttribute('aria-current');
  });
  document.querySelectorAll('.demo-card').forEach((card,index)=>{
    const active=index===step;
    card.classList.toggle('visible',active);
    card.classList.toggle('done',index<step);
    card.setAttribute('aria-hidden',String(!active));
  });
  demoEl('demoScene').dataset.scene=demoScenes[step];
  setJudgeActionAvailability(step);
  if(focus){
    const heading=document.querySelectorAll('.demo-card')[step]?.querySelector('h3');
    if(heading){
      heading.setAttribute('tabindex','-1');
      heading.focus({preventScroll:true});
      demoEl('demoScene').scrollIntoView({behavior:reduceMotion?'auto':'smooth',block:'center'});
    }
  }
}

function demoOwnership(ai,user){
  return `<div class="ownership-demo"><div class="node"><span>AI NOTICED</span><strong>${escapeHtml(ai)}</strong></div>${user?`<div class="demo-arrow" aria-hidden="true">→</div><div class="node human"><span>YOU DEFINED</span><strong>${escapeHtml(user)}</strong></div>`:''}</div>`;
}

async function startJudgeDemo(){
  const button=demoEl('startJudgeDemo');
  const result=await runButtonAction(button,'Building Maya’s story…',async()=>api('/api/v1/demo/seed',{method:'POST'}));
  if(!result)return;
  judgeDemo=result;
  userId=judgeDemo.user.id;
  currentPattern=judgeDemo.pattern.id;
  currentStrand=judgeDemo.strand.id;
  chapterId=judgeDemo.chapter.id;
  compassStrandId=null;
  demoEl('demoMaya').textContent=judgeDemo.user.display_name;
  demoEl('demoExperiences').innerHTML=judgeDemo.experiences.map((item,index)=>`<div class="demo-exp clue-fragment"><span>+ CLUE ${index+1} · ${escapeHtml(item.type.replaceAll('_',' '))}</span><b>${escapeHtml(item.label)}</b><small>accepted · one Happiness DNA fragment added</small></div>`).join('');
  demoEl('demoEntertainment').innerHTML=`Mirror also remembers <b>${escapeHtml(judgeDemo.entertainment.label)}</b> — <code>purpose=${escapeHtml(judgeDemo.entertainment.purpose)}</code>, <code>dna_allowed=${judgeDemo.entertainment.dna_allowed}</code>. It is not part of this inference.`;
  demoEl('demoStartState').classList.remove('hidden');
  setJudgeStep(0,{focus:false});
  demoEl('demoRevealBtn').focus();
  say('Judge path · Maya is ready at Experience');
}

async function demoRevealDNA(){
  if(!judgeDemo)return;
  const button=demoEl('demoRevealBtn');
  await runButtonAction(button,'Tracing the clues…',async()=>{
    const [why,patterns]=await Promise.all([
      api(`/api/v1/dna/${userId}/patterns/${currentPattern}/why`),
      api(`/api/v1/dna/${userId}/patterns`),
    ]);
    const pattern=patterns.find(item=>item.id===currentPattern);
    demoEl('demoDnaOwnership').innerHTML=demoOwnership(pattern.label,null);
    demoEl('demoDnaState').textContent=`${pattern.status.toUpperCase()} · ${pattern.support} independent supporting clues`;
    demoEl('demoWhyEvidence').innerHTML=why.supporting.map((item,index)=>`<div class="demo-evidence"><span>${index+1}</span><div><b>${escapeHtml(item.summary)}</b><small>${escapeHtml(item.original||'')}</small></div></div>`).join('');
    setJudgeStep(1);
    say('Judge path · three fragments connected before a Happiness DNA hypothesis surfaced');
  });
  setJudgeActionAvailability(judgeStep);
}

async function demoChallenge(){
  if(!judgeDemo)return;
  await runButtonAction(demoEl('demoChallengeBtn'),'Trying to prove this wrong…',async()=>{
    const data=await api(`/api/v1/dna/${userId}/patterns/${currentPattern}/challenge`,{method:'POST'});
    demoEl('demoChallengeState').textContent=data.status.replaceAll('_',' ');
    demoEl('demoCounters').innerHTML=data.contradicting.length?data.contradicting.map(item=>`<div class="demo-counter"><b>${escapeHtml(item.summary)}</b><p>${escapeHtml(item.original||'')}</p><small>Counter-evidence found by semantic retrieval</small></div>`).join(''):'<div class="demo-counter">No counter-evidence surfaced.</div>';
    setJudgeStep(2);
    say('Judge path · the AI tried to prove itself wrong');
  });
  setJudgeActionAvailability(judgeStep);
}

async function demoRename(){
  if(!judgeDemo)return;
  await runButtonAction(demoEl('demoRenameBtn'),'Giving authority to Maya…',async()=>{
    const label='Having control over my own choices';
    const data=await api(`/api/v1/dna/${userId}/strands/${currentStrand}/rename`,{method:'POST',body:JSON.stringify({user_label:label})});
    demoEl('demoRenameOwnership').innerHTML=demoOwnership(data.ai_label,data.user_label);
    demoEl('demoRenameMessage').textContent='The AI’s original label stays traceable. The human-defined meaning now has authority.';
    compassStrandId=currentStrand;
    setJudgeStep(3);
    say('Judge path · Look Again made Maya’s words authoritative');
  });
  setJudgeActionAvailability(judgeStep);
}

async function demoCompass(){
  if(!judgeDemo)return;
  await runButtonAction(demoEl('demoCompassBtn'),'Opening the horizon…',async()=>{
    const result=await api(`/api/v1/compass/${userId}/reflect`,{method:'POST',body:JSON.stringify({chapter_id:chapterId,strand_id:currentStrand,focus:{}})});
    demoEl('demoCompassOwnership').innerHTML=demoOwnership(result.ai_original_label,result.user_defined_label);
    demoEl('demoCompassQuestion').textContent=result.text;
    demoEl('demoCompassBoundary').textContent=result.boundary||result.note;
    setJudgeStep(4);
    say('Judge path · Your road. Your answer. Compass stopped at one question');
  });
  setJudgeActionAvailability(judgeStep);
}

async function demoPreviewDelete(){
  if(!judgeDemo)return;
  await runButtonAction(demoEl('demoDeletePreviewBtn'),'Tracing this memory…',async()=>{
    const id=judgeDemo.delete_candidate_evidence_id;
    const impact=await api(`/api/v1/vault/${userId}/evidence/${id}/impact`);
    demoEl('demoDeleteEvidence').innerHTML=`<span>REFLECTION</span><b>${escapeHtml(impact.evidence.summary)}</b><p>${escapeHtml(impact.evidence.original||'')}</p>`;
    const affected=impact.affected_patterns.find(item=>item.pattern_id===currentPattern)||impact.affected_patterns[0];
    demoEl('demoDeleteImpact').innerHTML=affected?`${demoOwnership(affected.ai_label,affected.user_label)}<p>This reflection currently contributes <b>${escapeHtml(affected.relationship)}</b> evidence to a <b>${escapeHtml(affected.pattern_status)}</b> pattern with <b>${affected.support_count}</b> supporting clues.</p>`:'<p>No affected pattern.</p>';
    setJudgeStep(5);
    say('Judge path · Your Story. Your Control. Vault exposed the inference link before deletion');
  });
  setJudgeActionAvailability(judgeStep);
}

async function demoDeleteAndWeaken(){
  if(!judgeDemo)return;
  await runButtonAction(demoEl('demoDeleteBtn'),'Deleting and recalculating…',async()=>{
    const id=judgeDemo.delete_candidate_evidence_id;
    const data=await api(`/api/v1/vault/${userId}/evidence/${id}/with-impact`,{method:'DELETE'});
    const change=data.changes.find(item=>item.pattern_id===currentPattern)||data.changes[0];
    if(!change)throw new Error('No pattern change was returned');
    demoEl('demoWeakenOwnership').innerHTML=demoOwnership(change.after.ai_label,change.after.user_label);
    demoEl('demoBeforeStatus').textContent=change.before.pattern_status;
    demoEl('demoBeforeSupport').textContent=`${change.before.support_count} supporting clues`;
    demoEl('demoAfterStatus').textContent=change.after.pattern_status;
    demoEl('demoAfterSupport').textContent=`${change.after.support_count} supporting clues`;
    demoEl('demoWeakenMessage').textContent=change.message;
    demoEl('demoOwnershipPreserved').textContent=change.ownership_preserved?'Your meaning was yours. Only my evidence changed.':'Ownership state changed.';
    setJudgeStep(6);
    await refreshDNA();
    say('Judge path complete · deleted evidence lost its influence');
  });
  setJudgeActionAvailability(judgeStep);
}

demoEl('startJudgeDemo').addEventListener('click',startJudgeDemo);
demoEl('demoRevealBtn').addEventListener('click',demoRevealDNA);
demoEl('demoChallengeBtn').addEventListener('click',demoChallenge);
demoEl('demoRenameBtn').addEventListener('click',demoRename);
demoEl('demoCompassBtn').addEventListener('click',demoCompass);
demoEl('demoDeletePreviewBtn').addEventListener('click',demoPreviewDelete);
demoEl('demoDeleteBtn').addEventListener('click',demoDeleteAndWeaken);

setJudgeStep(0,{focus:false});
