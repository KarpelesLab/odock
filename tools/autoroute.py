"""Autoroute the remaining (unrouted) connections of a KiCad board with Freerouting.

Existing tracks/vias are exported as fixed wiring, so hand/script-routed critical nets (diff pairs, power)
are preserved; Freerouting only completes what is left. Nets can be excluded from autorouting by net class.

Run with KiCad's bundled Python:
  /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3 \
      tools/autoroute.py hardware/odock-10/odock-10.kicad_pcb [--passes 100] [--out routed.kicad_pcb]

Freerouting 2.4 needs Java 25: a portable Temurin JDK + the jar live in ~/.local/share/odock/
(override with FREEROUTING_JAR / FREEROUTING_JAVA). Analytics, GUI and API server are disabled.
"""
import os, sys, glob, subprocess, argparse, tempfile, shutil
import pcbnew

BASE = os.path.expanduser("~/.local/share/odock")


def java():
    j = os.environ.get("FREEROUTING_JAVA")
    if j:
        return j
    homes = sorted(glob.glob(os.path.join(BASE, "jdk-25*/Contents/Home")))
    return os.path.join(homes[-1], "bin", "java") if homes else "java"


def jar():
    return os.environ.get("FREEROUTING_JAR") or sorted(glob.glob(os.path.join(BASE, "freerouting-*.jar")))[-1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pcb")
    ap.add_argument("--passes", type=int, default=100)
    ap.add_argument("--threads", type=int, default=0)
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    work = tempfile.mkdtemp(prefix="autoroute-")
    dsn, ses = os.path.join(work, "board.dsn"), os.path.join(work, "board.ses")
    board = pcbnew.LoadBoard(a.pcb)
    if not pcbnew.ExportSpecctraDSN(board, dsn):
        sys.exit("DSN export failed")
    env = dict(os.environ,
               FREEROUTING__GUI__ENABLED="false",
               FREEROUTING__API_SERVER__ENABLED="false",
               FREEROUTING__USAGE_AND_DIAGNOSTIC_DATA__DISABLE_ANALYTICS="true")
    cmd = [java(), "-jar", jar(), "-de", dsn, "-do", ses, "-mp", str(a.passes)]
    if a.threads:
        cmd += ["-mt", str(a.threads)]
    print(" ".join(cmd), flush=True)
    r = subprocess.run(cmd, env=env, cwd=work)
    if r.returncode != 0 or not os.path.exists(ses):
        sys.exit(f"freerouting failed (rc={r.returncode}); work dir {work}")
    if not pcbnew.ImportSpecctraSES(board, ses):
        sys.exit("SES import failed")
    board.Save(a.out or a.pcb)
    shutil.copy(ses, (a.out or a.pcb) + ".ses")
    print("routed ->", a.out or a.pcb)


if __name__ == "__main__":
    main()
