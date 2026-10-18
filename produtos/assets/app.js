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
  consultWhatsApp(btn.getAttribute('data-wa-name'), btn.getAttribute('data-wa-slug'));
});

function quoteWhatsApp(){
  const c=loadCart(); if(!c.length) return;
  let msg='Olá Lucas, vim pelo site da INFOLUX e quero um orçamento:\n\n';
  c.forEach(i=>{
    const url = productPageUrl(i.slug);
    msg += `• ${i.qty}x ${i.name}\n  ${url}\n`;
  });
  msg += '\n(Sem valores — aguardo os preços, por favor.)';
  window.open(`https://wa.me/${WA_NUMBER}?text=${encodeURIComponent(msg)}`,'_blank','noopener');
}

function loadCart(){ try{return JSON.parse(localStorage.getItem('infolux_cart')||'[]');}catch{return[]} }
function saveCart(c){ localStorage.setItem('infolux_cart', JSON.stringify(c)); updateCartBadge(); }
function updateCartBadge(){
  const n=loadCart().reduce((a,i)=>a+(i.qty||1),0);
  document.querySelectorAll('[data-cart-count]').forEach(el=>el.textContent=String(n));
}
function addToCart(item){
  const c=loadCart();
  const i=c.find(x=>x.slug===item.slug);
  if(i) i.qty+=(item.qty||1); else c.push({slug:item.slug, name:item.name, image:item.image, qty:item.qty||1});
  saveCart(c); openCart();
}
function removeFromCart(slug){ saveCart(loadCart().filter(x=>x.slug!==slug)); renderCart(); }
function setQty(slug,qty){ const c=loadCart(); const i=c.find(x=>x.slug===slug); if(!i) return; i.qty=Math.max(1,qty|0); saveCart(c); renderCart(); }
function openCart(){ const el=document.getElementById('cartDrawer'); if(!el) return; el.classList.add('open'); el.style.display='block'; renderCart(); }
function closeCart(){ const el=document.getElementById('cartDrawer'); if(!el) return; el.classList.remove('open'); el.style.display='none'; }
function openNav(){ const el=document.getElementById('navDrawer'); if(!el) return; el.classList.add('open'); el.style.display='block'; }
function closeNav(){ const el=document.getElementById('navDrawer'); if(!el) return; el.classList.remove('open'); el.style.display='none'; }
function renderCart(){
  const box=document.getElementById('cartItems'); if(!box) return;
  const title=document.querySelector('#cartDrawer h2');
  if(title) title.textContent='Orçamento';
  const c=loadCart();
  if(!c.length){ box.innerHTML=`<div class="cart-empty">
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M6 6h15l-1.5 9h-12z"/><circle cx="9" cy="20" r="1.5"/><circle cx="18" cy="20" r="1.5"/><path d="M6 6L5 3H2"/></svg>
<p>Seu orçamento está vazio</p>
<button class="btn-checkout" type="button" onclick="closeCart()">Continuar navegando</button>
</div>`; const t=document.getElementById('cartTotals'); if(t) t.innerHTML=''; return; }
  box.innerHTML=c.map(i=>`<div class="cart-item">
    <img src="${i.image||'assets/logo-infolux.svg'}" alt="">
    <div><strong style="font-size:13px">${i.name}</strong>
      <div style="margin-top:6px"><button class="btn" onclick="setQty('${i.slug}',${i.qty-1})">-</button>
      <span style="margin:0 8px">${i.qty}</span>
      <button class="btn" onclick="setQty('${i.slug}',${i.qty+1})">+</button></div></div>
    <button class="btn" onclick="removeFromCart('${i.slug}')">✕</button></div>`).join('');
  document.getElementById('cartTotals').innerHTML=`
    <div style="margin-top:14px;border-top:1px solid #eee;padding-top:12px">
      <p style="font-size:13px;color:#6B7280;margin:0 0 10px">Envie a lista no WhatsApp para receber os preços. Sem totais no site.</p>
      <button class="btn btn-primary btn-block" style="margin-top:4px" onclick="quoteWhatsApp()">Pedir orçamento no WhatsApp</button>
      <p style="font-size:11px;color:#6B7280;margin:8px 0 0">WhatsApp: (66) 99207-0127</p>
    </div>`;
}
// back-compat alias
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
  let ticking=false;
  const update=()=>{
    ticking=false;
    const rect=banner.getBoundingClientRect();
    const view=window.innerHeight || 800;
    if(rect.bottom<0 || rect.top>view){
      banner.style.setProperty('--parallax', '0px');
      return;
    }
    const progress = (view/2 - (rect.top+rect.height/2)) / view;
    const y = Math.max(-10, Math.min(10, progress*14));
    banner.style.setProperty('--parallax', y.toFixed(1)+'px');
  };
  const onScroll=()=>{ if(!ticking){ ticking=true; requestAnimationFrame(update); } };
  window.addEventListener('scroll', onScroll, {passive:true});
  update();
}

function initReveal(){
  const els=[...document.querySelectorAll('.section, .cat-carousel, .card, .banner')];
  els.forEach((el,idx)=>{
    if(!el.classList.contains('reveal')) el.classList.add('reveal');
    if(el.classList.contains('card')) el.classList.add('reveal-delay-'+(idx%3+1));
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
  // relabel cart → orçamento in chrome
  document.querySelectorAll('#cartDrawer h2').forEach(el=>{ el.textContent='Orçamento'; });
  document.querySelectorAll('button.cart-btn, .cart-btn').forEach(el=>{
    if(el.getAttribute('aria-label')==='Carrinho') el.setAttribute('aria-label','Orçamento');
  });
  document.querySelectorAll('button.btn-primary').forEach(el=>{
    if(/^Carrinho\b/.test(el.textContent.trim())){
      el.innerHTML = el.innerHTML.replace(/Carrinho/,'Orçamento');
    }
  });
  scrubSupplierLinks();
  initBannerSlider();
  initCookieBar();
  initHeaderScroll();
  initParallax();
  initReveal();
  initLazyImages();
});

function initWhatsAppFloat(){
  if(document.getElementById('waFloat')) return;
  const a=document.createElement('a');
  a.id='waFloat'; a.className='wa-float'; a.target='_blank'; a.rel='noopener';
  a.href='https://wa.me/5566992070127?text='+encodeURIComponent('Olá Lucas, vim pelo site da INFOLUX');
  a.setAttribute('aria-label','WhatsApp INFOLUX');
  a.innerHTML='<svg viewBox="0 0 32 32" width="28" height="28" fill="#fff" aria-hidden="true"><path d="M16.01 3C9.39 3 4 8.35 4 14.92c0 2.1.56 4.15 1.62 5.96L4 29l8.35-1.57a12.1 12.1 0 0 0 3.66.56h.01c6.62 0 11.99-5.35 11.99-11.92C28.01 8.35 22.63 3 16.01 3zm6.96 16.9c-.3.84-1.75 1.54-2.42 1.64-.62.1-1.4.14-2.26-.14-.52-.17-1.18-.38-2.03-.75-3.57-1.55-5.9-5.15-6.08-5.39-.17-.24-1.45-1.93-1.45-3.68 0-1.75.92-2.61 1.25-2.97.33-.35.72-.44.96-.44h.69c.22 0 .51-.08.8.61.3.72 1.02 2.49 1.11 2.67.09.17.15.38.03.61-.12.24-.18.38-.35.59-.17.2-.37.45-.53.61-.17.17-.35.36-.15.7.2.35.9 1.48 1.93 2.4 1.33 1.18 2.45 1.55 2.8 1.72.35.17.55.15.75-.09.2-.24.87-1.01 1.1-1.36.23-.35.46-.29.78-.17.33.12 2.07.98 2.42 1.15.35.17.58.26.67.41.09.15.09.87-.21 1.71z"/></svg>';
  document.body.appendChild(a);
}
document.addEventListener('DOMContentLoaded', ()=>{ initWhatsAppFloat(); });
