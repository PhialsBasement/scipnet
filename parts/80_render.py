def chunk_ansi(word, w):
    out, cur, cl = [], "", 0
    for m in re.finditer(r"\x1b\[[0-9;]*m|.", word, re.S):
        tok = m.group(0)
        if tok.startswith("\x1b"):
            cur += tok
            continue
        if cl == w:
            out.append(cur)
            cur, cl = "", 0
        cur += tok
        cl += 1
    if cur:
        out.append(cur)
    return out


def cell_wrap(txt, w):
    parts = []
    for word in txt.split(" "):
        if word == "":
            continue
        if vlen(word) > w:
            parts.extend(chunk_ansi(word, w))
        else:
            parts.append(word)
    return wrap_ansi(" ".join(parts), w)


def render_table(rows, pager, width):
    parsed = []
    for row in rows:
        cells = [c.strip()
                 for c in row.strip("|").split("||")]
        if any(c != "" for c in cells):
            parsed.append(
                [(inline(c.lstrip("~ ")),
                  c.startswith("~")) for c in cells])
    if len(parsed) == 0:
        return
    cols = max(len(r) for r in parsed)
    for r in parsed:
        r += [("", False)] * (cols - len(r))
    overhead = 3 * (cols - 1) + 4
    budget = max(cols * 4, width - overhead)
    naturals = [max(vlen(r[i][0]) for r in parsed) or 1
                for i in range(cols)]
    minw = []
    for i in range(cols):
        longest = 1
        for r in parsed:
            plain = ANSI_RE.sub("", r[i][0])
            for wd in plain.split():
                longest = max(longest, min(len(wd), 18))
        minw.append(min(longest, naturals[i]))
    if sum(naturals) <= budget:
        alloc = naturals
    elif sum(minw) >= budget:
        alloc = minw
    else:
        room = budget - sum(minw)
        growth = [naturals[i] - minw[i]
                  for i in range(cols)]
        tg = sum(growth) or 1
        alloc = [minw[i] + room * growth[i] // tg
                 for i in range(cols)]
        big = alloc.index(max(alloc))
        alloc[big] += budget - sum(alloc)
    rule = (DIM + "+" + "+".join(
        "-" * (a + 2) for a in alloc) + "+")
    sep = DIM + " | " + RESET
    pager.line(rule)
    for r in parsed:
        wrapped = [cell_wrap(txt, alloc[i]) if txt else [""]
                   for i, (txt, _) in enumerate(r)]
        height = max(len(wc) for wc in wrapped)
        for k in range(height):
            segs = []
            for i, (txt, hdr) in enumerate(r):
                seg = wrapped[i][k] \
                    if k < len(wrapped[i]) else ""
                pad = " " * max(0, alloc[i] - vlen(seg))
                style = BOLD if hdr else ""
                segs.append(style + seg + RESET + pad)
            pager.line(DIM + "| " + RESET
                       + sep.join(segs)
                       + DIM + " |")
        pager.line(rule)
    pager.line()


def render_box(lines, pager, width, heavy=False):
    inner = max(vlen(l) for l in lines) + 4
    inner = min(inner, width - 2)
    edge = ("=" if heavy else "-") * inner
    pager.line(BOLD + "+" + edge + "+")
    for l in lines:
        padlen = inner - vlen(l) - 2
        left = padlen // 2
        pager.line(BOLD + "| " + " " * left + l
                   + " " * (padlen - left) + " |")
    pager.line(BOLD + "+" + edge + "+")
    pager.line()


def render_acs(fields, pager, width):
    cls = fields.get("container-class",
                     fields.get("containment-class", ""))
    rows = []
    top = []
    if fields.get("item-number"):
        top.append("ITEM #: " + fields["item-number"].upper())
    if fields.get("clearance"):
        top.append("LEVEL %s/RESTRICTED"
                   % fields["clearance"])
    if top:
        rows.append("   ".join(top))
    if cls:
        rows.append("CONTAINMENT CLASS: " + cls.upper())
    if fields.get("secondary-class"):
        rows.append("SECONDARY CLASS: "
                    + fields["secondary-class"].upper())
    mid = []
    if fields.get("disruption-class"):
        mid.append("DISRUPTION: "
                   + fields["disruption-class"].upper())
    if fields.get("risk-class"):
        mid.append("RISK: " + fields["risk-class"].upper())
    if mid:
        rows.append("   ".join(mid))
    render_box([highlight(r) for r in rows], pager, width,
               heavy=True)


def render_lines(text, pager, width, depth=0):
    table_rows = []
    for raw in text.split("\n"):
        line = raw.rstrip()
        if line.startswith("||"):
            table_rows.append(line)
            continue
        if table_rows:
            render_table(table_rows, pager, width)
            table_rows = []
        if line.startswith(M_IMG):
            name, _, cap = line[len(M_IMG):].partition("|")
            show_image(name.strip(), inline(cap.strip()),
                       DOC["slug"], pager, width)
        elif line.startswith(M_COL):
            i = int(line[len(M_COL):])
            col = DOC["cols"][i]
            title = inline(col["title"].upper())
            if i in DOC["expanded"] or depth > 0:
                pager.line()
                pager.line(BOLD + "[-] %d. %s" % (i + 1, title))
                pager.line(DIM + "    (collapse %d to seal)"
                           % (i + 1))
                pager.line()
                render_lines(col["body"], pager, width,
                             depth + 1)
            else:
                pager.line()
                pager.line(BOLD + "[+] %d. %s " % (i + 1, title)
                           + DIM + "(sealed, expand %d to open)"
                           % (i + 1))
                pager.line()
        elif line.startswith(M_TAB):
            i = int(line[len(M_TAB):])
            tv = DOC["tabs"][i]
            base = sum(len(t["titles"])
                       for t in DOC["tabs"][:i])
            bar = []
            for j, title in enumerate(tv["titles"]):
                n = base + j + 1
                label = "[%d] %s" % (n, inline(title.upper()))
                if j == tv["active"]:
                    label = BOLD + "*" + label + RESET
                else:
                    label = DIM + label + RESET
                bar.append(label)
            pager.line()
            for ln in wrap_ansi("TABS:  " + "   ".join(bar),
                                width):
                pager.line(ln)
            pager.line(DIM + "(tab <n> to switch)")
            pager.line()
            render_lines(tv["bodies"][tv["active"]], pager,
                         width, depth + 1)
        elif line.startswith(M_ACS):
            render_acs(DOC["acs"][int(line[len(M_ACS):])],
                       pager, width)
        elif line.startswith(M_CODE):
            code = DOC["codes"][int(line[len(M_CODE):])]
            pager.line()
            for cl in code.split("\n"):
                pager.line(DIM + "    " + cl[:width - 4])
            pager.line()
        elif line.startswith(M_WARN):
            render_box(
                wrap_ansi(line[len(M_WARN):], width - 8),
                pager, width, heavy=True)
        elif line.startswith(M_AUDIO):
            url = line[len(M_AUDIO):]
            pager.line(DIM + "[AUDIO RECORDING ON FILE: %s]"
                       % url.rsplit("/", 1)[-1])
        elif line.startswith(M_MEDIA):
            i = int(line[len(M_MEDIA):])
            kind, _, label = DOC["media"][i]
            pager.line(DIM
                       + "[%s RECORDING %d ON FILE: %s]"
                         "  (play %d)"
                       % (kind.upper(), i + 1, label,
                          i + 1))
        elif line.startswith(M_OMIT):
            pager.line(DIM + "[%s]" % line[len(M_OMIT):])
        elif line.startswith(M_LIC):
            pager.line(DIM + "licensing on file: CC BY-SA 3.0")
        elif re.match(r"^\+{1,6}\s", line):
            text2 = re.sub(r"^\+{1,6}\s*", "", line)
            pager.line()
            pager.line(BOLD + UNDER + inline(text2))
            pager.line()
        elif line.startswith(">"):
            body = inline(re.sub(r"^>+\s?", "", line))
            for ln in wrap_ansi(body, width - 4):
                pager.line(DIM + "  | " + RESET + ln)
        elif re.match(r"^\s*[*#]\s", line):
            ind = len(line) - len(line.lstrip())
            body = inline(line.lstrip()[2:])
            first = True
            for ln in wrap_ansi(body, width - 4 - ind):
                pre = " " * ind + ("  * " if first else "    ")
                first = False
                pager.line(pre + ln)
        elif re.match(r"^[-=~]{3,}$", line):
            pager.line(DIM + "=" * width)
        elif line.strip() == "":
            pager.line()
        else:
            for ln in wrap_ansi(inline(line), width):
                pager.line(ln)
    if table_rows:
        render_table(table_rows, pager, width)


def set_expand(arg, expand):
    """Returns an error message, or None on success."""
    total = len(DOC["cols"])
    if total == 0:
        return "THIS DOCUMENT HAS NO SEALED SECTIONS."
    a = arg.strip().lower()
    if a == "all":
        DOC["expanded"] = set(range(total)) if expand \
            else set()
        return None
    try:
        i = int(a) - 1
    except ValueError:
        return "USE: expand <number> OR expand all"
    if i < 0 or i >= total:
        return "NO SUCH SECTION. SECTIONS: 1..%d" % total
    if expand:
        DOC["expanded"].add(i)
    else:
        DOC["expanded"].discard(i)
    return None


def set_tab(arg):
    if len(DOC["tabs"]) == 0:
        return "THIS DOCUMENT HAS NO TABBED VIEWS."
    try:
        n = int(arg) - 1
    except ValueError:
        return "USE: tab <number>"
    if n >= 0:
        base = 0
        for tv in DOC["tabs"]:
            if n < base + len(tv["titles"]):
                tv["active"] = n - base
                return None
            base += len(tv["titles"])
    total = sum(len(t["titles"]) for t in DOC["tabs"])
    return "NO SUCH TAB. TABS: 1..%d" % total


PENDING = []


def build_lines():
    DOC["links"] = []
    cols = shutil.get_terminal_size().columns
    width = min(cols - 4, 88)
    margin = max(0, (cols - width) // 2)
    pager = Pager(margin, width)
    pager.line(BOLD
               + (" DOCUMENT: %s " % DOC["title"])
               .center(width, "=") + RESET)
    pager.line()
    render_lines(DOC["src"], pager, width)
    if DOC["footnotes"]:
        pager.line()
        pager.line(BOLD + "NOTES" + RESET)
        for i, fn in enumerate(DOC["footnotes"], 1):
            for j, ln in enumerate(
                    wrap_ansi(inline(fn), width - 5)):
                pre = "[%d] " % i if j == 0 else "    "
                pager.line(DIM + pre + ln)
    hints = []
    if DOC["cols"]:
        hints.append("%d sealed section(s): expand <n>"
                     % len(DOC["cols"]))
    if DOC["tabs"]:
        hints.append("tab <n> switches views")
    if DOC["media"]:
        hints.append("%d recording(s): play <n>"
                     % len(DOC["media"]))
    if DOC["links"]:
        hints.append("%d cross-reference(s): follow <n>"
                     % len(DOC["links"]))
    pager.line()
    if hints:
        for ln in wrap_ansi(" // ".join(hints), width):
            pager.line(DIM + ln)
    pager.line(DIM
               + "rating %+d // SCP Foundation Wiki // "
                 "CC BY-SA 3.0" % DOC["rating"])
    m = re.fullmatch(r"scp-0*(\d+)", DOC["slug"])
    nxt = []
    if m:
        nxt.append("next >> SCP-%d" % (int(m.group(1)) + 1))
    if DOC["links"]:
        nxt.append("follow <n>")
    nxt.append("random")
    for ln in wrap_ansi("CONTINUE: " + " // ".join(nxt),
                        width):
        pager.line(DIM + ln)
    pager.line()
    return pager.lines


def render_doc():
    if DOC is None:
        slow("NO DOCUMENT LOADED.")
        return
    lines = build_lines()
    if TTY:
        cmd = viewer(build_lines, lines)
        if cmd:
            PENDING.append(cmd)
    else:
        print()
        sys.stdout.write("\n".join(lines) + "\n")


