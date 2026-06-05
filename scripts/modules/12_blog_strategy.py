"""
Module 12 — Estrategia de contenidos blog + interlinking (informe ejecutivo ES).

Genera un único informe profesional con hasta 5 propuestas de post bajo /blog/
y matriz de enlazado interno anti-canibalización.
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from lib.blog_strategy_utils import (  # noqa: E402
    best_matching_page,
    classify_url,
    coverage_ratio,
    is_transactional_service_query,
    normalize_terms,
    slugify,
    title_from_query,
    url_path,
)
from lib.common import latest_file, load_project_config, save_md, timestamp  # noqa: E402

INTENT_ES = {
    "informational": "informativa",
    "local": "local",
    "commercial": "comercial",
    "navigational": "de marca",
    "mixed": "mixta",
}

PRIORITY_ES = {"high": "Alta", "medium": "Media", "low": "Baja"}


def _read_csv(pattern: str) -> pd.DataFrame | None:
    path = latest_file(pattern)
    if not path or not Path(path).exists():
        return None
    return pd.read_csv(path)


def _bullet(lines: list[str], text: str) -> None:
    lines.append(f"- {text}")


def _load_pages(semantic: pd.DataFrame, blog_prefix: str) -> list[dict]:
    pages = []
    for _, row in semantic.iterrows():
        path = url_path(row.get("url", ""))
        pages.append(
            {
                "url": str(row.get("url", "")),
                "path": path,
                "title": str(row.get("title", "")),
                "primary_h1": str(row.get("primary_h1", "")),
                "topic_keywords": str(row.get("topic_keywords", "")),
                "word_count": int(row.get("word_count", 0) or 0),
                "kind": classify_url(path, blog_prefix),
            }
        )
    return pages


def _query_intent_map(intent_matrix: pd.DataFrame | None) -> dict[str, str]:
    if intent_matrix is None or intent_matrix.empty or "query" not in intent_matrix.columns:
        return {}
    out: dict[str, str] = {}
    for _, row in intent_matrix.iterrows():
        q = str(row.get("query", "")).strip().lower()
        if q:
            out[q] = str(row.get("intent", "mixed"))
    return out


def _priority(impressions: int, clicks: int, position: float, action: str) -> str:
    if impressions >= 80 and clicks <= 2 and action == "CREATE":
        return "high"
    if impressions >= 50 or action == "CREATE":
        return "medium"
    return "low"


def _decide_action(
    query: str,
    coverage: float,
    best_page: dict | None,
    best_score: float,
    blog_prefix: str,
    origin: str,
    missing_threshold: float,
    expand_threshold: float,
) -> tuple[str, str, str]:
    """Returns action, target_url, legacy_note."""
    if best_page and best_page["kind"] == "service":
        return "CREATE", "", ""

    if best_page and best_page["kind"] == "blog" and best_score >= expand_threshold:
        return "EXPAND", best_page["url"], ""

    if best_page and best_page["kind"] == "legacy_blog" and best_score >= 0.25:
        slug = slugify(query)
        return "MIGRATE", f"{origin.rstrip('/')}{blog_prefix.rstrip('/')}/{slug}/", best_page["url"]

    if coverage < expand_threshold:
        slug = slugify(query)
        return "CREATE", f"{origin.rstrip('/')}{blog_prefix.rstrip('/')}/{slug}/", ""

    if best_page and best_score >= missing_threshold:
        if best_page["kind"] == "blog":
            return "EXPAND", best_page["url"], ""
        slug = slugify(query)
        return "CREATE", f"{origin.rstrip('/')}{blog_prefix.rstrip('/')}/{slug}/", ""

    slug = slugify(query)
    return "CREATE", f"{origin.rstrip('/')}{blog_prefix.rstrip('/')}/{slug}/", ""


def _build_interlinks(
    suggestion: dict,
    cfg: dict,
    origin: str,
) -> list[dict]:
    links: list[dict] = []
    target = suggestion.get("target_url", "")
    if not target:
        return links

    for svc in cfg.get("service_pages", []):
        path = svc.get("path", "")
        anchors = svc.get("anchors") or ["related service"]
        links.append(
            {
                "from": target,
                "to": f"{origin.rstrip('/')}{path}",
                "anchor": anchors[0],
                "type": "Conversión (post → servicio)",
                "note": "Anchor transaccional; no repetir la KW exacta del post en la landing.",
            }
        )

    for hub in cfg.get("hub_pages", []):
        path = hub.get("path", "/our-services/")
        anchor = (hub.get("anchors") or ["our services"])[0]
        links.append(
            {
                "from": target,
                "to": f"{origin.rstrip('/')}{path}",
                "anchor": anchor,
                "type": "Arquitectura (post → hub)",
                "note": "Refuerza la jerarquía servicios sin canibalizar.",
            }
        )

    links.append(
        {
            "from": f"{origin.rstrip('/')}/",
            "to": target,
            "anchor": suggestion.get("hub_anchor", "sustainable renovation guide"),
            "type": "Opcional (home → post)",
            "note": "Solo si encaja en el menú o bloque editorial; anchor informativo.",
        }
    )

    for hub in cfg.get("hub_pages", []):
        path = hub.get("path", "/our-services/")
        links.append(
            {
                "from": f"{origin.rstrip('/')}{path}",
                "to": target,
                "anchor": suggestion.get("hub_anchor", "related guide"),
                "type": "Arquitectura (hub → post)",
                "note": "Tras publicar el post.",
            }
        )

    return links


def _collect_candidates(
    gsc: pd.DataFrame,
    pages: list[dict],
    intent_map: dict[str, str],
    cfg: dict,
    editorial: list[dict],
    gap_queries: set[str],
) -> list[dict]:
    blog_prefix = cfg.get("blog_path_prefix", "/blog/")
    min_imp = int(cfg.get("min_impressions", 50))
    missing_th = float(cfg.get("coverage_missing_threshold", 0.15))
    expand_th = float(cfg.get("coverage_expand_threshold", 0.35))
    prefer = set(cfg.get("prefer_intents", ["informational", "local", "mixed"]))
    origin = load_project_config()["project"]["origin"]

    all_page_terms: set[str] = set()
    for p in pages:
        all_page_terms.update(normalize_terms(p.get("title", "")))
        all_page_terms.update(normalize_terms(p.get("primary_h1", "")))
        all_page_terms.update(normalize_terms(p.get("topic_keywords", "")))

    gsc = gsc.copy()
    gsc["impressions"] = pd.to_numeric(gsc.get("impressions", 0), errors="coerce").fillna(0)
    gsc["clicks"] = pd.to_numeric(gsc.get("clicks", 0), errors="coerce").fillna(0)
    gsc["position"] = pd.to_numeric(gsc.get("position", 0), errors="coerce").fillna(0)

    agg = (
        gsc.groupby("query", dropna=False)
        .agg(impressions=("impressions", "sum"), clicks=("clicks", "sum"), avg_position=("position", "mean"))
        .reset_index()
    )
    agg = agg[agg["impressions"] >= min_imp].sort_values(["impressions", "clicks"], ascending=[False, True])

    agg["_gap_boost"] = agg["query"].astype(str).str.lower().isin(gap_queries)
    agg = agg.sort_values(["_gap_boost", "impressions", "clicks"], ascending=[False, False, True])

    seen_queries: set[str] = set()
    candidates: list[dict] = []

    for _, row in agg.iterrows():
        query = str(row["query"]).strip()
        ql = query.lower()
        if not query or ql in seen_queries:
            continue

        best_page, best_score = best_matching_page(query, pages)
        intent = intent_map.get(ql, "mixed")

        if is_transactional_service_query(query, cfg.get("service_pages", [])):
            continue
        if best_page and best_page["kind"] == "service" and best_score >= 0.35:
            continue
        if best_page and best_page["kind"] == "hub" and best_score >= 0.5 and ql not in gap_queries:
            if intent in ("commercial", "navigational") or "studio rethink" in ql:
                continue

        if intent == "navigational":
            continue
        if intent not in prefer:
            continue
        if intent == "commercial" and ql not in gap_queries and "how" not in ql and "guide" not in ql:
            if not any(x in ql for x in ("eco", "sustainable", "passive", "renovation", "finca", "villa")):
                continue

        cov = coverage_ratio(query, all_page_terms)
        if cov >= expand_th and ql not in gap_queries and intent not in ("informational",):
            if best_page and best_page["kind"] in ("service", "blog"):
                continue
            if best_page and best_page["kind"] == "hub":
                if not any(x in ql for x in ("eco", "sustainable", "passive", "renovation", "finca", "villa", "furniture")):
                    continue

        action, target_url, legacy = _decide_action(
            query, cov, best_page, best_score, blog_prefix, origin, missing_th, expand_th
        )

        if action == "EXPAND" and best_page and best_page["kind"] == "service":
            action = "CREATE"
            slug = slugify(query)
            target_url = f"{origin.rstrip('/')}{blog_prefix.rstrip('/')}/{slug}/"
            legacy = ""

        seen_queries.add(ql)
        slug = slugify(query)
        suffix = ": A Complete Guide" if "guide" not in query.lower() else ""
        if "ibiza" not in query.lower():
            suffix = ": A Practical Guide for Ibiza"
        title = title_from_query(query) + suffix
        candidates.append(
            {
                "query": query,
                "proposed_title": title,
                "proposed_slug": slug,
                "target_url": target_url,
                "action": action,
                "legacy_url": legacy,
                "impressions": int(row["impressions"]),
                "clicks": int(row["clicks"]),
                "avg_position": round(float(row["avg_position"]), 2),
                "coverage_ratio": round(cov, 2),
                "intent": intent,
                "priority": "high" if ql in gap_queries else _priority(
                    int(row["impressions"]), int(row["clicks"]), float(row["avg_position"]), action
                ),
                "data_source": "Google Search Console",
                "hub_anchor": f"guide to {query}" if len(query) < 40 else "related renovation guide",
            }
        )

    max_n = int(cfg.get("max_suggestions", 5))
    max_gsc = int(cfg.get("max_gsc_suggestions", 2))
    gsc_part = candidates[:max_gsc]

    for idea in editorial:
        if len(gsc_part) >= max_n:
            break
        q = str(idea.get("query", "")).strip()
        ql = q.lower()
        if not q or ql in seen_queries:
            continue
        slug = slugify(q)
        gsc_part.append(
            {
                "query": q,
                "proposed_title": str(idea.get("title", title_from_query(q))),
                "proposed_slug": slug,
                "target_url": f"{origin.rstrip('/')}{blog_prefix.rstrip('/')}/{slug}/",
                "action": "CREATE",
                "legacy_url": "",
                "impressions": 0,
                "clicks": 0,
                "avg_position": 0,
                "coverage_ratio": 0,
                "intent": str(idea.get("intent", "informational")),
                "priority": str(idea.get("priority", "medium")),
                "data_source": "Propuesta editorial (sin dato GSC en el periodo)",
                "hub_anchor": str(idea.get("hub_anchor", "related guide")),
            }
        )
        seen_queries.add(ql)

    return gsc_part[:max_n]


def _action_label(action: str) -> str:
    return {
        "CREATE": "Publicar nuevo artículo en `/blog/`",
        "EXPAND": "Ampliar URL existente en `/blog/`",
        "MIGRATE": "Crear en `/blog/` y migrar contenido legacy",
    }.get(action, action)


def build_report(cfg: dict, suggestions: list[dict], all_links: list[dict]) -> str:
    project = cfg["project"]["name"]
    domain = cfg["project"]["domain"]
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    blog_prefix = cfg.get("blog_strategy", {}).get("blog_path_prefix", "/blog/")

    lines = [
        "# Informe de estrategia de contenidos y enlazado interno",
        f"## {project}",
        "",
        "| | |",
        "|---|---|",
        f"| **Sitio web** | {domain} |",
        f"| **Fecha** | {now} |",
        f"| **Alcance** | Hasta 5 propuestas de blog bajo `{blog_prefix}` + matriz de interlinking |",
        "",
        "---",
        "",
        "## Introducción",
        "",
        "Este informe traduce los datos de Search Console y el mapa semántico del sitio en "
        "**propuestas editoriales concretas** y una **estrategia de enlazado interno** que evita "
        "canibalizar las landings de servicio (`/service/`).",
        "",
        "Todos los contenidos informativos nuevos se publican bajo **`/blog/`**, "
        "alineados con la arquitectura de URLs del sitio.",
        "",
        "---",
        "",
        "## Resumen ejecutivo",
        "",
    ]

    if not suggestions:
        _bullet(lines, "No se han generado propuestas con los umbrales actuales. Revisa exportación GSC o baja `min_impressions` en `project.yaml`.")
    else:
        for i, s in enumerate(suggestions, 1):
            pri = PRIORITY_ES.get(s["priority"], s["priority"])
            _bullet(
                lines,
                f"**{i}. {s['proposed_title']}** — Prioridad **{pri}** ({_action_label(s['action'])}).",
            )

    lines.extend(["", "---", "", "## Propuestas de contenido", ""])

    for i, s in enumerate(suggestions, 1):
        lines.extend([f"### {i}. {s['proposed_title']}", ""])
        lines.extend(["#### Diagnóstico", ""])
        _bullet(lines, f"**Consulta objetivo:** «{s['query']}».")
        _bullet(lines, f"**Intención predominante:** {INTENT_ES.get(s['intent'], s['intent'])}.")
        if s["impressions"] > 0:
            _bullet(
                lines,
                f"**Search Console:** {s['impressions']} impresiones, {s['clicks']} clics, "
                f"posición media ~{s['avg_position']}.",
            )
        else:
            _bullet(lines, f"**Origen del dato:** {s['data_source']}.")
        _bullet(lines, f"**Cobertura temática en el sitio:** {int(s['coverage_ratio'] * 100)}% (estimada).")
        _bullet(lines, f"**Acción recomendada:** {_action_label(s['action'])}.")

        lines.extend(["", "#### Recomendaciones", ""])
        _bullet(lines, f"**URL objetivo:** `{s['target_url']}`")
        _bullet(lines, f"**Slug:** `{s['proposed_slug']}`")
        _bullet(lines, f"**Title sugerido:** {s['proposed_title']} | {project}")
        _bullet(
            lines,
            f"**H1 sugerido:** {s['proposed_title']}" if "Guide" in s["proposed_title"] else f"**H1 sugerido:** {s['proposed_title']}: A Complete Guide",
        )
        if s["action"] == "MIGRATE" and s.get("legacy_url"):
            _bullet(
                lines,
                f"**Migración:** el tema existe en `{s['legacy_url']}` (ruta legacy). "
                "Publicar en `/blog/`, aplicar 301 desde la URL antigua cuando migres categorías.",
            )
        if s["action"] == "EXPAND":
            _bullet(lines, "Ampliar profundidad (FAQ, checklist, imágenes con alt descriptivo) sin cambiar la intención a transaccional.")
        if s["action"] == "CREATE":
            _bullet(
                lines,
                "Reservar la keyword exacta para title, meta y H1 **solo** en esta URL. "
                "No replicarla en `/service/*`.",
            )

        post_links = s.get("links", [])
        if post_links:
            lines.extend(["", "#### Enlaces sugeridos para esta pieza", ""])
            for lk in post_links:
                _bullet(
                    lines,
                    f"**{lk['from']}** → **{lk['to']}** | Anchor: «{lk['anchor']}» | {lk['type']}.",
                )

        lines.extend(["", "#### Nivel de prioridad", ""])
        pri = PRIORITY_ES.get(s["priority"], s["priority"])
        _bullet(lines, f"**Prioridad {pri}** según volumen de demanda y alineación con la estrategia local.")
        lines.append("")

    lines.extend(["---", "", "## Matriz de interlinking (visión global)", ""])
    if all_links:
        _bullet(lines, "Regla general: el blog informa; `/service/` convierte; `/our-services/` actúa como hub.")
        lines.append("")
        for lk in all_links:
            _bullet(
                lines,
                f"«{lk['anchor']}» — {lk['from']} → {lk['to']} ({lk['type']}). {lk.get('note', '')}",
            )
    else:
        _bullet(lines, "Sin enlaces generados (no hay propuestas con URL objetivo).")

    lines.extend(
        [
            "",
            "---",
            "",
            "## Reglas anti-canibalización",
            "",
            "- La **keyword exacta** del post vive en **una sola URL** bajo `/blog/`.",
            "- Las landings **`/service/`** usan anchors **transaccionales** distintos (servicios, joinery, diseño).",
            "- No crear posts que compitan con fichas de servicio ya posicionadas.",
            "- Tras publicar: solicitar indexación en Search Console y enlazar desde el hub `/our-services/`.",
            "",
            "---",
            "",
            "## Plan de implementación",
            "",
            "1. **Semana 1:** publicar la propuesta de prioridad Alta (si existe) en Elementor bajo `/blog/`.",
            "2. **Semana 2–4:** implementar matriz de enlaces post → servicios → hub.",
            "3. **Continuo:** mantener coherencia de categorías y slugs bajo `/blog/` en WordPress.",
            "4. **Medición:** revisar impresiones y clics en GSC a 30–60 días por cada URL nueva.",
            "",
        ]
    )
    return "\n".join(lines)


def run(gsc_path: str | None = None, semantic_path: str | None = None) -> dict:
    cfg = load_project_config()
    bs = cfg.get("blog_strategy", {})
    if not bs:
        raise ValueError("Define blog_strategy in config/project.yaml")

    ds = cfg.get("data_sources", {})
    gsc_file = gsc_path or latest_file(str(ROOT / ds.get("gsc_glob", "../data/raw/gsc_*.csv")))
    semantic_file = semantic_path or latest_file(str(ROOT / "reports/ai/01_semantic_map_*.csv"))
    intent_file = latest_file(str(ROOT / "reports/ai/03_intent_matrix_*.csv"))

    if not gsc_file or not Path(gsc_file).exists():
        raise FileNotFoundError("GSC CSV not found. Run export or pass --gsc.")
    if not semantic_file or not Path(semantic_file).exists():
        raise FileNotFoundError("Semantic map not found. Run module 01 first.")

    gsc = pd.read_csv(gsc_file)
    semantic = pd.read_csv(semantic_file)
    intent_matrix = _read_csv(str(ROOT / "reports/ai/03_intent_matrix_*.csv"))
    intent_map = _query_intent_map(intent_matrix)

    blog_prefix = bs.get("blog_path_prefix", "/blog/")
    pages = _load_pages(semantic, blog_prefix)
    editorial = bs.get("editorial_ideas", [])

    gap_queries: set[str] = set()
    gaps_df = _read_csv(str(ROOT / "reports/ai/05_content_gaps_*.csv"))
    if gaps_df is not None and "query" in gaps_df.columns:
        gap_queries = {str(q).strip().lower() for q in gaps_df["query"].tolist()}

    suggestions = _collect_candidates(gsc, pages, intent_map, bs, editorial, gap_queries)

    all_links: list[dict] = []
    for s in suggestions:
        s["links"] = _build_interlinks(s, bs, cfg["project"]["origin"])
        all_links.extend(s["links"])

    content = build_report(cfg, suggestions, all_links)
    ts = timestamp()
    md_path = ROOT / cfg["output"]["executive_dir"] / f"12_estrategia_blog_{ts}.md"
    save_md(content, md_path)
    print(f"[12] Estrategia blog (informe): {md_path}")
    return {"md": str(md_path), "suggestions": len(suggestions), "links": len(all_links)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Module 12 - Blog strategy and interlinking report")
    parser.add_argument("--gsc", default="")
    parser.add_argument("--semantic", default="")
    args = parser.parse_args()
    run(gsc_path=args.gsc or None, semantic_path=args.semantic or None)
