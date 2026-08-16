let pendingVaultEvidenceId=null;

function vaultStatusLabel(value='unknown'){
  return String(value).replaceAll('_',' ');
}

function ownershipTrail(item){
  const ai=escapeHtml(item.ai_label||'AI hypothesis');
  if(item.user_label){
    return `<div class="vault-owner-trail"><span class="vault-owner ai-owner"><small>AI NOTICED</small><b>${ai}</b></span><span class="vault-owner-arrow" aria-hidden="true">→</span><span class="vault-owner human-owner"><small>YOU DEFINED</small><b>${escapeHtml(item.user_label)}</b></span></div>`;
  }
  return `<div class="vault-owner-trail"><span class="vault-owner ai-owner"><small>AI HYPOTHESIS</small><b>${ai}</b></span></div>`;
}

function closeVaultDoor(){
  $('#vaultDoor').classList.remove('open');
  $('#vaultDoor').setAttribute('aria-label','A closed private memory vault');
}

function openVaultDoor(memoryCount){
  $('#vaultDoor').classList.add('open');
  $('#vaultDoor').setAttribute('aria-label',`An open private memory vault containing ${memoryCount} stored items`);
  $('#vaultCount').textContent=`${memoryCount} memory item${memoryCount===1?'':'s'} visible · every purpose is labelled`;
}

async function refreshVault(){
  if(!needUser()){
    closeVaultDoor();
    return;
  }
  const button=$('#refreshVault');
  await runButtonAction(button,'Unlocking your memory…',async()=>{
    const vault=await api(`/api/v1/vault/${userId}/inference-map`);
    const evidence=vault.self_discovery||[];
    const dna=vault.dna||[];
    const entertainment=vault.entertainment||[];
    openVaultDoor(evidence.length+dna.length+entertainment.length);

    $('#vaultData').innerHTML=`
      <section id="vaultImpactStory" class="vault-impact-story hidden" aria-live="polite" tabindex="-1"></section>
      <div class="vault-principle"><span>PRIVACY IS PART OF THE INTELLIGENCE</span><b>${escapeHtml(vault.principle||'If a memory disappears, its influence must disappear with it.')}</b></div>
      <div class="memory-corridor">
        <section class="memory-drawer entertainment-drawer" aria-labelledby="entertainmentDrawerTitle">
          <div class="drawer-handle" aria-hidden="true"></div>
          <div class="drawer-heading"><span>DRAWER A · JUST FOR FAMILIARITY</span><h3 id="entertainmentDrawerTitle">Things you enjoy</h3><p>Useful for play. Permanently forbidden from Human DNA.</p></div>
          <div class="drawer-contents">
            ${entertainment.map(item=>`<article class="vault-memory"><div><small>${escapeHtml(item.purpose)}</small><b>${escapeHtml(item.label)}</b></div><span class="purpose-tag">DNA access: ${item.dna_allowed?'allowed':'denied'}</span></article>`).join('')||'<p class="soft-copy">Nothing is stored in this drawer yet.</p>'}
          </div>
        </section>

        <section class="memory-drawer dna-drawer" aria-labelledby="dnaDrawerTitle">
          <div class="drawer-handle" aria-hidden="true"></div>
          <div class="drawer-heading"><span>DRAWER B · MEANING YOU CHOSE TO EXPLORE</span><h3 id="dnaDrawerTitle">Current Human DNA</h3><p>Your wording and the AI evidence state remain visibly separate.</p></div>
          <div class="drawer-contents">
            ${dna.map(item=>`<article class="vault-dna-card ${item.user_label?'human-owned':'ai-owned'}">${ownershipTrail(item)}<div class="vault-strength"><span>Evidence state</span><b>${escapeHtml(vaultStatusLabel(item.pattern_status))}</b><small>${item.support_count} supporting · ${item.contradiction_count} challenging</small></div></article>`).join('')||'<p class="soft-copy">No Human DNA patterns have surfaced.</p>'}
          </div>
        </section>
      </div>

      <section class="memory-drawer evidence-vault" aria-labelledby="evidenceDrawerTitle">
        <div class="drawer-handle" aria-hidden="true"></div>
        <div class="vault-section-head"><div class="drawer-heading"><span>DRAWER C · SOURCE MATERIAL</span><h3 id="evidenceDrawerTitle">Your self-discovery reflections</h3><p>Inspect the inference link before you decide whether to forget it.</p></div><span>${evidence.length} stored clue${evidence.length===1?'':'s'}</span></div>
        <div class="evidence-stack">
          ${evidence.map(item=>{
            const affect=item.affects?.[0];
            const impact=affect?`Supports <b>${escapeHtml(affect.display_label)}</b> · currently ${escapeHtml(vaultStatusLabel(affect.pattern_status))}`:'Not currently linked to a surfaced Human DNA pattern';
            return `<article class="vault-evidence-card"><div class="vault-evidence-copy"><span class="evidence-kind">${escapeHtml(item.experience_type||'reflection')} · ${escapeHtml(item.evidence_type)}</span><b>${escapeHtml(item.concept)}</b><p>${escapeHtml(item.summary)}</p><small>${impact}</small></div><div class="vault-evidence-actions"><button type="button" class="quiet-button impact-btn" data-impact="${escapeHtml(item.id)}" aria-label="See impact of ${escapeHtml(item.concept)}">See impact</button><button type="button" class="delete delete-impact" data-delete-impact="${escapeHtml(item.id)}" aria-label="Review deletion impact for ${escapeHtml(item.concept)}">Forget reflection</button></div></article>`;
          }).join('')||'<p class="soft-copy">No self-discovery evidence is stored.</p>'}
        </div>
      </section>`;

    $$('.impact-btn[data-impact]').forEach(item=>item.addEventListener('click',()=>previewVaultImpact(item.dataset.impact)));
    $$('.delete-impact[data-delete-impact]').forEach(item=>item.addEventListener('click',()=>previewVaultImpact(item.dataset.deleteImpact,true)));
    say('Vault · every memory and inference link is visible');
  });
}

async function previewVaultImpact(id,readyToDelete=false){
  try{
    const data=await api(`/api/v1/vault/${userId}/evidence/${id}/impact`);
    pendingVaultEvidenceId=id;
    const box=$('#vaultImpactStory');
    box.classList.remove('hidden','impact-complete');
    const affected=data.affected_patterns||[];
    box.innerHTML=`
      <div class="impact-kicker">BEFORE YOU FORGET</div>
      <h3>This is what the reflection currently influences.</h3>
      <div class="impact-evidence"><span>REFLECTION</span><b>${escapeHtml(data.evidence.summary)}</b><small>${escapeHtml(data.evidence.original||'')}</small></div>
      ${affected.length?affected.map(item=>`<div class="impact-link"><div class="impact-line" aria-hidden="true"></div>${ownershipTrail(item)}<div class="impact-state"><span>Current evidence state</span><b>${escapeHtml(vaultStatusLabel(item.pattern_status))}</b><small>${item.support_count} supporting clue(s)</small></div></div>`).join(''):'<div class="no-counter"><b>No surfaced Human DNA pattern currently depends on this clue.</b></div>'}
      <p class="trust-note">${escapeHtml(data.warning)}</p>
      <div class="impact-actions"><button id="cancelImpact" type="button" class="quiet-button">Keep it</button><button id="confirmImpactDelete" type="button" class="delete">Delete reflection &amp; recalculate DNA</button></div>`;
    $('#cancelImpact').addEventListener('click',()=>{
      box.classList.add('hidden');
      pendingVaultEvidenceId=null;
      $('#refreshVault').focus();
    });
    $('#confirmImpactDelete').addEventListener('click',confirmVaultDeletion);
    box.scrollIntoView({behavior:reduceMotion?'auto':'smooth',block:'center'});
    box.focus?.({preventScroll:true});
    if(readyToDelete)say('Vault · review the influence before deletion');
  }catch(error){handleError(error,'The Vault could not trace this reflection')}
}

async function confirmVaultDeletion(){
  if(!pendingVaultEvidenceId)return;
  const button=$('#confirmImpactDelete');
  button.disabled=true;
  button.setAttribute('aria-busy','true');
  button.textContent='Recalculating Human DNA…';
  try{
    const data=await api(`/api/v1/vault/${userId}/evidence/${pendingVaultEvidenceId}/with-impact`,{method:'DELETE'});
    const box=$('#vaultImpactStory');
    box.classList.add('impact-complete');
    const changes=data.changes||[];
    box.innerHTML=`
      <div class="impact-kicker">DNA RECALCULATED</div>
      <h3>The deleted reflection no longer has a vote.</h3>
      <div class="impact-evidence deleted"><span>FORGOTTEN</span><b>${escapeHtml(data.deleted.summary)}</b></div>
      ${changes.length?changes.map(change=>`<div class="before-after">${ownershipTrail(change.after)}<div class="state-change"><div><small>BEFORE</small><b>${escapeHtml(vaultStatusLabel(change.before.pattern_status))}</b><span>${change.before.support_count} supporting</span></div><div class="state-arrow" aria-hidden="true">→</div><div class="after-state"><small>AFTER</small><b>${escapeHtml(vaultStatusLabel(change.after.pattern_status))}</b><span>${change.after.support_count} supporting</span></div></div><p>${escapeHtml(change.message)}</p><small class="ownership-preserved">${change.ownership_preserved?'Your definition stayed yours; only the AI evidence state changed.':'Ownership state also changed.'}</small></div>`).join(''):'<p class="soft-copy">No surfaced pattern changed, but the reflection has still been removed from future inference.</p>'}
      <p class="trust-note">${escapeHtml(data.principle)}</p>
      <button id="closeImpact" type="button" class="quiet-button">Return to my memory</button>`;
    $('#closeImpact').addEventListener('click',()=>refreshVault());
    pendingVaultEvidenceId=null;
    await refreshDNA();
    say(changes.some(change=>change.changed)?'Vault · Human DNA weakened because evidence was removed':'Vault · reflection forgotten');
    $('#closeImpact').focus({preventScroll:true});
  }catch(error){
    handleError(error,'The reflection could not be deleted');
    button.disabled=false;
    button.removeAttribute('aria-busy');
    button.textContent='Delete reflection & recalculate DNA';
  }
}

$('#refreshVault').addEventListener('click',refreshVault);
