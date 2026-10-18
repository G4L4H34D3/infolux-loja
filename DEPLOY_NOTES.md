# INFOLUX deploy package

Structure:
- `/` → redirects to `/produtos/`
- `/produtos/` → full store

WhatsApp: +55 66 99207-0127 (wa.me/5566992070127), greeting addresses Lucas.

## GitHub Pages (intended)

Repo: `G4L4H34D3/infolux-loja` (public), Pages from `main` / root.

Live URLs after enable:
- `https://g4l4h34d3.github.io/infolux-loja/` (project pages — note path)
- Custom domain `infolux.app` (apex) pointing at GitHub Pages

### DNS at Name.com (registrar for infolux.app)

For **apex** `infolux.app` → GitHub Pages A records:
```
A     @     185.199.108.153
A     @     185.199.109.153
A     @     185.199.110.153
A     @     185.199.111.153
```
Optional www:
```
CNAME  www  g4l4h34d3.github.io
```
In the repo: `CNAME` file with `infolux.app` (already in this package).
In GitHub → Settings → Pages → Custom domain → `infolux.app` → enable HTTPS.

This replaces the old Lovable site on the root of infolux.app.

## Blocked on this box

- `gh` is **not** logged in (`gh auth login` required for HTTPS git push / repo create).
- Cursor GitHub MCP (account `G4L4H34D3`) can read repos but **cannot** create repositories or push files.
- No Netlify / Vercel / Wrangler tokens found.

After `gh auth login` as G4L4H34D3:

```bash
cd /workspace/infolux/deploy
gh repo create infolux-loja --public --source=. --remote=origin --push
gh api -X POST repos/G4L4H34D3/infolux-loja/pages -f build_type=legacy -f source='{"branch":"main","path":"/"}'
```

Then set DNS as above.

## Current state (2026-10-18)

- `infolux.app` (apex) = Lovable institutional site (not in this repo).
- `loja.infolux.app` = this repo (CNAME). Root `/` → `/produtos/`.
- `404.html` repairs legacy paths without the `/produtos/` prefix
  (`/categorias/…`, `/empresa.html`, `/slug-do-produto.html`) and falls back to `/produtos/`.

## FX v2 (front-end)

All effects live in `produtos/assets/styles.css` (section "INFOLUX FX v2") and
`produtos/assets/app.js` (initParallax, initTilt, initCounters, initReveal, initDynamicCards,
initWhatsAppFloat). No external libraries. Everything is disabled under `prefers-reduced-motion`.
Assets use `?v=YYYYMMDD` cache-busting — bump it in every page when CSS/JS change.
New home section: `#diferenciais` ("Mais que uma loja online").
