#!/usr/bin/env python3
"""Builds parts/*.py into the single-file scipnet tool.

Concatenates parts in name order, syntax-checks the
result, smoke-tests it, then installs to ~/.local/bin.
"""
import os
import py_compile
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PARTS = os.path.join(HERE, "parts")
ASSETS = os.path.join(HERE, "assets")
SHARE = os.path.expanduser("~/.local/share/scipnet")
TARGET = os.path.expanduser("~/.local/bin/scipnet")
STAGE = os.path.join(HERE, ".stage")

names = sorted(f for f in os.listdir(PARTS)
               if f.endswith(".py"))
if len(names) == 0:
    sys.exit("no parts found in " + PARTS)

blob = ""
for n in names:
    with open(os.path.join(PARTS, n)) as fh:
        blob += fh.read()

with open(STAGE, "w") as fh:
    fh.write(blob)

py_compile.compile(STAGE, doraise=True)

r = subprocess.run(
    [sys.executable, STAGE],
    input="agent\nhelp\nlogout\n",
    capture_output=True, text=True, timeout=60,
    env=dict(os.environ, SCIPNET_FAST="1"))
if "SESSION TERMINATED" not in r.stdout:
    sys.exit("smoke test failed:\n" + r.stdout[-2000:]
             + r.stderr[-2000:])

os.replace(STAGE, TARGET)
os.chmod(TARGET, 0o755)
installed = 0
if os.path.isdir(ASSETS):
    os.makedirs(SHARE, exist_ok=True)
    import shutil
    for a in sorted(os.listdir(ASSETS)):
        src = os.path.join(ASSETS, a)
        dst = os.path.join(SHARE, a)
        if os.path.exists(dst) is False or \
                os.path.getmtime(src) > os.path.getmtime(dst):
            shutil.copy2(src, dst)
            installed += 1
print("built %s from %d parts (%d lines), "
      "%d asset(s) installed"
      % (TARGET, len(names), blob.count("\n"), installed))
