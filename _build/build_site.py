#!/usr/bin/env python3
"""Merge catalog, compress images, emit category/product pages + JSON shards."""
from __future__ import annotations
import json, re, html as H, hashlib, io, shutil
from pathlib import Path
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.request import Request, urlopen
from PIL import Image

DEPLOY = Path('/workspace/infolux/deploy/produtos')
BUILD = Path('/workspace/infolux/deploy/_build')
META = Path('/tmp/vzro_import/meta')
IMG_DIR = DEPLOY / 'assets' / 'products'
CATALOG_DIR = DEPLOY / 'data' / 'catalog'
CAT_DIR = DEPLOY / 'categorias'
PROD_DIR = DEPLOY / 'produtos'
UA = 'Mozilla/5.0 (compatible; INFOLUXCatalog/1.0)'
PAGE_SIZE_HINT = 24

tree_wrap = json.loads((BUILD/'category_tree.json').read_text())
TREE = tree_wrap['categories']
BY_VZRO = tree_wrap['by_vzro_path']
LEGACY = tree_wrap['legacy_sub']
CAT_BY_SLUG = {c['slug']: c for c in TREE}

LISTING_MAP = {}
try:
  LISTING_MAP = json.loads(Path('/tmp/vzro_import/slug_to_path.json').read_text())
except Exception:
  pass

NAME_BY_SLUG = {c['slug']: c['name'] for c in TREE}

def slugify(s: str) -> str:
  import unicodedata
  s = H.unescape(s or '')
  s = unicodedata.normalize('NFKD', s)
  s = ''.join(c for c in s if not unicodedata.combining(c))
  s = s.lower()
  s = re.sub(r'[^a-z0-9]+', '-', s).strip('-')
  return s

def map_category(p: dict) -> dict:
  """Ensure category_slug / subcategory_slug on product."""
  vz = p.get('vzro_path') or ''
  if (not vz) and p.get('slug') in LISTING_MAP:
    vz = LISTING_MAP[p['slug']]
    p['vzro_path'] = vz
  if vz and vz in BY_VZRO:
    m = BY_VZRO[vz]
    p['category'] = m['category']
    p['category_slug'] = m['category_slug']
    p['subcategory'] = m['subcategory']
    p['subcategory_slug'] = m['subcategory_slug']
    return p
  # try prefix match deepest
  if vz:
    parts = vz.split('/')
    for i in range(len(parts), 0, -1):
      key = '/'.join(parts[:i])
      if key in BY_VZRO:
        m = BY_VZRO[key]
        p['category'] = m['category']
        p['category_slug'] = m['category_slug']
        p['subcategory'] = m['subcategory']
        p['subcategory_slug'] = m['subcategory_slug']
        return p
    # map by root
    root = parts[0]
    root_map = tree_wrap['root_map']
    if root in root_map:
      cslug = root_map[root]
      p['category_slug'] = cslug
      p['category'] = NAME_BY_SLUG[cslug]
      leaf = parts[-1]
      # find child by vzro_leaf or slugify
      cat = CAT_BY_SLUG[cslug]
      ch = next((c for c in cat['children'] if c.get('vzro_leaf')==leaf or c['slug']==leaf or c.get('vzro_path')==vz), None)
      if not ch:
        # create dynamic child
        name = leaf.replace('-',' ').title()
        ch = {'slug': slugify(name) or leaf, 'name': name, 'vzro_path': vz, 'vzro_leaf': leaf}
        cat['children'].append(ch)
      p['subcategory_slug'] = ch['slug']
      p['subcategory'] = ch['name']
      return p
  # legacy fields
  sub = p.get('subcategory') or ''
  cat = p.get('category') or ''
  if sub in LEGACY:
    m = LEGACY[sub]
    p['category_slug'] = m['category_slug']
    p['category'] = NAME_BY_SLUG[m['category_slug']]
    p['subcategory_slug'] = m['subcategory_slug']
    p['subcategory'] = m['subcategory']
    return p
  # match category name
  for c in TREE:
    if c['name'] == cat or c['slug'] == slugify(cat):
      p['category_slug'] = c['slug']
      p['category'] = c['name']
      sslug = slugify(sub) or 'geral'
      if not any(ch['slug']==sslug for ch in c['children']):
        c['children'].append({'slug': sslug, 'name': sub or 'Geral', 'vzro_path': None, 'vzro_leaf': sslug})
      p['subcategory_slug'] = sslug
      p['subcategory'] = sub or 'Geral'
      return p
  # fallback
  p['category_slug'] = p.get('category_slug') or 'pcs-notebooks-e-acessorios'
  p['category'] = NAME_BY_SLUG[p['category_slug']]
  p['subcategory_slug'] = p.get('subcategory_slug') or slugify(sub) or 'geral'
  p['subcategory'] = sub or 'Geral'
  return p

def load_existing():
  path = DEPLOY/'data'/'products.json'
  data = json.loads(path.read_text())
  by = {}
  for p in data:
    by[p['slug']] = p
  return by

def load_scraped():
  out = {}
  for fp in META.glob('*.json'):
    try:
      d = json.loads(fp.read_text())
      if d.get('slug') and d.get('name'):
        out[d['slug']] = d
    except Exception:
      pass
  return out

def merge(existing, scraped):
  merged = {}
  for slug, s in scraped.items():
    e = existing.get(slug, {})
    p = {
      'id': e.get('id') or hashlib.md5(slug.encode()).hexdigest()[:10],
      'slug': slug,
      'name': s.get('name') or e.get('name') or slug,
      'url_vzro': s.get('url_vzro') or e.get('url_vzro') or f'https://vzro.com.br/produtos/{slug}/',
      'price_vzro': e.get('price_vzro'),
      'price_infolux': e.get('price_infolux'),
      'sku': s.get('sku') or e.get('sku') or '',
      'stock': e.get('stock'),
      'available': s.get('available', True) if s.get('available') is not None else e.get('available', True),
      'brand': s.get('brand') or e.get('brand') or '',
      'category_root': e.get('category_root') or '',
      'category': e.get('category') or '',
      'subcategory': e.get('subcategory') or '',
      'description_src': e.get('description_src') or '',
      'description': s.get('description') or e.get('description') or '',
      'specs': s.get('specs') or e.get('specs') or {},
      'image': e.get('image') or f'assets/products/{slug}.webp',
      'image_vzro_ref': s.get('image_remote') or e.get('image_vzro_ref') or '',
      'images_remote': s.get('images_remote') or [],
      'model': e.get('model') or (s.get('specs') or {}).get('Modelo') or '',
      'weight': e.get('weight'),
      'supplier_url': e.get('supplier_url', ''),
      'vzro_path': s.get('vzro_path') or e.get('vzro_path') or '',
      'breadcrumbs': s.get('breadcrumbs') or [],
    }
    # strip prices from description
    p['description'] = re.sub(r'por R\$\s*[\d.,]+\.?\s*', '', p['description'] or '', flags=re.I)
    merged[slug] = map_category(p)
  # keep existing not in scraped
  for slug, e in existing.items():
    if slug in merged: continue
    p = dict(e)
    p.setdefault('supplier_url', '')
    p.setdefault('image', f'assets/products/{slug}.webp')
    p.setdefault('vzro_path', '')
    merged[slug] = map_category(p)
  return merged

def ensure_image(slug: str, remote: str, existing_image: str) -> str:
  IMG_DIR.mkdir(parents=True, exist_ok=True)
  dest = IMG_DIR / f'{slug}.webp'
  # reuse if exists and >1KB
  if dest.exists() and dest.stat().st_size > 1000:
    return f'assets/products/{slug}.webp'
  # try existing path
  if existing_image:
    cand = DEPLOY / existing_image if not existing_image.startswith('/') else Path(existing_image)
    if not cand.exists():
      cand = IMG_DIR / Path(existing_image).name
    if cand.exists() and cand.stat().st_size > 1000:
      if cand.resolve() != dest.resolve():
        try:
          im = Image.open(cand).convert('RGB')
          im.thumbnail((600, 600))
          im.save(dest, 'WEBP', quality=78, method=4)
        except Exception:
          shutil.copy2(cand, dest)
      return f'assets/products/{slug}.webp'
  if not remote:
    return f'assets/products/{slug}.webp'
  try:
    # prefer 480 or 512 size in nuvem CDN
    url = remote
    url = re.sub(r'-\d{3,4}-\d{3,4}\.', '-480-0.', url)
    req = Request(url, headers={'User-Agent': UA})
    raw = urlopen(req, timeout=30).read()
    im = Image.open(io.BytesIO(raw)).convert('RGB')
    im.thumbnail((600, 600))
    im.save(dest, 'WEBP', quality=78, method=4)
    return f'assets/products/{slug}.webp'
  except Exception as ex:
    return f'assets/products/{slug}.webp'

def download_images(products: dict):
  need = []
  for slug, p in products.items():
    dest = IMG_DIR / f'{slug}.webp'
    if dest.exists() and dest.stat().st_size > 1000:
      p['image'] = f'assets/products/{slug}.webp'
      continue
    need.append(p)
  print(f'images to fetch/convert: {len(need)}', flush=True)
  def job(p):
    img = ensure_image(p['slug'], p.get('image_vzro_ref') or (p.get('images_remote') or [None])[0], p.get('image'))
    return p['slug'], img
  n=0
  with ThreadPoolExecutor(max_workers=16) as ex:
    futs=[ex.submit(job,p) for p in need]
    for fut in as_completed(futs):
      slug, img = fut.result()
      products[slug]['image'] = img
      n+=1
      if n%100==0: print(f'  images {n}/{len(need)}', flush=True)
  print(f'images done {n}', flush=True)

def card_fields(p):
  return {
    'slug': p['slug'],
    'name': p['name'],
    'brand': p.get('brand') or '',
    'image': p.get('image') or '',
    'sku': p.get('sku') or '',
    'subcategory': p.get('subcategory') or '',
    'subcategory_slug': p.get('subcategory_slug') or '',
    'category_slug': p.get('category_slug') or '',
  }

def write_catalogs(products: dict):
  CATALOG_DIR.mkdir(parents=True, exist_ok=True)
  by_cat = defaultdict(list)
  by_sub = defaultdict(list)
  for p in products.values():
    by_cat[p['category_slug']].append(card_fields(p))
    by_sub[(p['category_slug'], p['subcategory_slug'])].append(card_fields(p))
  for c in TREE:
    items = sorted(by_cat.get(c['slug'], []), key=lambda x: x['name'].lower())
    (CATALOG_DIR/f"{c['slug']}.json").write_text(json.dumps({
      'title': c['name'], 'slug': c['slug'], 'products': items
    }, ensure_ascii=False, separators=(',',':')))
    for ch in c['children']:
      items = sorted(by_sub.get((c['slug'], ch['slug']), []), key=lambda x: x['name'].lower())
      # only emit pages that have products OR are legacy/nav
      (CATALOG_DIR/f"{c['slug']}__{ch['slug']}.json").write_text(json.dumps({
        'title': ch['name'], 'slug': ch['slug'], 'category_slug': c['slug'],
        'category': c['name'], 'products': items
      }, ensure_ascii=False, separators=(',',':')))
  # index of tree for runtime
  slim = []
  for c in TREE:
    kids=[{'slug':ch['slug'],'name':ch['name'],'count':len(by_sub.get((c['slug'],ch['slug']),[]))} for ch in c['children']]
    kids=[k for k in kids if k['count']>0]  # only non-empty for nav convenience; pages still exist for empty? we'll generate only non-empty + parents
    slim.append({'slug':c['slug'],'name':c['name'],'count':len(by_cat.get(c['slug'],[])),'children':kids})
  (DEPLOY/'data'/'categories.json').write_text(json.dumps({'categories':slim}, ensure_ascii=False, indent=2))
  return by_cat, by_sub

def rewrite_prefix(html: str, depth: int) -> str:
  """Adjust relative asset/links for category depth (1 or 2)."""
  if depth == 1:
    # from categorias/*.html
    html = html.replace('href="assets/', 'href="../assets/')
    html = html.replace('src="assets/', 'src="../assets/')
    html = html.replace('href="categorias/', 'href="')
    html = html.replace('href="produtos/', 'href="../produtos/')
    html = html.replace('href="busca.html', 'href="../busca.html')
    html = html.replace('href="index.html', 'href="../index.html')
    html = html.replace('action="busca.html', 'action="../busca.html')
    html = html.replace('src="assets/', 'src="../assets/')  # noop
    # scripts
    html = re.sub(r'(src|href)="\.\./assets/', r'\1="../assets/', html)
  elif depth == 2:
    html = html.replace('href="assets/', 'href="../../assets/')
    html = html.replace('src="assets/', 'src="../../assets/')
    html = html.replace('href="categorias/', 'href="../')
    html = html.replace('href="produtos/', 'href="../../produtos/')
    html = html.replace('href="busca.html', 'href="../../busca.html')
    html = html.replace('href="index.html', 'href="../../index.html')
    html = html.replace('action="busca.html', 'action="../../busca.html')
  return html

BY_SUB_COUNTS = {}

def build_mega_and_nav(prefix_cat='categorias/'):
  """prefix_cat is relative from page to categorias/ folder."""
  parts=[]
  for c in TREE:
    parts.append(f'<div><h4><a href="{prefix_cat}{c["slug"]}.html">{H.escape(c["name"])}</a></h4>')
    kids=[ch for ch in c['children'] if BY_SUB_COUNTS.get((c['slug'], ch['slug']), 0) > 0]
    kids=sorted(kids, key=lambda ch: -BY_SUB_COUNTS.get((c['slug'], ch['slug']), 0))[:16]
    for ch in kids:
      parts.append(f'<a href="{prefix_cat}{c["slug"]}/{ch["slug"]}.html">{H.escape(ch["name"])}</a>')
    parts.append('</div>')
  mega = '<div class="mega" data-mega hidden><div class="mega-grid">' + ''.join(parts) + '</div></div>'
  dparts=[]
  for c in TREE:
    dparts.append(f'<a href="{prefix_cat}{c["slug"]}.html"><strong>{H.escape(c["name"])}</strong></a>')
    kids=[ch for ch in c['children'] if BY_SUB_COUNTS.get((c['slug'], ch['slug']), 0) > 0]
    kids=sorted(kids, key=lambda ch: -BY_SUB_COUNTS.get((c['slug'], ch['slug']), 0))[:12]
    for ch in kids:
      dparts.append(f'<a class="sub" href="{prefix_cat}{c["slug"]}/{ch["slug"]}.html">{H.escape(ch["name"])}</a>')
  drawer = ''.join(dparts)
  top = ''.join(f'<a href="{prefix_cat}{c["slug"]}.html">{H.escape(c["name"])}</a>' for c in TREE)
  return mega, drawer, top

def chrome_for(depth: int, title: str):
  """Build page chrome with correct relative paths."""
  head = (BUILD/'frag_head_index.html').read_text()
  # fix title
  head = re.sub(r'<title>[^<]*</title>', f'<title>{H.escape(title)} — INFOLUX</title>', head)
  # fix stylesheet paths in head based on depth
  if depth == 1:
    head = head.replace('href="assets/', 'href="../assets/')
  elif depth == 2:
    head = head.replace('href="assets/', 'href="../../assets/')
  elif depth == 0:
    pass
  open_chrome = (BUILD/'frag_chrome_open.html').read_text()
  footer = (BUILD/'frag_footer.html').read_text()
  if depth == 1:
    prefix = ''  # we're inside categorias/
    open_chrome = rewrite_prefix(open_chrome, 1)
    footer = rewrite_prefix(footer, 1)
    mega, drawer, top = build_mega_and_nav('')
  elif depth == 2:
    open_chrome = rewrite_prefix(open_chrome, 2)
    footer = rewrite_prefix(footer, 2)
    mega, drawer, top = build_mega_and_nav('../')
  else:
    mega, drawer, top = build_mega_and_nav('categorias/')
  # replace mega block
  open_chrome = re.sub(r'<div class="mega" data-mega hidden>[\s\S]*?</div></div>', mega, open_chrome, count=1)
  # replace nav drawer links block — between navDrawer content
  open_chrome = re.sub(
    r'(<div class="nav-drawer"[^>]*>[\s\S]*?<nav[^>]*>)([\s\S]*?)(</nav>)',
    lambda m: m.group(1)+drawer+m.group(3),
    open_chrome, count=1
  )
  # desktop cat bar
  open_chrome = re.sub(
    r'(<nav class="d-cats"[^>]*>)([\s\S]*?)(</nav>)',
    lambda m: m.group(1)+top+m.group(3),
    open_chrome, count=1
  )
  # scripts at end of footer already include app.js — add catalog.js for cat pages later
  if depth == 1:
    footer = footer.replace('src="assets/', 'src="../assets/')
  elif depth == 2:
    footer = footer.replace('src="assets/', 'src="../../assets/')
  return head, open_chrome, footer

def category_page_html(cslug, cname, sub_slug=None, sub_name=None, depth=1):
  head, open_chrome, footer = chrome_for(depth, sub_name or cname)
  if depth == 1:
    data_url = f'../data/catalog/{cslug}.json' if not sub_slug else f'../data/catalog/{cslug}__{sub_slug}.json'
    home = '../index.html'
    cat_href = f'{cslug}.html'
  else:
    data_url = f'../../data/catalog/{cslug}__{sub_slug}.json'
    home = '../../index.html'
    cat_href = f'../{cslug}.html'
  title = sub_name or cname
  crumb = f'<p class="crumb"><a href="{home}">Início</a> / '
  if sub_slug:
    crumb += f'<a href="{cat_href}">{H.escape(cname)}</a> / <span id="catalogTitle">{H.escape(sub_name)}</span></p>'
  else:
    crumb += f'<span id="catalogTitle">{H.escape(cname)}</span></p>'
  # sub nav chips for category root
  subnav = ''
  cat = CAT_BY_SLUG[cslug]
  if not sub_slug:
    links=[]
    for ch in cat['children']:
      href = f'{cslug}/{ch["slug"]}.html' if depth==1 else f'{ch["slug"]}.html'
      # depth1 category page: links to subfolder
      if depth==1:
        href = f'{cslug}/{ch["slug"]}.html'
      links.append(f'<a class="chip-link" href="{href}">{H.escape(ch["name"])}</a>')
    # Actually on category root depth=1, path is categorias/cslug.html so sub is cslug/ch.html
    links=[]
    for ch in cat['children']:
      links.append(f'<a class="chip-link" href="{cslug}/{ch["slug"]}.html">{H.escape(ch["name"])}</a>')
    subnav = '<div class="subnav-chips">'+''.join(links)+'</div>'
  else:
    # sibling chips
    links=[]
    for ch in cat['children']:
      cls='chip-link active' if ch['slug']==sub_slug else 'chip-link'
      links.append(f'<a class="{cls}" href="{ch["slug"]}.html">{H.escape(ch["name"])}</a>')
    subnav = f'<div class="subnav-chips"><a class="chip-link" href="../{cslug}.html">Todas</a>'+''.join(links)+'</div>'

  main = f'''<main id="catalogRoot" data-catalog="{data_url}" data-depth="{depth}" {f'data-sub="{sub_slug}"' if sub_slug else ''}>
  {crumb}
  <div class="section-head" style="padding:12px 15px 0">
    <div><h1 style="margin:0;font-size:22px" id="catalogH1">{H.escape(title)}</h1>
      <p style="margin:4px 0 0;color:var(--muted);font-size:13px"><span id="visibleCount">0</span> de <span id="totalCount">0</span> produtos</p>
    </div>
  </div>
  {subnav}
  <div class="toolbar">
    <input id="filterQ" type="search" placeholder="Filtrar nesta categoria...">
    <select id="sortBy"><option value="name">Nome A–Z</option><option value="name-desc">Nome Z–A</option><option value="brand">Marca</option></select>
  </div>
  <div class="grid" id="catGrid"></div>
  <div id="catalogPager" class="catalog-pager" style="display:flex;justify-content:center;align-items:center;gap:8px;padding:20px"></div>
</main>
<script defer src="{'../' if depth==1 else '../../'}assets/catalog.js"></script>
'''
  # inject catalog script path fixed above
  # fix footer scripts already
  return head + open_chrome + main + footer

def product_page_html(p: dict):
  depth = 1  # produtos/*.html
  # custom chrome with ../ 
  head = (BUILD/'frag_head_index.html').read_text()
  head = re.sub(r'<title>[^<]*</title>', f'<title>{H.escape(p["name"])} — INFOLUX</title>', head)
  head = head.replace('href="assets/', 'href="../assets/')
  open_chrome = rewrite_prefix((BUILD/'frag_chrome_open.html').read_text(), 1)
  footer = rewrite_prefix((BUILD/'frag_footer.html').read_text(), 1)
  mega, drawer, top = build_mega_and_nav('../categorias/')
  open_chrome = re.sub(r'<div class="mega" data-mega hidden>[\s\S]*?</div></div>', mega, open_chrome, count=1)
  open_chrome = re.sub(r'(<div class="nav-drawer"[^>]*>[\s\S]*?<nav[^>]*>)([\s\S]*?)(</nav>)', lambda m: m.group(1)+drawer+m.group(3), open_chrome, count=1)
  open_chrome = re.sub(r'(<nav class="d-cats"[^>]*>)([\s\S]*?)(</nav>)', lambda m: m.group(1)+top+m.group(3), open_chrome, count=1)
  footer = footer.replace('src="assets/', 'src="../assets/')
  cslug=p['category_slug']; sslug=p['subcategory_slug']
  crumb = (f'<p class="crumb"><a href="../index.html">Início</a> / '
           f'<a href="../categorias/{cslug}.html">{H.escape(p["category"])}</a> / '
           f'<a href="../categorias/{cslug}/{sslug}.html">{H.escape(p["subcategory"])}</a> / '
           f'{H.escape(p["name"])}</p>')
  specs = p.get('specs') or {}
  specs_html = ''.join(f'<li><span>{H.escape(str(k))}</span><span>{H.escape(str(v))}</span></li>' for k,v in list(specs.items())[:30])
  if not specs_html and p.get('model'):
    specs_html = f'<li><span>Modelo</span><span>{H.escape(str(p["model"]))}</span></li>'
  if p.get('sku'):
    specs_html += f'<li><span>SKU</span><span>{H.escape(str(p["sku"]))}</span></li>'
  if p.get('brand'):
    specs_html += f'<li><span>Marca</span><span>{H.escape(str(p["brand"]))}</span></li>'
  specs_html += f'<li><span>Categoria</span><span>{H.escape(p["category"])} / {H.escape(p["subcategory"])}</span></li>'
  desc = H.escape(p.get('description') or 'Consulte o preço no WhatsApp.')
  img = '../' + (p.get('image') or f'assets/products/{p["slug"]}.webp')
  main = f'''<main>
  {crumb}
  <div class="product-page" data-product-page data-weight="{p.get('weight') or ''}" data-category="{H.escape(p['category'])}" data-sub="{H.escape(p['subcategory'])}" data-product-card data-slug="{H.escape(p['slug'])}">
    <div class="gallery"><img src="{H.escape(img)}" alt="{H.escape(p['name'])}" loading="eager"></div>
    <div>
      <div class="brand">{H.escape(p.get('brand') or '')}</div>
      <h1>{H.escape(p['name'])}</h1>
      <div style="display:grid;gap:8px;margin:14px 0">
        <button class="btn btn-primary btn-block btn-wa" type="button" data-wa-name="{H.escape(p['name'])}" data-wa-slug="{H.escape(p['slug'])}">Consulte no WhatsApp</button>
        <button class="btn btn-dark btn-block" type="button" onclick='addToCart({json.dumps({"slug":p["slug"],"name":p["name"],"image":p.get("image") or ""})})'>Adicionar ao orçamento</button>
      </div>
      <h3 style="font-size:15px">Descrição</h3>
      <p style="color:var(--muted)">{desc}</p>
      <h3 style="font-size:15px">Especificações</h3>
      <ul class="specs">{specs_html}</ul>
    </div>
  </div>
</main>
'''
  return head + open_chrome + main + footer

def update_index_links(by_sub):
  idx_path = DEPLOY/'index.html'
  t = idx_path.read_text()
  mega, drawer, top = build_mega_and_nav('categorias/')
  t = re.sub(r'<div class="mega" data-mega hidden>[\s\S]*?</div></div>', mega, t, count=1)
  t = re.sub(r'(<div class="nav-drawer"[^>]*>[\s\S]*?<nav[^>]*>)([\s\S]*?)(</nav>)', lambda m: m.group(1)+drawer+m.group(3), t, count=1)
  t = re.sub(r'(<nav class="d-cats"[^>]*>)([\s\S]*?)(</nav>)', lambda m: m.group(1)+top+m.group(3), t, count=1)
  # chip map: label → subcategory page
  CHIP_MAP = {
    'Acessórios para PCs': ('pcs-notebooks-e-acessorios','acessorios-para-pcs'),
    'Mouses': ('pcs-notebooks-e-acessorios','mouses-e-teclados'),
    'Wi-Fi Residencial': ('rede-e-internet','wi-fi-e-roteadores'),
    'Estabilizadores': ('pcs-notebooks-e-acessorios','nobreaks-e-estabilizadores'),
    'Nobreaks': ('pcs-notebooks-e-acessorios','nobreaks-e-estabilizadores'),
    'PC de Mesa': ('pcs-notebooks-e-acessorios','computadores'),
    'Monitores': ('pcs-notebooks-e-acessorios','monitores'),
    'Impressoras': ('impressao','impressoras'),
    'Material de Escritório': ('material-de-escritorio','material-de-escritorio'),
    'Notebooks': ('pcs-notebooks-e-acessorios','notebooks'),
    'Cabos e Conectores': ('eletronicos-audio-e-video','cabos-e-adaptadores'),
    'Câmeras de Segurança': ('cameras-e-alarmes','cameras-de-seguranca'),
  }
  def chip_repl(m):
    full=m.group(0)
    sm=re.search(r'<span>([^<]+)</span>', full)
    if not sm: return full
    label=sm.group(1)
    if label in CHIP_MAP:
      c,s = CHIP_MAP[label]
      return re.sub(r'href="[^"]*"', f'href="categorias/{c}/{s}.html"', full, count=1)
    return full
  t = re.sub(r'<a class="cat-chip" href="[^"]*">[\s\S]*?</a>', chip_repl, t)
  # section "Ver todos" already point to category roots — OK
  # update product counts in section heads if present
  for c in TREE:
    n = sum(1 for (cs,ss), items in by_sub.items() if cs==c['slug'] for _ in items)
    # also count from by_cat via sum children
    pass
  idx_path.write_text(t)

def add_subnav_css():
  css_path = DEPLOY/'assets'/'styles.css'
  css = css_path.read_text()
  block = '''
/* subcategory chip row */
.subnav-chips{display:flex;flex-wrap:wrap;gap:8px;padding:10px 15px 4px}
.subnav-chips .chip-link{font-size:12px;padding:6px 12px;border:1px solid var(--line);border-radius:999px;background:#fff;color:var(--ink);text-decoration:none}
.subnav-chips .chip-link:hover,.subnav-chips .chip-link.active{background:var(--red);color:#fff;border-color:var(--red)}
.catalog-pager .btn:disabled{opacity:.4;cursor:default}
'''
  if 'subnav-chips' not in css:
    css_path.write_text(css + block)

def main():
  print('loading…', flush=True)
  existing = load_existing()
  scraped = load_scraped()
  print(f'existing={len(existing)} scraped={len(scraped)}', flush=True)
  products = merge(existing, scraped)
  print(f'merged={len(products)}', flush=True)
  download_images(products)
  # persist products.json (keep supplier_url; keep prices in data but not rendered)
  # drop heavy transient fields for store file
  store_list=[]
  for slug in sorted(products.keys()):
    p=products[slug]
    store_list.append({
      'id': p['id'], 'slug': p['slug'], 'name': p['name'], 'url_vzro': p.get('url_vzro'),
      'price_vzro': p.get('price_vzro'), 'price_infolux': p.get('price_infolux'),
      'sku': p.get('sku'), 'stock': p.get('stock'), 'available': p.get('available', True),
      'brand': p.get('brand'), 'category_root': p.get('category_root'),
      'category': p['category'], 'category_slug': p['category_slug'],
      'subcategory': p['subcategory'], 'subcategory_slug': p['subcategory_slug'],
      'description_src': p.get('description_src'), 'description': p.get('description'),
      'specs': p.get('specs') or {}, 'image': p.get('image'),
      'image_vzro_ref': p.get('image_vzro_ref'), 'model': p.get('model'),
      'weight': p.get('weight'), 'supplier_url': p.get('supplier_url',''),
      'vzro_path': p.get('vzro_path') or '',
    })
  (DEPLOY/'data'/'products.json').write_text(json.dumps(store_list, ensure_ascii=False, indent=2))
  print('wrote products.json', len(store_list), flush=True)

  by_cat, by_sub = write_catalogs(products)
  global BY_SUB_COUNTS
  BY_SUB_COUNTS = {k: len(v) for k,v in by_sub.items()}
  add_subnav_css()

  # clean old flat category html cards — replace with thin pages
  # remove nested dirs first
  if CAT_DIR.exists():
    import shutil
    shutil.rmtree(CAT_DIR)
  CAT_DIR.mkdir(parents=True, exist_ok=True)
  # generate category + subcategory pages (only subs with products + all roots)
  n_cat=0; n_sub=0
  for c in TREE:
    html = category_page_html(c['slug'], c['name'], depth=1)
    # fix subnav links on root: should be `{slug}/{child}.html` but file is at categorias/{slug}.html
    html = html.replace(f'href="{c["slug"]}/{c["slug"]}/', f'href="{c["slug"]}/')
    # Fix botched subnav - regenerate properly
    links=[]
    for ch in c['children']:
      if len(by_sub.get((c['slug'], ch['slug']), []))==0 and ch.get('legacy'):
        # still show legacy even if empty? skip empty
        continue
      if len(by_sub.get((c['slug'], ch['slug']), []))==0:
        continue
      links.append(f'<a class="chip-link" href="{c["slug"]}/{ch["slug"]}.html">{H.escape(ch["name"])}</a>')
    subnav = '<div class="subnav-chips">'+''.join(links)+'</div>'
    html = re.sub(r'<div class="subnav-chips">[\s\S]*?</div>', subnav, html, count=1)
    (CAT_DIR/f"{c['slug']}.html").write_text(html)
    n_cat += 1
    subdir = CAT_DIR/c['slug']
    subdir.mkdir(exist_ok=True)
    for ch in c['children']:
      items = by_sub.get((c['slug'], ch['slug']), [])
      if not items:
        continue
      (subdir/f"{ch['slug']}.html").write_text(
        category_page_html(c['slug'], c['name'], ch['slug'], ch['name'], depth=2)
      )
      n_sub += 1
  print(f'category pages {n_cat} subcategory pages {n_sub}', flush=True)

  # product pages
  PROD_DIR.mkdir(exist_ok=True)
  # remove obsolete product html not in catalog? keep and overwrite all
  n=0
  for p in products.values():
    (PROD_DIR/f"{p['slug']}.html").write_text(product_page_html(p))
    n+=1
    if n%500==0: print(f'  pdp {n}', flush=True)
  print(f'product pages {n}', flush=True)

  update_index_links(by_sub)

  # update busca to use products.json without prices (already mostly ok)
  print('DONE build', flush=True)
  # summary
  summary={
    'products': len(products),
    'categories': n_cat,
    'subcategories': n_sub,
    'by_category': {c['slug']: len(by_cat.get(c['slug'],[])) for c in TREE},
  }
  (BUILD/'build_summary.json').write_text(json.dumps(summary, indent=2, ensure_ascii=False))
  print(json.dumps(summary, indent=2, ensure_ascii=False), flush=True)

if __name__ == '__main__':
  main()
