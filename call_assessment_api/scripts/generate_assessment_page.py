import json
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape

# Go up one level from /scripts to /researcher-demo
ROOT = Path(__file__).resolve().parents[1]

INPUT_DIR = ROOT / "examples" / "outputs"   # ../researcher-demo/examples/outputs
OUTPUT_DIR = ROOT / "docs"                  # ../researcher-demo/docs
TEMPLATE_DIR = ROOT / "templates"           # adjust if your templates live elsewhere
TEMPLATE_NAME = "game_assessment.md.j2"

def slugify(text: str) -> str:
    """
    Very small slug helper: lower-case, replace spaces with hyphens, and strip characters that are annoying in URLs. 
    """
    import re

    text = text.lower().strip()
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"[^a-z0-9\-\.]", "", text)
    return text

def get_slug_from_data(data: dict) -> str:
    """
    Derive a slug from the assessment JSON. 
    Tries a few keys in order so this is a bit future-proof
    """
    target = data.get("target", {}) or {}

    # Game case (your current JSON)
    if "game_name" in target:
        return slugify(target["game_name"])

    # Web/product style options if you add them later
    for key in ("domain", "product_name", "service_name", "target_identifier"): 
        if key in target and target[key]:
            return slugify(str(target[key]))

    # Fallback to something generic
    return "assessment"

def main():
    if not INPUT_DIR.exists():
        raise SystemExit(f"Input dir does not exist: {INPUT_DIR}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(enabled_extensions=("html", "xml"))
    )

    template = env.get_template(TEMPLATE_NAME)

    json_files = sorted(INPUT_DIR.glob("*.json"))
    if not json_files:
        print(f"No JSON files found in {INPUT_DIR}")
        return

    for json_path in json_files:
        with json_path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        slug = get_slug_from_data(data)
        out_path = OUTPUT_DIR / f"{slug}.md"

        rendered = template.render(**data)
        out_path.write_text(rendered, encoding="utf-8")

        print(f"[OK] {json_path.name} -> {out_path.relative_to(ROOT)}")

if __name__ == "__main__":
    main()