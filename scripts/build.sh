#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
blender --factory-startup --command extension validate uv_pixel_transform
mkdir -p dist
blender --factory-startup --command extension build --source-dir uv_pixel_transform --output-dir dist
