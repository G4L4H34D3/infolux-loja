#!/usr/bin/env python3
"""Achador de Soluções (quiz) + Kits. Uses ONLY products present in data/prices.json.
Outputs: assets/achador-data.js, kits.html, and the home sections in index.html (between markers).
Run after tools/build_prices.py (it is called automatically at its end)."""
import json, re, html as H
from pathlib import Path
SITE = Path('/workspace/infolux/deploy/produtos')
prods = json.load(open(SITE/'data/products.json')); prices = json.load(open(SITE/'data/prices.json'))
byid = {p['id']: p for p in prods}
K = {  # key -> product id
 'mic': '6ffe420abe', 'lamp': 'f977f23b1a', 'webcam2k': 'f602f743c1', 'c920s': '7d83640c16', 'sd64': '31017dab36',
 'ezviz_lc1c': '53a13f5eab', 'ezviz_c8c': 'f1b624daa9', 'kit_cftv': 'ab8cc9f64e', 'ax12': '099c1cc7bc', 'mr60x': '3dbbba81c7',
 'mk250': '80501040a3', 'mk470': '5358efc7f3', 'base_nb': 'bb506fc875', 'hub': 'b6eeb5e51b', 'tricerix': '8933cf63ff',
 'clanm': 'c0ad59e357', 'mon_get23': '3b79c94dd8', 'malus': '321b5f3a26', 'kuromori': '3eaf947b69', 'nowy': '122f7a6572',
 'ps4': 'ce53b9dcbf', 'fenner': 'b50ddc1ca3', 'arkeum': '688a4a6494', 'quantum360': '3c8af29cbb', 'dazz': 'ccf04c2afe',
 'starlink': '5c4bdf01a2', 'cabo_sl': '60fd94c4b2', 'cabo_sl_bt': '7267487ecd', 'cabo_sl_5m': 'be722a98a2', 'knup300': 'b9119731c0',
 'gilgal': '53997679ef', 'tws': '6cf9b2dead', 'km5221w': 'dc6857e8c4', 'ms105g': 'b3f9361fd8', 'nb720': '1859a9c09e',
 'shara300': '7b8cc78a34', 'ls108g': 'b3f4b0484b', 'tl120': 'f3fe9244e3', 'eap610': '2d76385c9e', 'xs2310': '42180d9d9e',
 'sms1500': 'b495589eea', 'hll1232': 'c4bce96d84',
}
REQ = {'cabo_sl': 'starlink', 'cabo_sl_bt': 'starlink', 'cabo_sl_5m': 'starlink'}
OBJ = [
 {'id': 'conteudo', 'label': 'Criar conteúdo', 'icon': '🎙️', 'kit': 'criador',
  'pools': {'pessoal': ['lamp', 'sd64', 'webcam2k', 'mic'], 'equipe': ['mic', 'webcam2k', 'sd64', 'lamp'], 'pro': ['mic', 'c920s', 'sd64', 'lamp']}},
 {'id': 'casa', 'label': 'Casa conectada e segurança', 'icon': '🏠', 'kit': 'casa',
  'pools': {'pessoal': ['lamp', 'ezviz_lc1c', 'ax12', 'sd64'], 'equipe': ['mr60x', 'lamp', 'ezviz_c8c', 'ezviz_lc1c'], 'pro': ['kit_cftv', 'ax12', 'lamp', 'nb720']}},
 {'id': 'office', 'label': 'Home office e estudo', 'icon': '💻', 'kit': 'office',
  'pools': {'pessoal': ['mk250', 'base_nb', 'hub', 'tricerix'], 'equipe': ['ax12', 'mk250', 'hub', 'webcam2k'], 'pro': ['mon_get23', 'mk470', 'c920s', 'clanm']}},
 {'id': 'gamer', 'label': 'Setup gamer', 'icon': '🎮', 'kit': 'gamer',
  'pools': {'pessoal': ['malus', 'kuromori', 'nowy', 'lamp'], 'equipe': ['ps4', 'nowy', 'malus', 'lamp'], 'pro': ['fenner', 'arkeum', 'quantum360', 'dazz']}},
 {'id': 'carro', 'label': 'Carro e estrada', 'icon': '🛻', 'kit': 'estrada',
  'pools': {'pessoal': ['knup300', 'starlink', 'cabo_sl', 'tws'], 'equipe': ['starlink', 'cabo_sl_bt', 'knup300', 'tws'], 'pro': ['starlink', 'cabo_sl_5m', 'gilgal', 'knup300']}},
 {'id': 'empresa', 'label': 'Empresa e escritório', 'icon': '🏢', 'kit': 'empresa',
  'pools': {'pessoal': ['km5221w', 'ax12', 'shara300', 'hub'], 'equipe': ['ax12', 'ls108g', 'nb720', 'tl120'], 'pro': ['eap610', 'xs2310', 'sms1500', 'hll1232']}},
]
KITS = [
 {'id': 'criador', 'name': 'Kit Criador de Conteúdo', 'tag': 'Áudio limpo + imagem 2K', 'desc': 'Microfone sem fio duplo para gravar duas pessoas, webcam 2K para lives e reuniões, cartão para gravar e luz RGB de fundo.',
  'items': [('mic', 1), ('webcam2k', 1), ('sd64', 1), ('lamp', 1)]},
 {'id': 'casa', 'name': 'Kit Casa Conectada', 'tag': 'Luz inteligente + câmera + Wi-Fi 6', 'desc': 'Duas lâmpadas Wi-Fi com Alexa/Google, câmera Wi-Fi com luminária para a entrada e roteador Wi-Fi 6 para cobrir a casa.',
  'items': [('lamp', 2), ('ezviz_lc1c', 1), ('ax12', 1)]},
 {'id': 'office', 'name': 'Kit Home Office', 'tag': 'Ergonomia + produtividade', 'desc': 'Teclado e mouse sem fio, suporte articulado de monitor, base para notebook, hub USB e headset com microfone para chamadas.',
  'items': [('mk250', 1), ('clanm', 1), ('base_nb', 1), ('hub', 1), ('tricerix', 1)]},
 {'id': 'gamer', 'name': 'Kit Setup Gamer', 'tag': 'RGB de ponta a ponta', 'desc': 'Mouse gamer RGB 12.400 DPI, teclado mecânico 60%, headset surround USB e lâmpada RGB para o clima do setup.',
  'items': [('malus', 1), ('kuromori', 1), ('nowy', 1), ('lamp', 1)]},
 {'id': 'estrada', 'name': 'Kit Estrada Conectada', 'tag': 'Internet e energia no carro', 'desc': 'Starlink Mini com cabo 12V veicular USB-C e inversor 300W com 4 USB para ligar notebook e carregadores.',
  'items': [('starlink', 1), ('cabo_sl', 1), ('knup300', 1)]},
 {'id': 'empresa', 'name': 'Kit Escritório Conectado', 'tag': 'Rede + energia protegida', 'desc': 'Roteador Wi-Fi 6, switch gigabit de 5 portas, nobreak 720VA e kit teclado e mouse sem fio Dell.',
  'items': [('ax12', 1), ('ms105g', 1), ('nb720', 1), ('km5221w', 1)]},
]
PRODUCTS, dropped = {}, []
for k, i in K.items():
    p = byid.get(i)
    if not p or i not in prices: dropped.append(k); continue
    PRODUCTS[k] = {'id': i, 'slug': p['slug'], 'name': p['name'], 'image': p['image'], 'price': prices[i]['price'],
                   'category': p.get('category') or '', 'sub': p.get('subcategory') or '', 'weight': p.get('weight')}
for o in OBJ:
    for u in o['pools']: o['pools'][u] = [k for k in o['pools'][u] if k in PRODUCTS]
kits = []
for kt in KITS:
    items = [(k, q) for k, q in kt['items'] if k in PRODUCTS]
    if len(items) < 2: dropped.append('kit:' + kt['id']); continue
    kt = dict(kt, items=[{'k': k, 'qty': q} for k, q in items]); kt['total'] = round(sum(PRODUCTS[k]['price'] * q for k, q in items), 2)
    kits.append(kt)
data = {'products': PRODUCTS, 'kits': kits, 'objectives': OBJ, 'req': REQ,
        'budgets': [{'id': 'b1', 'label': 'Até R$ 300', 'max': 300}, {'id': 'b2', 'label': 'R$ 300 a R$ 800', 'max': 800},
                    {'id': 'b3', 'label': 'R$ 800 a R$ 1.500', 'max': 1500}, {'id': 'b4', 'label': 'Acima de R$ 1.500', 'max': None}],
        'usages': [{'id': 'pessoal', 'label': 'Uso pessoal, começando agora'}, {'id': 'equipe', 'label': 'Família ou escritório, vários usuários'},
                   {'id': 'pro', 'label': 'Profissional, uso intenso'}]}
(SITE/'assets/achador-data.js').write_text('// generated by _build/build_kits.py - only priced products\nwindow.INFOLUX_ACHADOR=' + json.dumps(data, ensure_ascii=False) + ';\n')

def brl(v): return 'R$ ' + f'{v:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
def kit_card(kt, prefix=''):
    lis = ''.join(f'<li><img src="{prefix}{PRODUCTS[i["k"]]["image"]}" alt="" loading="lazy"><a href="{prefix}produtos/{PRODUCTS[i["k"]]["slug"]}.html">{H.escape(PRODUCTS[i["k"]]["name"])}</a>'
                  f'<span>{(str(i["qty"]) + "× ") if i["qty"] > 1 else ""}{brl(PRODUCTS[i["k"]]["price"])}</span></li>' for i in kt['items'])
    return (f'<article class="kit-card" id="kit-{kt["id"]}" data-kit="{kt["id"]}"><div class="kit-head"><span class="kit-tag">{H.escape(kt["tag"])}</span>'
            f'<h3>{H.escape(kt["name"])}</h3><p>{H.escape(kt["desc"])}</p></div><ul class="kit-items">{lis}</ul>'
            f'<div class="kit-foot"><div><small>Total do kit</small><strong data-kit-total>{brl(kt["total"])}</strong><small>Pix, boleto ou cartão · frete no carrinho</small></div>'
            f'<button class="btn btn-primary" type="button" data-add-kit="{kt["id"]}">Adicionar tudo ao carrinho</button></div></article>')

QUIZ = '''<section class="achador" id="achador" aria-labelledby="achador-title">
  <div class="ach-glow" aria-hidden="true"></div>
  <div class="ach-inner">
    <p class="ach-kicker"><i aria-hidden="true"></i>Achador de Soluções</p>
    <h2 id="achador-title">Responda 3 perguntas e <span>monte seu setup</span></h2>
    <p class="ach-lead">A gente indica um kit pronto ou 3–4 produtos com compra online, dentro do seu orçamento. Você adiciona tudo ao carrinho com um clique.</p>
    <div class="ach-card" data-achador>
      <div class="ach-steps" aria-hidden="true"><span class="on">1</span><span>2</span><span>3</span></div>
      <div class="ach-body"><noscript><p>Ative o JavaScript para usar o Achador ou <a href="kits.html">veja os kits</a>.</p></noscript></div>
    </div>
  </div>
</section>'''
def kits_teaser():
    cards = ''.join(f'<a class="kit-mini" href="kits.html#kit-{k["id"]}"><span class="kit-tag">{H.escape(k["tag"])}</span><strong>{H.escape(k["name"])}</strong>'
                    f'<span class="kit-mini-total">{len(k["items"])} itens · {brl(k["total"])}</span></a>' for k in kits)
    return (f'<section class="section kits-teaser" id="kits"><div class="section-head"><div><h2>Kits <span style="color:var(--red)">prontos</span></h2>'
            f'<p>Produtos que funcionam juntos, com preço normal de cada item. Adicione o kit inteiro ao carrinho.</p></div>'
            f'<a class="btn btn-dark" href="kits.html">Ver todos os kits</a></div><div class="kit-mini-grid">{cards}</div></section>')
idx = SITE/'index.html'; s = idx.read_text()
block = '<!--ACHADOR:START-->\n' + QUIZ + '\n' + kits_teaser() + '\n<!--ACHADOR:END-->'
if '<!--ACHADOR:START-->' in s: s = re.sub(r'<!--ACHADOR:START-->.*?<!--ACHADOR:END-->', lambda m: block, s, flags=re.S)
else: s = s.replace('<section class="mql" id="diferenciais"', block + '\n<section class="mql" id="diferenciais"', 1)
TAGS = '<script src="assets/achador-data.js?v={v}"></script>\n<script defer src="assets/achador.js?v={v}"></script>'
V = '20261018f'
if 'achador.js' not in s: s = s.replace('<script src="assets/app.js', TAGS.format(v=V) + '\n  <script src="assets/app.js', 1)
idx.write_text(s)

# kits.html from index shell
head, rest = s.split('<main>', 1); tail = rest.split('</main>', 1)[1]
head = head.replace('<title>INFOLUX Informática | INFOLUX</title>', '<title>Kits prontos | INFOLUX</title>\n<meta name="description" content="Kits INFOLUX: criador de conteúdo, casa conectada, home office, setup gamer, estrada e escritório. Compre o kit inteiro com um clique.">')
body = ('<main>\n<section class="kits-hero"><div class="container"><p class="crumb"><a href="index.html">Início</a> / Kits</p>'
        '<p class="ach-kicker"><i aria-hidden="true"></i>Kits INFOLUX</p><h1>Kits prontos para <span>cada missão</span></h1>'
        '<p>Combinações montadas na INFOLUX. Cada item sai pelo preço normal da loja: o kit é só um atalho para comprar tudo de uma vez. '
        'Precisa de instalação? A INFOLUX instala em Serra Nova Dourada, Espigão do Leste e região.</p>'
        '<div class="kits-hero-cta"><a class="btn btn-primary" href="index.html#achador">Fazer o Achador de Soluções</a>'
        '<a class="btn btn-dark" href="https://wa.me/5566992070127?text=Ol%C3%A1%20Lucas%2C%20vim%20pelo%20site%20e%20quero%20ajuda%20para%20montar%20um%20kit" target="_blank" rel="noopener">Montar kit com um técnico</a></div></div></section>\n'
        '<section class="section kits-page"><div class="kit-grid">' + ''.join(kit_card(k) for k in kits) + '</div>'
        '<p class="kits-note">Preços por item, sem desconto de kit. Frete calculado no carrinho pelo CEP. Produtos enviados pelo distribuidor parceiro; prazo confirmado após o pagamento.</p></section>\n</main>')
(SITE/'kits.html').write_text(head + body + tail)
print('kits', len(kits), 'products', len(PRODUCTS), 'dropped', dropped)
for k in kits: print(' ', k['name'], k['total'], [(PRODUCTS[i['k']]['name'], i['qty'], PRODUCTS[i['k']]['price']) for i in k['items']])
