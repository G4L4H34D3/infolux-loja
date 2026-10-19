#!/usr/bin/env python3
"""Remove unverified install-ease claims ('fácil instalação', 'instalação fácil/simples/rápida', 'fácil de instalar')
from product texts site-wide (products.json, catalog shards, product pages). Idempotent. 2026-10-18 (Apollo)."""
import re, sys
from pathlib import Path
SITE = Path('/workspace/infolux/deploy/produtos')
P = r'(?:f[áa]cil(?: de)? instala[çc][ãa]o|instala[çc][ãa]o (?:f[áa]cil|simples|r[áa]pida)|f[áa]cil de instalar)'
I = re.I
SPECIAL = [  # whole-phrase rewrites where the generic rules would read badly
  (r'\s*F[áa]cil instala[çc][ãa]o e opera[çc][ãa]o\.', ''),
  (r'\s*F[áa]cil instala[çc][ãa]o e economia\.', ''),
  (r'Conforto, resist[êe]ncia e f[áa]cil instala[çc][ãa]o para', 'Conforto e resistência para'),
  (r'(?:>|&gt;)\s*F[áa]cil instala[çc][ãa]o\s*[–-]\s*basta plugar na tomada', ''),
  (r' e f[áa]cil instala[çc][ãa]o USB', ' e conexão USB'),
  (r' e de instala[çc][ãa]o simples, f[áa]ceis de levar', ' e fáceis de levar'),
  (r'-\s*Instala[çc][ãa]o r[áa]pida e sem necessidade de configura[çc][ãa]o\s*', ''),
  (r'F[áa]cil instala[çc][ãa]o:\s*tecnologia', 'Tecnologia'),
]
GEN = [
  (rf'(^|[.!?>•]\s*|"\s*){P} e (\w)', lambda m: m.group(1) + m.group(2).upper()),  # "Fácil instalação e X" -> "X"
  (rf',\s*{P} e ', ' e '),            # ", fácil instalação e X" -> " e X"
  (rf',\s*{P}(?=\s*[,.!;])', ''),     # ", fácil instalação," / "." -> drop
  (rf',\s*{P}\s+', ', '),             # ", fácil instalação plug and play" -> ", plug and play"
  (rf'\s+e\s+{P}(?=\s*[,.!;])', ''),  # "resistente e fácil de instalar." -> "resistente."
  (rf'(^|[.!?]\s*){P}[,.!]?\s*', lambda m: m.group(1)),  # standalone sentence
]
def clean(s):
    for a, b in SPECIAL: s = re.sub(a, b, s, flags=I)
    for a, b in GEN: s = re.sub(a, b, s, flags=I | re.M)
    return s
files = [SITE/'data/products.json', *sorted((SITE/'data/catalog').glob('*.json')), *sorted((SITE/'produtos').glob('*.html'))]
changed = {}
for f in files:
    s = f.read_text(encoding='utf-8')
    if not re.search(P, s, I): continue
    t = clean(s)
    if t != s: f.write_text(t, encoding='utf-8'); changed[f] = len(re.findall(P, s, I))
left = [str(f) for f in SITE.rglob('*') if f.suffix in ('.html', '.json', '.js') and re.search(P, f.read_text(encoding='utf-8', errors='ignore'), I)]
import json
prods = json.loads((SITE/'data/products.json').read_text())
nprod = sum(1 for f in changed if f.parent.name == 'produtos')
print(f'files changed {len(changed)} | product pages {nprod} | leftover files {len(left)}'); [print(' LEFT', x) for x in left[:20]]
