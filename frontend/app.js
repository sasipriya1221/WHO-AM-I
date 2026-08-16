let userId=null,chapterId=null,currentPattern=null,currentStrand=null,compassStrandId=null,lastBlindSpot=null;
let mirrorStage=0;
let dnaFragmentCount=0;

const $=selector=>document.querySelector(selector);
const $$=selector=>[...document.querySelectorAll(selector)];
const reduceMotion=window.matchMedia('(prefers-reduced-motion: reduce)').matches;
const viewTitles={portal:'WHO AM I?',mirror:'Meet Yourself',dna:'Follow the Clues',compass:'Where Are You Going?',vault:'Your Story. Your Control.',demo:'Judge Path'};

async function api(path,opts={}){
  const response=await fetch(path,{headers:{'Content-Type':'application/json'},...opts});
  if(!response.ok){
    let body={};
    try{body=await response.json()}catch{}
    throw new Error(body.detail||`Request failed (${response.status})`);
  }
  return response.json();
}

function escapeHtml(value=''){
  return String(value).replace(/[&<>'"]/g,character=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#039;','"':'&quot;'}[character]));
}

function say(message,state='ready'){
  const status=$('#status');
  status.textContent=message;
  status.dataset.state=state;
}

function handleError(error,context='Something went wrong'){
  const message=error?.message||context;
  say(`${context}: ${message}`,'error');
  console.error(error);
}

function needUser(){
  if(userId)return true;
  say('Begin in Mirror so this journey has a name.','attention');
  setView('mirror',{focusSelector:'#name'});
  return false;
}

async function runButtonAction(button,busyText,action){
  const previous=button.textContent;
  button.disabled=true;
  button.setAttribute('aria-busy','true');
  button.textContent=busyText;
  try{return await action()}
  catch(error){handleError(error);return null}
  finally{
    button.disabled=false;
    button.removeAttribute('aria-busy');
    button.textContent=previous;
  }
}

function setView(id,{focus=true,focusSelector=null}={}){
  const target=document.getElementById(id);
  if(!target)return;

  $$('[data-view]').forEach(control=>{
    const active=control.dataset.view===id;
    control.classList.toggle('active',active);
    if(control.closest('.journey-links')){
      if(active)control.setAttribute('aria-current','page');
      else control.removeAttribute('aria-current');
    }
  });
  $$('.view').forEach(view=>{
    const active=view.id===id;
    view.classList.toggle('active',active);
    view.setAttribute('aria-hidden',String(!active));
  });
  document.body.dataset.world=id;
  document.title=`${viewTitles[id]||'WHO AM I?'} · WHO AM I?`;
  $('#journeyNav').classList.remove('open');
  $('#menuToggle').setAttribute('aria-expanded','false');
  $('#menuToggle .sr-only').textContent='Open journey navigation';
  window.scrollTo({top:0,behavior:reduceMotion?'auto':'smooth'});

  if(id==='dna'&&userId)refreshDNA().catch(error=>handleError(error,'The DNA room could not refresh'));
  if(focus){
    window.requestAnimationFrame(()=>{
      const focusTarget=focusSelector?target.querySelector(focusSelector):target;
      focusTarget?.focus({preventScroll:true});
    });
  }
}

$$('[data-view]').forEach(control=>control.addEventListener('click',event=>{
  if(control.tagName==='A')return;
  event.preventDefault();
  setView(control.dataset.view,{focusSelector:control.dataset.focus||null});
}));

$('#menuToggle').addEventListener('click',()=>{
  const open=$('#journeyNav').classList.toggle('open');
  $('#menuToggle').setAttribute('aria-expanded',String(open));
  $('#menuToggle .sr-only').textContent=open?'Close journey navigation':'Open journey navigation';
});

document.addEventListener('keydown',event=>{
  if(event.key==='Escape'&&$('#journeyNav').classList.contains('open')){
    $('#journeyNav').classList.remove('open');
    $('#menuToggle').setAttribute('aria-expanded','false');
    $('#menuToggle .sr-only').textContent='Open journey navigation';
    $('#menuToggle').focus();
  }
});

function setMirrorStage(stage,label){
  mirrorStage=Math.max(mirrorStage,stage);
  const values=[0,34,68,100];
  const pieceCount=mirrorStage*4;
  const puzzle=$('#mirrorPuzzle');
  puzzle.classList.remove('stage-1','stage-2','stage-3');
  if(mirrorStage)puzzle.classList.add(`stage-${mirrorStage}`);
  $$('.mirror-shard').forEach((shard,index)=>shard.classList.toggle('revealed',index<pieceCount));
  const value=values[mirrorStage];
  $('#mirrorProgress').setAttribute('aria-valuenow',String(value));
  $('#mirrorProgress span').style.width=`${value}%`;
  $('#mirrorMeterLabel').textContent=label||['The glass is waiting','A name enters the reflection','Familiar details find their place','The mirror knows enough to be kind'][mirrorStage];
  puzzle.setAttribute('aria-label',`A mirror puzzle that is ${value} percent complete`);
  $$('.story-step').forEach(step=>{
    const stepNumber=Number(step.dataset.mirrorStep);
    step.classList.toggle('complete',stepNumber<=mirrorStage);
    step.classList.toggle('active',stepNumber===Math.min(mirrorStage+1,3));
  });
}

$('#identityForm').addEventListener('submit',async event=>{
  event.preventDefault();
  const button=$('#start');
  await runButtonAction(button,'Opening the mirror…',async()=>{
    const name=$('#name').value.trim()||'Maya';
    const emailName=name.toLowerCase().replace(/[^a-z0-9]+/g,'.').replace(/^\.|\.$/g,'')||'maya';
    const user=await api('/api/v1/users/demo',{method:'POST',body:JSON.stringify({display_name:name,email:`${emailName}@demo.local`})});
    userId=user.id;
    $('#hello').innerHTML=`<p>Hey ${escapeHtml(name)}. One piece is clear now.</p>`;
    setMirrorStage(1);
    say('Mirror · a name has entered the reflection');
    $('#interestName').focus();
  });
});

$('#interestForm').addEventListener('submit',async event=>{
  event.preventDefault();
  if(!needUser())return;
  const interest=$('#interestName').value.trim();
  if(!interest){
    say('Mirror is listening for one thing you enjoy.','attention');
    $('#interestName').focus();
    return;
  }
  await runButtonAction($('#saveInterest'),'Remembering…',async()=>{
    const savedInterest=await api(`/api/v1/mirror/${userId}/interests`,{method:'POST',body:JSON.stringify({category:$('#interestType').value,name:interest})});
    setMirrorStage(2);
    say('Mirror remembers this for play—not for Happiness DNA');
    await loadGame(savedInterest.id);
  });
});

async function loadGame(interestId=null){
  if(!needUser())return;
  try{
    const suffix=interestId?`?interest_id=${encodeURIComponent(interestId)}`:'';
    const game=await api(`/api/v1/mirror/${userId}/game${suffix}`);
    const entertainmentOnly=game.purpose==='entertainment'&&game.dna_allowed===false;
    if(!entertainmentOnly)throw new Error('Mirror refused a response without the entertainment-only boundary');
    $('#game').innerHTML=`<div class="mini-game-meta"><span>${escapeHtml((game.interaction||'play').replaceAll('_',' '))}</span><span>Entertainment only</span></div><b>${escapeHtml(game.title)}</b><p>${escapeHtml(game.question)}</p><div class="mini-answer-grid">${(game.options||[]).map(option=>`<button type="button" class="mini-answer">${escapeHtml(option)}</button>`).join('')}</div><p id="gameFeedback" class="mini-game-feedback" role="status" aria-live="polite"></p><p class="tiny">${escapeHtml(game.note||'')}</p>`;
    const answers=$$('#game .mini-answer');
    answers.forEach(answer=>answer.addEventListener('click',()=>{
      answers.forEach(item=>item.classList.toggle('selected',item===answer));
      const feedback=$('#gameFeedback');
      if(game.answer)feedback.textContent=answer.textContent===game.answer?'Nice play — that clears this round.':'Plot twist. Try another move or keep your wonderfully chaotic answer.';
      else feedback.textContent='Choice locked in. Tiny challenge complete.';
      setMirrorStage(3);
      say('Mirror · playful moment complete, with no DNA created');
    }));
  }catch(error){handleError(error,'Mirror could not find a question')}
}

$('#loadGame').addEventListener('click',()=>loadGame());

$('#consent').addEventListener('click',async()=>{
  if(!needUser())return;
  const opened=await runButtonAction($('#consent'),'Opening the room…',async()=>{
    await api(`/api/v1/dna/${userId}/consent`,{method:'POST',body:JSON.stringify({consent:true})});
    return true;
  });
  if(!opened)return;
  $('#dnaExperienceFieldset').disabled=false;
  $('#dnaRoomVisual').classList.add('is-consented');
  $('#consent').setAttribute('aria-pressed','true');
  $('#consent').textContent='Consent active · the room is yours';
  $('#dnaStrengthLabel').textContent='The room is open. Every accepted clue will add a fragment before any pattern appears.';
  $('#dnaRoomVisual').setAttribute('aria-label','An open virtual room with a faint helix waiting for consented clues');
  say('Happiness DNA · you chose to explore');
  await refreshDNA();
  $('#room').focus();
});

$$('.submitExp').forEach(button=>button.addEventListener('click',async()=>{
  if(!needUser())return;
  const type=button.dataset.exp;
  const input={empty_room:$('#room'),future_me:$('#future'),reflection:$('#reflection')}[type];
  const reflection=input.value.trim();
  if(!reflection){
    say('Place a reflection in the room first.','attention');
    input.focus();
    return;
  }
  await runButtonAction(button,'Reading this clue…',async()=>{
    const result=await api(`/api/v1/dna/${userId}/experiences`,{method:'POST',body:JSON.stringify({experience_type:type,input_mode:'text',response:{reflection},consent_for_analysis:true})});
    await refreshDNA({animateFragments:result.evidence_created>0});
    say(result.evidence_created?'Happiness DNA · + 1 clue discovered':'Happiness DNA · no reliable clue extracted yet');
  });
}));

$('#refreshDNA').addEventListener('click',()=>refreshDNA().catch(error=>handleError(error,'The DNA room could not refresh')));

function acceptedClueExperiences(evidenceItems=[]){
  const experiences=new Map();
  evidenceItems.forEach(item=>{
    if(item.experience_id&&!experiences.has(item.experience_id))experiences.set(item.experience_id,item);
  });
  return [...experiences.values()];
}

function syncDnaFragments(evidenceItems=[],{animateNewest=false}={}){
  const experiences=acceptedClueExperiences(evidenceItems);
  const nextCount=experiences.length;
  const previousCount=dnaFragmentCount;
  const previousSegments=Math.min(12,previousCount*4);
  const visibleSegments=Math.min(12,nextCount*4);

  $$('#dnaHelix i').forEach((fragment,index)=>{
    fragment.classList.toggle('fragment-visible',index<visibleSegments);
    fragment.classList.toggle('fragment-new',animateNewest&&index>=previousSegments&&index<visibleSegments);
  });
  $('#dnaFragmentLedger').innerHTML=experiences.map((item,index)=>`<span class="${animateNewest&&index>=previousCount?'fragment-new':''}" title="Clue ${index+1}: ${escapeHtml(item.experience_type||'reflection')}"></span>`).join('');
  $('#dnaFragmentStatus').textContent=nextCount===0
    ? 'HAPPINESS DNA · NO CLUES YET'
    : nextCount===1
      ? 'HAPPINESS DNA · + 1 CLUE DISCOVERED · 4 FRAGMENTS'
      : nextCount===2
        ? 'HAPPINESS DNA · + ANOTHER CLUE · 8 FRAGMENTS'
        : `HAPPINESS DNA · 12 FRAGMENTS · ${nextCount} CLUES CONNECTED`;
  $('#dnaRoomVisual').dataset.clueCount=String(nextCount);
  $('#dnaRoomVisual').dataset.visibleFragments=String(visibleSegments);
  dnaFragmentCount=nextCount;
  return {clueCount:nextCount,grew:nextCount>previousCount};
}

function syncDnaRoom(strands,patterns,clueCount){
  const room=$('#dnaRoomVisual');
  room.classList.remove('strength-emerging','strength-repeated','is-questioned','is-human');
  const hasHuman=strands.some(strand=>strand.status==='user_defined');
  const hasQuestioned=strands.some(strand=>strand.status==='questioned')||patterns.some(pattern=>pattern.status==='questioned');
  const hasRepeated=patterns.some(pattern=>pattern.status==='repeated');
  if(hasRepeated)room.classList.add('strength-repeated');
  else if(clueCount)room.classList.add('strength-emerging');
  room.classList.toggle('is-questioned',hasQuestioned);
  room.classList.toggle('is-human',hasHuman);

  if(!strands.length){
    $('#dnaStrengthLabel').textContent=clueCount
      ? `${clueCount} accepted clue${clueCount===1?' is':'s are'} forming the helix. No pattern has been inferred.`
      : room.classList.contains('is-consented')?'The room is open. Your first clue can begin the helix.':'The room is quiet. Nothing has been inferred.';
    $('#dnaInferenceMessage').textContent=clueCount===0?'Not enough independent clues yet.':clueCount===1?'+ 1 clue discovered.':`${clueCount} clue fragments are forming.`;
    $('#dnaInferenceDetail').textContent=clueCount<3
      ? `${3-clueCount} more independent clue${3-clueCount===1?' is':'s are'} needed before a repeated pattern is even possible.`
      : 'The clues have not met every repetition rule yet. “I don’t know yet” is better than invented certainty.';
    room.setAttribute('aria-label',`A virtual room with ${clueCount} visible Happiness DNA clue fragments and no inferred pattern`);
    return;
  }
  const state=hasHuman?'solid in language you defined':hasQuestioned?'destabilized by counter-evidence':hasRepeated?'brightening through repeated evidence':'forming from independent clues';
  $('#dnaStrengthLabel').textContent=`The helix is ${state}.`;
  $('#dnaInferenceMessage').textContent='Something may be repeating.';
  $('#dnaInferenceDetail').textContent='Only now—after the evidence threshold—can the AI offer a contestable hypothesis.';
  room.setAttribute('aria-label',`A virtual room with ${clueCount} visible Happiness DNA clue fragments and a helix ${state}`);
}

async function refreshDNA({animateFragments=false}={}){
  if(!userId)return;
  const [strands,patterns,inferenceMap]=await Promise.all([
    api(`/api/v1/dna/${userId}/strands`),
    api(`/api/v1/dna/${userId}/patterns`),
    api(`/api/v1/vault/${userId}/inference-map`),
  ]);
  const fragmentState=syncDnaFragments(inferenceMap.self_discovery||[],{animateNewest:animateFragments});
  const patternsById=new Map(patterns.map(pattern=>[pattern.id,pattern]));
  const surfaced=strands.filter(strand=>{
    if(strand.status==='retired')return false;
    const patternStatus=patternsById.get(strand.pattern_id)?.status;
    return strand.status==='user_defined'||patternStatus==='repeated'||patternStatus==='questioned';
  });
  syncDnaRoom(surfaced,patterns,fragmentState.clueCount);
  if(animateFragments&&fragmentState.grew&&!reduceMotion)await new Promise(resolve=>window.setTimeout(resolve,650));
  $('#revealEmpty').classList.toggle('hidden',surfaced.length>0);
  $('#patterns').innerHTML=surfaced.map(strand=>{
    const label=strand.user_label||strand.ai_label||'Unnamed clue';
    const ownership=strand.status==='user_defined'?'Defined by you':strand.status==='questioned'?'AI hypothesis · tested against counter-evidence':'AI hypothesis · threshold reached';
    return `<button type="button" class="dna-chip ${strand.status==='user_defined'?'human':'ai'}" data-pattern="${escapeHtml(strand.pattern_id||'')}" data-strand="${escapeHtml(strand.id)}" data-label="${escapeHtml(label)}"><span aria-hidden="true">${strand.status==='user_defined'?'●':'◌'}</span><b>${escapeHtml(label)}</b><small>${ownership}</small></button>`;
  }).join('');
  $$('.dna-chip').forEach(chip=>chip.addEventListener('click',()=>openReveal(chip.dataset.pattern,chip.dataset.strand,chip.dataset.label)));
  if(currentStrand){
    const updated=surfaced.find(strand=>strand.id===currentStrand);
    if(updated)await openReveal(updated.pattern_id,updated.id,updated.user_label||updated.ai_label,false);
  }
}

async function openReveal(patternId,strandId,label,scroll=true){
  if(!patternId)return;
  currentPattern=patternId;
  currentStrand=strandId;
  const [patterns,strands]=await Promise.all([
    api(`/api/v1/dna/${userId}/patterns`),
    api(`/api/v1/dna/${userId}/strands`),
  ]);
  const pattern=patterns.find(item=>item.id===patternId);
  const strand=strands.find(item=>item.id===strandId);
  const human=strand?.status==='user_defined';
  const questioned=pattern?.status==='questioned'||strand?.status==='questioned';
  $('#revealPanel').classList.remove('hidden');
  $('#revealPanel').classList.toggle('human-defined',human);
  $('#revealLabel').textContent=label||pattern?.label||'Possible pattern';
  $('#revealStatus').textContent=(pattern?.status||'emerging').replaceAll('_',' ');
  $('#ownershipLine').textContent=human?'Defined by you. The original AI hypothesis remains traceable, but your words have authority.':'AI reflects. You decide. This hypothesis may be wrong.';
  $('#contestResult').classList.add('hidden');
  $('#contestResult').innerHTML='';
  $('#renameInput').value=human?(strand.user_label||''):'';
  $('#dnaRoomVisual').classList.toggle('is-questioned',questioned);
  $('#dnaRoomVisual').classList.toggle('is-human',human);
  resetBlindSpot();
  $('#blindSpotPanel').classList.remove('hidden');
  $('#blindQuestion').textContent='A useful reflection may live in the difference between what AI noticed and what you mean.';
  $('#blindBridge').textContent='Ask the AI to prove itself wrong or define the clue in your own words, then look again.';
  $('#blindBoundary').textContent='The AI can surface a tension. It cannot decide what that tension means.';
  if(scroll)$('#revealPanel').scrollIntoView({behavior:reduceMotion?'auto':'smooth',block:'start'});
}

$('#whyBtn').addEventListener('click',async()=>{
  if(!currentPattern)return;
  await runButtonAction($('#whyBtn'),'Tracing evidence…',async()=>{
    const data=await api(`/api/v1/dna/${userId}/patterns/${currentPattern}/why`);
    const box=$('#contestResult');
    box.classList.remove('hidden');
    box.innerHTML=`<div class="contest-heading"><strong>Why did the room notice this?</strong><span>${data.supporting.length} supporting clue(s)</span></div>${data.supporting.length?data.supporting.map((item,index)=>`<div class="evidence-line support"><span>${index+1}</span><div><b>${escapeHtml(item.summary)}</b><p>${escapeHtml(item.original||'')}</p></div></div>`).join(''):'<p class="soft-copy">There is not enough supporting evidence yet.</p>'}<p class="trust-note">Every conclusion stays traceable to experiences you intentionally shared.</p>`;
  });
});

$('#challengeBtn').addEventListener('click',async()=>{
  if(!currentPattern)return;
  await runButtonAction($('#challengeBtn'),'Trying to prove this wrong…',async()=>{
    const data=await api(`/api/v1/dna/${userId}/patterns/${currentPattern}/challenge`,{method:'POST'});
    const resultMarkup=`<div class="contest-heading"><strong>The AI tried to prove itself wrong.</strong><span>${data.status.replaceAll('_',' ')}</span></div>${data.contradicting.length?data.contradicting.map(item=>`<div class="evidence-line counter"><span aria-hidden="true">↔</span><div><b>${escapeHtml(item.summary)}</b><p>${escapeHtml(item.original||'')}</p><small>semantic similarity ${item.similarity}</small></div></div>`).join(''):'<div class="no-counter"><b>No meaningful counter-evidence surfaced yet.</b><p>That does not make the hypothesis true. It only means the current story is incomplete.</p></div>'}<p class="trust-note">${escapeHtml(data.message||'')}</p>`;
    await refreshDNA();
    const box=$('#contestResult');
    box.classList.remove('hidden');
    box.innerHTML=resultMarkup;
    $('#revealStatus').textContent=data.status.replaceAll('_',' ');
    $('#dnaRoomVisual').classList.add('is-questioned');
    await loadBlindSpot(false);
    say('Happiness DNA · the AI tried to prove itself wrong');
  });
});

$('#notMeBtn').addEventListener('click',async()=>{
  if(!currentPattern)return;
  const accepted=confirm('Reject this AI hypothesis? It will not be treated as your identity or used by Compass.');
  if(!accepted)return;
  await runButtonAction($('#notMeBtn'),'Letting it go…',async()=>{
    const data=await api(`/api/v1/dna/${userId}/patterns/${currentPattern}/not-me`,{method:'POST'});
    $('#contestResult').classList.remove('hidden');
    $('#contestResult').innerHTML=`<div class="rejected-state"><b>Not you. Understood.</b><p>${escapeHtml(data.message)}</p></div>`;
    say('Happiness DNA · AI hypothesis rejected');
    compassStrandId=null;
    lastBlindSpot=null;
    currentPattern=null;
    currentStrand=null;
    window.setTimeout(async()=>{$('#revealPanel').classList.add('hidden');await refreshDNA()},reduceMotion?0:600);
  });
});

$('#renameBtn').addEventListener('click',async()=>{
  if(!currentStrand)return;
  const value=$('#renameInput').value.trim();
  if(!value){
    say('Use your own words before defining this strand.','attention');
    $('#renameInput').focus();
    return;
  }
  await runButtonAction($('#renameBtn'),'Making your words solid…',async()=>{
    const data=await api(`/api/v1/dna/${userId}/strands/${currentStrand}/rename`,{method:'POST',body:JSON.stringify({user_label:value})});
    $('#revealLabel').textContent=data.user_label;
    $('#ownershipLine').textContent=`Defined by you. AI originally suggested “${data.ai_label||'a different label'}”.`;
    $('#revealPanel').classList.add('human-defined');
    $('#dnaRoomVisual').classList.add('is-human');
    $('#contestResult').classList.remove('hidden');
    $('#contestResult').innerHTML=`<div class="human-win"><span aria-hidden="true">●</span><div><b>${escapeHtml(data.user_label)}</b><p>The AI's label did not become your identity. Your interpretation did.</p></div></div>`;
    say('Happiness DNA · defined by you');
    await refreshDNA();
    await loadBlindSpot(false);
  });
});

function resetBlindSpot(){
  lastBlindSpot=null;
  $('#blindOwnership').innerHTML='';
  $('#toCompassBtn').classList.add('hidden');
  $('#openBlindSpotBtn').classList.remove('hidden');
}

$('#openBlindSpotBtn').addEventListener('click',()=>loadBlindSpot(true));

async function loadBlindSpot(scroll=true){
  if(!currentStrand)return;
  try{
    const data=await api(`/api/v1/dna/${userId}/strands/${currentStrand}/blind-spot`);
    lastBlindSpot=data;
    const owner=data.ownership_state;
    const ownerMarkup=owner==='user_defined'
      ? `<div class="owner-node ai-node"><span>AI NOTICED</span><b>${escapeHtml(data.ai_label)}</b></div><div class="owner-arrow" aria-hidden="true">→</div><div class="owner-node human-node"><span>YOU DEFINED</span><b>${escapeHtml(data.user_label)}</b></div>`
      : `<div class="owner-node ai-node"><span>${owner==='ai_challenged'?'AI HYPOTHESIS · TESTED AGAINST COUNTER-EVIDENCE':'AI HYPOTHESIS'}</span><b>${escapeHtml(data.ai_label)}</b></div>`;
    $('#blindOwnership').innerHTML=ownerMarkup;
    $('#blindQuestion').textContent=data.question;
    $('#blindBridge').textContent=data.bridge_text;
    $('#blindBoundary').textContent=data.boundary;
    $('#openBlindSpotBtn').classList.add('hidden');
    $('#toCompassBtn').classList.toggle('hidden',!data.can_enter_compass);
    $('#blindSpotPanel').classList.remove('hidden');
    if(scroll)$('#blindSpotPanel').scrollIntoView({behavior:reduceMotion?'auto':'smooth',block:'center'});
    say(data.can_enter_compass?'Look Again · your words are ready for Compass':'Look Again · define this in your words before Compass');
  }catch(error){handleError(error,'Look Again could not open')}
}

$('#toCompassBtn').addEventListener('click',()=>{
  if(!lastBlindSpot?.can_enter_compass||!currentStrand)return;
  compassStrandId=currentStrand;
  $('#handoffAI').textContent=lastBlindSpot.ai_label||'AI hypothesis';
  $('#handoffUser').textContent=lastBlindSpot.user_label||'Your words';
  $('#compassHandoff').classList.remove('hidden');
  setView('compass');
  say('Where Are You Going? · carrying your interpretation toward the horizon');
});

$('#chapterForm').addEventListener('submit',async event=>{
  event.preventDefault();
  if(!needUser())return;
  await runButtonAction($('#makeChapter'),'Placing this chapter…',async()=>{
    const chapter=await api(`/api/v1/compass/${userId}/chapters`,{method:'POST',body:JSON.stringify({title:$('#chapter').value.trim()||'My current chapter',description:$('#chapterDescription').value.trim()||null})});
    chapterId=chapter.id;
    say(`Compass · ${chapter.title} is on the road`);
  });
});

$('#reflect').addEventListener('click',async()=>{
  if(!chapterId){
    say('Name your current chapter before looking toward the horizon.','attention');
    $('#chapter').focus();
    return;
  }
  await runButtonAction($('#reflect'),'Looking toward the horizon…',async()=>{
    const result=await api(`/api/v1/compass/${userId}/reflect`,{method:'POST',body:JSON.stringify({chapter_id:chapterId,strand_id:compassStrandId,focus:{}})});
    $('#compassResult').innerHTML=`<div class="compass-question">${escapeHtml(result.text)}</div><p class="tiny">${escapeHtml(result.note||'')}</p>`;
    if(result.type==='question'){
      $('#compassReflection').classList.remove('hidden');
      $('#compassAIOriginal').textContent=result.ai_original_label||'AI hypothesis';
      $('#compassUserDefined').textContent=result.user_defined_label||result.strand;
      $('#compassQuestion').textContent=result.text;
      $('#compassBoundary').textContent=result.boundary||result.note||'';
      $('#compassReflection').scrollIntoView({behavior:reduceMotion?'auto':'smooth',block:'center'});
      say('Where Are You Going? · your road, your answer');
    }else{
      $('#compassReflection').classList.add('hidden');
      say('Compass · your words must lead before a question can follow','attention');
    }
  });
});

function initializeRoute(){
  const onDemoPath=window.location.pathname.replace(/\/+$/,'')==='/demo';
  const demoQuery=new URLSearchParams(window.location.search).get('demo')==='judge';
  const hashView=window.location.hash.slice(1);
  if(onDemoPath||demoQuery){
    setView('demo',{focus:false});
    say('Judge path · ready to begin');
  }
  else if(['portal','mirror','dna','compass','vault'].includes(hashView))setView(hashView,{focus:false});
  else setView('portal',{focus:false});
  setMirrorStage(0);
}

initializeRoute();
