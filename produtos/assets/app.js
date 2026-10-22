const WA_NUMBER = '5566992070127';
const prefersReduced = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches;

function siteBase(){
  const s=[...document.scripts].find(x=>/assets\/app\.js/.test(x.src||''));
  if(s){
    try{ const u=new URL(s.src); return u.origin + u.pathname.replace(/assets\/app\.js.*$/,''); }
    catch{}
  }
  const path=location.pathname;
  const i=path.lastIndexOf('/produtos/');
  if(i>=0) return location.origin + path.slice(0, i+ '/produtos/'.length);
  return location.origin + path.replace(/[^/]*$/,'');
}
function productPageUrl(slug){
  return siteBase() + 'produtos/' + encodeURIComponent(slug) + '.html';
}
function consultWhatsApp(name, slug){
  const url = productPageUrl(slug);
  const msg = `Olá Lucas, vim pelo site da INFOLUX e quero saber o preço de: ${name} (${url})`;
  window.open(`https://wa.me/${WA_NUMBER}?text=${encodeURIComponent(msg)}`,'_blank','noopener');
}

document.addEventListener('click', (e)=>{
  const btn = e.target.closest('[data-wa-name][data-wa-slug]');
  if(!btn) return;
  e.preventDefault();
  btn.classList.remove('is-sent'); void btn.offsetWidth; btn.classList.add('is-sent');
  consultWhatsApp(btn.getAttribute('data-wa-name'), btn.getAttribute('data-wa-slug'));
});

const money = n => (Number(n)||0).toLocaleString('pt-BR',{style:'currency',currency:'BRL'});
function escHtml(s){ return String(s??'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/"/g,'&quot;'); }
function imgUrl(i){ return /^https?:/.test(i||'') ? i : siteBase() + String(i||'assets/logo-infolux.svg').replace(/^(\.\.\/)+/,''); }

/* Cart: only priced items (id + price). Older "orçamento" entries without price are dropped. */
function loadCart(){ try{ return JSON.parse(localStorage.getItem('infolux_cart')||'[]').filter(i=>i && i.id && Number(i.price)>0); }catch{ return []; } }
function saveCart(c){ localStorage.setItem('infolux_cart', JSON.stringify(c)); updateCartBadge(); }
function updateCartBadge(){
  const n=loadCart().reduce((a,i)=>a+(i.qty||1),0);
  document.querySelectorAll('[data-cart-count]').forEach(el=>el.textContent=String(n));
}
function cartSubtotal(c){ return Math.round((c||loadCart()).reduce((a,i)=>a+i.price*(i.qty||1),0)*100)/100; }
function addToCart(item){
  if(!item || !item.id || !(Number(item.price)>0)) return;
  const c=loadCart();
  const i=c.find(x=>x.id===item.id);
  if(i) i.qty+=(item.qty||1);
  else c.push({id:item.id, slug:item.slug, name:item.name, image:item.image, price:Number(item.price), category:item.category||'', subcategory:item.sub||item.subcategory||'', weight:item.weight??null, qty:item.qty||1});
  saveCart(c); openCart();
}
function removeFromCart(id){ saveCart(loadCart().filter(x=>x.id!==id)); renderCart(); document.dispatchEvent(new Event('cart:change')); }
function setQty(id,qty){ const c=loadCart(); const i=c.find(x=>x.id===id); if(!i) return; i.qty=Math.max(1,Math.min(99,qty|0)); saveCart(c); renderCart(); document.dispatchEvent(new Event('cart:change')); }
function openCart(){ const el=document.getElementById('cartDrawer'); if(!el) return; el.classList.add('open'); el.style.display='block'; renderCart(); }
function closeCart(){ const el=document.getElementById('cartDrawer'); if(!el) return; el.classList.remove('open'); el.style.display='none'; }
function openNav(){ const el=document.getElementById('navDrawer'); if(!el) return; el.classList.add('open'); el.style.display='block'; }
function closeNav(){ const el=document.getElementById('navDrawer'); if(!el) return; el.classList.remove('open'); el.style.display='none'; }
function cartItemsHTML(c){
  return c.map(i=>`<div class="cart-item">
    <img src="${escHtml(imgUrl(i.image))}" alt="" loading="lazy">
    <div><strong style="font-size:13px">${escHtml(i.name)}</strong>
      <div class="cart-unit">${money(i.price)}</div>
      <div style="margin-top:6px"><button class="btn" type="button" onclick="setQty('${escHtml(i.id)}',${i.qty-1})">-</button>
      <span style="margin:0 8px">${i.qty}</span>
      <button class="btn" type="button" onclick="setQty('${escHtml(i.id)}',${i.qty+1})">+</button></div></div>
    <button class="btn" type="button" aria-label="Remover" onclick="removeFromCart('${escHtml(i.id)}')">✕</button></div>`).join('');
}
function renderCart(){
  const box=document.getElementById('cartItems'); if(!box) return;
  const title=document.querySelector('#cartDrawer h2'); if(title) title.textContent='Carrinho';
  const c=loadCart(); const t=document.getElementById('cartTotals');
  if(!c.length){ box.innerHTML=`<div class="cart-empty">
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M6 6h15l-1.5 9h-12z"/><circle cx="9" cy="20" r="1.5"/><circle cx="18" cy="20" r="1.5"/><path d="M6 6L5 3H2"/></svg>
<p>Seu carrinho está vazio</p>
<button class="btn-checkout" type="button" onclick="closeCart()">Continuar navegando</button>
</div>`; if(t) t.innerHTML=''; return; }
  box.innerHTML=cartItemsHTML(c);
  if(t) t.innerHTML=`<div style="margin-top:14px;border-top:1px solid #eee;padding-top:12px">
      <div class="cart-sum"><span>Subtotal</span><strong>${money(cartSubtotal(c))}</strong></div>
      <p style="font-size:12px;color:#666;margin:4px 0 10px">Frete calculado no carrinho pelo CEP.</p>
      <a class="btn btn-primary btn-block" href="${siteBase()}carrinho.html">Ir para o carrinho e finalizar</a>
    </div>`;
}
function orderWhatsAppText(c, extra){
  let msg='Olá Lucas, vim pelo site da INFOLUX e quero finalizar este pedido:\n\n';
  c.forEach(i=>{ msg += `• ${i.qty}x ${i.name} — ${money(i.price*i.qty)}\n  ${productPageUrl(i.slug)}\n`; });
  msg += `\nSubtotal: ${money(cartSubtotal(c))}`;
  if(extra) msg += '\n' + extra;
  return msg;
}
function quoteWhatsApp(){
  const c=loadCart(); if(!c.length) return;
  window.open(`https://wa.me/${WA_NUMBER}?text=${encodeURIComponent(orderWhatsAppText(c))}`,'_blank','noopener');
}
function checkoutWhatsApp(){ quoteWhatsApp(); }

/* ===== Premium: swipe slider + autoplay ===== */
function initBannerSlider(){
  const root=document.querySelector('.banner-slider');
  if(!root) return;
  const slides=[...root.querySelectorAll('.slide')];
  const dots=[...document.querySelectorAll('.banner-dots button')];
  if(!slides.length) return;
  let i=0, timer=null, startX=0, dx=0, dragging=false;

  function show(n){
    i=(n+slides.length)%slides.length;
    slides.forEach((s,k)=>s.classList.toggle('active',k===i));
    dots.forEach((d,k)=>d.classList.toggle('active',k===i));
  }
  function next(){ show(i+1); }
  function prev(){ show(i-1); }
  function arm(){
    clearInterval(timer);
    if(prefersReduced() || slides.length<2) return;
    timer=setInterval(next, 4800);
  }
  dots.forEach((d,k)=>d.addEventListener('click',()=>{ show(k); arm(); }));

  const onStart = (x)=>{ dragging=true; startX=x; dx=0; clearInterval(timer); };
  const onMove = (x)=>{ if(!dragging) return; dx=x-startX; };
  const onEnd = ()=>{
    if(!dragging) return; dragging=false;
    if(Math.abs(dx)>42){ dx<0 ? next() : prev(); }
    arm();
  };
  root.addEventListener('touchstart', e=>onStart(e.touches[0].clientX), {passive:true});
  root.addEventListener('touchmove', e=>onMove(e.touches[0].clientX), {passive:true});
  root.addEventListener('touchend', onEnd);
  root.addEventListener('mousedown', e=>onStart(e.clientX));
  window.addEventListener('mousemove', e=>onMove(e.clientX));
  window.addEventListener('mouseup', onEnd);

  show(0); arm();
}

function initCookieBar(){
  const el=document.getElementById('cookieBar');
  if(!el) return;
  if(localStorage.getItem('infolux_cookies')==='1'){ el.classList.add('hidden'); return; }
  el.querySelector('button')?.addEventListener('click',()=>{
    localStorage.setItem('infolux_cookies','1');
    el.classList.add('hidden');
  });
}

function initHeaderScroll(){
  const h=document.querySelector('.header');
  if(!h) return;
  const onScroll=()=>h.classList.toggle('is-scrolled', window.scrollY>8);
  onScroll();
  window.addEventListener('scroll', onScroll, {passive:true});
}

function initParallax(){
  if(prefersReduced()) return;
  const banner=document.querySelector('.banner');
  if(!banner) return;
  let ticking=false, mx=0, my=0;
  const update=()=>{
    ticking=false;
    const r=banner.getBoundingClientRect();
    if(r.bottom<0 || r.top>(window.innerHeight||800)) return;
    const p=Math.min(1, Math.max(0, -r.top / (r.height||1)));   // 0 → 1 enquanto o hero sai da tela
    banner.style.setProperty('--hero-bg',  (p*r.height*0.35).toFixed(1)+'px');
    banner.style.setProperty('--hero-media',(p*r.height*-0.12).toFixed(1)+'px');
    banner.style.setProperty('--hero-cap', (p*r.height*0.18).toFixed(1)+'px');
    banner.style.setProperty('--hero-fade', (1-p*0.9).toFixed(3));
    banner.style.setProperty('--hero-mx', mx.toFixed(1)+'px');
    banner.style.setProperty('--hero-my', my.toFixed(1)+'px');
  };
  const req=()=>{ if(!ticking){ ticking=true; requestAnimationFrame(update); } };
  window.addEventListener('scroll', req, {passive:true});
  if(window.matchMedia('(hover:hover) and (pointer:fine)').matches){
    banner.addEventListener('pointermove', e=>{
      const r=banner.getBoundingClientRect();
      mx=((e.clientX-r.left)/r.width-.5)*-18; my=((e.clientY-r.top)/r.height-.5)*-12; req();
    }, {passive:true});
    banner.addEventListener('pointerleave', ()=>{ mx=0; my=0; req(); });
  }
  update();
}

/* tilt 3D + glow que segue o cursor (delegado: funciona também nos cards gerados por catalog.js) */
function initTilt(){
  if(prefersReduced() || !window.matchMedia('(hover:hover) and (pointer:fine)').matches) return;
  let active=null, frame=0, ev=null;
  const paint=()=>{
    frame=0; if(!active||!ev) return;
    const r=active.getBoundingClientRect();
    const x=(ev.clientX-r.left)/r.width, y=(ev.clientY-r.top)/r.height;
    active.style.setProperty('--mx',(x*100).toFixed(1)+'%');
    active.style.setProperty('--my',(y*100).toFixed(1)+'%');
    active.style.transform=`perspective(900px) rotateX(${((.5-y)*7).toFixed(2)}deg) rotateY(${((x-.5)*9).toFixed(2)}deg) translateY(-4px)`;
  };
  const reset=(c)=>{ if(!c) return; c.classList.remove('is-tilting'); c.style.transform=''; };
  document.addEventListener('pointermove', e=>{
    const c=e.target.closest && e.target.closest('.card, .mql-card');
    if(c!==active){ reset(active); active=c; if(c) c.classList.add('is-tilting'); }
    if(!c) return;
    ev=e; if(!frame) frame=requestAnimationFrame(paint);
  }, {passive:true});
  document.addEventListener('pointerleave', ()=>{ reset(active); active=null; });
}

/* contadores animados: <strong data-count="3526" data-from="0" data-suffix=" dias"> */
function initCounters(){
  const els=[...document.querySelectorAll('[data-count]')];
  if(!els.length) return;
  const fmt=(n,el)=> (el.dataset.raw!==undefined ? String(n) : n.toLocaleString('pt-BR')) + (el.dataset.suffix||'');
  if(prefersReduced() || !('IntersectionObserver' in window)){ els.forEach(el=>el.textContent=fmt(+el.dataset.count,el)); return; }
  const run=(el)=>{
    const to=+el.dataset.count, from=+(el.dataset.from||0), dur=1400, t0=performance.now();
    const step=(t)=>{
      const k=Math.min(1,(t-t0)/dur), e=1-Math.pow(1-k,3);
      el.textContent=fmt(Math.round(from+(to-from)*e),el);
      if(k<1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  };
  els.forEach(el=>{ el.textContent=fmt(+(el.dataset.from||0),el); });
  const io=new IntersectionObserver(es=>es.forEach(e=>{ if(e.isIntersecting){ run(e.target); io.unobserve(e.target); } }),{threshold:.6});
  els.forEach(el=>io.observe(el));
}

function initReveal(){
  const els=[...document.querySelectorAll('.section, .cat-carousel, .card, .svc-card, .svc-stats > div, .mql-card, .mql-compare, .mql-stats > div, .unit')];
  els.forEach((el,idx)=>{
    if(!el.classList.contains('reveal')) el.classList.add('reveal');
    if(!el.classList.contains('section')) el.classList.add('reveal-up');
    if(el.matches('.card, .svc-card, .mql-card, .svc-stats > div, .mql-stats > div, .unit')){
      const d='reveal-delay-'+(idx%3+1); el.classList.add(d);
      el.addEventListener('transitionend', ()=>el.classList.remove(d), {once:true});
    }
  });
  if(prefersReduced()){ els.forEach(el=>el.classList.add('in')); return; }
  const io=new IntersectionObserver((entries)=>{
    entries.forEach(e=>{
      if(e.isIntersecting){ e.target.classList.add('in'); io.unobserve(e.target); }
    });
  },{rootMargin:'0px 0px -8% 0px', threshold:0.08});
  els.forEach(el=>io.observe(el));
  requestAnimationFrame(()=>{
    const h=window.innerHeight||800;
    els.forEach(el=>{
      const r=el.getBoundingClientRect();
      if(r.top < h*0.95 && r.bottom > 0) el.classList.add('in');
    });
  });
}

function initDynamicCards(){
  const g=document.getElementById('catGrid'); if(!g || prefersReduced()) return;
  new MutationObserver(()=>{
    g.querySelectorAll('.card:not(.reveal)').forEach((c,i)=>{
      c.classList.add('reveal','reveal-up');
      c.style.transitionDelay=(Math.min(i,11)*30)+'ms';
      requestAnimationFrame(()=>requestAnimationFrame(()=>c.classList.add('in')));
      c.addEventListener('transitionend',()=>{ c.style.transitionDelay=''; },{once:true});
    });
  }).observe(g,{childList:true});
}

function initLazyImages(){
  document.querySelectorAll('.card .thumb img[loading="lazy"], .cat-chip img[loading="lazy"]').forEach(img=>{
    const thumb=img.closest('.thumb');
    if(thumb && !img.complete){
      img.classList.add('lazy-pending');
      let sk=thumb.querySelector('.thumb-skel');
      if(!sk){ sk=document.createElement('div'); sk.className='thumb-skel'; thumb.appendChild(sk); }
      const done=()=>{ img.classList.remove('lazy-pending'); img.classList.add('lazy-loaded'); sk?.remove(); };
      if(img.complete) done(); else { img.addEventListener('load', done, {once:true}); img.addEventListener('error', done, {once:true}); }
    }
  });
}

function scrubSupplierLinks(){
  document.querySelectorAll('a[href*="supplier"], [data-supplier-url], .supplier-url').forEach(el=>el.remove());
  document.querySelectorAll('*').forEach(el=>{
    if(el.childNodes.length===1 && el.childNodes[0].nodeType===3){
      const t=el.textContent||'';
      if(/supplier_url/i.test(t)) el.remove();
    }
  });
}

document.addEventListener('DOMContentLoaded', ()=>{
  updateCartBadge();
  document.querySelectorAll('[data-mega-toggle]').forEach(b=>b.addEventListener('click',()=>{
    const m=document.querySelector('[data-mega]'); if(!m) return;
    if(window.matchMedia('(max-width:979px)').matches){ openNav(); return; }
    m.classList.toggle('open'); m.hidden=!m.classList.contains('open');
  }));
  // relabel orçamento → carrinho in chrome
  document.querySelectorAll('#cartDrawer h2').forEach(el=>{ el.textContent='Carrinho'; });
  document.querySelectorAll('button.cart-btn, .cart-btn').forEach(el=>el.setAttribute('aria-label','Carrinho'));
  document.querySelectorAll('button.btn-primary').forEach(el=>{
    if(/^Orçamento\b/.test(el.textContent.trim())) el.innerHTML = el.innerHTML.replace(/Orçamento/,'Carrinho');
  });
  scrubSupplierLinks();
  initBannerSlider();
  initCookieBar();
  initHeaderScroll();
  initParallax();
  initReveal();
  initLazyImages();
  initTilt();
  initCounters();
  initDynamicCards();
  initServiceGuide();
});

/* Orientador de serviços: catálogo local, sem rede. O relato só sai no WhatsApp. */
function initServiceGuide(){
  const root=document.querySelector('[data-svc-guide]');
  if(!root) return;
  const input=root.querySelector('textarea');
  const out=root.querySelector('[data-svc-out]');
  const countEl=root.querySelector('[data-svc-count]');
  const hint=root.querySelector('[data-svc-hint]');
  const btn=root.querySelector('[data-svc-go]');
  if(!input||!out||!btn) return;
  const MIN=15, MAX=1200;
  const items=[
    {name:'Instalação Starlink', href:'#starlink', keys:['starlink','satelite','satélite','antena starlink'],
      reason:'O relato combina com instalação de internet via satélite Starlink.',
      next:'Diga se o equipamento já chegou e como é o local da instalação.'},
    {name:'Câmeras de Segurança', href:'#cameras', keys:['câmera','camera','cftv','alarme','dvr','nvr','segurança','seguranca','visão noturna','visao noturna'],
      reason:'O relato combina com câmeras, CFTV ou alarme.',
      next:'Informe o local e se quer ver as imagens pelo celular.'},
    {name:'Redes e Conectividade', href:'#redes', keys:['wi-fi','wifi','roteador','cabeamento','switch','repetidor','rede ','redes','sinal fraco'],
      reason:'O relato combina com instalação ou ajuste de rede e Wi-Fi.',
      next:'Diga se é casa, empresa ou fazenda e quantos ambientes precisam de sinal.'},
    {name:'Conserto de Celulares', href:'#celulares', keys:['celular','smartphone','iphone','android','bateria','conector de carga','tablet'],
      reason:'O relato aponta para reparo de celular ou tablet.',
      next:'Envie a marca, o modelo e o defeito para o Lucas.'},
    {name:'Impressão e Toners', href:'#impressao', keys:['impressora','toner','cartucho','tinta','não imprime','nao imprime'],
      reason:'O relato combina com impressora, toner ou suprimento.',
      next:'Envie a marca e o modelo da impressora.'},
    {name:'Formatação e Backup', href:'#formatacao', keys:['format','backup','vírus','virus','windows','lento','arquivos','dados'],
      reason:'Formatação com backup combina com lentidão, vírus ou sistema que não abre.',
      next:'Diga se precisa guardar arquivos antes da formatação.'},
    {name:'Suporte Técnico Remoto', href:'#remoto', keys:['remoto','senha','e-mail','email','configura','software','programa'],
      reason:'Dá para começar por atendimento remoto de software e configuração.',
      next:'Combine um horário com o Lucas no WhatsApp.'},
    {name:'Manutenção de Computadores', href:'#manutencao', keys:['computador','notebook','pc','desktop','esquenta','ssd','memória','memoria','não liga','nao liga','tela azul','fonte','placa'],
      reason:'O relato combina com manutenção de computador ou notebook.',
      next:'Informe a marca, o modelo e o que o aparelho faz quando o problema aparece.'}
  ];
  const high=['não liga','nao liga','quebrou','quebrado','trinc','parou','urgente','molhou','caiu','sem imagem'];
  const mid=['lento','esquenta','trav','intermit'];
  const urgLabel=t=> high.some(k=>t.includes(k))?'Alta':mid.some(k=>t.includes(k))?'Média':'Baixa';
  const sync=()=>{
    const n=input.value.length;
    if(countEl) countEl.textContent=n+'/'+MAX;
    const ok=input.value.trim().length>=MIN;
    btn.disabled=!ok;
    if(hint){
      hint.hidden=ok||n===0;
      hint.textContent=ok||n===0?'':'Escreva pelo menos '+MIN+' caracteres para receber uma recomendação.';
    }
  };
  input.addEventListener('input',()=>{ if(input.value.length>MAX) input.value=input.value.slice(0,MAX); sync(); });
  root.addEventListener('submit',(e)=>{
    e.preventDefault();
    const raw=input.value.trim();
    if(raw.length<MIN) return;
    const text=raw.toLowerCase();
    let scored=items.map(it=>{
      let s=0; it.keys.forEach(k=>{ if(text.includes(k)) s+=k.length>7?2:1; });
      return Object.assign({s}, it);
    }).filter(it=>it.s>0).sort((a,b)=>b.s-a.s).slice(0,3);
    const urg=urgLabel(text);
    if(!scored.length){
      scored=[{name:'Assistência técnica', href:'#manutencao', reason:'Não houve um encaixe claro no catálogo. O Lucas confirma o serviço no WhatsApp.', next:'Descreva o aparelho e o sintoma para o Lucas.', s:0}];
    }
    const lines=scored.map((it,i)=>`${i+1}. ${it.name} (urgência ${urg.toLowerCase()}) — ${it.reason}`);
    const msg='Olá Lucas, vim pelo site da INFOLUX. Usei o orientador de serviços.\n\nMeu problema:\n'+raw+'\n\nIndicações:\n'+lines.join('\n')+'\n\nGostaria de confirmar o diagnóstico e solicitar um orçamento.';
    const wa='https://wa.me/'+WA_NUMBER+'?text='+encodeURIComponent(msg);
    out.innerHTML='<p class="sp-kicker" style="color:var(--red)">Análise concluída</p><h3>Serviços recomendados</h3>'+
      scored.map(it=>`<article class="sp-rec"><header><h4><a href="${escHtml(it.href)}">${escHtml(it.name)}</a></h4><span class="sp-urg ${urg==='Alta'?'alta':urg==='Média'?'media':'baixa'}">Urgência ${escHtml(urg.toLowerCase())}</span></header><p>${escHtml(it.reason)}</p><p><strong>Próximo passo:</strong> ${escHtml(it.next)}</p></article>`).join('')+
      `<a class="sp-btn" href="${escHtml(wa)}" target="_blank" rel="noopener">Enviar análise para o Lucas</a>`+
      '<p class="sp-hint">Esta é uma orientação inicial, feita neste aparelho. O diagnóstico e o orçamento são confirmados pelo Lucas.</p>';
  });
  sync();
}

function initWhatsAppFloat(){
  if(document.getElementById('waFloat')) return;
  const a=document.createElement('a');
  a.id='waFloat'; a.className='wa-float'; a.target='_blank'; a.rel='noopener';
  a.href='https://wa.me/5566992070127?text='+encodeURIComponent('Olá Lucas, vim pelo site da INFOLUX');
  a.setAttribute('aria-label','Fale com o Lucas no WhatsApp');
  a.innerHTML='<svg viewBox="0 0 32 32" width="28" height="28" fill="#fff" aria-hidden="true"><path d="M16.01 3C9.39 3 4 8.35 4 14.92c0 2.1.56 4.15 1.62 5.96L4 29l8.35-1.57a12.1 12.1 0 0 0 3.66.56h.01c6.62 0 11.99-5.35 11.99-11.92C28.01 8.35 22.63 3 16.01 3zm6.96 16.9c-.3.84-1.75 1.54-2.42 1.64-.62.1-1.4.14-2.26-.14-.52-.17-1.18-.38-2.03-.75-3.57-1.55-5.9-5.15-6.08-5.39-.17-.24-1.45-1.93-1.45-3.68 0-1.75.92-2.61 1.25-2.97.33-.35.72-.44.96-.44h.69c.22 0 .51-.08.8.61.3.72 1.02 2.49 1.11 2.67.09.17.15.38.03.61-.12.24-.18.38-.35.59-.17.2-.37.45-.53.61-.17.17-.35.36-.15.7.2.35.9 1.48 1.93 2.4 1.33 1.18 2.45 1.55 2.8 1.72.35.17.55.15.75-.09.2-.24.87-1.01 1.1-1.36.23-.35.46-.29.78-.17.33.12 2.07.98 2.42 1.15.35.17.58.26.67.41.09.15.09.87-.21 1.71z"/></svg><span class="wa-label">Fale com o Lucas</span><span class="wa-dot" aria-hidden="true"></span>';
  document.body.appendChild(a);
}
document.addEventListener('DOMContentLoaded', ()=>{ initWhatsAppFloat(); });
