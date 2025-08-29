#!/usr/bin/env python3
"""Update conda recipe with current version from versioningit."""

import subprocess
import sys

import yaml


def main():
    # Get version from versioningit
    try:
        result = subprocess.run([sys.executable, "-m", "versioningit", "."], capture_output=True, text=True, check=True)
        version = result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error getting version: {e}", file=sys.stderr)
        sys.exit(1)

    # Read recipe
    recipe_path = "recipe/recipe.yaml"
    with open(recipe_path, "r") as f:
        recipe = yaml.safe_load(f)

    # Update version
    recipe["package"]["version"] = version

    # Write back
    with open(recipe_path, "w") as f:
        yaml.dump(recipe, f, default_flow_style=False, sort_keys=False)

    print(f"Updated recipe version to: {version}")


if __name__ == "__main__":
    main()
