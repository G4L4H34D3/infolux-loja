#!/usr/bin/env python3
"""Apollo review fixes (2026-10-18): copy, footer, menu, Hollyland, recategorization, dedupe.
Idempotent-ish: run once on a clean checkout."""
import json, re, html as H, shutil
from pathlib import Path
SITE = Path('/workspace/infolux/deploy/produtos'); CAT = SITE/'data/catalog'
prods = json.load(open(SITE/'data/products.json')); bys = {p['slug']: p for p in prods}
tree = json.load(open(SITE/'data/categories.json')); roots = {c['slug']: c for c in tree['categories']}
ROOTNAME = {s: c['name'] for s, c in roots.items()}
html_files = [p for p in SITE.rglob('*.html')]
TXT = {}  # path -> text cache
def rd(p):
    if p not in TXT: TXT[p] = p.read_text()
    return TXT[p]
def wr(p, s): TXT[p] = s

# ---------- 1. descriptions / names (claims) ----------
DESC = {
 '57d518b338': 'Apoio de punho em gel para teclado Multilaser AC033, com garantia de 3 anos direto com o fabricante. Mais conforto na digitação.',
 '3e99081e2a': 'Base suporte para notebook regulável, preta, produto novo. Ajusta a altura da tela e melhora a postura no dia a dia.',
 'c95db7914e': 'Cabo 12V/24V resistente à água com conector original para Starlink Mini. Ideal para carro, caminhão ou barco.',
 '4af3122b08': 'HD Seagate SATA 3.5" 500GB 7.200 RPM (ST3500CS312), produto novo em embalagem econômica OEM.',
 '4f9797f900': 'Lápis de cor Bic com 12 cores vibrantes + 4 lápis Evolution sem borracha. Ideal para desenho e colorir.',
 'ab8cc9f64e': 'Kit CFTV com 4 câmeras Intelbras iM5 Full HD e 4 cartões 32GB para monitoramento 24h com imagem nítida. A INFOLUX também faz a instalação: consulte no WhatsApp.',
}
byid = {p['id']: p for p in prods}
RENAME = {'Lapis Cor Bic 12 Cores Gratis 4 Lapis Sem Borracha Evolution': 'Lapis Cor Bic 12 Cores + 4 Lapis Sem Borracha Evolution'}
for i, new in DESC.items():
    p = byid[i]; old = p['description']; p['description'] = new
    f = SITE/'produtos'/f"{p['slug']}.html"; s = rd(f)
    for o in {old, H.escape(old, quote=False), H.escape(old, quote=True)}:
        s = s.replace(o, H.escape(new, quote=False))
    # meta description variants (may be truncated differently)
    s = re.sub(r'(<meta name="description" content=")[^"]*(")', lambda m: m.group(1) + H.escape(new, quote=True) + m.group(2), s, 1)
    s = re.sub(r'(<meta property="og:description" content=")[^"]*(")', lambda m: m.group(1) + H.escape(new, quote=True) + m.group(2), s, 1)
    wr(f, s)
for p in prods:
    if p['name'] in RENAME: p['name'] = RENAME[p['name']]
    for k in ('name', 'brand', 'description'):
        if p.get(k): p[k] = p[k].replace('Hollyand', 'Hollyland').replace('HOLLYAND', 'HOLLYLAND')

# ---------- 2. recategorization ----------
def child(root, sub):
    for c in roots[root]['children']:
        if c['slug'] == sub: return c
MOVE_SUB = ['cadeiras-para-escritorio', 'garrafas-de-cafe', 'garrafas', 'lixeiras', 'sacos-de-lixo',
            'tesouras-de-cozinha', 'apoios-para-pes', 'organizadores-de-escritorio', 'adesivos-decorativos']
MERGE = {('cameras-e-alarmes', 'usb1'): ('eletronicos-audio-e-video', 'cabos-usb-e-dados'),
         ('cameras-e-alarmes', 'microfones3'): ('pcs-notebooks-e-acessorios', 'microfones'),
         ('cameras-e-alarmes', 'audio-e-video'): ('eletronicos-audio-e-video', 'adaptadores-e-conversores')}
RENAME_SUB = {('cameras-e-alarmes', 'fita-de-led'): ('casa-inteligente', 'Casa Inteligente')}
CASA = ['lampada-dicroica-smart-rgbw-2700-6500-geonav', 'lampada-intelbras-inteligente-led-wi-fi-ews409',
        'lampada-inteligente-led-wi-fi-intelbras-ews410', 'lampada-inteligente-led-wi-fi-intelbras-ews440',
        'lampada-smart-rgbw-2700-6500-soquete-geonav']
CASA_NAMES = ['Luminaria Inteligente Wi-Fi Geonav', 'Atuador Smart Registro Hidraulico', 'Central Controle Remoto Infravermelho Smart Wi-Fi Geonav',
  'Controle Remoto Ir Inteligente Intelbras Izy Connect', 'Sensor Fumaca Inteligente Wi-Fi Geonav', 'Sistema Seguranca Smart Iss 1001 Izy Intelbras',
  'Amazon Echo Flex Plug-In Smart Speaker + Alexa', 'Alimentador Inteligente Wi-Fi Caes E Gatos Geonav', 'Tomada Interruptor Smart Wi-Fi Intelbras Izy Ews301',
  'Interruptor Smart Soquete E27 Intelbras Izy Ews 400', 'Interruptor Smart Wi-Fi Intelbras Izy Ews 101 I']
ALARM_NAMES = ['Sensor Intelbras Infravermelho Sem Fio Ivp 4101 Pet Smart', 'Sensor Intelbras Magnetico Sem Fio Xas 4010 Smart',
  'Receptor Central Serie 2000 E 4000 Xar 4000 Smart Intelbras', 'Controle Remoto Intelbras Inteligente Xac 4000 - Preto', 'Controle Remoto Intelbras Xac 4000 Smart - Azul']
CAM_NAMES = ['Camera Smart Mini Bullet Wi-Fi 1080P Full Hd Geonav']
byname = {p['name']: p for p in prods}
target = {}   # slug -> (root, sub, subname)
for p in prods:
    if p['category_slug'] == 'cameras-e-alarmes' and p['subcategory_slug'] in MOVE_SUB:
        target[p['slug']] = ('material-de-escritorio', p['subcategory_slug'], p['subcategory'])
    k = (p['category_slug'], p['subcategory_slug'])
    if k in MERGE:
        r, s = MERGE[k]; target[p['slug']] = (r, s, child(r, s)['name'])
    if k in RENAME_SUB:
        target[p['slug']] = ('cameras-e-alarmes',) + RENAME_SUB[k]
    if p['category_slug'] == 'pcs-notebooks-e-acessorios' and p['subcategory_slug'] == 'geral':
        if p['slug'] in CASA or p['name'] in CASA_NAMES or (p['name'].startswith('Interruptor Smart Wi-Fi Touch')) or p['name'].startswith('Interruptor Smart Bivolt'):
            target[p['slug']] = ('cameras-e-alarmes', 'casa-inteligente', 'Casa Inteligente')
        elif p['name'] in ALARM_NAMES: target[p['slug']] = ('cameras-e-alarmes', 'alarmes-e-sensores', 'Alarmes e Sensores')
        elif p['name'] in CAM_NAMES: target[p['slug']] = ('cameras-e-alarmes', 'cameras', 'Cameras')
hub = byname['Hub Controlador Cooler Argb C3Tech Fh-L100']['slug']
target[hub] = ('pcs-notebooks-e-acessorios', 'coolers-e-ventoinhas', 'Coolers e Ventoinhas')
assert all(s in bys for s in CASA)
print('products to move', len(target))

# load shards
shards = {f.stem: json.load(open(f)) for f in CAT.glob('*.json')}
def entry(p):
    return {'slug': p['slug'], 'name': p['name'], 'brand': p.get('brand', ''), 'image': p['image'], 'sku': p.get('sku', ''),
            'subcategory': p['subcategory'], 'subcategory_slug': p['subcategory_slug'], 'category_slug': p['category_slug'],
            'id': p['id'], 'price_infolux': p.get('price_infolux'), 'category': p['category'], 'weight': p.get('weight')}
moved_pages = {}
for slug, (r, s, sn) in target.items():
    p = bys[slug]; old_r, old_s, old_sn = p['category_slug'], p['subcategory_slug'], p['subcategory']
    p['category_slug'], p['category'], p['subcategory_slug'], p['subcategory'] = r, ROOTNAME[r], s, sn
    for k, d in shards.items():
        kr = k.split('__')[0]
        if kr != r or (('__' in k) and k.split('__')[1] in ('fita-de-led',)):
            d['products'] = [x for x in d['products'] if x['slug'] != slug]
        if kr == r and '__' in k and k.split('__')[1] != s and k.split('__')[1] in (old_s,) and old_r == r:
            d['products'] = [x for x in d['products'] if x['slug'] != slug]
    for key, title in ((r, ROOTNAME[r]), (f'{r}__{s}', sn)):
        d = shards.setdefault(key, {'title': title, 'slug': key.split('__')[-1], 'category_slug': r, 'category': ROOTNAME[r], 'products': []} if '__' in key else {'title': title, 'slug': r, 'products': []})
        d['products'] = [x for x in d['products'] if x['slug'] != slug] + [entry(p)]
    moved_pages[slug] = (old_r, old_s, old_sn)
# dedupe balun (root = cameras) from eletronicos shard
for k, d in shards.items():
    for x in d['products']:
        q = bys.get(x['slug'])
        if q and k.split('__')[0] != q['category_slug']:
            pass
    if k.split('__')[0] != 'cameras-e-alarmes':
        d['products'] = [x for x in d['products'] if x['slug'] != 'balun-passivo-1-canal-video-protetor-intelbras-vb501p']
# refresh name fields in all shards (Hollyland / Bic) and categories in entries
for k, d in shards.items():
    for x in d['products']:
        q = bys.get(x['slug'])
        if q: x['name'] = q['name']; x['brand'] = q.get('brand', x.get('brand'))
# remove empty sub shards of moved/merged/renamed sources; ensure renamed shard
for sub in MOVE_SUB: shards.pop(f'cameras-e-alarmes__{sub}', None)
for (r, s) in list(MERGE) + list(RENAME_SUB): shards.pop(f'{r}__{s}', None)
for f in CAT.glob('*.json'):
    if f.stem not in shards: f.unlink()
for k, d in shards.items(): (CAT/f'{k}.json').write_text(json.dumps(d, ensure_ascii=False))
# root shard order/consistency check
for r in roots:
    assert len(shards[r]['products']) == sum(1 for p in prods if p['category_slug'] == r), r

# categories.json
cam = roots['cameras-e-alarmes']; mat = roots['material-de-escritorio']
for sub in MOVE_SUB:
    c = child('cameras-e-alarmes', sub); cam['children'].remove(c); mat['children'].append(c)
for (r, s) in MERGE: cam['children'].remove(child(r, s))
c = child('cameras-e-alarmes', 'fita-de-led'); c['slug'], c['name'] = 'casa-inteligente', 'Casa Inteligente'
for r, c in roots.items():
    c['count'] = len(shards[r]['products'])
    for ch in c['children']:
        d = shards.get(f'{r}__{ch["slug"]}'); ch['count'] = len(d['products']) if d else 0
    c['children'] = [ch for ch in c['children'] if ch['count'] > 0]
(SITE/'data/categories.json').write_text(json.dumps(tree, ensure_ascii=False, indent=2))
json.dump(prods, open(SITE/'data/products.json', 'w'), ensure_ascii=False)

# ---------- 3. sub pages: move / redirect ----------
def redirect_stub(to_rel, title):
    return (f'<!DOCTYPE html><html lang="pt-BR"><head><meta charset="utf-8"><title>{title} — INFOLUX</title>'
            f'<meta http-equiv="refresh" content="0; url={to_rel}"><link rel="canonical" href="{to_rel}"><meta name="robots" content="noindex"></head>'
            f'<body><p>Esta categoria mudou: <a href="{to_rel}">{title}</a>.</p></body></html>\n')
RELINK = {}  # 'categorias/a/b.html' -> 'categorias/c/d.html'
CD = SITE/'categorias'
for sub in MOVE_SUB:
    src = CD/'cameras-e-alarmes'/f'{sub}.html'; dst = CD/'material-de-escritorio'/f'{sub}.html'
    s = rd(src).replace('data/catalog/cameras-e-alarmes__', 'data/catalog/material-de-escritorio__')
    s = s.replace('<a href="../cameras-e-alarmes.html">Câmeras e Alarmes</a> / <span id="catalogTitle">', '<a href="../material-de-escritorio.html">Material de Escritório</a> / <span id="catalogTitle">')
    wr(dst, s); html_files.append(dst)
    wr(src, redirect_stub(f'../material-de-escritorio/{sub}.html', child('material-de-escritorio', sub)['name']))
    RELINK[f'categorias/cameras-e-alarmes/{sub}.html'] = f'categorias/material-de-escritorio/{sub}.html'
for (r, s), (tr, ts) in MERGE.items():
    wr(CD/r/f'{s}.html', redirect_stub(f'../{tr}/{ts}.html', child(tr, ts)['name']))
    RELINK[f'categorias/{r}/{s}.html'] = f'categorias/{tr}/{ts}.html'
src = CD/'cameras-e-alarmes'/'fita-de-led.html'; dst = CD/'cameras-e-alarmes'/'casa-inteligente.html'
s = rd(src).replace('cameras-e-alarmes__fita-de-led.json', 'cameras-e-alarmes__casa-inteligente.json').replace('data-sub="fita-de-led"', 'data-sub="casa-inteligente"')
s = s.replace('<title>Fita De Led — INFOLUX</title>', '<title>Casa Inteligente — INFOLUX</title>').replace('<span id="catalogTitle">Fita De Led</span>', '<span id="catalogTitle">Casa Inteligente</span>').replace('id="catalogH1">Fita De Led<', 'id="catalogH1">Casa Inteligente<')
wr(dst, s); html_files.append(dst)
wr(src, redirect_stub('casa-inteligente.html', 'Casa Inteligente'))
RELINK['categorias/cameras-e-alarmes/fita-de-led.html'] = 'categorias/cameras-e-alarmes/casa-inteligente.html'

# ---------- 4. product pages of moved products ----------
for slug, (old_r, old_s, old_sn) in moved_pages.items():
    p = bys[slug]; f = SITE/'produtos'/f'{slug}.html'
    if not f.exists(): continue
    s = rd(f)
    s = re.sub(r'(<p class="crumb"><a href="\.\./index\.html">Início</a> / )<a href="\.\./categorias/[^"]+\.html">[^<]*</a> / <a href="\.\./categorias/[^"]+\.html">[^<]*</a>',
               lambda m: m.group(1) + f'<a href="../categorias/{p["category_slug"]}.html">{H.escape(p["category"])}</a> / <a href="../categorias/{p["category_slug"]}/{p["subcategory_slug"]}.html">{H.escape(p["subcategory"])}</a>', s, 1)
    s = re.sub(r'data-category="[^"]*" data-sub="[^"]*"', f'data-category="{H.escape(p["category"], quote=True)}" data-sub="{H.escape(p["subcategory"], quote=True)}"', s, 1)
    s = re.sub(r'(<li><span>Categoria</span><span>)[^<]*(</span></li>)', lambda m: m.group(1) + H.escape(f'{p["category"]} / {p["subcategory"]}') + m.group(2), s, 1)
    wr(f, s)

# ---------- 5. global html passes ----------
def mega_group(prefix, r):
    c = roots[r]; kids = sorted(c['children'], key=lambda ch: -ch['count'])[:16]
    return (f'<div><h4><a href="{prefix}categorias/{r}.html">{c["name"]}</a></h4>' +
            ''.join(f'<a href="{prefix}categorias/{r}/{ch["slug"]}.html">{ch["name"]}</a>' for ch in kids) + '</div>')
def chips_root(r):
    return '<div class="subnav-chips">' + ''.join(f'<a class="chip-link" href="{r}/{ch["slug"]}.html">{ch["name"]}</a>' for ch in roots[r]['children']) + '</div>'
def chips_sub(r):
    return (f'<div class="subnav-chips"><a class="chip-link" href="../{r}.html">Todas</a>' +
            ''.join(f'<a class="chip-link" href="{ch["slug"]}.html">{ch["name"]}</a>' for ch in roots[r]['children']) + '</div>')
n = 0
for f in html_files:
    s0 = s = rd(f)
    if 'http-equiv="refresh"' in s: continue
    s = s.replace(' · cores vermelho/preto/branco · imagens locais', '')
    s = s.replace('<li>Espigão do Leste (São Félix do Araguaia-MT)</li>', '<li>Espigão do Leste — Av. Espigão do Leste, Centro, ao lado da Dubai Lanches (São Félix do Araguaia-MT)</li>')
    s = s.replace('<li>Espigão do Leste — Av. Espigão do Leste, Centro (São Félix do Araguaia-MT)</li>', '<li>Espigão do Leste — Av. Espigão do Leste, Centro, ao lado da Dubai Lanches (São Félix do Araguaia-MT)</li>')
    s = re.sub(r'\s*<a href="[^"]*index\.html#ofertas" style="color:#fff;font-weight:700">Ofertas</a>', '', s)
    s = s.replace('Hollyand', 'Hollyland').replace('HOLLYAND', 'HOLLYLAND')
    for o, nn in RENAME.items(): s = s.replace(o, nn)
    for a, b in RELINK.items(): s = s.replace(a, b)
    # mega menu groups
    def mg(m):
        return mega_group(m.group(1), m.group(2))
    s = re.sub(r'<div><h4><a href="((?:\.\./)*)categorias/([a-z0-9-]+)\.html">[^<]*</a></h4>(?:<a href="[^"]*">[^<]*</a>)*</div>', mg, s)
    # chips on category pages
    rel = f.relative_to(SITE).parts
    if rel[0] == 'categorias' and 'subnav-chips' in s:
        if len(rel) == 2: s = re.sub(r'<div class="subnav-chips">.*?</div>', lambda m: chips_root(rel[1][:-5]), s, 1, flags=re.S)
        elif len(rel) == 3: s = re.sub(r'<div class="subnav-chips">.*?</div>', lambda m: chips_sub(rel[1]), s, 1, flags=re.S)
    if s != s0: wr(f, s)
for f, s in TXT.items():
    if not f.exists() or f.read_text() != s: f.write_text(s); n += 1
print('html files written', n, 'relinks', len(RELINK))
