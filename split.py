#!/usr/bin/env python3
"""One-time splitter: cuts the installed single-file
scipnet into verbatim parts. Kept for reference."""
import os

SRC = os.path.expanduser("~/.local/bin/scipnet")
OUT = os.path.join(os.path.dirname(
    os.path.abspath(__file__)), "parts")

# (name, first line 1-based, first line of next part)
BOUNDS = [
    ("00_header", 1, 142),
    ("10_flavor", 142, 235),
    ("20_profile", 235, 298),
    ("30_gate", 298, 600),
    ("40_net", 600, 698),
    ("50_parse", 698, 954),
    ("60_viewer", 954, 1141),
    ("70_images", 1141, 1243),
    ("80_render", 1243, 1509),
    ("90_repl", 1509, None),
]

with open(SRC) as fh:
    lines = fh.readlines()

os.makedirs(OUT, exist_ok=True)
for name, a, b in BOUNDS:
    chunk = lines[a - 1:(b - 1 if b else None)]
    with open(os.path.join(OUT, name + ".py"), "w") as fh:
        fh.writelines(chunk)
    print("%-12s %4d lines" % (name, len(chunk)))
