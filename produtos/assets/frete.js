
/* INFOLUX frete estimator — loads /assets/frete-config.json (or relative) */
(function(){
  const money = n => (n??0).toLocaleString('pt-BR',{style:'currency',currency:'BRL'});
  let CFG = null;
  let CFG_PROMISE = null;

  function configUrl(){
    const s = document.querySelector('script[src*="frete.js"]');
    if(s){
      const u = new URL(s.getAttribute('src'), location.href);
      u.pathname = u.pathname.replace(/frete\.js$/,'frete-config.json');
      return u.href;
    }
    // fallback relative to page depth
    const depth = (location.pathname.match(/\//g)||[]).length;
    // try common roots
    return new URL('assets/frete-config.json', location.href.replace(/\/[^/]*$/, '/')).href;
  }

  async function loadConfig(){
    if(CFG) return CFG;
    if(CFG_PROMISE) return CFG_PROMISE;
    CFG_PROMISE = (async()=>{
      const candidates = [];
      const script = document.querySelector('script[src*="frete.js"], script[src*="app.js"]');
      if(script){
        const base = new URL(script.getAttribute('src'), location.href);
        candidates.push(new URL('frete-config.json', base).href);
        candidates.push(new URL('../assets/frete-config.json', base).href);
      }
      candidates.push(new URL('assets/frete-config.json', location.origin + location.pathname.replace(/\/[^/]*$/, '/')).href);
      // walk up for nested pages
      let p = location.pathname;
      for(let i=0;i<4;i++){
        p = p.replace(/\/[^/]+\/?$/, '/');
        candidates.push(location.origin + p + 'assets/frete-config.json');
      }
      let lastErr;
      for(const url of [...new Set(candidates)]){
        try{
          const r = await fetch(url, {cache:'no-cache'});
          if(!r.ok) continue;
          CFG = await r.json();
          return CFG;
        }catch(e){ lastErr=e; }
      }
      throw lastErr || new Error('frete-config.json não encontrado');
    })();
    return CFG_PROMISE;
  }

  function onlyDigits(s){ return String(s||'').replace(/\D/g,''); }
  function formatCep(d){
    d = onlyDigits(d).slice(0,8);
    return d.length>5 ? d.slice(0,5)+'-'+d.slice(5) : d;
  }

  function estimateWeightKg(items, cfg){
    // items: [{weight?, category?, subcategory?, qty}]
    let total = 0;
    for(const it of items){
      const qty = it.qty || 1;
      let w = Number(it.weight);
      if(!Number.isFinite(w) || w<=0){
        const map = cfg.category_weight_kg || {};
        w = map[it.subcategory] || map[it.category] || map.default || 0.8;
      } else if(w > 80){
        // likely grams
        w = w/1000;
      }
      total += w * qty;
    }
    return Math.max(0.3, Math.round(total*100)/100);
  }

  function cubicWeightKg(items, cfg){
    const d = cfg.default_dims_cm || {l:20,w:15,h:10};
    const factor = cfg.cubic_factor_cm3_per_kg || 6000;
    // rough: each item uses default box; scale volume with weight proxy
    let vol = 0;
    for(const it of items){
      const qty = it.qty || 1;
      const scale = Math.cbrt(Math.max(0.5, (Number(it.weight)||1)));
      vol += (d.l*d.w*d.h) * scale * qty;
    }
    return Math.max(0.3, Math.round((vol/factor)*100)/100);
  }

  function billableKg(items, cfg){
    return Math.max(estimateWeightKg(items,cfg), cubicWeightKg(items,cfg));
  }

  function matchRegion(uf, cep, cfg){
    const pref = onlyDigits(cep).slice(0,3);
    const regions = cfg.regions || {};
    // explicit capital first
    for(const [id, r] of Object.entries(regions)){
      const m = r.match || {};
      if(m.cep_prefix && m.cep_prefix.some(p => pref.startsWith(p))) return {id, ...r};
    }
    for(const [id, r] of Object.entries(regions)){
      const m = r.match || {};
      if(m.ufs && m.ufs.includes(uf)){
        if(m.exclude_cep_prefix && m.exclude_cep_prefix.some(p => pref.startsWith(p))) continue;
        return {id, ...r};
      }
    }
    // fallback sudeste-ish mid
    return {id:'sudeste', ...(regions.sudeste||{})};
  }

  function priceFor(table, kg){
    if(!table) return null;
    const v = table.base + table.per_kg * Math.max(0, kg - 1);
    return Math.max(table.min ?? table.base, Math.round(v*100)/100);
  }

  async function viaCep(cep){
    const d = onlyDigits(cep);
    if(d.length!==8) throw new Error('CEP inválido');
    const r = await fetch('https://viacep.com.br/ws/'+d+'/json/');
    const j = await r.json();
    if(j.erro) throw new Error('CEP não encontrado');
    return j;
  }

  function quote(cfg, dest, items){
    const kg = billableKg(items, cfg);
    const region = matchRegion(dest.uf, dest.cep, cfg);
    const opts = [];
    opts.push({
      id:'pac',
      name: (cfg.labels&&cfg.labels.pac)||'PAC',
      price: priceFor(region.pac, kg),
      days: region.days_pac,
      note: region.label
    });
    opts.push({
      id:'sedex',
      name: (cfg.labels&&cfg.labels.sedex)||'SEDEX',
      price: priceFor(region.sedex, kg),
      days: region.days_sedex,
      note: region.label
    });
    const x = cfg.xavante;
    if(x && x.ufs && x.ufs.includes(dest.uf)){
      const px = Math.max(x.min??x.base, Math.round((x.base + x.per_kg*Math.max(0,kg-1))*100)/100);
      opts.push({
        id:'xavante',
        name: x.name,
        price: px,
        days: x.days,
        note: x.note || 'valor estimado, confirmado no WhatsApp'
      });
    }
    return {kg, region, options: opts, origin: cfg.origin};
  }

  function renderBox(host, state){
    const cfg = state.cfg;
    host.innerHTML = `
      <div class="frete-box" data-frete>
        <div class="frete-head">
          <strong>Calcular frete</strong>
          <span class="frete-origin">Enviado pelo distribuidor parceiro; prazo confirmado após o pagamento</span>
        </div>
        <form class="frete-form" autocomplete="postal">
          <input type="text" name="cep" inputmode="numeric" placeholder="CEP de destino" maxlength="9" value="${state.cep||''}" aria-label="CEP">
          <button type="submit" class="btn btn-primary">Calcular</button>
        </form>
        <div class="frete-msg" aria-live="polite">${state.msg||''}</div>
        <div class="frete-results"></div>
        <p class="frete-foot">${(cfg.labels&&cfg.labels.footnote)||''}</p>
      </div>`;
    const form = host.querySelector('form');
    const input = form.querySelector('input[name=cep]');
    input.addEventListener('input', ()=>{ input.value = formatCep(input.value); });
    form.addEventListener('submit', async (e)=>{
      e.preventDefault();
      const msg = host.querySelector('.frete-msg');
      const results = host.querySelector('.frete-results');
      msg.textContent = 'Consultando CEP…';
      results.innerHTML = '';
      try{
        const addr = await viaCep(input.value);
        const q = quote(cfg, {cep: onlyDigits(input.value), uf: addr.uf, city: addr.localidade}, state.items);
        msg.innerHTML = `<strong>${addr.localidade}/${addr.uf}</strong> · ${addr.logradouro||'CEP válido'} · peso cobrado ~ <strong>${q.kg.toLocaleString('pt-BR')} kg</strong>`;
        results.innerHTML = q.options.map(o => `
          <div class="frete-opt">
            <div>
              <strong>${o.name}</strong>
              <div class="frete-meta">Prazo confirmado após o pagamento${o.note?` · ${o.note}`:''}</div>
            </div>
            <div class="frete-price">${money(o.price)}</div>
          </div>`).join('');
        try{ localStorage.setItem('infolux_cep', onlyDigits(input.value)); }catch{}
      }catch(err){
        msg.textContent = err.message || 'Não foi possível calcular.';
      }
    });
  }

  function collectProductItems(){
    const page = document.querySelector('.product-page[data-product-page], .product-page, main[data-category]');
    if(!document.querySelector('.product-page')) return null;
    const el = document.querySelector('.product-page[data-product-page]') || document.querySelector('.product-page') || document.querySelector('main');
    const weight = el && el.dataset ? el.dataset.weight : '';
    const category = el && el.dataset ? el.dataset.category : '';
    const subcategory = el && el.dataset ? (el.dataset.sub || el.dataset.subcategory || '') : '';
    return [{
      weight: weight ? Number(weight) : null,
      category: category || '',
      subcategory: subcategory || '',
      qty: 1
    }];
  }

  function collectCartItems(){
    if(typeof loadCart !== 'function') return null;
    const c = loadCart();
    if(!c.length) return [];
    return c.map(i => ({
      weight: i.weight, category: i.category, subcategory: i.subcategory, qty: i.qty||1
    }));
  }

  async function mount(){
    try{ await loadConfig(); }catch(e){ console.warn('frete', e); return; }
    const saved = (()=>{ try{return localStorage.getItem('infolux_cep')||'';}catch{return ''} })();

    // Product page
    const prodItems = collectProductItems();
    if(prodItems){
      let host = document.getElementById('freteProduct');
      if(!host){
        host = document.createElement('div');
        host.id = 'freteProduct';
        const anchor = document.querySelector('.product-page .cta, .product-page .price, .product-page h1');
        const box = document.querySelector('.product-page') || document.querySelector('main');
        if(box) box.appendChild(host);
      }
      renderBox(host, {cfg: CFG, items: prodItems, cep: formatCep(saved), msg:''});
    }

    // Cart drawer — re-mount when opened
    const cart = document.getElementById('cartDrawer');
    if(cart){
      const ensure = ()=>{
        let host = document.getElementById('freteCart');
        if(!host){
          host = document.createElement('div');
          host.id = 'freteCart';
          const panel = cart.querySelector('.cart-panel');
          if(panel) panel.appendChild(host);
        }
        const items = collectCartItems() || [];
        renderBox(host, {cfg: CFG, items: items.length?items:[{category:'default',qty:1}], cep: formatCep(saved), msg: items.length?'':'Informe o CEP; o peso usará os itens do carrinho quando houver.'});
      };
      const _open = window.openCart;
      window.openCart = function(){ if(_open) _open(); setTimeout(ensure, 30); };
      // if already open
      if(cart.classList.contains('open') || cart.style.display==='block') ensure();
    }
  }

  document.addEventListener('DOMContentLoaded', mount);
  window.InfoluxFrete = { loadConfig, quote, viaCep, billableKg };
})();
