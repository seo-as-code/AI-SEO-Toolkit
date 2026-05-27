# AI SEO Toolkit

> **Languages:** [English](README.md) | [Español](README.es.md)

## Quick test (no credentials)

Test this repository **without API keys or OAuth tokens** (Module 01: semantic site map).

```bash
git clone https://github.com/seo-as-code/AI-SEO-Toolkit.git
cd AI-SEO-Toolkit
pip install -r requirements.txt
python scripts/modules/01_semantic_map.py
```

Expected output:

- `reports/ai/01_semantic_map_*.csv`
- `reports/ai/01_semantic_map_*.json`

Change target website in `config/project.yaml` (`project.domain`, `project.origin`).

---

## 1. Project overview

**AI SEO Toolkit** is a modular analysis system that transforms SEO data into structured, prioritized recommendations.

It is designed as the **decision layer** on top of the data extraction repository:

- [SEO-as-Code-Toolkit](https://github.com/seo-as-code/SEO-as-Code-Toolkit)

Current reference project: `studiorethinkibiza.com`

---

## 2. Problem addressed

SEO teams usually receive fragmented outputs (GSC, GA4, CrUX, crawl files) without a unified action framework.

This repository solves that by providing:

1. Standardized module outputs (`reports/ai`)
2. Executive action plans (`reports/executive`)
3. Reproducible Python workflows
4. Clear integration with SEO-as-Code data exports

---

## 3. How both repositories work together

```text
SEO-as-Code-Toolkit (Data Layer)
  ├─ Extract GSC / GA4 / CrUX / SF
  └─ Save raw exports in data/raw

AI-SEO-Toolkit (Decision Layer)
  ├─ Read raw exports + website crawl
  ├─ Run 10 AI SEO modules
  └─ Generate prioritized action plan
```

### Data handoff

| Source repo | Output file | Used by AI module |
|---|---|---|
| SEO-as-Code | `data/raw/gsc_*.csv` | 03, 05 |
| SEO-as-Code | `data/raw/ga4_traffic_last30days.csv` | future scoring |
| SEO-as-Code | `data/raw/internos_todo.csv` | 07 |
| AI-SEO | live crawl of configured domain | 01, 08, 09 |

---

## 4. Framework: 10 AI SEO modules

| # | Module | Script | Primary output | Business use |
|---|---|---|---|---|
| 01 | Semantic site map | `01_semantic_map.py` | topic map by URL | Understand content coverage |
| 02 | Entity extraction | `02_entity_extraction.py` | entity frequency table | Improve E-E-A-T and semantic clarity |
| 03 | Search intent classification | `03_intent_classifier.py` | intent matrix | Match content to intent |
| 04 | Tone and style analysis | `04_tone_style.py` | tone/readability report | Keep brand consistency |
| 05 | Content gap detection | `05_content_gaps.py` | gap opportunities | Define new/expanded content |
| 06 | AI rewrite suggestions | `06_ai_rewrite.py` | title/meta/H1/CTA suggestions | Improve SERP assets |
| 07 | Technical SEO audit | `07_technical_audit.py` | technical issue list | Fix indexability/metadata issues |
| 08 | UX/CRO analysis | `08_ux_cro.py` | UX checks | Improve conversion paths |
| 09 | Competitor gap analysis | `09_competitor_gap.py` | competitor topic gaps | Capture missed opportunities |
| 10 | Prioritized action plan | `10_action_plan.py` | executive action plan | Execution roadmap |

Master orchestrator:

- `scripts/orchestrator/ai_seo_master.py`

---

## 5. Repository structure

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

## 6. Configuration

Main config file: `config/project.yaml`

Key fields:

- `project.domain`
- `project.origin`
- `data_sources.gsc_glob`
- `data_sources.ga4_csv`
- `data_sources.sf_csv`
- `competitors`
- `thresholds`

Model config file: `config/model.yaml`

- Optional OpenAI settings (`OPENAI_API_KEY`)
- Rule-based mode works without API key

---

## 7. Execution workflow

### 7.1 Prepare data (SEO-as-Code repo)

```powershell
cd "C:\Users\emami\proyecto_seo"
python scripts/gsc/gsc_fetch.py
python scripts/ga4/ga4_extract.py
```

### 7.2 Run full AI SEO pipeline

```powershell
cd "C:\Users\emami\proyecto_seo\ai-seo-toolkit"
pip install -r requirements.txt
.\reports\code\run_ai_seo_master.ps1
```

### 7.3 Run one module

```powershell
.\reports\code\run_module_01.ps1
.\reports\code\run_module_05.ps1
.\reports\code\run_module_10.ps1
```

---

## 8. Deliverables

After execution, outputs are generated in:

- `reports/ai/` (module-level analytics)
- `reports/executive/` (consolidated action plan)

Main files to review:

- `reports/executive/10_action_plan_*.md`
- `reports/executive/10_action_plan_*.csv`
- `reports/ai/05_content_gaps_*.csv`
- `reports/ai/07_technical_audit_*.csv`

---

## 9. Security and compliance

Sensitive files are excluded via `.gitignore`:

- API keys (`.env`, `*.key`, `*.pem`)
- Generated local reports

Recommended policy:

- Commit code and documentation
- Never commit credentials or client secrets

---

## 10. Technology stack

- Python 3
- pandas
- requests + BeautifulSoup
- YAML configuration
- Optional OpenAI API integration

---

## 11. Module maturity status

| Module | Status | Notes |
|---|---|---|
| 01 | Production-ready | Crawl + semantic mapping |
| 02 | Production-ready | Entity extraction from semantic data |
| 03 | Production-ready | Intent rules + GSC integration |
| 04 | Production-ready | Tone/readability heuristics |
| 05 | Production-ready | GSC demand vs semantic coverage |
| 06 | Production-ready | Rule-based rewrite suggestions |
| 07 | Production-ready | SF + semantic technical checks |
| 08 | Production-ready | UX/CRO heuristic checks |
| 09 | Production-ready | Competitor topic gap comparison |
| 10 | Production-ready | Cross-module prioritization |

---

## 12. Related repository

- Data layer: [SEO-as-Code-Toolkit](https://github.com/seo-as-code/SEO-as-Code-Toolkit)
- Decision layer: **AI-SEO-Toolkit** (this repository)

---

## 13. Author

**Emanuel / SEO as Code**

Data-driven SEO automation and AI-assisted decision systems.
