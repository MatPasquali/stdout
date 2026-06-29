"""Static site generator — turn edition JSON into a dark, modern tech journal.

Reads every `edicoes/*/edition.json` and writes a self-contained site under
`docs/` (the folder GitHub Pages can serve directly). Needs no API key, so the
site can be rebuilt from existing editions any time.

    docs/
    ├── index.html          # capa: what stdout is + list of editions
    ├── style.css
    ├── favicon.svg
    └── <date>/{pt,en}.html # each edition, in both languages
"""

from __future__ import annotations

import html
import json
from pathlib import Path
from urllib.parse import urlparse

from .layout import LABELS, group_sections

EDICOES = Path("edicoes")
DOCS = Path("docs")

# --- author / contacts -------------------------------------------------------
AUTHOR = "Mateus de Pasquali"
CONTACTS = {
    "github": "https://github.com/MatPasquali",
    "linkedin": "https://www.linkedin.com/in/mateuspasquali/",
}

# --- inline SVG icons (currentColor, no external requests) --------------------
ICONS = {
    "github": '<svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor" aria-hidden="true"><path d="M12 .5A11.5 11.5 0 0 0 .5 12a11.5 11.5 0 0 0 7.9 10.9c.6.1.8-.25.8-.56v-2c-3.2.7-3.9-1.36-3.9-1.36-.53-1.34-1.3-1.7-1.3-1.7-1.06-.72.08-.71.08-.71 1.17.08 1.79 1.2 1.79 1.2 1.04 1.79 2.73 1.27 3.4.97.1-.76.4-1.27.74-1.56-2.55-.29-5.24-1.28-5.24-5.69 0-1.26.45-2.28 1.19-3.09-.12-.29-.52-1.46.11-3.05 0 0 .97-.31 3.18 1.18a11 11 0 0 1 5.8 0c2.2-1.49 3.17-1.18 3.17-1.18.63 1.59.23 2.76.11 3.05.74.81 1.19 1.83 1.19 3.09 0 4.42-2.69 5.39-5.25 5.68.41.36.78 1.05.78 2.12v3.14c0 .31.21.67.81.56A11.5 11.5 0 0 0 23.5 12 11.5 11.5 0 0 0 12 .5Z"/></svg>',
    "linkedin": '<svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor" aria-hidden="true"><path d="M20.45 20.45h-3.56v-5.57c0-1.33-.03-3.04-1.85-3.04-1.86 0-2.14 1.45-2.14 2.94v5.67H9.35V9h3.42v1.56h.05c.48-.9 1.64-1.85 3.37-1.85 3.6 0 4.27 2.37 4.27 5.46v6.28ZM5.34 7.43a2.07 2.07 0 1 1 0-4.14 2.07 2.07 0 0 1 0 4.14ZM7.12 20.45H3.56V9h3.56v11.45ZM22.22 0H1.77C.8 0 0 .78 0 1.73v20.54C0 23.22.8 24 1.77 24h20.45c.98 0 1.78-.78 1.78-1.73V1.73C24 .78 23.2 0 22.22 0Z"/></svg>',
}

FAVICON = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
    '<rect width="64" height="64" rx="14" fill="#0a0e16"/>'
    '<path d="M17 22 L29 32 L17 42" fill="none" stroke="#3ddc97" stroke-width="5" '
    'stroke-linecap="round" stroke-linejoin="round"/>'
    '<rect x="34" y="37" width="15" height="5" rx="2.5" fill="#3ddc97"/>'
    "</svg>\n"
)

CSS = """\
:root{
  --bg:#0a0e16; --panel:#111726; --panel2:#0f1420;
  --ink:#e6e9f0; --muted:#8b93a7; --rule:#1d2638;
  --teal:#3ddc97; --blue:#5b8cff;
  --mono:"JetBrains Mono",ui-monospace,"SF Mono",Menlo,Consolas,monospace;
  --sans:"Inter",ui-sans-serif,system-ui,"Segoe UI",Roboto,sans-serif;
}
*{box-sizing:border-box}
html{font-size:18px}
body{margin:0;background:var(--bg);color:var(--ink);font-family:var(--sans);line-height:1.62;
  background-image:radial-gradient(circle at 50% -8%,rgba(61,220,151,.10),transparent 55%),
    radial-gradient(rgba(255,255,255,.022) 1px,transparent 1px);
  background-size:auto,22px 22px;background-attachment:fixed}
a{color:var(--teal);text-decoration:none}
.wrap{max-width:780px;margin:0 auto;padding:0 22px}

.topbar{max-width:780px;margin:0 auto;display:flex;align-items:center;justify-content:space-between;
  padding:20px 22px}
.brand{font-family:var(--mono);font-weight:700;font-size:1.05rem;color:var(--ink);letter-spacing:-.02em}
.brand .tilde{color:var(--teal)}
.brand .cursor{color:var(--teal);animation:blink 1.1s step-end infinite}
@keyframes blink{50%{opacity:0}}
.topbar .ghlink{font-family:var(--mono);font-size:.78rem;color:var(--muted);display:inline-flex;
  align-items:center;gap:7px;border:1px solid var(--rule);background:var(--panel);padding:6px 12px;border-radius:8px}
.topbar .ghlink:hover{border-color:var(--teal);color:var(--teal)}
.langs{font-family:var(--mono);font-size:.74rem;border:1px solid var(--rule);border-radius:999px;
  padding:4px;background:var(--panel)}
.langs a{color:var(--muted);padding:5px 11px;border-radius:999px;display:inline-block}
.langs a.active{color:var(--bg);background:var(--teal);font-weight:700}

.hero{max-width:780px;margin:6px auto 0;padding:18px 22px 0;text-align:center}
.logo{font-family:var(--mono);font-weight:700;font-size:3.6rem;letter-spacing:-.03em;line-height:1;
  background:linear-gradient(90deg,var(--ink) 10%,var(--teal) 65%,var(--blue));
  -webkit-background-clip:text;background-clip:text;color:transparent}
.logo .cursor{-webkit-text-fill-color:var(--teal);color:var(--teal)}
.tagline{color:var(--muted);margin:14px auto 0;max-width:560px;font-size:1.02rem}

.about{max-width:780px;margin:30px auto 0;padding:0 22px}
.terminal{background:var(--panel);border:1px solid var(--rule);border-radius:12px;overflow:hidden;
  box-shadow:0 24px 60px -34px rgba(0,0,0,.9)}
.tbar{display:flex;align-items:center;gap:7px;padding:11px 14px;border-bottom:1px solid var(--rule);background:var(--panel2)}
.dot{width:11px;height:11px;border-radius:50%}
.dot.r{background:#ff5f56}.dot.y{background:#ffbd2e}.dot.g{background:#27c93f}
.ttitle{font-family:var(--mono);font-size:.74rem;color:var(--muted);margin-left:6px}
.tbody{padding:17px 19px;font-family:var(--mono);font-size:.82rem;line-height:1.75}
.tbody .prompt{color:var(--teal);font-weight:700;margin-right:8px}
.tbody .out{color:var(--muted);margin:9px 0 0}
.tbody .out b{color:var(--ink);font-weight:600}
.pipeline{display:flex;flex-wrap:wrap;align-items:center;justify-content:center;gap:9px;
  margin:18px 0 0;font-family:var(--mono);font-size:.72rem}
.chip{border:1px solid var(--rule);background:var(--panel);color:var(--ink);padding:6px 11px;border-radius:7px;letter-spacing:.02em}
.arrow{color:var(--teal);font-weight:700}

.edition-date{margin:26px 0 0;font-family:var(--mono);font-size:.74rem;color:var(--muted);
  letter-spacing:.14em;text-transform:uppercase}
.section{display:flex;align-items:center;gap:9px;margin:40px 0 2px;font-family:var(--mono);font-size:.82rem;
  text-transform:uppercase;letter-spacing:.12em;color:var(--teal)}
.section::before{content:"//";color:var(--muted)}
.story{padding:21px 0;border-bottom:1px solid var(--rule)}
.story .src{display:inline-block;font-family:var(--mono);font-size:.64rem;color:var(--teal);
  border:1px solid var(--rule);background:var(--panel);padding:3px 9px;border-radius:6px;
  text-transform:uppercase;letter-spacing:.07em;margin-bottom:11px}
.story h3{margin:0 0 7px;font-size:1.3rem;line-height:1.3;font-weight:600}
.story h3 a{color:var(--ink)}
.story h3 a:hover{color:var(--teal)}
.story p{margin:0;color:#c7cdda}
.refs{margin:10px 0 0;padding-left:26px;color:var(--muted)}
.refs li{padding:8px 0;font-size:.84rem;line-height:1.5}
.refs .ref-src{display:inline-block;font-family:var(--mono);font-size:.62rem;color:var(--teal);
  text-transform:uppercase;letter-spacing:.06em;margin-right:9px}
.refs a{color:#c7cdda}
.refs a:hover{color:var(--teal)}
.refs .ref-url{font-family:var(--mono);font-size:.7rem;color:var(--muted);margin-left:9px;word-break:break-all}
.badge{display:inline-block;font-family:var(--mono);font-size:.6rem;font-weight:700;letter-spacing:.1em;
  text-transform:uppercase;color:var(--bg);background:var(--teal);padding:3px 8px;border-radius:5px}
.weekly-title{margin:12px 0 2px;font-family:var(--mono);font-weight:700;font-size:2rem;letter-spacing:-.02em;
  background:linear-gradient(90deg,var(--ink) 20%,var(--teal),var(--blue));
  -webkit-background-clip:text;background-clip:text;color:transparent}
.weekly-range{font-family:var(--mono);font-size:.78rem;color:var(--muted);letter-spacing:.08em}
.weekly-intro{margin:18px 0 0;font-size:1.06rem;line-height:1.6;color:var(--ink);
  border-left:2px solid var(--teal);padding-left:15px}
.weekly-label .badge{margin-right:7px}

.editions{list-style:none;margin:8px 0 0;padding:0}
.editions li{display:flex;align-items:center;gap:14px;padding:17px 0;border-bottom:1px solid var(--rule)}
.editions .date{font-family:var(--mono);font-weight:700;color:var(--ink)}
.editions .links{display:flex;gap:8px}
.editions .links a{font-family:var(--mono);font-size:.76rem;border:1px solid var(--rule);
  padding:4px 11px;border-radius:6px;background:var(--panel)}
.editions .links a:hover{border-color:var(--teal)}
.editions .count{margin-left:auto;color:var(--muted);font-size:.78rem;font-family:var(--mono)}

.foot{max-width:780px;margin:50px auto 36px;padding:28px 22px 0;border-top:1px solid var(--rule);text-align:center}
.contacts{display:flex;justify-content:center;flex-wrap:wrap;gap:10px}
.contacts a{display:inline-flex;align-items:center;gap:8px;color:var(--ink);font-family:var(--mono);
  font-size:.8rem;border:1px solid var(--rule);background:var(--panel);padding:9px 15px;border-radius:9px}
.contacts a:hover{border-color:var(--teal);color:var(--teal)}
.contacts svg{flex:none}
.credit,.byline{color:var(--muted);font-size:.78rem;margin-top:16px}
.byline strong{color:var(--ink)} .byline code{font-family:var(--mono);color:var(--teal)}

@media(max-width:560px){
  html{font-size:17px}.logo{font-size:2.5rem}
  .topbar .ghlink span{display:none}.contacts a span{display:none}
}
"""


def _esc(text) -> str:
    return html.escape(str(text or ""))


def _domain(url: str) -> str:
    """Bare hostname of a URL — shows the reader where a reference came from."""
    try:
        host = urlparse(url).netloc
        return host[4:] if host.startswith("www.") else host
    except Exception:  # noqa: BLE001
        return url


def _doc(title: str, body: str, base: str = "", lang: str = "pt") -> str:
    return (
        f'<!doctype html>\n<html lang="{lang}">\n<head>\n'
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{_esc(title)}</title>\n"
        f'<link rel="icon" type="image/svg+xml" href="{base}favicon.svg">\n'
        '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
        '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700'
        '&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">\n'
        f'<link rel="stylesheet" href="{base}style.css">\n'
        "</head>\n<body>\n" + body + "\n</body>\n</html>\n"
    )


def _brand(base: str) -> str:
    return (
        f'<a class="brand" href="{base}index.html">'
        '<span class="tilde">~/</span>stdout<span class="cursor">_</span></a>'
    )


def _footer(credits: str = "") -> str:
    links = (
        f'<a href="{CONTACTS["github"]}" target="_blank" rel="noopener" aria-label="GitHub">'
        f'{ICONS["github"]}<span>GitHub</span></a>'
        f'<a href="{CONTACTS["linkedin"]}" target="_blank" rel="noopener" aria-label="LinkedIn">'
        f'{ICONS["linkedin"]}<span>LinkedIn</span></a>'
    )
    credit = f'<div class="credit">{_esc(credits)}</div>' if credits else ""
    return (
        '<footer class="foot">'
        f'<div class="contacts">{links}</div>'
        f"{credit}"
        f'<div class="byline">Feito por <strong>{_esc(AUTHOR)}</strong> · '
        "gerado automaticamente por <code>stdout</code></div>"
        "</footer>"
    )


def _about() -> str:
    steps = ["coleta", "ranking", "redação", "revisão", "publicação"]
    chips = ' <span class="arrow">→</span> '.join(f'<span class="chip">{s}</span>' for s in steps)
    return (
        '<section class="about"><div class="terminal">'
        '<div class="tbar"><span class="dot r"></span><span class="dot y"></span>'
        '<span class="dot g"></span><span class="ttitle">stdout@portfolio: ~</span></div>'
        '<div class="tbody">'
        '<div><span class="prompt">$</span>stdout --how</div>'
        '<div class="out">Todo dia eu coleto notícias e papers de <b>arXiv</b>, '
        '<b>Hacker News</b>, <b>RSS</b> e <b>GitHub</b>, ranqueio por relevância '
        "(heurística, sem IA), e uma IA <b>redige e revisa</b> cada matéria em "
        "português e inglês. Tudo automático, publicado aqui.</div>"
        "</div></div>"
        f'<div class="pipeline">{chips}</div>'
        "</section>"
    )


def _edition_html(data: dict, lang: str) -> str:
    L = LABELS[lang]
    day = data["date"]
    other_active = "active" if lang == "en" else ""
    pt_active = "active" if lang == "pt" else ""
    body = [
        '<div class="topbar">',
        _brand("../"),
        '<nav class="langs">'
        f'<a class="{pt_active}" href="pt.html">PT</a>'
        f'<a class="{other_active}" href="en.html">EN</a></nav>',
        "</div>",
        '<main class="wrap">',
    ]
    if data.get("weekly"):
        body.append(f'<span class="badge">{_esc(L["weekly_badge"])}</span>')
        body.append(f'<h1 class="weekly-title">{_esc(L["weekly_title"])}</h1>')
        body.append(f'<div class="weekly-range">{_esc(data.get("range", ""))}</div>')
        intro = (data.get("intro") or {}).get(lang, "")
        if intro:
            body.append(f'<p class="weekly-intro">{_esc(intro)}</p>')
    else:
        body.append(f'<div class="edition-date">{_esc(day)}</div>')
    for heading, group in group_sections(data["items"], lang):
        if not group:
            continue
        body.append(f'<h2 class="section">{_esc(heading)}</h2>')
        for r in group:
            body.append('<article class="story">')
            body.append(f'<span class="src">{_esc(r["source"])}</span>')
            body.append(
                f'<h3><a href="{_esc(r["url"])}" target="_blank" rel="noopener">'
                f'{_esc(r["title"])}</a></h3>'
            )
            body.append(f"<p>{_esc(r[lang])}</p>")
            body.append("</article>")

    # References — explicit attribution: source, title and origin domain.
    body.append(f'<h2 class="section">{_esc(L["references"])}</h2>')
    body.append('<ol class="refs">')
    for r in data["items"]:
        body.append(
            f'<li><span class="ref-src">{_esc(r["source"])}</span>'
            f'<a href="{_esc(r["url"])}" target="_blank" rel="noopener">{_esc(r["title"])}</a>'
            f'<span class="ref-url">{_esc(_domain(r["url"]))}</span></li>'
        )
    body.append("</ol>")
    body.append("</main>")
    body.append(_footer(data.get("credits", "")))
    page_title = f"stdout · {L['weekly_title']}" if data.get("weekly") else f"stdout · {day}"
    return _doc(page_title, "\n".join(body), base="../", lang=lang)


def _index_html(editions: list[dict]) -> str:
    body = [
        '<div class="topbar">',
        _brand(""),
        f'<a class="ghlink" href="{CONTACTS["github"]}" target="_blank" rel="noopener">'
        f'{ICONS["github"]}<span>GitHub</span></a>',
        "</div>",
        '<header class="hero">',
        '<div class="logo">stdout<span class="cursor">_</span></div>',
        '<p class="tagline">Um jornal diário do mundo tech: coletado, curado e '
        "redigido automaticamente por IA. Em português e inglês.</p>",
        "</header>",
        _about(),
        '<main class="wrap">',
        '<h2 class="section">Edições · Editions</h2>',
        '<ul class="editions">',
    ]
    for data in editions:
        day = _esc(data["date"])
        folder = _esc(data.get("_folder", data["date"]))
        n = len(data["items"])
        if data.get("weekly"):
            tag = (f'<span class="count weekly-label"><span class="badge">Semana</span> '
                   f'Resumo da Semana ({_esc(data.get("range", ""))})</span>')
        else:
            tag = f'<span class="count">{n} matérias</span>'
        body.append(
            f'<li><span class="date">{day}</span>'
            f'<span class="links"><a href="{folder}/pt.html">PT</a>'
            f'<a href="{folder}/en.html">EN</a></span>'
            f'{tag}</li>'
        )
    body.append("</ul></main>")
    body.append(_footer())
    return _doc("stdout · jornal tech automático", "\n".join(body), base="")


def build_site() -> Path:
    DOCS.mkdir(exist_ok=True)
    (DOCS / "style.css").write_text(CSS, encoding="utf-8")
    (DOCS / "favicon.svg").write_text(FAVICON, encoding="utf-8")
    # .nojekyll tells GitHub Pages to serve the files as-is (no Jekyll build).
    (DOCS / ".nojekyll").write_text("", encoding="utf-8")

    editions: list[dict] = []
    for jf in sorted(EDICOES.glob("*/edition.json")):
        data = json.loads(jf.read_text(encoding="utf-8"))
        data["_folder"] = jf.parent.name
        editions.append(data)
        out = DOCS / data["_folder"]
        out.mkdir(exist_ok=True)
        (out / "pt.html").write_text(_edition_html(data, "pt"), encoding="utf-8")
        (out / "en.html").write_text(_edition_html(data, "en"), encoding="utf-8")

    editions.sort(key=lambda d: (d["date"], d.get("weekly", False)), reverse=True)
    (DOCS / "index.html").write_text(_index_html(editions), encoding="utf-8")
    print(f"  Site gerado em {DOCS}/ ({len(editions)} edição(ões))")
    return DOCS
