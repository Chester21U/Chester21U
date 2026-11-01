import json
import os
import sys
import urllib.request
from xml.sax.saxutils import escape

BG = "#07110d"
PANEL = "#0c1a14"
EDGE = "#1f3a2e"
GRID = "#13261d"
COPPER = "#c8894a"
CYAN = "#3cf2c4"
AMBER = "#f5c542"
TEXT = "#d7e4dc"
MUTED = "#6f8a7c"
GREEN = "#4ade80"
PALETA = [CYAN, AMBER, COPPER, GREEN, "#a78bfa", MUTED]
MONO = "ui-monospace, 'JetBrains Mono', 'Fira Code', 'Cascadia Code', Consolas, 'Courier New', monospace"

QUERY = """
query($login: String!) {
  user(login: $login) {
    repositories(ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC, first: 100) {
      totalCount
      nodes {
        stargazerCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name } }
        }
      }
    }
    contributionsCollection {
      totalCommitContributions
      contributionCalendar { totalContributions }
    }
  }
}
"""


def consultar(login, token):
    cuerpo = json.dumps({"query": QUERY, "variables": {"login": login}}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=cuerpo,
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json", "User-Agent": login},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        datos = json.load(r)
    if "errors" in datos:
        raise SystemExit(json.dumps(datos["errors"], ensure_ascii=False))
    return datos["data"]["user"]


def resumir(usuario):
    repos = usuario["repositories"]
    tam = {}
    for nodo in repos["nodes"]:
        for e in nodo["languages"]["edges"]:
            nombre = e["node"]["name"]
            tam[nombre] = tam.get(nombre, 0) + e["size"]
    total = sum(tam.values()) or 1
    orden = sorted(tam.items(), key=lambda x: x[1], reverse=True)
    top = [(n, s / total * 100) for n, s in orden[:5]]
    resto = sum(s for _, s in orden[5:]) / total * 100
    if resto > 0.05:
        top.append(("Otros", resto))
    cc = usuario["contributionsCollection"]
    return {
        "contribuciones": cc["contributionCalendar"]["totalContributions"],
        "commits": cc["totalCommitContributions"],
        "repos": repos["totalCount"],
        "estrellas": sum(n["stargazerCount"] for n in repos["nodes"]),
        "lenguajes": top,
    }


def marco(titulo, ancho, alto, contenido, extra_css=""):
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{ancho}" height="{alto}" viewBox="0 0 {ancho} {alto}" role="img" aria-label="{titulo}">
  <defs>
    <pattern id="p" width="16" height="16" patternUnits="userSpaceOnUse"><circle cx="2" cy="2" r="1" fill="{GRID}"/></pattern>
    <filter id="g" x="-20%" y="-40%" width="140%" height="180%"><feGaussianBlur stdDeviation="2" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
  </defs>
  <style>
    text{{font-family:{MONO}}}
    .led{{animation:led 1.8s ease-in-out infinite}}
    @keyframes led{{50%{{opacity:.2}}}}{extra_css}
  </style>
  <rect x="1" y="1" width="{ancho-2}" height="{alto-2}" rx="12" fill="{PANEL}" stroke="{EDGE}" stroke-width="1.5"/>
  <rect x="1" y="1" width="{ancho-2}" height="{alto-2}" rx="12" fill="url(#p)"/>
  <circle cx="26" cy="28" r="4" fill="{GREEN}" class="led"/>
  <text x="40" y="32" font-size="11.5" fill="{COPPER}" letter-spacing="2">{titulo}</text>
  <line x1="20" y1="46" x2="{ancho-20}" y2="46" stroke="{EDGE}"/>
{contenido}
</svg>
"""


def svg_actividad(d):
    celdas = [
        ("CONTRIBUCIONES", d["contribuciones"], "último año", CYAN),
        ("COMMITS", d["commits"], "último año", AMBER),
        ("REPOS PÚBLICOS", d["repos"], "propios", CYAN),
        ("ESTRELLAS", d["estrellas"], "recibidas", AMBER),
    ]
    partes = []
    for i, (etq, val, sub, color) in enumerate(celdas):
        x = 20 + (i % 2) * 205
        y = 58 + (i // 2) * 66
        partes.append(
            f'  <rect x="{x}" y="{y}" width="195" height="56" rx="6" fill="{BG}" stroke="{EDGE}"/>\n'
            f'  <text x="{x+12}" y="{y+19}" font-size="10" fill="{MUTED}" letter-spacing="1.5">{etq}</text>\n'
            f'  <text x="{x+12}" y="{y+45}" font-size="24" font-weight="700" fill="{color}" filter="url(#g)">{val}</text>\n'
            f'  <text x="{x+183}" y="{y+45}" font-size="10" fill="{MUTED}" text-anchor="end">{sub}</text>'
        )
    return marco("CH1 · ACTIVIDAD", 440, 200, "\n".join(partes))


def svg_lenguajes(d):
    langs = d["lenguajes"] or [("Sin datos", 100.0)]
    x0, ancho_barra = 20, 400
    partes = [f'  <rect x="{x0}" y="62" width="{ancho_barra}" height="12" rx="6" fill="{BG}" stroke="{EDGE}"/>']
    segs = []
    x = x0
    for i, (_, pct) in enumerate(langs):
        w = ancho_barra * pct / 100
        segs.append(f'<rect x="{x:.1f}" y="62" width="{w:.1f}" height="12" fill="{PALETA[i % len(PALETA)]}"/>')
        x += w
    partes.append(
        f'  <clipPath id="c"><rect x="{x0}" y="62" width="{ancho_barra}" height="12" rx="6"/></clipPath>\n'
        f'  <g clip-path="url(#c)"><g class="barra">{"".join(segs)}</g></g>'
    )
    for i, (nombre, pct) in enumerate(langs):
        col = i % 2
        fila = i // 2
        lx = 24 + col * 205
        ly = 106 + fila * 28
        partes.append(
            f'  <circle cx="{lx+5}" cy="{ly-4}" r="5" fill="{PALETA[i % len(PALETA)]}"/>\n'
            f'  <text x="{lx+18}" y="{ly}" font-size="13" fill="{TEXT}">{escape(nombre)}</text>\n'
            f'  <text x="{lx+188}" y="{ly}" font-size="12.5" fill="{MUTED}" text-anchor="end">{pct:.1f}%</text>'
        )
    css = """
    .barra{transform-box:fill-box;transform-origin:left;animation:crece 1.4s ease-out both}
    @keyframes crece{from{transform:scaleX(0)}to{transform:scaleX(1)}}"""
    return marco("CH2 · LENGUAJES", 440, 200, "\n".join(partes), css)


def main():
    login = os.environ.get("LOGIN") or os.environ["GITHUB_REPOSITORY_OWNER"]
    salida = sys.argv[1] if len(sys.argv) > 1 else "dist"
    os.makedirs(salida, exist_ok=True)
    d = resumir(consultar(login, os.environ["GH_TOKEN"]))
    with open(os.path.join(salida, "stats.svg"), "w", encoding="utf-8") as f:
        f.write(svg_actividad(d))
    with open(os.path.join(salida, "lenguajes.svg"), "w", encoding="utf-8") as f:
        f.write(svg_lenguajes(d))


if __name__ == "__main__":
    main()
