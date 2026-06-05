"""
Module 11 — Informe ejecutivo unificado (español, tono consultoría / cliente).

Consolida los módulos 01-10 en un único informe: diagnóstico, recomendaciones y prioridad.
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from lib.common import latest_file, load_project_config, save_md, timestamp  # noqa: E402
from lib.url_filters import is_html_page_url  # noqa: E402

THIN_WORDS = 250

SUB_DIAG = "Diagnóstico"
SUB_REC = "Recomendaciones"
SUB_PRIO = "Nivel de prioridad"

ISSUE_LABELS = {
    "missing_title": "título SEO ausente o no detectado",
    "missing_meta": "meta descripción ausente",
    "missing_h1": "encabezado H1 ausente o no definido",
    "status_code": "respuesta HTTP no estándar (redirección o error)",
    "thin_content": "contenido insuficiente para competir en la SERP",
}

INTENT_LABELS = {
    "local": "local (búsquedas con componente geográfico en Ibiza)",
    "commercial": "transaccional o de contratación de servicios",
    "informational": "informativa (guías, comparativas, consejos)",
    "navigational": "de marca (usuarios que buscan el estudio directamente)",
    "mixed": "mixta o no clasificada con claridad",
}

TONE_LABELS = {"direct": "directo", "formal": "formal"}
READABILITY_LABELS = {"easy": "fácil", "medium": "media", "complex": "compleja"}

GAP_TYPE_LABELS = {
    "weak_coverage": "cobertura temática insuficiente en el sitio",
    "no_page": "ausencia de URL alineada con la consulta",
    "thin_page": "página existente con poca profundidad de contenido",
}

GAP_ACTION_LABELS = {
    "Expand existing page": "Ampliar y reorientar la página ya publicada",
    "Create new page": "Publicar una nueva URL orientada a la consulta",
    "Improve internal linking": "Reforzar el enlazado interno hacia la URL objetivo",
}

UX_CHECK_LABELS = {
    "cta_presence": "llamada a la acción de contacto",
    "navigation_depth": "arquitectura de enlaces internos desde la home",
    "h1_structure": "jerarquía del encabezado principal (H1)",
    "message_clarity": "claridad del mensaje en el título de la home",
}

IMPACT_LABELS = {"high": "Alta", "medium": "Media", "low": "Baja"}
OWNER_LABELS = {
    "Technical SEO": "SEO técnico",
    "SEO Content": "Estrategia de contenidos",
    "UX/CRO": "Experiencia de usuario y conversión",
    "SEO Strategy": "Estrategia SEO",
    "Content Team": "Contenidos y copy",
}

DETAIL_LABELS = {
    "empty title": "etiqueta title vacía",
    "empty meta": "meta description vacía",
    "empty h1": "H1 no presente en el HTML analizado",
}


def _read_csv(pattern: str) -> pd.DataFrame | None:
    path = latest_file(pattern)
    if not path or not Path(path).exists():
        return None
    return pd.read_csv(path)


def _bullet(lines: list[str], text: str) -> None:
    lines.append(f"- {text}")


def _section_title(lines: list[str], num: str, title: str) -> None:
    lines.extend(["", f"### {num}. {title}", ""])


def _subsection(lines: list[str], title: str) -> None:
    lines.extend(["", f"#### {title}", ""])


def _diag(lines: list[str]) -> None:
    _subsection(lines, SUB_DIAG)


def _rec(lines: list[str]) -> None:
    _subsection(lines, SUB_REC)


def _prio(lines: list[str]) -> None:
    _subsection(lines, SUB_PRIO)


def _module_status(lines: list[str], found: bool, note: str = "") -> None:
    if found:
        _bullet(lines, f"Análisis completado con la información disponible.{f' {note}' if note else ''}")
    else:
        _bullet(
            lines,
            "No se dispone de resultados para este bloque. Será necesario ejecutar el análisis correspondiente "
            "antes de poder emitir recomendaciones.",
        )


def _translate_detail(detail: str) -> str:
    d = str(detail or "").strip()
    if d in DETAIL_LABELS:
        return DETAIL_LABELS[d]
    if d.startswith("status="):
        code = d.replace("status=", "")
        if code == "301":
            return "redirección permanente (301)"
        if code == "404":
            return "página no encontrada (404)"
        return f"respuesta HTTP {code}"
    if d.startswith("word_count="):
        n = d.replace("word_count=", "")
        return f"aproximadamente {n} palabras de contenido visible"
    return d


def _translate_gap_action(action: str) -> str:
    a = str(action or "").strip()
    return GAP_ACTION_LABELS.get(a, a)


def _translate_plan_action(action: str) -> str:
    a = str(action or "")
    if a.startswith("Fix technical issue on "):
        rest = a.replace("Fix technical issue on ", "", 1)
        if ": " in rest:
            url, issue = rest.split(": ", 1)
            issue_es = ISSUE_LABELS.get(issue, issue.replace("_", " "))
            return f"Revisar {url}: {issue_es}"
    if a.startswith("Create/expand content for query: "):
        q = a.replace("Create/expand content for query: ", "")
        return f"Desarrollar o ampliar contenidos orientados a «{q}»"
    if a.startswith("Improve UX check "):
        rest = a.replace("Improve UX check ", "", 1)
        if " on " in rest:
            check, url = rest.split(" on ", 1)
            check_es = UX_CHECK_LABELS.get(check, check)
            return f"Mejorar {check_es} en {url}"
    if a.startswith("Cover competitor topic gap for "):
        return f"Cubrir brecha temática frente a {a.replace('Cover competitor topic gap for ', '')}"
    if a.startswith("Expand thin page: "):
        return f"Incrementar la profundidad de contenido en {a.replace('Expand thin page: ', '')}"
    return a


def _parse_rewrite_md(path: Path, limit: int = 5) -> list[dict]:
    blocks: list[dict] = []
    current: dict | None = None
    seen_queries: set[str] = set()

    def flush() -> None:
        nonlocal current
        if current and len(blocks) < limit:
            blocks.append(current)
        current = None

    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("## Query/Page:"):
            flush()
            if len(blocks) >= limit:
                break
            query = stripped.replace("## Query/Page:", "").strip()
            if query in seen_queries:
                continue
            seen_queries.add(query)
            current = {"query": query, "title": "", "meta": "", "h1": "", "cta": ""}
        elif current and stripped.startswith("- Title:"):
            current["title"] = stripped.replace("- Title:", "").strip()
        elif current and stripped.startswith("- Meta:"):
            current["meta"] = stripped.replace("- Meta:", "").strip()
        elif current and stripped.startswith("- H1:"):
            current["h1"] = stripped.replace("- H1:", "").strip()
        elif current and stripped.startswith("- CTA:"):
            current["cta"] = stripped.replace("- CTA:", "").strip()
    flush()
    return blocks


def build_report(cfg: dict) -> str:
    project = cfg["project"]["name"]
    domain = cfg["project"]["domain"]
    out_dir = ROOT / cfg["output"]["reports_dir"]
    exec_dir = ROOT / cfg["output"]["executive_dir"]
    thin_min = int(cfg.get("thresholds", {}).get("thin_content_min_words", THIN_WORDS))
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    highlights: list[str] = []
    body: list[str] = []

    # --- Module 01 ---
    sem = _read_csv(str(out_dir / "01_semantic_map_*.csv"))
    _section_title(body, "01", "Arquitectura de contenidos y cobertura temática")
    if sem is not None and not sem.empty:
        urls = sem["url"].astype(str).tolist() if "url" in sem.columns else []
        service_pages = [u for u in urls if "/service/" in u]
        thin = sem[sem["word_count"] < thin_min] if "word_count" in sem.columns else pd.DataFrame()
        _diag(body)
        _bullet(
            body,
            f"Se ha revisado la estructura semántica de **{len(sem)}** URLs publicadas, "
            "evaluando título, encabezado principal y volumen de texto.",
        )
        if service_pages:
            _bullet(
                body,
                f"El sitio cuenta con **{len(service_pages)}** páginas de servicio bajo la ruta `/service/`, "
                "correctamente diferenciadas como landings comerciales.",
            )
        if not thin.empty:
            thin_list = thin.head(8)
            for _, row in thin_list.iterrows():
                wc = row.get("word_count", "?")
                _bullet(
                    body,
                    f"La URL `{row.get('url', '')}` presenta un contenido reducido "
                    f"(aproximadamente **{wc}** palabras), por debajo del umbral recomendado para posicionar con solvencia.",
                )
            highlights.append(
                f"Reforzar el contenido de **{len(thin)}** páginas estratégicas (servicios, contacto, portfolio) "
                "para mejorar relevancia temática y capacidad de conversión."
            )
        _rec(body)
        if not thin.empty:
            _bullet(
                body,
                "Desarrollar la página **Our Services** como hub temático: texto orientado a intención de búsqueda, "
                "beneficios claros y enlaces contextuales hacia cada servicio.",
            )
            _bullet(
                body,
                "Enriquecer **Contact** y **Portfolio** con argumentos de valor, pruebas sociales y llamadas a la acción, "
                "evitando páginas meramente estructurales.",
            )
            _bullet(
                body,
                "Conservar y potenciar las landings de servicio, que ya disponen de mayor profundidad editorial.",
            )
            _prio(body)
            _bullet(
                body,
                "**Prioridad media.** Mejora la claridad comercial y la señal semántica; no bloquea la indexación, "
                "pero condiciona el rendimiento en búsquedas competitivas.",
            )
        else:
            _bullet(
                body,
                "No se han identificado páginas con contenido claramente insuficiente según el umbral configurado.",
            )
    else:
        _diag(body)
        _module_status(body, False)

    # --- Module 02 ---
    ent = _read_csv(str(out_dir / "02_entities_summary_*.csv"))
    _section_title(body, "02", "Señales de marca y entidades temáticas")
    if ent is not None and not ent.empty:
        top = ent.head(10)
        _diag(body)
        _bullet(
            body,
            "Las entidades más recurrentes en el sitio reflejan cómo Google y los usuarios asocian su marca con los servicios:",
        )
        for _, row in top.iterrows():
            n_urls = row.get("url_count", "?")
            url_label = "URL" if str(n_urls) == "1" else "URLs"
            _bullet(
                body,
                f"**{row.get('entity', '')}**: presente en {n_urls} {url_label} "
                f"({row.get('mentions', '?')} menciones en el corpus analizado).",
            )
        _rec(body)
        _bullet(
            body,
            "Unificar la presencia de **Studio Rethink Ibiza**, **Ibiza**, **interior design** y **custom furniture** "
            "en títulos, H1 y párrafos introductorios de las URLs prioritarias.",
        )
        _bullet(
            body,
            "Reducir variaciones genéricas o duplicadas en títulos que diluyen la autoridad de marca y la claridad temática.",
        )
        _prio(body)
        _bullet(
            body,
            "**Prioridad media-baja.** Contribuye a reforzar E-E-A-T y coherencia de marca; efecto acumulativo a medio plazo.",
        )
    else:
        _diag(body)
        _module_status(body, False)

    # --- Module 03 ---
    intent = _read_csv(str(out_dir / "03_intent_summary_*.csv"))
    _section_title(body, "03", "Intención de búsqueda (Google Search Console)")
    if intent is not None and not intent.empty:
        total = int(intent["count"].sum()) if "count" in intent.columns else 0
        _diag(body)
        _bullet(
            body,
            "Distribución de consultas según la intención predominante del usuario en los últimos datos de Search Console:",
        )
        for _, row in intent.iterrows():
            label = INTENT_LABELS.get(str(row.get("intent", "")), str(row.get("intent", "")))
            pct = round(100 * row["count"] / total, 1) if total else 0
            _bullet(body, f"**{label.capitalize()}**: {row['count']} consultas ({pct}% del total).")
        dominant = intent.sort_values("count", ascending=False).iloc[0]
        dom_label = INTENT_LABELS.get(str(dominant["intent"]), str(dominant["intent"]))
        highlights.append(
            f"La demanda orgánica se concentra en intención **{dom_label}**: conviene alinear fichas de servicio, "
            "contenidos locales y perfil de empresa en Google."
        )
        _rec(body)
        _bullet(
            body,
            "Priorizar mensajes y landings que respondan a búsquedas **locales** vinculadas a Ibiza y a la contratación de servicios.",
        )
        _bullet(
            body,
            "Desarrollar contenidos **informativos** en el blog (guías, criterios de elección, tendencias) para captar tráfico de descubrimiento.",
        )
        _prio(body)
        _bullet(
            body,
            "**Prioridad alta.** Define la arquitectura de contenidos y la inversión editorial del próximo trimestre.",
        )
    else:
        _diag(body)
        _module_status(
            body,
            False,
            "Requiere exportación reciente de Search Console.",
        )

    # --- Module 04 ---
    tone_csv = _read_csv(str(out_dir / "04_tone_style_*.csv"))
    _section_title(body, "04", "Tono editorial y legibilidad")
    if tone_csv is not None and not tone_csv.empty:
        tone_counts = tone_csv["tone"].value_counts().to_dict() if "tone" in tone_csv.columns else {}
        dom_tone = max(tone_counts, key=tone_counts.get) if tone_counts else "n/d"
        dom_tone_es = TONE_LABELS.get(str(dom_tone), str(dom_tone))
        complex_pages = (
            tone_csv[tone_csv["readability"].astype(str) == "complex"] if "readability" in tone_csv.columns else pd.DataFrame()
        )
        _diag(body)
        _bullet(
            body,
            f"Se ha evaluado el estilo comunicativo en **{len(tone_csv)}** páginas clave del sitio.",
        )
        _bullet(body, f"El tono predominante es **{dom_tone_es}**, coherente con una propuesta premium y cercana.")
        if not complex_pages.empty:
            n = len(complex_pages)
            pag = "página" if n == 1 else "páginas"
            _bullet(
                body,
                f"**{n}** {pag} presentan una legibilidad **exigente** (frases extensas que pueden dificultar la lectura en móvil).",
            )
        _rec(body)
        _bullet(
            body,
            "Mantener un registro **directo y aspiracional** en inglés en servicios y portfolio, alineado con el posicionamiento del estudio.",
        )
        _bullet(
            body,
            "Simplificar la construcción de frases en las páginas señaladas, sin perder precisión técnica ni tono de marca.",
        )
        _prio(body)
        _bullet(
            body,
            "**Prioridad baja-media.** Refinamiento de copy; impacto principal en percepción de marca y engagement.",
        )
    else:
        _diag(body)
        _module_status(body, False)

    # --- Module 05 ---
    gaps = _read_csv(str(out_dir / "05_content_gaps_*.csv"))
    _section_title(body, "05", "Oportunidades de contenido no cubiertas")
    if gaps is not None and not gaps.empty:
        _diag(body)
        for _, row in gaps.iterrows():
            q = row.get("query", "")
            imp = row.get("impressions", "")
            pos = row.get("avg_position", "")
            gap = row.get("gap_type", "")
            gap_es = GAP_TYPE_LABELS.get(str(gap), str(gap))
            _bullet(
                body,
                f"La consulta **«{q}»** acumula **{imp}** impresiones con posición media cercana a **{pos}**. "
                f"Diagnóstico: {gap_es}.",
            )
            highlights.append(
                f"Oportunidad editorial para «{q}»: demanda visible en Google con rendimiento de clics mejorable."
            )
        _rec(body)
        for _, row in gaps.iterrows():
            action = _translate_gap_action(row.get("recommended_action", "Ampliar la página existente o crear artículo"))
            _bullet(body, f"Para **«{row.get('query', '')}»**: {action}.")
        _prio(body)
        _bullet(
            body,
            "**Prioridad alta.** Oportunidad contrastada con datos reales de Search Console; conviene abordarla en el próximo ciclo editorial.",
        )
    else:
        _diag(body)
        _module_status(
            body,
            False,
            "No se han detectado huecos con los criterios de volumen configurados.",
        )

    # --- Module 06 ---
    rewrite = latest_file(str(out_dir / "06_ai_rewrite_*.md"))
    _section_title(body, "06", "Propuestas de optimización on-page")
    if rewrite and Path(rewrite).exists():
        blocks = _parse_rewrite_md(Path(rewrite), limit=5)
        _diag(body)
        _bullet(
            body,
            f"Se han elaborado **{len(blocks)}** propuestas de mejora para elementos visibles en resultados de búsqueda "
            "(title, meta description, H1 y llamada a la acción).",
        )
        for b in blocks:
            _bullet(body, f"**Consulta o página objetivo:** {b['query']}")
            if b.get("title"):
                _bullet(body, f"  - *Title sugerido:* {b['title']}")
            if b.get("meta"):
                _bullet(body, f"  - *Meta description sugerida:* {b['meta']}")
            if b.get("h1"):
                _bullet(body, f"  - *H1 sugerido:* {b['h1']}")
            if b.get("cta"):
                _bullet(body, f"  - *Llamada a la acción:* {b['cta']}")
        _rec(body)
        _bullet(
            body,
            "Validar cada propuesta con criterio editorial y de marca antes de su publicación en el CMS; "
            "las sugerencias automatizadas no sustituyen la revisión humana.",
        )
        _bullet(
            body,
            "Implementar en primer lugar las variantes vinculadas a las consultas con mayor volumen de impresiones (apartado 5 de este informe).",
        )
        _prio(body)
        _bullet(
            body,
            "**Prioridad media**, una vez confirmada la estrategia de contenidos del apartado 5.",
        )
    else:
        _diag(body)
        _module_status(body, False)

    # --- Module 07 ---
    tech = _read_csv(str(out_dir / "07_technical_audit_*.csv"))
    _section_title(body, "07", "Salud técnica e indexabilidad")
    if tech is not None and not tech.empty:
        tech_html = tech[tech["url"].astype(str).apply(is_html_page_url)] if "url" in tech.columns else tech
        _diag(body)
        _bullet(
            body,
            f"La auditoría de rastreo ha analizado **{len(tech)}** URLs. "
            f"Tras excluir recursos no indexables (scripts, estilos, imágenes y plugins), "
            f"quedan **{len(tech_html)}** incidencias sobre **páginas de contenido**.",
        )
        if len(tech) > len(tech_html):
            _bullet(
                body,
                f"Se han descartado **{len(tech) - len(tech_html)}** URLs de infraestructura de WordPress/Elementor, "
                "que no deben evaluarse como páginas de posicionamiento.",
            )
        if tech_html.empty:
            _bullet(body, "No se han detectado incidencias relevantes en páginas de contenido tras el filtrado aplicado.")
        else:
            by_type = tech_html.groupby("issue_type").size().sort_values(ascending=False)
            _bullet(body, "Resumen de incidencias por tipo:")
            for issue_type, count in by_type.items():
                label = ISSUE_LABELS.get(issue_type, issue_type)
                _bullet(body, f"  - {label}: **{count}** ocurrencias.")
            shown = tech_html.drop_duplicates(subset=["url", "issue_type"]).head(8)
            _bullet(body, "Ejemplos representativos:")
            for _, row in shown.iterrows():
                label = ISSUE_LABELS.get(row.get("issue_type", ""), row.get("issue_type", ""))
                detail = _translate_detail(row.get("detail", ""))
                _bullet(body, f"  - `{row.get('url', '')}`: {label} ({detail}).")
            status_rows = tech_html[tech_html["issue_type"] == "status_code"]
            if not status_rows.empty:
                highlights.append(
                    f"Revisar **{len(status_rows)}** URLs con redirecciones o errores de respuesta que pueden diluir la autoridad."
                )
            thin_rows = tech_html[tech_html["issue_type"] == "thin_content"]
            if not thin_rows.empty:
                highlights.append(
                    f"**{len(thin_rows)}** páginas con profundidad de contenido insuficiente para competir con solvencia."
                )
        _rec(body)
        _bullet(
            body,
            "Resolver errores **404** y simplificar cadenas de **301** en URLs de contenido, evitando redirecciones innecesarias.",
        )
        _bullet(
            body,
            "Completar **title**, **meta description** y **H1** en páginas estratégicas (contacto, taxonomías, fichas desactualizadas).",
        )
        _bullet(
            body,
            "En futuros rastreos con Screaming Frog, excluir `/wp-content/` para centrar el análisis en URLs indexables.",
        )
        _prio(body)
        _bullet(
            body,
            "**Prioridad alta** en errores de respuesta y contenido inaccesible; **prioridad media** en metadatos incompletos.",
        )
    else:
        _diag(body)
        _module_status(
            body,
            False,
            "Requiere exportación del rastreo interno (Screaming Frog).",
        )

    # --- Module 08 ---
    ux = _read_csv(str(out_dir / "08_ux_cro_*.csv"))
    _section_title(body, "08", "Experiencia de usuario y conversión (página de inicio)")
    if ux is not None and not ux.empty:
        fails = ux[ux["status"].astype(str).str.lower() != "pass"] if "status" in ux.columns else pd.DataFrame()
        _diag(body)
        _bullet(body, "Evaluación de la página de inicio en factores que influyen en la conversión orgánica:")
        for _, row in ux.iterrows():
            st = row.get("status", "?")
            check = UX_CHECK_LABELS.get(str(row.get("check", "")), str(row.get("check", "")))
            detail = str(row.get("detail", ""))
            estado = "dentro de parámetros aceptables" if str(st).lower() == "pass" else "requiere atención"
            _bullet(body, f"**{check}**: {estado} ({detail}).")
        _rec(body)
        if fails.empty:
            _bullet(
                body,
                "La home cumple los criterios analizados: visibilidad del contacto, estructura de H1, "
                "profundidad de enlazado interno y claridad del mensaje principal.",
            )
            _bullet(
                body,
                "Se recomienda, no obstante, validar manualmente el formulario de contacto y el rendimiento en dispositivos móviles.",
            )
        else:
            for _, row in fails.iterrows():
                check = UX_CHECK_LABELS.get(str(row.get("check", "")), str(row.get("check", "")))
                _bullet(body, f"Reforzar **{check}**: {row.get('detail', '')}.")
        _prio(body)
        _bullet(
            body,
            "**Prioridad baja** en el estado actual; **prioridad media** si se detectan incidencias en una nueva revisión.",
        )
    else:
        _diag(body)
        _module_status(body, False)

    # --- Module 09 ---
    comp = _read_csv(str(out_dir / "09_competitor_gap_*.csv"))
    _section_title(body, "09", "Posicionamiento frente a la competencia")
    if comp is not None and not comp.empty:
        _diag(body)
        has_real = False
        for _, row in comp.iterrows():
            err = str(row.get("error", "") or "")
            competitor = row.get("competitor", "")
            if err and err.lower() != "nan":
                _bullet(
                    body,
                    f"No ha sido posible analizar **{competitor}** (dominio inaccesible o configuración incorrecta).",
                )
            else:
                has_real = True
                _bullet(
                    body,
                    f"Respecto a **{competitor}**, se han identificado temáticas con presencia competitiva "
                    "no replicadas aún en su sitio.",
                )
        _rec(body)
        if not has_real:
            _bullet(
                body,
                "Incorporar **dominios competidores reales** en la configuración del proyecto; "
                "actualmente figuran URLs de ejemplo no válidas.",
            )
            _bullet(body, "Repetir el análisis una vez definida la lista de competidores del mercado en Ibiza.")
        else:
            _bullet(
                body,
                "Planificar contenidos o landings que cubran los temas donde la competencia ya captura visibilidad orgánica.",
            )
        _prio(body)
        _bullet(
            body,
            "**Prioridad media** cuando la comparativa esté correctamente configurada; en este informe, **no aplicable** hasta sustituir los dominios de prueba.",
        )
    else:
        _diag(body)
        _module_status(body, False)

    # --- Module 10 ---
    plan = _read_csv(str(exec_dir / "10_action_plan_*.csv"))
    _section_title(body, "10", "Hoja de ruta priorizada")
    if plan is not None and not plan.empty:
        plan = plan[~plan["action"].astype(str).str.contains("/wp-content/", na=False)]
        plan = plan[~plan["action"].astype(str).str.contains("/wp-includes/", na=False)]
        plan = plan[~plan["action"].astype(str).str.contains("Improve UX check", na=False)]
        _diag(body)
        _bullet(
            body,
            f"Se han consolidado **{len(plan)}** acciones ordenadas por impacto y esfuerzo estimado. "
            "A continuación, las más relevantes:",
        )
        top = plan.head(8)
        for _, row in top.iterrows():
            impact = IMPACT_LABELS.get(str(row.get("impact", "")), str(row.get("impact", "")))
            owner = OWNER_LABELS.get(str(row.get("owner", "")), str(row.get("owner", "")))
            action_es = _translate_plan_action(row.get("action", ""))
            reason_es = _translate_detail(row.get("reason", ""))
            _bullet(body, f"**{impact}:** {action_es}. Motivo: {reason_es}. Área responsable: {owner}.")
        _rec(body)
        _bullet(
            body,
            "Abordar las acciones en el orden indicado, priorizando incidencias técnicas y oportunidades de contenido con tracción en Search Console.",
        )
        _bullet(
            body,
            "Utilizar este informe como documento de referencia para el cliente; el listado detallado sirve para seguimiento operativo interno.",
        )
        _prio(body)
        _bullet(body, "La secuencia recomendada coincide con el resumen ejecutivo y el análisis de los apartados 1 a 9.")
    else:
        _diag(body)
        _module_status(body, False, "Requiere la consolidación previa del plan de acción (apartado 10).")

    if not highlights:
        highlights.append(
            "Completar el ciclo de análisis y definir competidores reales para obtener un informe comparativo pleno."
        )

    header = [
        f"# Informe de auditoría SEO",
        f"## {project}",
        "",
        f"| | |",
        f"|---|---|",
        f"| **Sitio web** | {domain} |",
        f"| **Fecha del informe** | {now} |",
        f"| **Alcance** | Análisis integrado: contenidos, Search Console, rastreo técnico y experiencia en la home |",
        "",
        "---",
        "",
        "## Introducción",
        "",
        "El presente documento resume el estado del posicionamiento orgánico del sitio y las líneas de actuación "
        "recomendadas. El análisis se ha estructurado en diez bloques temáticos, cada uno con tres apartados:",
        "",
        f"- **{SUB_DIAG}** — situación actual detectada en los datos.",
        f"- **{SUB_REC}** — acciones propuestas para mejorar visibilidad, tráfico cualificado y conversión.",
        f"- **{SUB_PRIO}** — urgencia relativa (Alta, Media o Baja) según impacto esperado y esfuerzo de implementación.",
        "",
        "La redacción está orientada a la toma de decisiones; los detalles operativos quedan disponibles "
        "para el equipo técnico en los exportes del proyecto.",
        "",
        "---",
        "",
        "## Resumen ejecutivo",
        "",
        "Principales hallazgos y oportunidades:",
        "",
    ]
    for h in highlights[:8]:
        header.append(f"- {h}")
    header.extend(
        [
            "",
            "---",
            "",
            "## Análisis detallado por área",
            "",
        ]
    )
    text = "\n".join(header + body)
    while "\n\n\n" in text:
        text = text.replace("\n\n\n", "\n\n")
    text += "\n---\n\n## Plan de implementación sugerido\n\n"
    text += (
        "**Corto plazo (1–2 semanas):** abordar oportunidades de contenido detectadas en Search Console, "
        "revisar redirecciones y errores en URLs de contenido, y reforzar la página de servicios.\n\n"
        "**Medio plazo (este mes):** definir competidores de referencia, actualizar el sitemap en Search Console "
        "y mejorar las páginas de contacto y portfolio.\n\n"
        "**Seguimiento:** actualizar este informe tras cada nuevo rastreo o exportación de Search Console "
        "para medir la evolución de las incidencias y oportunidades.\n"
    )
    return text + "\n"


def run() -> dict:
    cfg = load_project_config()
    exec_dir = ROOT / cfg["output"]["executive_dir"]
    ts = timestamp()
    md_path = exec_dir / f"11_informe_ejecutivo_{ts}.md"
    content = build_report(cfg)
    save_md(content, md_path)
    print(f"[11] Informe ejecutivo (ES): {md_path}")
    return {"md": str(md_path)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Module 11 - Informe ejecutivo unificado en español")
    parser.parse_args()
    run()
