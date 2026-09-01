#!/usr/bin/env python3
"""SCiPNET Direct Access Terminal (TUI).

Fetches SCP wiki articles live from the Crom GraphQL API.
Article content is CC BY-SA 3.0, credit: SCP Foundation Wiki.
"""
import html
import json
import os
import random
import re
import select
import socket
import shutil
import subprocess
import sys
import threading
import time
import urllib.request

try:
    import readline  # noqa: F401, arrows + history
except ImportError:
    readline = None

API = "https://api.crom.avn.sh/graphql"
WIKI = "http://scp-wiki.wikidot.com"
FILES = "https://scp-wiki.wdfiles.com/local--files"
CACHE = os.path.expanduser("~/.cache/scipnet")
AMBIENCE = os.path.expanduser(
    "~/.local/share/scipnet/ambience.opus")
TTY = sys.stdin.isatty() and sys.stdout.isatty()
FAST = os.environ.get("SCIPNET_FAST") == "1" or not TTY

BOLD = "\033[1m"
DIM = "\033[2m"
ITAL = "\033[3m"
UNDER = "\033[4m"
STRIKE = "\033[9m"
REV = "\033[7m"
RED = "\033[31m"
GRN = "\033[32m"
YEL = "\033[33m"
BLU = "\033[34m"
MAG = "\033[35m"
CYN = "\033[36m"
RESET = "\033[0m"
ANSI_RE = re.compile(r"\033\[[0-9;]*m")

WORD_RULES = (
    (r"\[(?:REDACTED|DATA EXPUNGED|CLASSIFIED)[^\]]*\]"
     r"|\b(?:DATA )?EXPUNGED\b|\bREDACTED\b|\bCLASSIFIED\b",
     REV, 0),
    (r"[█▓▒■▉▊]+", RED, 0),
    (r"\b(?:Item #|Object Class|Containment Class|"
     r"Special Containment Procedures|Disruption Class|"
     r"Risk Class|Description|Addendum(?:\s[\w.-]+)?|"
     r"Interview Log|Incident Report|Exploration Log|"
     r"Test Log|Recovery Log|Foreword|Afterword|"
     r"Conclusion|Update|Note)(?=\s*:)",
     BOLD + YEL, 0),
    (r"\bSCP-[\d█]{2,5}(?:-[A-Za-z0-9█]+)*\b", BOLD, 0),
    (r"\bO5-(?:\d{1,2}|█+)\b|\bO5 Council\b",
     BOLD + RED, 0),
    (r"\b(?:Site|Area|Sector|Outpost|Zone)-[\d█]+\b",
     BLU, 0),
    (r"\bD-[\d█]{3,5}\b|\bD-[Cc]lass\b", YEL, 0),
    (r"\bMobile Task Forces?\b|\bMTF\b|"
     r"\b(?:Alpha|Beta|Gamma|Delta|Epsilon|Zeta|Eta|Theta|"
     r"Iota|Kappa|Lambda|Mu|Nu|Xi|Omicron|Pi|Rho|Sigma|Tau|"
     r"Upsilon|Phi|Chi|Psi|Omega)-\d+\b",
     MAG, 0),
    (r"\b(?:Dr|Doctor|Researcher|Agent|Director|Professor|"
     r"Prof|Cmdr|Commander|Captain|Lieutenant|Sgt)\.?"
     r"\s+[A-Z█][\w█'-]+", CYN, 0),
    (r"\b(?:Interviewer|Interviewee|Interviewed|Subject)"
     r"(?=\s*:)", BOLD + CYN, 0),
    (r"<[^<>\n]{1,50}>", GRN, 0),
    (r"\b(?:terminated?|termination|deceased|"
     r"fatalit(?:y|ies)|casualt(?:y|ies))\b", RED, re.I),
    (r"\bcontainment breach(?:es|ed)?\b|"
     r"\bbreach(?:es|ed)?\b", RED, re.I),
    (r"\bamnestic(?:s|ized|ization)?\b", MAG, re.I),
    (r"\b(?:Chaos Insurgency|Global Occult Coalition|"
     r"Serpent'?s Hand|Church of the Broken God|"
     r"Marshall,? Carter,? (?:and|&) Dark|"
     r"Wondertainment|Are We Cool Yet\??|GRU Division)\b",
     MAG, 0),
    (r"\bLevel [0-6](?:/[A-Z0-9█]+)?\b|"
     r"\bLEVEL [0-6](?:/[A-Z0-9█]+)?\b", YEL, 0),
    (r"\b(?:Keter|KETER|keter)\b", RED, 0),
    (r"\b(?:Euclid|EUCLID|euclid)\b", YEL, 0),
    (r"\bSafe\b|\bSAFE\b", GRN, 0),
    (r"\b(?:Thaumiel|THAUMIEL|Archon|ARCHON)\b", MAG, 0),
    (r"\b(?:Apollyon|APOLLYON)\b", RED, 0),
    (r"\b(?:Neutralized|NEUTRALIZED|Decommissioned|"
     r"DECOMMISSIONED|Explained|EXPLAINED)\b", DIM, 0),
    (r"\bNOTICE\b", GRN, 0),
    (r"\b(?:CAUTION|WARNING|VLAM|KENEQ)\b", YEL, 0),
    (r"\b(?:DANGER|CRITICAL|AMIDA|EKHI|DARK)\b", RED, 0),
)


def highlight(t):
    for pat, color, flags in WORD_RULES:
        t = re.sub(pat, color + r"\g<0>" + RESET, t,
                   flags=flags)
    return t

M_IMG = "\x02I\x02"
M_COL = "\x02C\x02"
M_TAB = "\x02T\x02"
M_ACS = "\x02A\x02"
M_CODE = "\x02D\x02"
M_WARN = "\x02W\x02"
M_AUDIO = "\x02U\x02"
M_OMIT = "\x02O\x02"
M_LIC = "\x02L\x02"
M_MEDIA = "\x02V\x02"

DOC = None

LOGO = r"""
                :=--------=-
               .%:.........%-
            .-=+-          :*=-.
          -+=-.      --      .:=+=.
        -*-.    .-=++%%++=-.     -*=
      .*+     =**+=::*#::-+**=.    =*:
     .#-    -#*:     *#     :*%=    :#:
     *=    +%-     .+%%*.     :%*    :#
    :#    :%=        +*        -@-    *-
    -#    +%.    ....  .....   .%*    ++
    =#    -%-  :*%%%-  :#%%*:  :%=    **
  -+=.     #%+**=:+.    .+:=**+##.     -+-
  =#.     -*+%*.             +%**=      *+
   :#-       .+#*=:.    .:=*#+:       :#-
    .*+         :=+******+=-         -#:
      +*--==-.                .-==--+*
       ::...:===--:......::-===-...:-
                .:--------::.
"""


