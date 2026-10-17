#!/bin/sh
# Import LCSC parts (symbol + footprint + 3D model) into hardware/lib via easyeda2kicad,
# then make 3D paths project-relative and upgrade files to the current KiCad format.
# usage: tools/import_lcsc.sh C2870250 [C123 ...]
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LIB="$ROOT/hardware/lib"
E2K="${E2K:-$HOME/.venvs/odock/bin/easyeda2kicad}"
KCLI="/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
cd "$LIB"
# serialize concurrent imports (several agents/scripts may run at once)
while ! mkdir "$LIB/.lock" 2>/dev/null; do sleep 1; done
trap 'rmdir "$LIB/.lock"' EXIT INT TERM
# protect existing footprints: easyeda2kicad overwrites same-named footprints of *other* parts
BK="$(mktemp -d)"; cp -p odock.pretty/*.kicad_mod "$BK/" 2>/dev/null || true
"$E2K" --full --overwrite --output "$LIB/odock" --lcsc_id "$@"
for f in "$BK"/*.kicad_mod; do
  [ -e "$f" ] || continue
  n="odock.pretty/$(basename "$f")"
  if ! cmp -s "$f" "$n"; then
    echo "WARNING: import changed existing footprint $(basename "$f") - restored the original." >&2
    echo "         The new part shares that footprint name; check it and give it its own footprint if needed." >&2
    cp -p "$f" "$n"
  fi
done
# absolute 3D model paths -> relative to the project dir (projects live in hardware/<name>/)
sed -i '' "s#$LIB/odock.3dshapes/#\${KIPRJMOD}/../lib/odock.3dshapes/#g" odock.pretty/*.kicad_mod
"$KCLI" sym upgrade --force odock.kicad_sym >/dev/null
# upgrade only footprints that are new from this import (don't reformat the verified library)
UP="$(mktemp -d)/new.pretty"; mkdir -p "$UP"
for f in odock.pretty/*.kicad_mod; do [ -e "$BK/$(basename "$f")" ] || cp -p "$f" "$UP/"; done
if ls "$UP"/*.kicad_mod >/dev/null 2>&1; then
  "$KCLI" fp upgrade --force "$UP" >/dev/null 2>&1 || true
  cp -p "$UP"/*.kicad_mod odock.pretty/
fi
rm -rf "$BK"
