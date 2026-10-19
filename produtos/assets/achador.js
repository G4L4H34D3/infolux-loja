/* INFOLUX Achador de Soluções + Kits: one-click add-all (priced products only, re-checked against data/prices.json) */
(function(){
  const D = window.INFOLUX_ACHADOR; if(!D) return;
  const P = D.products; const base = (typeof siteBase==='function') ? siteBase() : '';
  const brl = n => (Number(n)||0).toLocaleString('pt-BR',{style:'currency',currency:'BRL'});
  const esc = s => String(s??'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/"/g,'&quot;');
  let live = null;
  const ready = fetch(base+'data/prices.json',{cache:'no-cache'}).then(r=>r.ok?r.json():null).then(j=>{ live=j; sync(); }).catch(()=>{});
  function ok(k){ const p=P[k]; if(!p) return false; if(!live) return true; const l=live[p.id]; if(!l) return false; p.price=l.price; return true; }
  function sync(){
    document.querySelectorAll('[data-kit]').forEach(card=>{
      const kt=D.kits.find(x=>x.id===card.dataset.kit); if(!kt) return;
      const items=kt.items.filter(i=>ok(i.k));
      const t=items.reduce((a,i)=>a+P[i.k].price*i.qty,0);
      const el=card.querySelector('[data-kit-total]'); if(el) el.textContent=brl(t);
      if(items.length<2){ card.classList.add('kit-off'); const b=card.querySelector('[data-add-kit]'); if(b){ b.disabled=true; b.textContent='Indisponível no momento'; } }
    });
  }
  function addAll(list){
    const items=list.filter(i=>ok(i.k)); if(!items.length) return 0;
    const c=loadCart();
    items.forEach(({k,qty})=>{ const p=P[k]; const ex=c.find(x=>x.id===p.id);
      if(ex) ex.qty=Math.min(99,(ex.qty||1)+qty);
      else c.push({id:p.id,slug:p.slug,name:p.name,image:p.image,price:Number(p.price),category:p.category,subcategory:p.sub,weight:p.weight??null,qty}); });
    saveCart(c); openCart(); document.dispatchEvent(new Event('cart:change')); return items.length;
  }
  document.addEventListener('click',e=>{
    const b=e.target.closest('[data-add-kit]'); if(!b) return;
    const kt=D.kits.find(x=>x.id===b.dataset.addKit); if(!kt) return;
    ready.then(()=>{ if(addAll(kt.items)){ b.classList.add('is-added'); b.textContent='Kit no carrinho ✓'; setTimeout(()=>{ b.classList.remove('is-added'); b.textContent='Adicionar tudo ao carrinho'; },2500);} });
  });

  /* ---- quiz ---- */
  const host=document.querySelector('[data-achador]'); if(!host) return;
  const body=host.querySelector('.ach-body'); const steps=host.querySelectorAll('.ach-steps span');
  const st={obj:null,budget:null,usage:null};
  function stepUI(n){ steps.forEach((s,i)=>{ s.classList.toggle('on',i<=n); s.classList.toggle('done',i<n); }); }
  function opts(title,list,key,next,back){
    body.innerHTML=`<h3 class="ach-q">${title}</h3><div class="ach-opts">${list.map(o=>`<button type="button" class="ach-opt" data-v="${esc(o.id)}">${o.icon?`<span class="ach-ico" aria-hidden="true">${o.icon}</span>`:''}<span>${esc(o.label)}</span></button>`).join('')}</div>${back?'<button type="button" class="ach-back">← Voltar</button>':''}`;
    body.querySelectorAll('.ach-opt').forEach(b=>b.addEventListener('click',()=>{ st[key]=b.dataset.v; next(); }));
    const bk=body.querySelector('.ach-back'); if(bk) bk.addEventListener('click',back);
    const f=body.querySelector('.ach-opt'); if(f && document.activeElement && host.contains(document.activeElement)) f.focus();
  }
  function q1(){ stepUI(0); opts('1. Qual é o seu objetivo?',D.objectives,'obj',q2); }
  function q2(){ stepUI(1); opts('2. Quanto você quer investir?',D.budgets,'budget',q3,q1); }
  function q3(){ stepUI(2); opts('3. Como vai ser o uso?',D.usages,'usage',()=>ready.then(result),q2); }
  function pick(){
    const o=D.objectives.find(x=>x.id===st.obj); const b=D.budgets.find(x=>x.id===st.budget); const max=b.max==null?Infinity:b.max;
    const pool=(o.pools[st.usage]||[]).filter(ok); const out=[]; let t=0;
    for(const k of pool){ if(out.length>=4) break; const r=D.req[k]; if(r && !out.some(i=>i.k===r)) continue; if(t+P[k].price<=max){ out.push({k,qty:1}); t+=P[k].price; } }
    let over=false;
    if(!out.length && pool.length){ const k=pool.filter(k=>!D.req[k]).sort((a,c)=>P[a].price-P[c].price)[0]; if(k){ out.push({k,qty:1}); over=P[k].price>max; } }
    const kt=D.kits.find(x=>x.id===o.kit); let kit=null;
    if(kt){ const items=kt.items.filter(i=>ok(i.k)); const kt_t=items.reduce((a,i)=>a+P[i.k].price*i.qty,0); if(items.length>=2 && kt_t<=max) kit={...kt,items,total:kt_t}; }
    return {o,b,out,over,kit};
  }
  function list(items){ return `<ul class="ach-items">${items.map(i=>{const p=P[i.k]; return `<li><img src="${esc(base+p.image)}" alt="" loading="lazy"><a href="${esc(base+'produtos/'+p.slug+'.html')}">${esc(p.name)}</a><span>${i.qty>1?i.qty+'× ':''}${brl(p.price)}</span></li>`;}).join('')}</ul>`; }
  function result(){
    stepUI(3); const r=pick(); const tot=r.out.reduce((a,i)=>a+P[i.k].price*i.qty,0);
    const wa='https://wa.me/5566992070127?text='+encodeURIComponent(`Olá Lucas, fiz o Achador de Soluções no site (${r.o.label}, ${r.b.label}) e quero ajuda para escolher.`);
    body.innerHTML=`<h3 class="ach-q">Sua recomendação: ${esc(r.o.label)}</h3><p class="ach-sub">${esc(r.b.label)} · ${esc(D.usages.find(u=>u.id===st.usage).label)}</p>
      ${r.out.length?`<div class="ach-res">${list(r.out)}<div class="ach-total"><div><small>Total</small><strong>${brl(tot)}</strong>${r.over?'<small class="ach-warn">Acima do orçamento escolhido: é a opção mais em conta desta linha.</small>':''}</div>
      <button type="button" class="btn btn-primary" data-add-quiz>Adicionar tudo ao carrinho</button></div></div>`:'<p>Não encontramos produtos com compra online para essa combinação. Fale com a gente no WhatsApp.</p>'}
      ${r.kit?`<div class="ach-kit"><span class="kit-tag">Kit pronto que cabe no orçamento</span><strong>${esc(r.kit.name)}</strong><span>${r.kit.items.length} itens · ${brl(r.kit.total)}</span><button type="button" class="btn btn-dark" data-add-kit="${esc(r.kit.id)}">Adicionar o kit</button></div>`:''}
      <div class="ach-actions"><button type="button" class="ach-back" data-restart>↺ Refazer</button><a class="ach-link" href="${esc(base+'kits.html')}">Ver todos os kits</a><a class="ach-link" href="${wa}" target="_blank" rel="noopener">Falar com um técnico</a></div>`;
    const ab=body.querySelector('[data-add-quiz]'); if(ab) ab.addEventListener('click',()=>{ if(addAll(r.out)){ ab.textContent='No carrinho ✓'; ab.classList.add('is-added'); } });
    body.querySelector('[data-restart]').addEventListener('click',()=>{ st.obj=st.budget=st.usage=null; q1(); });
  }
  q1();
})();
