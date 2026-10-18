/* INFOLUX catalog: JSON-driven category grids with sort + pagination */
(function(){
  const PAGE_SIZE = 24;
  const root = document.getElementById('catalogRoot');
  if(!root) return;
  const dataUrl = root.dataset.catalog;
  const grid = document.getElementById('catGrid');
  const countEl = document.getElementById('visibleCount');
  const totalEl = document.getElementById('totalCount');
  const pager = document.getElementById('catalogPager');
  const sortSel = document.getElementById('sortBy');
  const qInput = document.getElementById('filterQ');
  const crumbTitle = document.getElementById('catalogTitle');
  let all = [];
  let page = 1;

  function productHref(slug){
    const depth = root.dataset.depth || '1';
    const prefix = depth === '2' ? '../../produtos/' : '../produtos/';
    return prefix + slug + '.html';
  }
  function imgSrc(image){
    if(!image) return (root.dataset.depth==='2'?'../../':'../') + 'assets/logo-infolux.svg';
    if(image.startsWith('http')||image.startsWith('assets/')||image.startsWith('../')) return image;
    const depth = root.dataset.depth || '1';
    return (depth==='2'?'../../':'../') + image.replace(/^\//,'');
  }
  function esc(s){ return String(s??'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/"/g,'&quot;'); }

  function cardHTML(p){
    const href = productHref(p.slug);
    const img = imgSrc(p.image);
    return `<article class="card" data-product-card data-slug="${esc(p.slug)}" data-sub="${esc(p.subcategory||'')}" data-brand="${esc(p.brand||'')}">
      <a class="thumb" href="${href}"><img src="${esc(img)}" alt="${esc(p.name)}" loading="lazy" width="400" height="400"></a>
      <div class="body">
        <div class="brand">${esc(p.brand||p.subcategory||'')}</div>
        <h3><a href="${href}">${esc(p.name)}</a></h3>
        <button class="btn btn-primary btn-wa" type="button" data-wa-name="${esc(p.name)}" data-wa-slug="${esc(p.slug)}">Consulte no WhatsApp</button>
        <div class="cta">
          <a class="btn btn-dark" href="${href}">Ver</a>
          <button class="btn btn-dark" type="button" onclick='addToCart(${JSON.stringify({slug:p.slug,name:p.name,image:p.image||""})})'>Orçamento</button>
        </div>
      </div>
    </article>`;
  }

  function filtered(){
    const term = (qInput?.value||'').toLowerCase().trim();
    let list = all.slice();
    if(term) list = list.filter(p => (`${p.name} ${p.brand||''} ${p.subcategory||''} ${p.sku||''}`).toLowerCase().includes(term));
    const mode = sortSel?.value || 'name';
    list.sort((a,b)=>{
      if(mode==='name-desc') return b.name.localeCompare(a.name,'pt-BR');
      if(mode==='brand') return (`${a.brand||''}${a.name}`).localeCompare(`${b.brand||''}${b.name}`,'pt-BR');
      return a.name.localeCompare(b.name,'pt-BR');
    });
    return list;
  }

  function render(){
    const list = filtered();
    const pages = Math.max(1, Math.ceil(list.length / PAGE_SIZE));
    if(page > pages) page = pages;
    const slice = list.slice((page-1)*PAGE_SIZE, page*PAGE_SIZE);
    grid.innerHTML = slice.map(cardHTML).join('') || '<p class="muted" style="padding:24px;grid-column:1/-1">Nenhum produto nesta categoria.</p>';
    if(countEl) countEl.textContent = String(list.length);
    if(totalEl) totalEl.textContent = String(all.length);
    if(pager){
      let html = '';
      if(pages > 1){
        html += `<button class="btn" type="button" data-page="${page-1}" ${page<=1?'disabled':''}>Anterior</button>`;
        html += `<span style="padding:0 10px;font-size:13px">Página ${page} / ${pages}</span>`;
        html += `<button class="btn" type="button" data-page="${page+1}" ${page>=pages?'disabled':''}>Próxima</button>`;
      }
      pager.innerHTML = html;
    }
  }

  pager?.addEventListener('click', e=>{
    const b = e.target.closest('[data-page]');
    if(!b || b.disabled) return;
    page = Math.max(1, parseInt(b.dataset.page,10)||1);
    render();
    root.scrollIntoView({behavior:'smooth', block:'start'});
  });
  qInput?.addEventListener('input', ()=>{ page=1; render(); });
  sortSel?.addEventListener('change', ()=>{ page=1; render(); });

  fetch(dataUrl).then(r=>{
    if(!r.ok) throw new Error('catalog '+r.status);
    return r.json();
  }).then(data=>{
    all = data.products || [];
    if(crumbTitle && data.title) crumbTitle.textContent = data.title;
    const sub = new URLSearchParams(location.search).get('sub');
    if(sub && !root.dataset.sub){
      all = all.filter(p => (p.subcategory_slug||'') === sub || (p.subcategory||'') === sub);
    }
    render();
  }).catch(err=>{
    grid.innerHTML = `<p style="padding:24px;grid-column:1/-1">Falha ao carregar catálogo.</p>`;
    console.error(err);
  });
})();
