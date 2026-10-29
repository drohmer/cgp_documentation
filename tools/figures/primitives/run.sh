#!/bin/bash
# Regenerate the figures of content/how-to/create-basic-shapes.md from the real CGP meshes.
#  1. export_primitives.cpp is linked with the CGP objects compiled by `make recipes`
#     (build/recipes/base, native build of the cgp-2027 template), and writes the meshes as JSON;
#  2. render_primitives.py draws each mesh as an SVG (flat shading, triangle edges, axes).
# Usage (from the root of cgp-documentation):  bash tools/figures/primitives/run.sh
set -e
ROOT=$(cd "$(dirname "$0")/../../.." && pwd)
BASE=$ROOT/build/recipes/base
HERE=$ROOT/tools/figures/primitives
TMP=$(mktemp -d)
[ -d "$BASE/build/cgp" ] || { echo "run 'make recipes' first (needs build/recipes/base)"; exit 1; }
OBJS=$(find "$BASE/build/cgp" -name "*.o" | grep -v "/test/" | grep -v "opengl4")
c++ -std=c++17 -O1 -I"$BASE" -I"$BASE/cgp" $(pkg-config --cflags glfw3) -DCGP_OPENGL_3_3 \
    "$HERE/export_primitives.cpp" $OBJS -o "$TMP/export" $(pkg-config --libs glfw3) $( [ "$(uname)" = Darwin ] && echo "-framework OpenGL" )
"$TMP/export" "$TMP/primitives.json"
python3 "$HERE/render_primitives.py" "$TMP/primitives.json" "$ROOT/content/assets/primitives"
rm -rf "$TMP"
