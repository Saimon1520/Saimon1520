"""Genera las tarjetas SVG del perfil (estadísticas, lenguajes y actividad) con datos reales.

Cuenta TODOS los repos del usuario (públicos y privados) si el token lo permite, pero
nunca escribe nombres de repos privados: solo totales. Tema: tokyonight.

Uso: GH_TOKEN=... python3 generate_cards.py <usuario> <carpeta_salida>
"""
import datetime as dt
import json
import os
import sys
import urllib.request
from collections import Counter
from xml.sax.saxutils import escape

USER, OUT = sys.argv[1], sys.argv[2]
TOKEN = os.environ["GH_TOKEN"]
BG, BORDER, TITLE, TEXT, ICON = "#1a1b27", "#2f3248", "#70a5fd", "#38bdae", "#bf91f3"
FONT = "font-family='Segoe UI, Ubuntu, Helvetica, Arial, sans-serif'"
SKIP_LANGS = {"Jupyter Notebook", "ShaderLab"}  # código generado (notebooks, Unity)
LANG_COLORS = {
    "TypeScript": "#3178c6", "JavaScript": "#f1e05a", "Python": "#3572A5", "C#": "#178600",
    "Java": "#b07219", "PHP": "#4F5D95", "HTML": "#e34c26", "CSS": "#663399", "Go": "#00ADD8",
    "C++": "#f34b7d", "Shell": "#89e051", "GDScript": "#355570", "Kotlin": "#A97BFF",
    "Dockerfile": "#384d54", "SCSS": "#c6538c", "Vue": "#41b883",
}


def api(path):
    out, url = [], f"https://api.github.com{path}"
    while url:
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {TOKEN}",
                                                   "Accept": "application/vnd.github+json"})
        try:
            with urllib.request.urlopen(req) as r:
                data = json.load(r)
                link = r.headers.get("Link", "")
        except urllib.error.HTTPError as e:
            if e.code == 409:  # repo vacío
                return []
            raise
        if isinstance(data, dict):
            return data
        out += data
        url = next((p.split(";")[0].strip(" <>") for p in link.split(",") if 'rel="next"' in p), None)
    return out


repos = [r for r in api("/user/repos?per_page=100&affiliation=owner")
         if not r["fork"] and r["name"] != USER]
since = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=365)).date()

langs, commits_total, commits_year, prs = Counter(), 0, 0, 0
monthly = Counter()
for r in repos:
    for lang, size in api(f"/repos/{r['full_name']}/languages").items():
        if lang not in SKIP_LANGS:
            langs[lang] += size
    for c in api(f"/repos/{r['full_name']}/commits?author={USER}&per_page=100"):
        day = dt.date.fromisoformat(c["commit"]["author"]["date"][:10])
        commits_total += 1
        if day >= since:
            commits_year += 1
            monthly[day.strftime("%Y-%m")] += 1
    prs += sum(1 for p in api(f"/repos/{r['full_name']}/pulls?state=all&per_page=100") if p["user"]["login"] == USER)

public = sum(1 for r in repos if not r["private"])
first_year = min(r["created_at"][:4] for r in repos)


UPDATED = dt.datetime.now(dt.timezone.utc).strftime("Updated %Y-%m-%d %H:%M UTC")


def card(w, h, title, body):
    return (f"<svg xmlns='http://www.w3.org/2000/svg' width='{w}' height='{h}' viewBox='0 0 {w} {h}' {FONT}>"
            f"<rect x='0.5' y='0.5' rx='6' width='{w - 1}' height='{h - 1}' fill='{BG}' stroke='{BORDER}'/>"
            f"<text x='25' y='35' fill='{TITLE}' font-size='18' font-weight='600'>{escape(title)}</text>"
            f"{body}<text x='{w - 12}' y='{h - 10}' fill='{TEXT}' fill-opacity='0.55' font-size='10' text-anchor='end'>{UPDATED}</text></svg>")


rows = [
    ("Total commits", f"{commits_total:,}"),
    ("Commits (last 12 months)", f"{commits_year:,}"),
    ("Repositories", f"{len(repos)} ({public} public)"),
    ("Pull requests", f"{prs}"),
    ("Languages used", f"{len(langs)}"),
    ("Building on GitHub since", first_year),
]
body = "".join(
    f"<circle cx='31' cy='{68 + i * 28}' r='5' fill='{ICON}'/>"
    f"<text x='46' y='{73 + i * 28}' fill='{TEXT}' font-size='14' font-weight='600'>{escape(k)}:</text>"
    f"<text x='420' y='{73 + i * 28}' fill='{TEXT}' font-size='14' font-weight='700' text-anchor='end'>{escape(v)}</text>"
    for i, (k, v) in enumerate(rows))
open(f"{OUT}/stats.svg", "w").write(card(450, 60 + len(rows) * 28 + 22, "Saimon's GitHub Stats", body))

top = langs.most_common(8)
total = sum(s for _, s in top) or 1
bar, x = "", 25
for lang, size in top:
    w = 400 * size / total
    bar += f"<rect x='{x:.1f}' y='55' width='{w:.1f}' height='8' fill='{LANG_COLORS.get(lang, ICON)}'/>"
    x += w
items = "".join(
    f"<circle cx='{31 + (i % 2) * 205}' cy='{88 + (i // 2) * 24}' r='5' fill='{LANG_COLORS.get(l, ICON)}'/>"
    f"<text x='{43 + (i % 2) * 205}' y='{93 + (i // 2) * 24}' fill='{TEXT}' font-size='13'>{escape(l)} {100 * s / total:.1f}%</text>"
    for i, (l, s) in enumerate(top))
clip = "<clipPath id='c'><rect x='25' y='55' width='400' height='8' rx='4'/></clipPath>"
open(f"{OUT}/top-langs.svg", "w").write(
    card(450, 102 + ((len(top) + 1) // 2) * 24, "Most Used Languages",
         f"<defs>{clip}</defs><g clip-path='url(#c)'>{bar}</g>{items}"))

today = dt.date.today()
months = [f"{(today.year * 12 + today.month - 1 - k) // 12}-{(today.month - 1 - k) % 12 + 1:02d}" for k in range(11, -1, -1)]
values = [monthly[m] for m in months]
W, H, L, T, PW, PH = 900, 310, 60, 60, 810, 190
peak = max(values) or 1
pts = [(L + i * PW / 11, T + PH - PH * v / peak) for i, v in enumerate(values)]
line = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
area = f"{L},{T + PH} {line} {L + PW},{T + PH}"
grid = "".join(f"<line x1='{L}' x2='{L + PW}' y1='{T + PH * k / 4:.1f}' y2='{T + PH * k / 4:.1f}' stroke='{BORDER}'/>"
               f"<text x='{L - 10}' y='{T + PH * k / 4 + 4:.1f}' fill='{TEXT}' font-size='11' text-anchor='end'>{round(peak * (4 - k) / 4)}</text>"
               for k in range(5))
labels = "".join(f"<text x='{x:.1f}' y='{T + PH + 22}' fill='{TEXT}' font-size='11' text-anchor='middle'>"
                 f"{dt.date.fromisoformat(m + '-01').strftime('%b %y')}</text>" for (x, _), m in zip(pts, months))
dots = "".join(f"<circle cx='{x:.1f}' cy='{y:.1f}' r='4' fill='{ICON}'/>" for x, y in pts)
open(f"{OUT}/activity.svg", "w").write(card(
    W, H, f"Commits per month — last 12 months ({commits_year:,} total)",
    f"{grid}<polygon points='{area}' fill='{TITLE}' fill-opacity='0.15'/>"
    f"<polyline points='{line}' fill='none' stroke='{TITLE}' stroke-width='3'/>{dots}{labels}"))

print(f"repos={len(repos)} public={public} commits={commits_total} year={commits_year} prs={prs} langs={top}")
