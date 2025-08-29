#!/bin/bash
set -euo pipefail

# Install the Python package
python -m pip install . --no-deps --no-build-isolation -vv

# Get the full version from versioningit
FULL_VERSION=$(python -c "import versioningit; print(versioningit.get_version())")
echo "Full versioningit version: $FULL_VERSION"

# Use the conda package version (normalized, without local version identifier)
echo "Conda package version: $PKG_VERSION"

# Debug: Check if SP_DIR is set and the directory exists
echo "SP_DIR: $SP_DIR"
echo "Checking if $SP_DIR exists..."
ls -la "$SP_DIR" || echo "SP_DIR does not exist"

# Find the actual installation location
echo "Looking for plot_publisher installation..."
python -c "import plot_publisher; print('plot_publisher location:', plot_publisher.__file__)"

# Write the conda package version to _version.py so they match
VERSION_FILE="$SP_DIR/plot_publisher/_version.py"
echo "Writing to version file: $VERSION_FILE"
echo "version = \"$PKG_VERSION\"" > "$VERSION_FILE"
echo "Fixed _version.py with version: $PKG_VERSION"

# Verify the file was written correctly
echo "Contents of $VERSION_FILE:"
cat "$VERSION_FILE"
