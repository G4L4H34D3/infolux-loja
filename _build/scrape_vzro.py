#!/usr/bin/env python3
"""Scrape VZRO product pages from sitemap slugs; save meta JSON + download images later."""
from __future__ import annotations
import json, re, time, html as H
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

ROOT = Path('/tmp/vzro_import')
META = ROOT / 'meta'
META.mkdir(parents=True, exist_ok=True)
SLUGS = json.loads((ROOT/'slugs.json').read_text())
UA = 'Mozilla/5.0 (compatible; INFOLUXCatalog/1.0; +https://infolux.app)'
WORKERS = 24

def fetch(url: str, timeout=25) -> str:
  req = Request(url, headers={'User-Agent': UA, 'Accept': 'text/html'})
  with urlopen(req, timeout=timeout) as r:
    return r.read().decode('utf-8', 'replace')

def parse_product(slug: str, html: str) -> dict:
  def meta(prop):
    m = re.search(rf'property="{re.escape(prop)}" content="([^"]*)"', html)
    return H.unescape(m.group(1)) if m else ''
  name = meta('og:title') or ''
  if ' - ' in name: name = name.split(' - ')[0].strip()
  h1 = re.search(r'<h1[^>]*id="product-name"[^>]*>([^<]+)', html)
  if h1: name = H.unescape(h1.group(1)).strip()
  image = meta('og:image').replace('http://','https://')
  desc = meta('og:description')
  # brand from LS.product
  brand = ''
  bm = re.search(r'brand\s*:\s*"((?:\\.|[^"\\])*)"', html)
  if bm: brand = H.unescape(bm.group(1).encode().decode('unicode_escape'))
  # sku from data-variants
  sku = ''
  vm = re.search(r'data-variants="([^"]+)"', html)
  variants = []
  if vm:
    try:
      variants = json.loads(H.unescape(vm.group(1)))
      if variants:
        sku = variants[0].get('sku') or ''
        if not image and variants[0].get('image_url'):
          image = 'https:' + variants[0]['image_url'] if variants[0]['image_url'].startswith('//') else variants[0]['image_url']
    except Exception:
      pass
  # breadcrumbs
  crumbs = []
  for mm in re.finditer(r'<script type="application/ld\+json">([\s\S]*?)</script>', html):
    raw = mm.group(1).strip()
    if 'BreadcrumbList' not in raw: continue
    try:
      d = json.loads(raw)
      for el in d.get('itemListElement') or []:
        item = el.get('item') or {}
        if isinstance(item, str):
          crumbs.append({'name': el.get('name',''), 'url': item})
        else:
          crumbs.append({'name': item.get('name') or el.get('name',''), 'url': item.get('@id') or item.get('id') or ''})
    except Exception:
      pass
  # description body
  dm = re.search(r'id="product-description"[^>]*>([\s\S]*?)</div>\s*<', html)
  description_html = dm.group(1) if dm else ''
  description = re.sub(r'<[^>]+>', ' ', description_html)
  description = re.sub(r'\s+', ' ', H.unescape(description)).strip()
  if not description: description = desc
  # strip price mentions
  description = re.sub(r'por R\$\s*[\d.,]+\.?\s*', '', description, flags=re.I)
  # specs: definition lists / tables
  specs = {}
  for m in re.finditer(r'<tr[^>]*>\s*<t[dh][^>]*>(.*?)</t[dh]>\s*<t[dh][^>]*>(.*?)</t[dh]>', html, re.I|re.S):
    k=re.sub(r'<[^>]+>','',m.group(1)).strip(); v=re.sub(r'<[^>]+>','',m.group(2)).strip()
    if k and v and len(k)<80: specs[H.unescape(k)]=H.unescape(v)
  # vzro path from breadcrumb urls
  vzro_path = ''
  for c in crumbs:
    u = (c.get('url') or '').replace('https://vzro.com.br/','').strip('/')
    if u and not u.startswith('produtos') and u not in ('','inicio'):
      vzro_path = u  # deepest wins as we iterate
  # more images
  imgs = []
  for m in re.finditer(r'(https://dcdn-us\.mitiendanube\.com/stores/[^"\']+\.(?:webp|jpg|jpeg|png))', html, re.I):
    u=m.group(1)
    if '/products/' in u and u not in imgs:
      imgs.append(u)
  if image and image not in imgs:
    imgs.insert(0, image)
  return {
    'slug': slug,
    'name': name,
    'brand': brand,
    'sku': sku,
    'description': description[:4000],
    'specs': specs,
    'image_remote': imgs[0] if imgs else image,
    'images_remote': imgs[:6],
    'url_vzro': f'https://vzro.com.br/produtos/{slug}/',
    'vzro_path': vzro_path,
    'breadcrumbs': crumbs,
    'available': True,
  }

def one(slug: str):
  out = META / f'{slug}.json'
  if out.exists() and out.stat().st_size > 50:
    return 'skip', slug
  url = f'https://vzro.com.br/produtos/{slug}/'
  try:
    html = fetch(url)
    if 'product-name' not in html and 'og:title' not in html:
      return 'empty', slug
    data = parse_product(slug, html)
    if not data.get('name'):
      return 'noname', slug
    out.write_text(json.dumps(data, ensure_ascii=False))
    return 'ok', slug
  except HTTPError as e:
    return f'http{e.code}', slug
  except Exception as e:
    return f'err:{type(e).__name__}', slug

def main():
  done = sum(1 for _ in META.glob('*.json'))
  print(f'starting scrape: {len(SLUGS)} slugs, already {done}', flush=True)
  counts = {}
  t0 = time.time()
  with ThreadPoolExecutor(max_workers=WORKERS) as ex:
    futs = {ex.submit(one, s): s for s in SLUGS}
    n = 0
    for fut in as_completed(futs):
      status, slug = fut.result()
      counts[status] = counts.get(status, 0) + 1
      n += 1
      if n % 100 == 0 or n == len(SLUGS):
        print(f'  {n}/{len(SLUGS)} {counts} elapsed={time.time()-t0:.0f}s', flush=True)
  print('DONE', counts, f'elapsed={time.time()-t0:.0f}s', flush=True)
  Path(ROOT/'scrape_summary.json').write_text(json.dumps(counts, indent=2))

if __name__ == '__main__':
  main()
