/* INFOLUX cart page: items, CEP shipping (frete.js / frete-config.json), customer data, checkout. */
(function(){
  const $ = id => document.getElementById(id);
  const CFG = window.INFOLUX_CHECKOUT || {};
  const digits = s => String(s||'').replace(/\D/g,'');
  let ship = null;          // {id,name,price,days}
  let shipOpts = [];
  let cepOk = '';
  let shipBlock = [];      // cart items the partner does not ship to this CEP's UF

  function validCPF(c){ c=digits(c); if(c.length!==11||/^(\d)\1+$/.test(c)) return false;
    for(let t=9;t<11;t++){ let s=0; for(let i=0;i<t;i++) s+=+c[i]*(t+1-i); if(((s*10)%11)%10!==+c[t]) return false; } return true; }
  function validCNPJ(c){ c=digits(c); if(c.length!==14||/^(\d)\1+$/.test(c)) return false;
    const calc=n=>{ let s=0,p=n-7; for(let i=0;i<n;i++){ s+=+c[i]*p--; if(p<2) p=9; } const r=s%11; return r<2?0:11-r; };
    return calc(12)===+c[12] && calc(13)===+c[13]; }
  const validDoc = d => digits(d).length===11 ? validCPF(d) : validCNPJ(d);

  async function syncPrices(){
    // drop items no longer priced; refresh prices from the public list
    try{
      const r = await fetch(siteBase()+'data/prices.json',{cache:'no-cache'}); if(!r.ok) return;
      const map = await r.json();
      const c = loadCart().filter(i=>map[i.id]).map(i=>({...i, price: map[i.id].price}));
      saveCart(c);
    }catch{}
  }

  function itemsForFrete(){ return loadCart().map(i=>({weight:i.weight, category:i.category, subcategory:i.subcategory, qty:i.qty})); }

  function renderItems(){
    const c = loadCart(); const box = $('coItems');
    if(!c.length){ box.innerHTML = '<p style="color:#666">Seu carrinho está vazio. <a href="index.html" style="color:var(--red);font-weight:700">Ver produtos</a></p>'; }
    else box.innerHTML = cartItemsHTML(c);
    totals();
  }
  function total(){ return Math.round((cartSubtotal()+(ship?ship.price:0))*100)/100; }
  function totals(){
    $('coSub').textContent = money(cartSubtotal());
    $('coFrete').textContent = ship ? money(ship.price) : '—';
    $('coTotal').textContent = money(total());
  }

  async function calcFrete(e){
    e && e.preventDefault();
    const cep = digits($('coCep').value); const msg = $('coCepMsg');
    ship = null; shipOpts = []; shipBlock = []; $('coShip').innerHTML=''; $('coBlock') && $('coBlock').remove(); totals();
    if(!loadCart().length){ msg.textContent='Adicione produtos ao carrinho.'; return; }
    msg.className='co-msg'; msg.textContent='Consultando CEP…';
    try{
      const F = window.InfoluxFrete; const cfg = await F.loadConfig();
      const addr = await F.viaCep(cep);
      const q = F.quote(cfg, {cep, uf: addr.uf, city: addr.localidade}, itemsForFrete());
      cepOk = cep; shipOpts = q.options;
      msg.innerHTML = `<strong>${escHtml(addr.localidade)}/${escHtml(addr.uf)}</strong> · peso cobrado ~ ${q.kg.toLocaleString('pt-BR')} kg`;
      $('coShip').innerHTML = q.options.map((o,k)=>`<label class="ship-opt"><input type="radio" name="ship" value="${o.id}" ${k===0?'checked':''}>
        <span><strong>${escHtml(o.name)}</strong><br><small style="color:#666">Enviado pelo distribuidor parceiro; prazo confirmado após o pagamento</small></span>
        <span class="sp">${money(o.price)}</span></label>`).join('');
      ship = q.options[0]; totals();
      const SB = window.INFOLUX_SHIP_BLOCK || {};
      shipBlock = loadCart().filter(i=>SB[i.id] && SB[i.id].ufs.includes(addr.uf));
      if(shipBlock.length){
        const wa = `https://wa.me/${WA_NUMBER}?text=${encodeURIComponent(`Olá! Quero comprar ${shipBlock.map(i=>i.name).join(', ')} com entrega em ${addr.localidade}/${addr.uf} (CEP ${cep}). Tem alternativa?`)}`;
        const box = document.createElement('div'); box.id='coBlock'; box.className='co-msg err co-block'; box.style.marginTop='10px';
        box.innerHTML = `<strong>${shipBlock.map(i=>escHtml(i.name)).join(', ')}</strong>: não enviamos para <strong>${escHtml(addr.uf)}</strong> pela loja online. Remova este item para pagar os demais, ou <a href="${wa}" target="_blank" rel="noopener">fale com a INFOLUX no WhatsApp</a> que buscamos uma alternativa.`;
        $('coShip').after(box);
      }
      const f = $('coForm');
      if(!f.address.value) f.address.value = addr.logradouro||'';
      if(!f.province.value) f.province.value = addr.bairro||'';
      f.city.value = addr.localidade||f.city.value; f.state.value = addr.uf||f.state.value;
      try{ localStorage.setItem('infolux_cep', cep); }catch{}
    }catch(err){ msg.className='co-msg err'; msg.textContent = err.message||'Não foi possível calcular o frete.'; }
  }

  function customer(){
    const f = $('coForm'); const o = {};
    ['name','cpfCnpj','phone','email','address','addressNumber','complement','province','city','state'].forEach(k=>o[k]=f[k].value.trim());
    o.cpfCnpj = digits(o.cpfCnpj); o.phone = digits(o.phone); o.postalCode = cepOk; o.state = o.state.toUpperCase();
    return o;
  }
  function validate(){
    const f = $('coForm'); let bad = [];
    f.querySelectorAll('input[required]').forEach(i=>{ const v=i.value.trim(); const ok = v && (i.name!=='email' || /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(v)) && (i.name!=='cpfCnpj' || validDoc(v)) && (i.name!=='phone' || digits(v).length>=10); i.classList.toggle('invalid',!ok); if(!ok) bad.push(i); });
    if(!loadCart().length) return 'Carrinho vazio.';
    if(!ship) return 'Calcule o frete pelo CEP.';
    if(shipBlock.length) return 'Um item do carrinho não é enviado para o seu estado pela loja online. Remova-o ou fale com a gente no WhatsApp.';
    if(bad.length){ bad[0].focus(); return 'Confira os campos destacados.'; }
    return '';
  }

  function waFallback(){
    const c = loadCart(); if(!c.length) return;
    const cu = customer();
    const extra = (ship?`Frete (${ship.name}): ${money(ship.price)}\nTotal: ${money(total())}\n`:'') +
      (cepOk?`CEP: ${cepOk}\n`:'') + (cu.name?`Nome: ${cu.name}\n`:'') + (cu.cpfCnpj?`CPF/CNPJ: ${cu.cpfCnpj}\n`:'') +
      (cu.address?`Endereço: ${cu.address}, ${cu.addressNumber} ${cu.complement} — ${cu.province}, ${cu.city}/${cu.state}`:'');
    window.open(`https://wa.me/${WA_NUMBER}?text=${encodeURIComponent(orderWhatsAppText(c, extra))}`,'_blank','noopener');
  }

  async function pay(){
    const msg = $('coMsg'); msg.className='co-msg';
    const err = validate(); if(err){ msg.className='co-msg err'; msg.textContent=err; return; }
    if(!CFG.live || !CFG.CHECKOUT_API){
      msg.className='co-msg err'; msg.textContent='Pagamento online em breve. Finalize pelo WhatsApp — já enviamos seu pedido completo.';
      $('coWa').focus(); return;
    }
    const btn = $('coPay'); btn.disabled = true; msg.textContent = 'Gerando pagamento seguro…';
    try{
      const r = await fetch(CFG.CHECKOUT_API, {method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({items: loadCart().map(i=>({id:i.id, qty:i.qty})), cep: cepOk, shipping: ship.id, customer: customer()})});
      const j = await r.json().catch(()=>({}));
      if(!r.ok || !j.invoiceUrl) throw new Error(j.error || 'Falha ao gerar pagamento');
      try{ localStorage.setItem('infolux_last_order', JSON.stringify({id:j.orderId, at:Date.now()})); }catch{}
      location.href = j.invoiceUrl;
    }catch(e){
      btn.disabled = false; msg.className='co-msg err';
      msg.textContent = (e.message||'Erro') + '. Você pode finalizar pelo WhatsApp.';
    }
  }

  document.addEventListener('DOMContentLoaded', async ()=>{
    if(!$('checkout')) return;
    await syncPrices(); renderItems();
    const cepIn = $('coCep');
    cepIn.addEventListener('input', ()=>{ const d=digits(cepIn.value).slice(0,8); cepIn.value = d.length>5? d.slice(0,5)+'-'+d.slice(5) : d; });
    const saved = (()=>{ try{return localStorage.getItem('infolux_cep')||'';}catch{return ''} })();
    if(saved){ cepIn.value = saved.slice(0,5)+'-'+saved.slice(5); }
    $('coCepForm').addEventListener('submit', calcFrete);
    $('coShip').addEventListener('change', e=>{ if(e.target.name==='ship'){ ship = shipOpts.find(o=>o.id===e.target.value)||null; totals(); }});
    document.addEventListener('cart:change', ()=>{ renderItems(); if(cepOk) calcFrete(); });
    $('coPay').addEventListener('click', pay);
    $('coWa').addEventListener('click', waFallback);
    if(!CFG.live){ $('coPay').textContent = 'Pagamento online (em breve)'; $('coPay').classList.remove('btn-primary'); $('coPay').classList.add('btn-dark'); $('coWa').classList.remove('btn-wa-final'); $('coWa').classList.add('btn-primary'); }
    if(saved && loadCart().length) calcFrete();
  });
})();
