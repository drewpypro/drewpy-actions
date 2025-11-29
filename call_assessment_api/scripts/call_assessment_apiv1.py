#!/usr/bin/env python
"""
Call OpenAI to generate an assessment in JSON format. 

Usage examples:

    # simplest: just game name, auto output path
    python3 scripts/call_assessment_api.py "Helldivers 2"

    # with explicit Steam appid and output path
    python3 scripts/call_assessment_api.py "Helldivers 2" \
        --steam-appid 553850 \
        --output examples/outputs/helldivers2_assessment_v1.json

Requires
    - pip install openai
    - OPENAI_API_KEY set in your environment
"""

import argparse
import json
import os
from pathlib import Path
from openai import OpenAI

def load_schema(repo_root: Path) -> str:
    schema_path = repo_root / "schema" / "game_assessment_v1.json"
    if not schema_path.exists():
        raise FileNotFoundError(f"Missing schema file: {schema_path}")
    return schema_path.read_text(encoding="utf-8")

def load_instructions(repo_root: Path) -> str:
    """
    Concatenate the instruction markdown files into a single prompt string.
    Adjusut file_order if you add/remove instruction files:
    """
    instructions_dir = repo_root / "instructions"

    file_order = [
        "game_researcher_v1.md", # top-level instructions
        "game_identity_v1.md",
        "game_anti_cheat_v1.md",
        "game_community_v1.md",
    ]

    parts = []
    for filename in file_order:
        path = instructions_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"Missing instruction file: {path}")
        text = path.read_text(encoding="utf-8")
        parts.append(f"# {filename}\n\n{text}")

    return "\n\n\n".join(parts)

def make_default_output_path(repo_root: Path, game_name: str) -> Path:
    slug = (
        game_name.strip()
        .lower()
        .replace(" ", "_")
        .replace("/", "_")
        .replace("\\", "_")
    )
    out_dir = repo_root / "examples" / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir / f"{slug}_assessment_v1.json"

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a game assessment JSON file with OpenAI API."
    )
    parser.add_argument("game_name", help="Name of the game to assess")
    parser.add_argument(
        "--steam-appid",
        help="Optional Steam appid for the game",
        default=None,
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Path to write the JSON assessment output",
        default=None,
    )

    args = parser.parse_args()

    # Resolve repo root (parent of scripts/)
    repo_root = Path(__file__).resolve().parents[1]

    # Load concatenated instructions
    instructions_text = load_instructions(repo_root)

    # Decide output path
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
    else:
        output_path = make_default_output_path(repo_root, args.game_name)

    # Ensure API key is present
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY environment variable is not set.")

    client = OpenAI()

    # Input payload for the model
    user_payload = {"game_name": args.game_name}
    if args.steam_appid:
        user_payload["steam_appid"] = str(args.steam_appid)

    schema_text = load_schema(repo_root)

    # Single API call using the responses API
    response = client.responses.create(
        model="gpt-5.1",
        temperature=0,
        tools=[{"type": "web_search_preview"}],
        input=[
            {
                "role": "system",
                "content": (
                    instructions_text
                    + "\n\nHere is the REQUIRED JSON schema you MUST follow exactly:\n\n"
                    + schema_text
                    + "\n\nYou MUST output a JSON object matching the schema exactly. "
                      "Do not omit fields. Do NOT add fields. "
                      "Do not output markdown, explanation or prose outside JSON."
                )
            },
            {
                "role": "user",
                "content": (
                    "Run the assessment using the instructions above. "
                    "Here is the input JSON for the game:\n"
                    + json.dumps(user_payload)
                ),
            },
        ],
        # # Ask the model to emit a JSON object only. 
        # response_format={"type": "json_object"},
    )

    # Extract the text output from the response object
    # See docs: https://platform.openai.com/docs/api-reference/responses
    raw_text = response.output_text

    # Best-effort JSON parse so we can pretty-print; if it fails, write raw text
    try:
        parsed = json.loads(raw_text)
        output_text = json.dumps(parsed, indent=2, ensure_ascii=False)
    except json.JSONDecodeError:
        print(
            "Warning: model output was not valid JSON; "
            "writing raw text to the output file for debugging."
        )
        output_text = raw_text

    with output_path.open("w", encoding="utf-8") as f:
        f.write(output_text)

    print(f"Wrote assessment to {output_path}")

if __name__ == "__main__":
    main()