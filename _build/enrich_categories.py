#!/usr/bin/env python3
"""Re-fetch VZRO PDPs to extract breadcrumb category paths into meta JSON."""
from __future__ import annotations
import json, re, html as H, time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.request import Request, urlopen
from urllib.error import HTTPError

META = Path('/tmp/vzro_import/meta')
UA = 'Mozilla/5.0 (compatible; INFOLUXCatalog/1.0)'
WORKERS = 28

def fetch(url):
  req=Request(url, headers={'User-Agent':UA})
  with urlopen(req, timeout=25) as r:
    return r.read().decode('utf-8','replace')

def extract_path(html: str):
  # Find BreadcrumbList item URLs inside any JSON-LD blob
  paths=[]
  for m in re.finditer(r'"item"\s*:\s*"(https://vzro\.com\.br/[^"]+)"', html):
    u=m.group(1).rstrip('/')
    path=u.replace('https://vzro.com.br/','').strip('/')
    if not path or path.startswith('produtos') or path in ('contato',):
      continue
    paths.append(path)
  # also names
  # deepest non-home path
  if not paths:
    return ''
  # prefer longest path
  paths=sorted(set(paths), key=lambda p: (p.count('/'), len(p)))
  return paths[-1]

def one(fp: Path):
  d=json.loads(fp.read_text())
  if d.get('vzro_path'):
    return 'skip'
  slug=d['slug']
  try:
    html=fetch(f'https://vzro.com.br/produtos/{slug}/')
  except HTTPError as e:
    return f'http{e.code}'
  except Exception as e:
    return type(e).__name__
  path=extract_path(html)
  # also improve brand/sku if empty
  if not d.get('brand'):
    bm=re.search(r"brand\s*:\s*'((?:\\.|[^'\\])*)'|brand\s*:\s*\"((?:\\.|[^\"\\])*)\"", html)
    if bm: d['brand']=H.unescape((bm.group(1) or bm.group(2) or '').encode().decode('unicode_escape'))
  d['vzro_path']=path
  # crumbs list
  crumbs=[]
  for m in re.finditer(r'"name"\s*:\s*"([^"]+)"\s*,\s*"item"\s*:\s*"(https://vzro\.com\.br/[^"]+)"', html):
    crumbs.append({'name':H.unescape(m.group(1)), 'url':m.group(2)})
  d['breadcrumbs']=crumbs
  fp.write_text(json.dumps(d, ensure_ascii=False))
  return 'ok' if path else 'nopath'

def main():
  files=list(META.glob('*.json'))
  print('enrich', len(files), flush=True)
  counts={}
  t0=time.time()
  with ThreadPoolExecutor(max_workers=WORKERS) as ex:
    futs=[ex.submit(one, fp) for fp in files]
    n=0
    for fut in as_completed(futs):
      st=fut.result(); counts[st]=counts.get(st,0)+1; n+=1
      if n%200==0 or n==len(files):
        print(f'  {n}/{len(files)} {counts} {time.time()-t0:.0f}s', flush=True)
  print('DONE', counts, flush=True)

if __name__=='__main__':
  main()
