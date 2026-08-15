let pendingVaultEvidenceId=null;

function vaultStatusLabel(value='unknown'){
  return String(value).replaceAll('_',' ');
}

function ownershipTrail(item){
  const ai=escapeHtml(item.ai_label||'AI hypothesis');
  if(item.user_label){
    return `<div class="vault-owner-trail"><span class="vault-owner ai-owner"><small>AI NOTICED</small><b>${ai}</b></span><span class="vault-owner-arrow">→</span><span class="vault-owner human-owner"><small>YOU DEFINED</small><b>${escapeHtml(item.user_label)}</b></span></div>`;
  }
  return `<div class="vault-owner-trail"><span class="vault-owner ai-owner"><small>AI HYPOTHESIS</small><b>${ai}</b></span></div>`;
}

async function refreshVault(){
  if(!needUser())return;
  const v=await api(`/api/v1/vault/${userId}/inference-map`);
  const evidence=v.self_discovery||[];
  const dna=v.dna||[];
  $('#vaultData').innerHTML=`
    <div id="vaultImpactStory" class="vault-impact-story hidden" aria-live="polite"></div>
    <div class="vault-principle"><span>PRIVACY IS PART OF THE INTELLIGENCE</span><b>${escapeHtml(v.principle||'')}</b></div>
    <div class="vault-grid">
      <div class="vault-group vault-entertainment">
        <h3>Entertainment memory</h3>
        <p class="tiny">Useful for familiarity. Forbidden from Happiness DNA.</p>
        ${(v.entertainment||[]).map(x=>`<div class="vault-memory"><span>${escapeHtml(x.label)}</span><span class="purpose-tag">${escapeHtml(x.purpose)}</span><small>DNA access: ${x.dna_allowed?'allowed':'denied'}</small></div>`).join('')||'<p class="soft-copy">Nothing remembered here yet.</p>'}
      </div>
      <div class="vault-group vault-dna-map">
        <h3>Current DNA evidence state</h3>
        <p class="tiny">Your wording and the AI's evidence state are shown separately.</p>
        ${dna.map(x=>`<div class="vault-dna-card ${x.user_label?'human-owned':'ai-owned'}">${ownershipTrail(x)}<div class="vault-strength"><span>Evidence state</span><b>${escapeHtml(vaultStatusLabel(x.pattern_status))}</b><small>${x.support_count} supporting · ${x.contradiction_count} challenging</small></div></div>`).join('')||'<p class="soft-copy">No DNA patterns yet.</p>'}
      </div>
    </div>
    <div class="vault-group evidence-vault">
      <div class="vault-section-head"><div><h3>Your self-discovery evidence</h3><p class="tiny">Delete a reflection and the evidence graph is recalculated immediately.</p></div><span>${evidence.length} stored clue(s)</span></div>
      ${evidence.map(x=>{
        const affect=x.affects?.[0];
        const impact=affect?`Supports <b>${escapeHtml(affect.display_label)}</b> · currently ${escapeHtml(vaultStatusLabel(affect.pattern_status))}`:'Not currently linked to a surfaced DNA pattern';
        return `<div class="vault-evidence-card"><div class="vault-evidence-copy"><span class="evidence-kind">${escapeHtml(x.experience_type||'reflection')} · ${escapeHtml(x.evidence_type)}</span><b>${escapeHtml(x.concept)}</b><p>${escapeHtml(x.summary)}</p><small>${impact}</small></div><div class="vault-evidence-actions"><button class="ghost impact-btn" data-impact="${x.id}">See impact</button><button class="delete delete-impact" data-delete-impact="${x.id}">Forget reflection</button></div></div>`;
      }).join('')||'<p class="soft-copy">No self-discovery evidence stored.</p>'}
    </div>`;
  $$('.impact-btn[data-impact]').forEach(b=>b.onclick=()=>previewVaultImpact(b.dataset.impact));
  $$('.delete-impact[data-delete-impact]').forEach(b=>b.onclick=()=>previewVaultImpact(b.dataset.deleteImpact,true));
}

async function previewVaultImpact(id,readyToDelete=false){
  const d=await api(`/api/v1/vault/${userId}/evidence/${id}/impact`);
  pendingVaultEvidenceId=id;
  const box=$('#vaultImpactStory');
  box.classList.remove('hidden','impact-complete');
  const affected=d.affected_patterns||[];
  box.innerHTML=`<div class="impact-kicker">BEFORE YOU FORGET</div><h3>This is what the reflection currently influences.</h3><div class="impact-evidence"><span>REFLECTION</span><b>${escapeHtml(d.evidence.summary)}</b><small>${escapeHtml(d.evidence.original||'')}</small></div>${affected.length?affected.map(x=>`<div class="impact-link"><div class="impact-line"></div>${ownershipTrail(x)}<div class="impact-state"><span>Current evidence state</span><b>${escapeHtml(vaultStatusLabel(x.pattern_status))}</b><small>${x.support_count} supporting clue(s)</small></div></div>`).join(''):'<div class="no-counter"><b>No surfaced DNA pattern currently depends on this clue.</b></div>'}<p class="trust-note">${escapeHtml(d.warning)}</p><div class="impact-actions"><button id="cancelImpact" class="ghost">Keep it</button><button id="confirmImpactDelete" class="delete">Delete reflection & recalculate DNA</button></div>`;
  $('#cancelImpact').onclick=()=>{box.classList.add('hidden');pendingVaultEvidenceId=null};
  $('#confirmImpactDelete').onclick=confirmVaultDeletion;
  box.scrollIntoView({behavior:'smooth',block:'center'});
  if(readyToDelete)say('Vault · review the impact before deletion');
}

async function confirmVaultDeletion(){
  if(!pendingVaultEvidenceId)return;
  const button=$('#confirmImpactDelete');
  button.disabled=true;button.textContent='Recalculating…';
  try{
    const d=await api(`/api/v1/vault/${userId}/evidence/${pendingVaultEvidenceId}/with-impact`,{method:'DELETE'});
    const box=$('#vaultImpactStory');
    box.classList.add('impact-complete');
    const changes=d.changes||[];
    box.innerHTML=`<div class="impact-kicker">DNA RECALCULATED</div><h3>The deleted reflection no longer has a vote.</h3><div class="impact-evidence deleted"><span>FORGOTTEN</span><b>${escapeHtml(d.deleted.summary)}</b></div>${changes.length?changes.map(c=>`<div class="before-after">${ownershipTrail(c.after)}<div class="state-change"><div><small>BEFORE</small><b>${escapeHtml(vaultStatusLabel(c.before.pattern_status))}</b><span>${c.before.support_count} supporting</span></div><div class="state-arrow">→</div><div class="after-state"><small>AFTER</small><b>${escapeHtml(vaultStatusLabel(c.after.pattern_status))}</b><span>${c.after.support_count} supporting</span></div></div><p>${escapeHtml(c.message)}</p><small class="ownership-preserved">${c.ownership_preserved?'Your definition stayed yours; only the AI evidence state changed.':'Ownership state also changed.'}</small></div>`).join(''):'<p class="soft-copy">No surfaced pattern changed, but the reflection has still been removed from future inference.</p>'}<p class="trust-note">${escapeHtml(d.principle)}</p><button id="closeImpact" class="ghost">Back to my Vault</button>`;
    $('#closeImpact').onclick=refreshVault;
    pendingVaultEvidenceId=null;
    await refreshDNA();
    say(changes.some(c=>c.changed)?'Vault · DNA changed because evidence was removed':'Vault · reflection forgotten');
  }catch(err){alert(err.message);button.disabled=false;button.textContent='Delete reflection & recalculate DNA'}
}

$('#refreshVault').onclick=refreshVault;
