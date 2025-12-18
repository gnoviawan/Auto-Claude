#!/usr/bin/env python3
"""
Fix existing tasks with "Unnamed Feature" titles.

This script scans all specs and updates implementation_plan.json files
that have "feature": "Unnamed Feature" by extracting the actual title
from spec.md.
"""

import json
from pathlib import Path


def extract_title_from_spec(spec_file: Path) -> str:
    """Extract feature title from spec.md file."""
    if not spec_file.exists():
        return "Unnamed Feature"

    try:
        with open(spec_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # Look for H1 header in first 10 lines
        for line in lines[:10]:
            line = line.strip()
            if line.startswith("# "):
                title = line[2:].strip()
                # Remove common prefixes
                for prefix in ["Specification:", "Spec:", "Feature:"]:
                    if title.startswith(prefix):
                        title = title[len(prefix):].strip()
                return title
    except Exception as e:
        print(f"Error reading {spec_file}: {e}")

    return "Unnamed Feature"


def fix_spec_dir(spec_dir: Path) -> bool:
    """Fix a single spec directory if it has 'Unnamed Feature'."""
    plan_file = spec_dir / "implementation_plan.json"
    spec_file = spec_dir / "spec.md"

    if not plan_file.exists():
        return False

    try:
        with open(plan_file, 'r', encoding='utf-8') as f:
            plan = json.load(f)

        current_feature = plan.get("feature", "")

        # Only fix if it's "Unnamed Feature"
        if current_feature != "Unnamed Feature":
            return False

        # Extract real title from spec.md
        new_title = extract_title_from_spec(spec_file)

        if new_title != "Unnamed Feature":
            plan["feature"] = new_title

            # Write back
            with open(plan_file, 'w', encoding='utf-8') as f:
                json.dump(plan, f, indent=2)

            print(f"✓ Fixed {spec_dir.name}: '{new_title}'")
            return True
        else:
            print(f"⚠ Could not extract title for {spec_dir.name}")
            return False

    except Exception as e:
        print(f"✗ Error fixing {spec_dir.name}: {e}")
        return False


def main():
    """Main function to fix all specs."""
    # Find the specs directory
    project_root = Path(__file__).parent.parent
    specs_dir = project_root / ".auto-claude" / "specs"

    if not specs_dir.exists():
        print(f"Specs directory not found: {specs_dir}")
        return

    print(f"Scanning {specs_dir}...\n")

    fixed_count = 0
    total_count = 0

    for spec_dir in sorted(specs_dir.iterdir()):
        if not spec_dir.is_dir():
            continue

        total_count += 1
        if fix_spec_dir(spec_dir):
            fixed_count += 1

    print(f"\n{'='*60}")
    print(f"Fixed {fixed_count}/{total_count} specs")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
