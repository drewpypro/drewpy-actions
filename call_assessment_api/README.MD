# request validation
- **Workflow trigger**
```yaml
      - name: Validate Request
        uses: drewpypro/drewpy-actions/request_validation@gamesv1
        id: request_validation
        with:
          game_name: ${{ steps.pre_process_validation.outputs.game_name }}
```
- **workflow example output**
```sh
Run drewpypro/drewpy-actions/request_validation@gamesv1
  with:
    game_name: curtain fun
  env:
    pythonLocation: /opt/hostedtoolcache/Python/3.10.19/x64
    PKG_CONFIG_PATH: /opt/hostedtoolcache/Python/3.10.19/x64/lib/pkgconfig
    Python_ROOT_DIR: /opt/hostedtoolcache/Python/3.10.19/x64
    Python2_ROOT_DIR: /opt/hostedtoolcache/Python/3.10.19/x64
    Python3_ROOT_DIR: /opt/hostedtoolcache/Python/3.10.19/x64
    LD_LIBRARY_PATH: /opt/hostedtoolcache/Python/3.10.19/x64/lib
Run actions/setup-python@v4
Installed versions
Run python3 "/home/runner/work/_actions/drewpypro/drewpy-actions/gamesv1/request_validation/request_validation.py" \
 Validation Okay
   Original: curtain fun
   Slug: curtain-fun
```
- request_validation@gamesv1
```
#!/usr/bin/env python3
"""
Request Validation Script for Game Assessment Workflow

Validates, sanitizes, and normalizes game name requests from GitHub issues.
"""

import argparse
import json
import os
import re
import sys
from enum import Enum
from typing import NamedTuple


class ValidationResult(Enum):
    SUCCESS = "success"
    TOO_LONG = "too_long"
    BAD_CHARACTERS = "bad_characters"
    ACCESS_DENIED = "access_denied"
    SCRIPT_ERROR = "script_error"


class ValidationOutput(NamedTuple):
    result: ValidationResult
    message: str
    slug: str | None = None
    original_name: str | None = None


# Maximum allowed character count
MAX_CHAR_COUNT = 69

# Allowed characters pattern (standard unicode)
# [A-Z], [a-z], [0-9], spaces, !, ?, ,, :, ', -, &, ., TM symbol, _, (, )
ALLOWED_CHARS_PATTERN = re.compile(r'^[A-Za-z0-9 !?,:\'\-&._\u2122()]+$')

# Denied games list (case-insensitive patterns)
DENIED_PATTERNS = [
    re.compile(r'ARK.*Survival', re.IGNORECASE),
]

# Error messages
ERROR_MESSAGES = {
    ValidationResult.TOO_LONG: "Game name longer than 69 characters, please shorten and try again or contact the administrator.",
    ValidationResult.BAD_CHARACTERS: "Bad characters in your request, please try again by submitting again using a normal human keyboard.",
    ValidationResult.ACCESS_DENIED: "I refuse to assess this game, it sucks.",
    ValidationResult.SCRIPT_ERROR: "Script has errored, please review logs and contact admin.",
}


def normalize_game_name(game_name: str) -> str:
    """
    Normalize game name to slug format.

    Rules:
    - Convert to lowercase
    - "&" gets transformed to "-and-"
    - "-" and "." do not get transformed
    - All other special characters (spaces, !, ?, ,, :, ', TM, _, (, ))
      get translated to "-"
    - Collapse multiple consecutive hyphens into one
    - Remove leading/trailing hyphens
    """
    slug = game_name.lower()

    # Transform "&" to "-and-"
    slug = slug.replace('&', '-and-')

    # Characters that become hyphens (excluding "-" and "." which stay as-is)
    # Note: "." stays as-is per requirements
    chars_to_hyphen = [' ', '!', '?', ',', ':', "'", '\u2122', '_', '(', ')']

    for char in chars_to_hyphen:
        slug = slug.replace(char, '-')

    # Collapse multiple consecutive hyphens
    slug = re.sub(r'-+', '-', slug)

    # Remove leading/trailing hyphens
    slug = slug.strip('-')

    return slug


def check_length(game_name: str) -> bool:
    """Check if game name is within allowed length."""
    return len(game_name) <= MAX_CHAR_COUNT


def check_allowed_characters(game_name: str) -> bool:
    """Check if game name contains only allowed characters."""
    return bool(ALLOWED_CHARS_PATTERN.match(game_name))


def check_denied_list(game_name: str) -> bool:
    """Check if game name matches any denied pattern. Returns True if denied."""
    for pattern in DENIED_PATTERNS:
        if pattern.search(game_name):
            return True
    return False


def validate_game_name(game_name: str) -> ValidationOutput:
    """
    Validate and process game name.

    Returns ValidationOutput with result status and appropriate message.
    """
    # Strip whitespace
    game_name = game_name.strip()

    # Check for empty input
    if not game_name:
        return ValidationOutput(
            result=ValidationResult.BAD_CHARACTERS,
            message=ERROR_MESSAGES[ValidationResult.BAD_CHARACTERS],
            original_name=game_name
        )

    # Check character count (too long)
    if not check_length(game_name):
        return ValidationOutput(
            result=ValidationResult.TOO_LONG,
            message=ERROR_MESSAGES[ValidationResult.TOO_LONG],
            original_name=game_name
        )

    # Check for bad characters
    if not check_allowed_characters(game_name):
        return ValidationOutput(
            result=ValidationResult.BAD_CHARACTERS,
            message=ERROR_MESSAGES[ValidationResult.BAD_CHARACTERS],
            original_name=game_name
        )

    # Check denied list (access denied)
    if check_denied_list(game_name):
        return ValidationOutput(
            result=ValidationResult.ACCESS_DENIED,
            message=ERROR_MESSAGES[ValidationResult.ACCESS_DENIED],
            original_name=game_name
        )

    # Normalize the game name to slug
    slug = normalize_game_name(game_name)

    return ValidationOutput(
        result=ValidationResult.SUCCESS,
        message="Validation Okay",
        slug=slug,
        original_name=game_name
    )


def set_github_output(name: str, value: str) -> None:
    """Set GitHub Actions output variable."""
    github_output = os.environ.get('GITHUB_OUTPUT')
    if github_output:
        with open(github_output, 'a') as f:
            f.write(f"{name}={value}\n")
    else:
        # Fallback for local testing
        print(f"::set-output name={name}::{value}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Validate and sanitize game name requests'
    )
    parser.add_argument(
        '--input-file',
        type=str,
        help='Path to file containing game name'
    )
    parser.add_argument(
        '--game-name',
        type=str,
        help='Game name directly as argument'
    )

    args = parser.parse_args()

    try:
        # Get game name from file or argument
        game_name = None

        if args.input_file:
            with open(args.input_file, 'r', encoding='utf-8') as f:
                game_name = f.read().strip()
        elif args.game_name:
            game_name = args.game_name
        else:
            # Try reading from environment variable
            game_name = os.environ.get('INPUT_GAME_NAME', '').strip()

        if not game_name:
            print("Error: No game name provided", file=sys.stderr)
            set_github_output('result', ValidationResult.SCRIPT_ERROR.value)
            set_github_output('message', ERROR_MESSAGES[ValidationResult.SCRIPT_ERROR])
            return 1

        # Validate the game name
        output = validate_game_name(game_name)

        # Set GitHub outputs
        set_github_output('result', output.result.value)
        set_github_output('message', output.message)
        set_github_output('original_name', output.original_name or '')

        if output.result == ValidationResult.SUCCESS:
            set_github_output('slug', output.slug or '')
            set_github_output('json_path', f"json/{output.slug}-assessment.json")
            set_github_output('md_path', f"docs/{output.slug}-assessment.md")
            print(f" {output.message}")
            print(f"   Original: {output.original_name}")
            print(f"   Slug: {output.slug}")
            return 0
        else:
            # For user-facing errors, print the message
            if output.result in [ValidationResult.TOO_LONG,
                                 ValidationResult.BAD_CHARACTERS,
                                 ValidationResult.ACCESS_DENIED]:
                print(f"L {output.message}")
            else:
                print(f"Error: {output.message}", file=sys.stderr)
            return 1

    except Exception as e:
        print(f"Script error: {e}", file=sys.stderr)
        set_github_output('result', ValidationResult.SCRIPT_ERROR.value)
        set_github_output('message', ERROR_MESSAGES[ValidationResult.SCRIPT_ERROR])
        return 1


if __name__ == '__main__':
    sys.exit(main())
```

- **drewpy-ai-actions/call_assessment_api.py**
    - where assessment instructions, context and persona are stored. 
    - generates game assessment json db. 
    - takes input $game_name-assessment.json file and generates markdown report based on template. 
- **assessment workflow**
    * runs composite action from drewpy-ai-actions/call_assessment_api.py to trigger researcher response and generate /assessments/$game_name-assessment.json and /assessments/$game_name-assessment.md files and outputs them to $GITHUB_OUTPUT
    * docs are built using jinja template. 


- **workflow output (next step-workinprogress)**
```md
- **drewpy-actions/doc_generator.py**
    - receives input pushed to staging branch and generates required npm and yarn commands required to build the site and deploy the docs on drewpypro.github.io through the gh-pages branch. 
```