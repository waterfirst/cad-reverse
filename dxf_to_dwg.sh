#!/usr/bin/env bash
# DXF -> DWG (AutoCAD 2018) via ODA File Converter (free, installed separately).
# Usage: ODA_CONVERTER=/path/to/ODAFileConverter ./dxf_to_dwg.sh <input.dxf> <output_dir>
# If ODAFileConverter is on PATH, ODA_CONVERTER can be omitted.
# On some Linux systems the bundled Qt rejects the offscreen plugin; then point
# LD_LIBRARY_PATH / QT_PLUGIN_PATH at the system Qt6 libs before running this script.
set -euo pipefail
IN_DIR=$(mktemp -d); trap 'rm -rf "$IN_DIR"' EXIT
cp "$1" "$IN_DIR/"
ODA="${ODA_CONVERTER:-ODAFileConverter}"
QT_QPA_PLATFORM=offscreen "$ODA" "$IN_DIR" "$2" ACAD2018 DWG 0 1
