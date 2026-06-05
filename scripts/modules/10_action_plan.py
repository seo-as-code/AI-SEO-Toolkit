import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from lib.common import latest_file, load_project_config, save_csv, save_md, timestamp  # noqa: E402
from lib.url_filters import is_html_page_url  # noqa: E402


def score_action(impact: str, effort: str) -> int:
    impact_map = {"high": 3, "medium": 2, "low": 1}
    effort_map = {"low": 3, "medium": 2, "high": 1}
    return impact_map.get(impact, 1) + effort_map.get(effort, 1)


def add_from_csv(actions: list, pattern: str, module: str, action_tpl: str, reason_col: str, impact: str, effort: str, owner: str, limit: int = 10):
    path = latest_file(pattern)
    if not path or not Path(path).exists():
        return
    df = pd.read_csv(path).head(limit * 3)
    if "url" in df.columns:
        df = df[df["url"].astype(str).apply(is_html_page_url)]
    if module == "ux_cro" and "status" in df.columns:
        df = df[df["status"].astype(str).str.lower() != "pass"]
    df = df.head(limit)
    for _, row in df.iterrows():
        actions.append(
            {
                "module": module,
                "priority_score": score_action(impact, effort),
                "action": action_tpl.format(**row.to_dict()) if "{" in action_tpl else action_tpl,
                "reason": str(row.get(reason_col, "")),
                "impact": impact,
                "effort": effort,
                "owner": owner,
            }
        )


def run() -> dict:
    cfg = load_project_config()
    project = cfg["project"]["name"]
    out_dir = ROOT / cfg["output"]["reports_dir"]
    exec_dir = ROOT / cfg["output"]["executive_dir"]
    actions = []

    add_from_csv(
        actions,
        str(out_dir / "05_content_gaps_*.csv"),
        "content_gaps",
        "Create/expand content for query: {query}",
        "impressions",
        "high",
        "medium",
        "SEO Content",
        15,
    )
    add_from_csv(
        actions,
        str(out_dir / "07_technical_audit_*.csv"),
        "technical_audit",
        "Fix technical issue on {url}: {issue_type}",
        "detail",
        "high",
        "low",
        "Technical SEO",
        15,
    )
    add_from_csv(
        actions,
        str(out_dir / "08_ux_cro_*.csv"),
        "ux_cro",
        "Improve UX check {check} on {url}",
        "detail",
        "medium",
        "medium",
        "UX/CRO",
        10,
    )
    add_from_csv(
        actions,
        str(out_dir / "09_competitor_gap_*.csv"),
        "competitor_gap",
        "Cover competitor topic gap for {competitor}",
        "missing_on_own_site",
        "medium",
        "medium",
        "SEO Strategy",
        5,
    )

    semantic = latest_file(str(out_dir / "01_semantic_map_*.csv"))
    if semantic and Path(semantic).exists():
        sdf = pd.read_csv(semantic)
        thin = sdf[sdf.get("word_count", 0) < 250] if "word_count" in sdf.columns else pd.DataFrame()
        for _, row in thin.head(10).iterrows():
            actions.append(
                {
                    "module": "semantic_map",
                    "priority_score": 3,
                    "action": f"Expand thin page: {row.get('url')}",
                    "reason": f"word_count={row.get('word_count', 0)}",
                    "impact": "medium",
                    "effort": "medium",
                    "owner": "Content Team",
                }
            )

    if not actions:
        raise FileNotFoundError("No module outputs found. Run AI SEO master pipeline first.")

    action_df = pd.DataFrame(actions).sort_values("priority_score", ascending=False).drop_duplicates()
    ts = timestamp()
    csv_path = exec_dir / f"10_action_plan_{ts}.csv"
    md_path = exec_dir / f"10_action_plan_{ts}.md"
    save_csv(action_df, csv_path)

    lines = [
        f"# AI SEO Action Plan - {project}",
        "",
        "Consolidated recommendations from modules 01-09.",
        "",
        "## Prioritized actions",
    ]
    for _, row in action_df.head(25).iterrows():
        lines.append(
            f"- **[{row['impact']}/{row['effort']}] ({row['module']})** {row['action']}  \n"
            f"  Reason: {row['reason']} | Owner: {row['owner']}"
        )
    save_md("\n".join(lines) + "\n", md_path)

    print(f"[10] Action plan CSV: {csv_path}")
    print(f"[10] Action plan MD: {md_path}")
    return {"csv": str(csv_path), "md": str(md_path), "actions": len(action_df)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Module 10 - Prioritized action plan")
    parser.parse_args()
    run()
