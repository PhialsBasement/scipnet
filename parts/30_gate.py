ORACLE_NOUNS = (
    "lantern", "mirror", "threshold", "hour", "ash",
    "salt", "tide", "bell", "key", "door", "name",
    "shadow", "thread", "candle", "well", "stone",
    "gate", "breath", "seam", "coin", "root", "glass",
    "dust", "harbour", "echo", "needle", "veil", "hinge",
    "clock", "river", "lock", "wick", "seed", "window",
)
ORACLE_VERBS = (
    "keeps", "forgets", "remembers", "answers",
    "swallows", "holds", "loosens", "opens", "closes",
    "waits for", "returns", "denies", "mends", "drowns",
    "burns", "counts", "empties", "outlives",
)
ORACLE_IMPS = (
    "count", "name", "close", "hold", "weigh", "bury",
    "mark", "follow", "forget", "salt", "open", "carry",
)
ORACLE_TEMPLATES = (
    "the {n1} {v1} what the {n2} {v2}",
    "no {n1} {v1} the {n2} it left",
    "{i1} the {n1} before the {n2} {v1}",
    "what the {n1} {v1} the {n2} will not",
    "every {n1} owes the {n2} one {n3}",
    "the {n1} {v1} longer than the {n2}",
    "{i1} nothing the {n1} has already {v1}",
    "between the {n1} and the {n2} lies the {n3}",
)


def generate_oracle():
    t = random.choice(ORACLE_TEMPLATES)
    n1, n2, n3 = random.sample(ORACLE_NOUNS, 3)
    v1, v2 = random.sample(ORACLE_VERBS, 2)
    return t.format(n1=n1, n2=n2, n3=n3,
                    v1=v1, v2=v2,
                    i1=random.choice(ORACLE_IMPS))

COGNITO_RE = re.compile(
    r"cognitohazard|cognitohazardous|memetic hazard|"
    r"memetic agent|memetic kill|infohazard|antimeme|"
    r"antimemetic|visual hazard|memetic effect|"
    r"object-warning-box", re.I)

ANTIDOTE_RE = re.compile(
    r"(?:inoculat\w*|counter-?memetic|antimemetic|vaccine|"
    r"prophylactic|verification phrase|mnemonic)"
    r"[^\n]{0,180}?[\"“]([^\"”\n]{8,90})"
    r"[\"”]", re.I)


def find_antidote(src):
    """Returns an inoculation phrase from the file, or None."""
    for m in ANTIDOTE_RE.finditer(src):
        phrase = " ".join(m.group(1).split())
        if re.search(r"[<>=|{}\[\]/\\@#]|__|\*\*", phrase):
            continue
        words = phrase.split(" ")
        if len(words) < 2 or len(words) > 12:
            continue
        wordy = sum(1 for w in words
                    if re.fullmatch(r"[A-Za-z][A-Za-z'-]*",
                                    w))
        if wordy >= max(2, len(words) - 1):
            return phrase
    return None


ORACLE_URL = "https://sacred-texts.com/ich/ic%02d.htm"
ORACLE_CACHE = os.path.join(CACHE, "oracle")
ORACLE_LINE = re.compile(
    r"^\d\.\s+The\s+(?:first|second|third|fourth|fifth|"
    r"sixth|topmost)\s+(?:NINE|SIX|nine|six)\b", re.I)
ORACLE_LEAD = re.compile(
    r"^.*?\b(?:shows us|shows that|shows|suggests the "
    r"idea of|reminds us of|indicates|represents)\b"
    r"[,:]?\s*", re.I)


def parse_oracle(raw):
    raw = raw.split("Footnotes")[0]
    out = []
    for p in re.split(r"<p[^>]*>", raw, flags=re.I):
        t = " ".join(html.unescape(
            re.sub(r"<[^>]+>", " ", p)).split())
        if ORACLE_LINE.match(t) is None:
            continue
        t = re.sub(r"\([^)]*\)", "", t)
        t = ORACLE_LEAD.sub("", t)
        t = " ".join(re.sub(r"p\.\s*\d+", " ", t).split())
        for s in re.split(r"(?<=[.;])\s+", t):
            s = s.strip().strip(".;,: ")
            w = [x for x in s.split(" ") if x]
            if 4 <= len(w) <= 11 and len(s) <= 62 \
                    and re.fullmatch(r"[A-Za-z ,'-]+", s):
                out.append(s[0].upper() + s[1:])
    return out


def oracle_lines(n):
    os.makedirs(ORACLE_CACHE, exist_ok=True)
    path = os.path.join(ORACLE_CACHE, "%02d.json" % n)
    if os.path.exists(path):
        try:
            with open(path) as fh:
                return json.load(fh)
        except Exception:
            pass
    req = urllib.request.Request(
        ORACLE_URL % n,
        headers={"User-Agent": "scipnet-tui/1.0"})
    with urllib.request.urlopen(req, timeout=8) as r:
        lines = parse_oracle(r.read().decode("utf-8",
                                             "ignore"))
    if lines:
        with open(path, "w") as fh:
            json.dump(lines, fh)
    return lines


def cached_oracle():
    try:
        files = [f for f in os.listdir(ORACLE_CACHE)
                 if f.endswith(".json")]
    except OSError:
        return None
    random.shuffle(files)
    for f in files:
        try:
            with open(os.path.join(ORACLE_CACHE, f)) as fh:
                lines = json.load(fh)
            if lines:
                return (random.choice(lines),
                        "I Ching, hexagram %d"
                        % int(f[:2]), True)
        except Exception:
            continue
    return None


def challenge_phrase():
    """Returns (phrase, attribution, from_corpus)."""
    for n in random.sample(range(1, 65), 3):
        try:
            lines = oracle_lines(n)
        except Exception:
            continue
        if lines:
            return (random.choice(lines),
                    "I Ching, hexagram %d" % n, True)
    hit = cached_oracle()
    if hit:
        return hit
    return (generate_oracle(), None, False)


def normalize(s):
    s = re.sub(r"[^a-z0-9 ]", " ", s.lower())
    return " ".join(s.split())


WARNBOX_RE = re.compile(
    r"\[\[include\s+\S*object-warning-box\S*([^\]]*)\]\]",
    re.S | re.I)


def clean_markup(v):
    v = re.sub(r"\*\*|//|__|@@", "", v)
    return v.strip()


def warning_box_fields(src):
    """The file's own warning proclamation, or None."""
    m = WARNBOX_RE.search(src)
    if m is None:
        return None
    args = parse_args(m.group(1))
    top = clean_markup(args.get("text-top", ""))
    bottom = clean_markup(args.get("text-bottom", ""))
    if top == "" and bottom == "":
        return None
    return {"top": top, "bottom": bottom,
            "img": args.get("bg-image", "")}


def gate_art(url, slug):
    """Chafa rendering of a warning image, or None."""
    if shutil.which("chafa") is None:
        return None
    path = fetch_image(url, slug)
    if path is None:
        return None
    gray = path + ".gray.png"
    src2 = gray if os.path.exists(gray) else path
    if src2 == path and shutil.which("magick"):
        r = subprocess.run(
            ["magick", path, "-colorspace", "Gray", gray],
            capture_output=True)
        if r.returncode == 0:
            src2 = gray
    r = subprocess.run(
        ["chafa", "-f", "symbols", "--size", "44x14", src2],
        capture_output=True, text=True)
    if r.returncode != 0:
        return None
    return art_lines(r.stdout)


def hazard_stripe(w):
    return ("/// " * (w // 4 + 1))[:w]


def gate_frame(slug, source_line, phrase, who, attempts,
               warn=None, art=None):
    """Builds the containment-seal screen as a line list."""
    size = shutil.get_terminal_size()
    w = min(size.columns - 4, 74)
    inner = w - 2
    R, D, B = RED, DIM, BOLD

    def bar(ch="="):
        return R + "+" + ch * inner + "+"

    def row(txt="", style="", cen=True):
        pad = inner - vlen(txt)
        left = pad // 2 if cen else 1
        right = pad - left
        return (R + "|" + RESET + " " * left + style + txt
                + RESET + " " * right + R + "|")

    def field(k, v):
        txt = "%-14s %s" % (k, v)
        return row(txt[:inner - 4], cen=False)

    title = " M E M E T I C   I N T E R L O C K "
    lines = [
        R + B + hazard_stripe(w),
        bar("="),
        row(title, B + RED),
        bar("="),
        row(),
    ]
    if art:
        for al in art:
            lines.append(row(al))
        lines.append(row())
    if warn:
        for wl in wrap_ansi(warn["top"].upper(), inner - 4):
            lines.append(row(wl, B + RED))
        lines.append(row())
        for para in warn["bottom"].split("\n"):
            para = " ".join(para.split())
            if para == "":
                continue
            for wl in wrap_ansi(para, inner - 4):
                lines.append(row(wl, RED))
        lines.append(row())
    else:
        lines += [
            row("!!  COGNITOHAZARD WARNING  !!", B + RED),
            row(),
            row("THIS RECORD IS FLAGGED FOR MEMETIC OR",
                RED),
            row("COGNITOHAZARDOUS CONTENT.", RED),
            row(),
        ]
    lines += [
        bar("-"),
        field("RECORD:", slug.upper()),
        field("FLAG TYPE:", "CLASS III COGNITOHAZARD"),
        field("PROTOCOL:", "BASELINE RECITAL, 3 ATTEMPTS"),
        field("INOCULATION:", source_line),
        bar("-"),
        row(),
        row("RECITE THE STRING BELOW, WORD FOR WORD,", D),
        row("TO CONFIRM COGNITIVE BASELINE.", D),
        row(),
        row("\"" + phrase + "\"", B),
    ]
    if who:
        lines.append(row("-- %s" % who, D))
    meter = "[" + "#" * attempts + "." * (3 - attempts) + "]"
    lines += [
        row(),
        row("ATTEMPTS %s   BLANK LINE ABORTS" % meter, D),
        bar("="),
        R + B + hazard_stripe(w),
    ]
    return lines, w


def play_alert():
    """One-shot: first 5s of the site track (the alert)."""
    if os.environ.get("SCIPNET_SILENT") == "1" \
            or shutil.which("mpv") is None \
            or os.path.exists(AMBIENCE) is False:
        return
    subprocess.Popen(
        ["mpv", "--no-video", "--really-quiet",
         "--start=0", "--end=5", "--volume=60", AMBIENCE],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL)


def cognitohazard_gate(src, slug="unknown"):
    """Red inoculation screen. True if cleared to proceed."""
    antidote = find_antidote(src)
    who = None
    if antidote:
        phrase = antidote
        source_line = "RECOVERED FROM FILE HEADER"
    else:
        phrase, who, live = challenge_phrase()
        source_line = ("DRAWN FROM LIVE MNEMONIC POOL"
                       if live else "LOCAL STRING ISSUED")
    warn = warning_box_fields(src)
    art = None
    if warn and warn.get("img"):
        u = warn["img"].lower()
        stock = ("emblem" in u or "scp_foundation" in u)
        if stock is False:
            art = gate_art(warn["img"], slug)
    attempts = 3
    verdict = None
    play_alert()
    sys.stdout.write("\033[?1049h")
    try:
        while attempts > 0:
            size = shutil.get_terminal_size()
            frame, w = gate_frame(slug, source_line, phrase,
                                  who, attempts, warn, art)
            top = max(1, (size.lines - len(frame) - 4) // 2)
            left = max(1, (size.columns - w) // 2 + 1)
            sys.stdout.write("\033[2J")
            logo_rows = [l.rstrip() for l in LOGO.split("\n")
                         if l.strip()]
            lw = max(len(l) for l in logo_rows)
            larea = left - 4
            if larea >= lw + 2:
                ltop = max(1, (size.lines - len(logo_rows))
                           // 2)
                lcol = max(1, (larea - lw) // 2 + 1)
                rcol = left + w + 2 \
                    + max(0, (size.columns - left - w - 2
                              - lw) // 2)
                for k, ll in enumerate(logo_rows):
                    sys.stdout.write(
                        "\033[%d;%dH%s%s%s"
                        % (ltop + k, lcol, DIM + RED, ll,
                           RESET))
                    sys.stdout.write(
                        "\033[%d;%dH%s%s%s"
                        % (ltop + k, rcol, DIM + RED, ll,
                           RESET))
            for i, ln in enumerate(frame):
                sys.stdout.write("\033[%d;%dH%s%s"
                                 % (top + i, left, ln, RESET))
            if verdict:
                vcol = max(1, (size.columns - vlen(verdict))
                           // 2 + 1)
                sys.stdout.write("\033[%d;%dH%s%s"
                                 % (top + len(frame) + 1,
                                    vcol, verdict, RESET))
            prow = top + len(frame) + 2
            sys.stdout.write("\033[%d;1H" % prow)
            sys.stdout.flush()
            prompt = (" " * (left - 1)
                      + "\001" + BOLD + RED + "\002"
                      + "RECITE > "
                      + "\001" + RESET + "\002")
            try:
                said = input(prompt)
            except (EOFError, KeyboardInterrupt):
                return False
            if said.strip() == "":
                return False
            if normalize(said) == normalize(phrase):
                sys.stdout.write(
                    "\033[%d;%dH%sBASELINE CONFIRMED. "
                    "MEMETIC INTERLOCK RELEASED.%s"
                    % (prow + 1, left, GRN, RESET))
                sys.stdout.flush()
                pause(0.9)
                return True
            attempts -= 1
            verdict = (BOLD + RED + "RECITAL MISMATCH. "
                       "BASELINE UNCONFIRMED.")
        return False
    finally:
        sys.stdout.write(RESET + "\033[?1049l")
        sys.stdout.flush()


