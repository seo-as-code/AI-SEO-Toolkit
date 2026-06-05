import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

MODULES = [
    ("01 Semantic map", "scripts/modules/01_semantic_map.py", []),
    ("02 Entity extraction", "scripts/modules/02_entity_extraction.py", []),
    ("03 Intent classifier", "scripts/modules/03_intent_classifier.py", ["--gsc"]),
    ("04 Tone and style", "scripts/modules/04_tone_style.py", []),
    ("05 Content gaps", "scripts/modules/05_content_gaps.py", ["--gsc"]),
    ("06 AI rewrite", "scripts/modules/06_ai_rewrite.py", []),
    ("07 Technical audit", "scripts/modules/07_technical_audit.py", []),
    ("08 UX/CRO", "scripts/modules/08_ux_cro.py", []),
    ("09 Competitor gap", "scripts/modules/09_competitor_gap.py", []),
    ("10 Action plan", "scripts/modules/10_action_plan.py", []),
    ("12 Blog strategy", "scripts/modules/12_blog_strategy.py", ["--gsc"]),
    ("11 Executive report (ES)", "scripts/modules/11_executive_report.py", []),
]


def run_step(label: str, script_rel: str, extra_args: list[str]) -> None:
    script = ROOT / script_rel
    cmd = [sys.executable, str(script)] + extra_args
    print(f"\n=== {label} ===")
    print(" ".join(cmd))
    result = subprocess.run(cmd, cwd=str(ROOT))
    if result.returncode != 0:
        raise RuntimeError(f"Failed step: {label}")


def main() -> None:
    parser = argparse.ArgumentParser(description="AI SEO master orchestrator (12 modules)")
    parser.add_argument("--gsc", default="", help="Optional GSC CSV path")
    args = parser.parse_args()

    gsc_value = args.gsc
    for label, script_rel, arg_names in MODULES:
        extra = []
        if "--gsc" in arg_names and gsc_value:
            extra = ["--gsc", gsc_value]
        run_step(label, script_rel, extra)

    print("\nAI SEO full pipeline completed.")
    print(f"- Module outputs: {ROOT / 'reports/ai'}")
    print(f"- Executive plan: {ROOT / 'reports/executive'}")


if __name__ == "__main__":
    main()
