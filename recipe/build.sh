#!/bin/bash
set -euxo pipefail

# Install the package normally
python -m pip install . --no-deps --no-build-isolation -vv

# Use the normalized PKG_VERSION from rattler-build instead of versioningit
echo "PKG_VERSION from rattler-build: $PKG_VERSION"
echo "version = \"$PKG_VERSION\"" > $SP_DIR/plot_publisher/_version.py

echo "Fixed _version.py with version: $PKG_VERSION"
