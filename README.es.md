# AI SEO Toolkit

> **Idiomas:** [English](README.md) | [Español](README.es.md)

## Quick test (sin credenciales)

Puedes probar este repositorio **sin API keys ni tokens OAuth** (Modulo 01: mapa semantico).

```bash
git clone https://github.com/seo-as-code/AI-SEO-Toolkit.git
cd AI-SEO-Toolkit
pip install -r requirements.txt
python scripts/modules/01_semantic_map.py
```

Salida esperada:

- `reports/ai/01_semantic_map_*.csv`
- `reports/ai/01_semantic_map_*.json`

### Configura tu sitio antes de probar

1. Copia `config/project.local.yaml.example` → `config/project.local.yaml`
2. Edita **solo** `project.local.yaml` (está en `.gitignore`, no se sube a GitHub)

Campos de la sección `project:`:

| Campo | Qué poner | Ejemplo |
|-------|-----------|---------|
| `name` | Nombre del sitio o marca | `"Mi Empresa SEO"` |
| `domain` | Dominio sin `https://` | `"example.com"` |
| `origin` | URL base con `https://` | `"https://example.com"` |
| `locale` | Idioma/región BCP-47 | `"es-ES"` o `"en-US"` |
| `market` | Mercado objetivo (texto libre) | `"Madrid, Spain"` |

`config/project.yaml` en GitHub lleva placeholders genéricos. Tus datos reales van en `project.local.yaml`.

---

## 1. Descripcion general del proyecto

**AI SEO Toolkit** es un sistema modular de analisis que transforma datos SEO en recomendaciones estructuradas y priorizadas.

Esta capa funciona sobre el repositorio de extraccion de datos:

- [SEO-as-Code-Toolkit](https://github.com/seo-as-code/SEO-as-Code-Toolkit)

---

## 2. Problema que resuelve

En equipos SEO, los datos suelen llegar fragmentados (GSC, GA4, CrUX, crawl) sin un marco unificado de accion.

Este repositorio aporta:

1. Salidas estandarizadas por modulo (`reports/ai`)
2. Planes ejecutivos de accion (`reports/executive`)
3. Flujos Python reproducibles
4. Integracion clara con exportes del repo SEO-as-Code

---

## 3. Como trabajan juntos los dos repositorios

```text
SEO-as-Code-Toolkit (Capa de Datos)
  ├─ Extrae GSC / GA4 / CrUX / SF
  └─ Guarda exportes en data/raw

AI-SEO-Toolkit (Capa de Decision)
  ├─ Lee exportes + crawl del dominio
  ├─ Ejecuta 12 modulos AI SEO (01-10, 12, 11)
  └─ Genera plan de accion + informe ejecutivo
```

### Transferencia de datos

| Repo origen | Archivo | Modulo AI que lo usa |
|---|---|---|
| SEO-as-Code | `data/raw/gsc_*.csv` | 03, 05, 12 |
| SEO-as-Code | `data/raw/ga4_last30days.csv` | scoring futuro |
| SEO-as-Code | `data/raw/internos_todo.csv` | 07 |
| AI-SEO | crawl del dominio configurado | 01, 08, 09 |

---

## 4. Framework: 12 modulos AI SEO

| # | Modulo | Script | Output principal | Uso de negocio |
|---|---|---|---|---|
| 01 | Mapa semantico | `01_semantic_map.py` | mapa de temas por URL | Entender cobertura de contenido |
| 02 | Extraccion de entidades | `02_entity_extraction.py` | tabla de entidades | Reforzar E-E-A-T y claridad semantica |
| 03 | Clasificacion de intencion | `03_intent_classifier.py` | matriz de intencion | Alinear contenido con intencion |
| 04 | Tono y estilo | `04_tone_style.py` | informe de tono/legibilidad | Mantener consistencia de marca |
| 05 | Gaps de contenido | `05_content_gaps.py` | oportunidades de gap | Definir contenido nuevo/ampliado |
| 06 | Reescritura IA | `06_ai_rewrite.py` | sugerencias title/meta/H1/CTA | Mejorar activos SERP |
| 07 | Auditoria tecnica SEO | `07_technical_audit.py` | listado de incidencias | Corregir indexabilidad/metadata |
| 08 | Analisis UX/CRO | `08_ux_cro.py` | checks UX | Mejorar conversion |
| 09 | Gap competitivo | `09_competitor_gap.py` | gaps vs competidores | Capturar oportunidades no cubiertas |
| 10 | Plan de accion | `10_action_plan.py` | CSV priorizado (Excel) | Seguimiento operativo |
| 12 | Estrategia de blog | `12_blog_strategy.py` | calendario / temas de blog | Priorizar contenido editorial |
| 11 | Informe ejecutivo (ES) | `11_executive_report.py` | **`11_informe_ejecutivo_*.md`** | **Informe final legible (resume todo)** |

**Orden del pipeline completo:** `01 → 10 → 12 → 11`  
El modulo **11 siempre va al final** (consolida los demas). El **12** va justo antes.

Orquestador maestro:

- `scripts/orchestrator/ai_seo_master.py`

---

## 5. Estructura del repositorio

```text
ai-seo-toolkit/
  config/
    project.yaml
    model.yaml
  scripts/
    lib/common.py
    modules/
      01_semantic_map.py
      02_entity_extraction.py
      03_intent_classifier.py
      04_tone_style.py
      05_content_gaps.py
      06_ai_rewrite.py
      07_technical_audit.py
      08_ux_cro.py
      09_competitor_gap.py
      10_action_plan.py
      11_executive_report.py
      12_blog_strategy.py
    orchestrator/
      ai_seo_master.py
  prompts/
  data/
    raw/
    features/
  reports/
    ai/
    executive/
    code/
  requirements.txt
  .gitignore
```

---

## 6. Configuracion

Archivos de configuración:

| Archivo | En GitHub | Uso |
|---------|-----------|-----|
| `config/project.yaml` | Sí | Plantilla genérica |
| `config/project.local.yaml` | **No** | Tu sitio real (copia desde `.example`) |

Campos clave en `project:` (añade tu web en el `.local`):

- `name` — nombre del sitio o marca
- `domain` — dominio sin `https://`
- `origin` — URL base con `https://`
- `locale` — idioma/región (ej. `es-ES`)
- `market` — mercado objetivo (texto libre)
- `data_sources.gsc_glob`
- `data_sources.ga4_csv`
- `data_sources.sf_csv`
- `competitors`
- `thresholds`

Archivo de modelo: `config/model.yaml`

- Configuracion OpenAI opcional (`OPENAI_API_KEY`)
- Modo basado en reglas funciona sin API key

---

## 7. Flujo de ejecucion

### 7.1 Preparar datos (repo SEO-as-Code)

```powershell
cd "C:\Users\emami\proyecto_seo"
python scripts/gsc/gsc_fetch.py
python scripts/ga4/ga4_extract.py
```

### 7.2 Ejecutar pipeline completo AI SEO

```powershell
cd "C:\Users\emami\proyecto_seo\ai-seo-toolkit"
pip install -r requirements.txt
.\reports\code\run_ai_seo_master.ps1
```

### 7.3 Ejecutar un modulo individual

```powershell
.\reports\code\run_module_01.ps1
.\reports\code\run_module_05.ps1
.\reports\code\run_module_10.ps1
```

---

## 8. Entregables

Tras la ejecucion, los resultados se guardan en:

- `reports/ai/` (analitica por modulo)
- `reports/executive/` (plan consolidado)

Archivos principales:

- `reports/executive/11_informe_ejecutivo_*.md` — **informe final para cliente**
- `reports/executive/12_blog_strategy_*.md` — estrategia de blog
- `reports/executive/10_action_plan_*.csv` — plan de accion priorizado
- `reports/ai/05_content_gaps_*.csv`
- `reports/ai/07_technical_audit_*.csv`

---

## 9. Seguridad y cumplimiento

Archivos sensibles excluidos via `.gitignore`:

- API keys (`.env`, `*.key`, `*.pem`)
- Reportes locales generados

Politica recomendada:

- Subir codigo y documentacion
- No subir credenciales ni secretos de cliente

---

## 10. Stack tecnologico

- Python 3
- pandas
- requests + BeautifulSoup
- Configuracion YAML
- Integracion opcional OpenAI API

---

## 11. Estado de madurez por modulo

| Modulo | Estado | Notas |
|---|---|---|
| 01 | Production-ready | Crawl + mapa semantico |
| 02 | Production-ready | Entidades desde mapa semantico |
| 03 | Production-ready | Reglas de intencion + GSC |
| 04 | Production-ready | Heuristicas de tono/legibilidad |
| 05 | Production-ready | Demanda GSC vs cobertura semantica |
| 06 | Production-ready | Reescritura basada en reglas |
| 07 | Production-ready | Checks tecnicos SF + semanticos |
| 08 | Production-ready | Checks UX/CRO heuristicos |
| 09 | Production-ready | Comparativa de gaps competitivos |
| 10 | Production-ready | Priorizacion cross-modulo |
| 11 | Production-ready | Informe ejecutivo final en Markdown |
| 12 | Production-ready | Estrategia de blog con datos GSC |

---

## 12. Repositorio relacionado

- Capa de datos: [SEO-as-Code-Toolkit](https://github.com/seo-as-code/SEO-as-Code-Toolkit)
- Capa de decision: **AI-SEO-Toolkit** (este repositorio)

---

## 13. Autor

**Emanuel / SEO as Code**

Automatizacion SEO data-driven y sistemas de decision asistidos por IA.
