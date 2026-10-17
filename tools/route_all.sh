#!/bin/sh
# Full routing pipeline for odock-10 (writes the routed board to hardware/odock-10/odock-10.kicad_pcb).
#  1. scripted routing (planes, power, high-speed)       routing/[a-y]*.py
#  2. drop outer-layer GND pours so they don't block the autorouter
#  3. Freerouting on the remaining nets (long: run detached, see README)
#  4. re-add zones (a_planes), GND stitching (z_stitch), fill, DRC
# usage: tools/route_all.sh [passes]
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PD="$ROOT/hardware/odock-10"
P=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3
K=/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli
W="$PD/build"; mkdir -p "$W"
PASSES="${1:-8}"
SCRIPTS=$(cd "$PD/routing" && ls [a-y]*.py | sed 's/\.py$//' | tr '\n' ',' | sed 's/,$//')
echo "== 1. scripted routing: $SCRIPTS"
$P "$ROOT/tools/apply_routing.py" "$PD" --only "$SCRIPTS" --no-fill --out "$W/stage1.kicad_pcb"
echo "== 2. drop outer GND pours"
$P - "$W/stage1.kicad_pcb" "$W/stage1b.kicad_pcb" <<'PY'
import sys, pcbnew
b = pcbnew.LoadBoard(sys.argv[1])
# only the general GND pours from a_planes (re-added in step 4); keep b_power's hot-loop pours (P_GND_HOT_*)
for z in list(b.Zones()):
    if z.GetNetname() == "GND" and z.GetLayer() in (pcbnew.F_Cu, pcbnew.B_Cu) and not z.GetZoneName().startswith("P_"):
        b.Remove(z)
b.Save(sys.argv[2])
PY
echo "== 3. autoroute ($PASSES passes)"
$P "$ROOT/tools/autoroute.py" "$W/stage1b.kicad_pcb" --passes "$PASSES" --out "$W/stage2.kicad_pcb"
echo "== 4. zones + stitching + fill"
$P "$ROOT/tools/apply_routing.py" "$PD" --pcb "$W/stage2.kicad_pcb" --only a_planes,z_stitch --out "$PD/odock-10.kicad_pcb"
$K pcb drc --severity-error -o "$W/drc.rpt" "$PD/odock-10.kicad_pcb" || true
grep "^\*\* Found" "$W/drc.rpt" || true
