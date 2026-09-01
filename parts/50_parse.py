def link_sub(m):
    target = (m.group(1) or "").strip()
    text = (m.group(2) or target).strip()
    slug = target.lower().replace(" ", "-")
    slug = re.sub(r"^/+", "", slug)
    internal = slug != "" and slug.find(":") == -1
    mark = ""
    if internal and DOC:
        DOC["links"].append((slug, text))
        mark = DIM + "[L%d]" % len(DOC["links"]) + RESET
    return UNDER + text + RESET + mark


REDLINK_RE = re.compile(
    r"\[(?P<pre>DATA\s+|Data\s+)?"
    r"(?:\x1b\[[0-9;]*m)+"
    r"(?P<w>EXPUNGED|REDACTED|CLASSIFIED)"
    r"(?:\x1b\[[0-9;]*m)*"
    r"(?P<mark>(?:\x1b\[[0-9;]*m|\[L\d+\])*)"
    r"\]")


def redlink_sub(m):
    pre = (m.group("pre") or "").strip()
    bar = "[" + (pre + " " if pre else "") \
        + m.group("w") + "]"
    return (REV + bar + RESET + (m.group("mark") or ""))


def inline(t):
    t = re.sub(r"\[\[\[([^|\[\]]*)\|([^\[\]]*)\]\]\]",
               link_sub, t)
    t = re.sub(r"\[\[\[([^\[\]]*)()\]\]\]", link_sub, t)
    t = re.sub(r"\[\*?(/[a-zA-Z0-9_:+-]+)\s+([^\]]+)\]",
               link_sub, t)
    t = re.sub(r"\[\*?https?://\S+\s+([^\]]*)\]",
               UNDER + r"\1" + RESET, t)
    t = re.sub(r"\[#\S*\s+([^\]]+)\]", r"\1", t)
    t = re.sub(r"@<(.*?)>@",
               lambda m: html.unescape(m.group(1)), t)
    t = re.sub(r"\(\(bibcite\s+([^)]+)\)\)",
               DIM + r"[ref \1]" + RESET, t, flags=re.I)
    t = re.sub(r"\[\[\*?user\s+([^\]]+)\]\]", r"\1", t,
               flags=re.I)
    t = re.sub(r"\[\[file\s+([^\]|]+)[^\]]*\]\]",
               DIM + r"[ATTACHMENT: \1]" + RESET, t,
               flags=re.I)
    t = re.sub(r"(\[L\d+\]" + re.escape(RESET)
               + r")(?=[^\s.,;:!?)\]'\"])", r"\1 ", t)
    t = highlight(t)
    t = re.sub(r"\*\*(.+?)\*\*", BOLD + r"\1" + RESET, t)
    t = re.sub(r"(?<![:/])//(.+?)//", ITAL + r"\1" + RESET, t)
    t = re.sub(r"__(.+?)__", UNDER + r"\1" + RESET, t)
    t = re.sub(r"(?<!-)--(?!-)(.+?)(?<!-)--(?!-)",
               STRIKE + r"\1" + RESET, t)
    t = re.sub(r"\{\{(.+?)\}\}", DIM + r"\1" + RESET, t)
    t = re.sub(r"##[^|#]*\|(.*?)##", r"\1", t)
    t = re.sub(r"\^\^(.+?)\^\^", r"\1", t)
    t = re.sub(r",,(.+?),,", r"\1", t)
    t = re.sub(r"@@(.*?)@@", r"\1", t)
    t = re.sub(r"\[\[\$(.+?)\$\]\]", DIM + r"\1" + RESET, t)
    t = re.sub(r"\[\[[^\]]*\]\]", "", t)
    t = REDLINK_RE.sub(redlink_sub, t)
    return t


def img_sub(m):
    args = parse_args(m.group(1).replace("\n", " "))
    return "\n%s%s|%s\n" % (M_IMG, args.get("name", ""),
                           args.get("caption", ""))


def html_to_text(inner):
    inner = re.sub(
        r"(?is)<(script|style|noscript|head|button|form|"
        r"select|textarea)[^>]*>.*?</\1>",
        " ", inner)
    inner = re.sub(r"(?is)<!--.*?-->", " ", inner)
    inner = re.sub(
        r"(?is)<(\w+)[^>]*onclick[^>]*>[^<]*</\1>",
        " ", inner)
    inner = re.sub(
        r"(?i)<br\s*/?>|</(?:p|div|tr|li|h[1-6]|"
        r"blockquote|section|article)\s*>",
        "\n", inner)
    inner = re.sub(r"<[^>]+>", " ", inner)
    inner = html.unescape(inner)
    out = []
    for ln in inner.split("\n"):
        ln = " ".join(ln.split())
        if ln:
            out.append(ln)
    return out


ENCODED_RE = re.compile(r"%[0-9A-Za-z]{2}")


def html_block_sub(m):
    lines = html_to_text(m.group(1))
    out = []
    dropped = 0
    for ln in lines:
        if len(ENCODED_RE.findall(ln)) >= 2:
            dropped += 1
            if dropped == 1:
                out.append(M_OMIT + "ENCODED PAYLOAD "
                           "SEALED BY INTERACTIVE LOCK, "
                           "UNSUPPORTED ON THIS TERMINAL")
            continue
        out.append(ln)
    if len(out) == 0:
        return ("\n" + M_OMIT + "EMBEDDED INTERACTIVE "
                "CONTENT OMITTED\n")
    return "\n" + "\n\n".join(out) + "\n"


QUOTE_DIV = re.compile(
    r'\[\[div[^\]]*class="[^"]*(?:blockquote|notation|'
    r'raisa[-_]memo|document)[^"]*"[^\]]*\]\]', re.I)
ANY_DIV = re.compile(r"\[\[div[^\]]*\]\]", re.I)
END_DIV = re.compile(r"\[\[/div\]\]", re.I)


def convert_quote_divs(src):
    """Turns quote-styled div blocks into > quote lines."""
    while True:
        m = QUOTE_DIV.search(src)
        if m is None:
            return src
        depth = 1
        pos = m.end()
        inner_end = None
        while depth > 0:
            om = ANY_DIV.search(src, pos)
            cm = END_DIV.search(src, pos)
            if cm is None:
                return src
            if om and om.start() < cm.start():
                depth += 1
                pos = om.end()
            else:
                depth -= 1
                inner_end = cm.start()
                pos = cm.end()
        inner = src[m.end():inner_end].strip("\n")
        quoted = "\n".join(
            "> " + l if l.strip() else ">"
            for l in inner.split("\n"))
        src = src[:m.start()] + "\n" + quoted + "\n" \
            + src[pos:]


def load_doc(page):
    global DOC
    info = page["wikidotInfo"]
    src = (info["source"] or "").replace("\r", "")
    DOC = {
        "title": info["title"],
        "rating": info["rating"],
        "slug": page.get("url", "").rsplit("/", 1)[-1],
        "footnotes": [], "codes": [], "cols": [],
        "tabs": [], "acs": [], "links": [],
        "media": [], "expanded": set(),
    }

    def add_media(url, kind):
        url = url.strip()
        if url.startswith("//"):
            url = "https:" + url
        label = url.rstrip("/").rsplit("/", 1)[-1][:48]
        DOC["media"].append((kind, url, label))
        return M_MEDIA + str(len(DOC["media"]) - 1)

    def fn_sub(m):
        DOC["footnotes"].append(m.group(1).strip())
        return (BOLD + "[%d]" % len(DOC["footnotes"])
                + RESET)

    def code_sub(m):
        DOC["codes"].append(m.group(1).strip("\n"))
        return "\n%s%d\n" % (M_CODE, len(DOC["codes"]) - 1)

    def col_sub(m):
        title = "SEALED ATTACHMENT"
        tm = re.search(r'show\s*=\s*"([^"]*)"', m.group(1))
        if tm:
            title = tm.group(1).strip("+- ")
        DOC["cols"].append({"title": title,
                            "body": m.group(2)})
        return "\n%s%d\n" % (M_COL, len(DOC["cols"]) - 1)

    def tab_sub(m):
        inner = m.group(1)
        parts = re.split(r"\[\[tab\s+(.*?)\]\]", inner)
        titles, bodies = [], []
        for i in range(1, len(parts), 2):
            titles.append(parts[i].strip())
            bodies.append(
                re.sub(r"\[\[/tab\]\]", "", parts[i + 1],
                       flags=re.I))
        if len(titles) == 0:
            return ""
        DOC["tabs"].append({"titles": titles,
                            "bodies": bodies, "active": 0})
        return "\n%s%d\n" % (M_TAB, len(DOC["tabs"]) - 1)

    def acs_sub(m):
        args = parse_args(m.group(1).replace("\n", " "))
        keep = {}
        for k in ("item-number", "clearance",
                  "container-class", "containment-class",
                  "secondary-class", "disruption-class",
                  "risk-class"):
            v = args.get(k, "")
            if v and v.lower() != "none" and v != "--":
                keep[k] = v
        if len(keep) == 0:
            return ""
        DOC["acs"].append(keep)
        return "\n%s%d\n" % (M_ACS, len(DOC["acs"]) - 1)

    def table_sub(m):
        inner = m.group(1)
        rows = []
        for rm in re.finditer(
                r"\[\[row[^\]]*\]\](.*?)\[\[/row\]\]",
                inner, flags=re.S | re.I):
            cells = []
            for cm in re.finditer(
                    r"\[\[(h?cell)[^\]]*\]\](.*?)\[\[/\1\]\]",
                    rm.group(1), flags=re.S | re.I):
                text = " ".join(cm.group(2).split())
                if cm.group(1).lower() == "hcell":
                    text = "~ " + text
                cells.append(text)
            if cells:
                rows.append("||" + "||".join(cells) + "||")
        return "\n" + "\n".join(rows) + "\n"

    src = re.sub(r"\[!--.*?--\]", "", src, flags=re.S)
    src = re.sub(r"\[\[code[^\]]*\]\](.*?)\[\[/code\]\]",
                 code_sub, src, flags=re.S | re.I)
    src = re.sub(r"\[\[footnote\]\](.*?)\[\[/footnote\]\]",
                 fn_sub, src, flags=re.S | re.I)
    src = convert_quote_divs(src)
    src = re.sub(r"\[\[include\s+\S*anomaly-class-bar\S*"
                 r"([^\]]*)\]\]",
                 acs_sub, src, flags=re.S | re.I)
    src = re.sub(r"\[\[include\s+\S*customizable-acs"
                 r"([^\]]*)\]\]",
                 acs_sub, src, flags=re.S | re.I)
    src = re.sub(r"\[\[include\s+\S*image\S*([^\]]*)\]\]",
                 img_sub, src, flags=re.S | re.I)
    src = re.sub(r"\[\[f?[<>=]?image\s+(\S+?)[\s\]][^\]]*\]?\]",
                 "\n" + M_IMG + r"\1|\n", src, flags=re.I)
    src = re.sub(r"\[\[include\s+\S*license-box\]\].*?"
                 r"\[\[include\s+\S*license-box-end[^\]]*\]\]",
                 "\n" + M_LIC + "\n", src, flags=re.S | re.I)
    src = re.sub(r"\[\[include\s+\S*info:start[^\]]*\]\].*?"
                 r"\[\[include\s+\S*info:end[^\]]*\]\]",
                 "", src, flags=re.S | re.I)
    src = re.sub(r"\[\[include\s+\S*adult-content-warning"
                 r"[^\]]*\]\]",
                 "\n" + M_WARN + "THIS FILE CONTAINS ADULT "
                 "CONTENT. VIEWER DISCRETION REQUIRED.\n",
                 src, flags=re.S | re.I)
    def warnbox_sub(m):
        args = parse_args(m.group(1))
        parts = []
        for k in ("text-top", "text-bottom"):
            v = clean_markup(args.get(k, ""))
            v = " ".join(v.split())
            if v:
                parts.append(v)
        text = " // ".join(parts) or (
            "MEMETIC HAZARDS MAY BE PRESENT. VERIFY "
            "INOCULATION BEFORE PROCEEDING.")
        return "\n" + M_WARN + text + "\n"

    src = re.sub(r"\[\[include\s+\S*object-warning-box"
                 r"\S*([^\]]*)\]\]",
                 warnbox_sub, src, flags=re.S | re.I)
    src = re.sub(r"\[\[html5player[^\]]*?src\s*=\s*"
                 r"\"?([^\s\"\]]+)[^\]]*\]\]",
                 lambda m: "\n" + add_media(
                     m.group(1), "audio") + "\n",
                 src, flags=re.I)
    src = re.sub(r"\[\[include\s+\S*(?:html5player|"
                 r"audio-player)\S*[^\]]*?url\s*=\s*"
                 r"([^\s|\]]+)[^\]]*\]\]",
                 lambda m: "\n" + add_media(
                     m.group(1), "audio") + "\n",
                 src, flags=re.S | re.I)
    def html_sub(m):
        inner = m.group(1)
        markers = []
        for mm in re.finditer(
                r"<(iframe|audio|video|source|embed)"
                r"[^>]*?src=[\"']([^\"']+)", inner, re.I):
            kind = "audio" \
                if mm.group(1).lower() == "audio" \
                else "video"
            markers.append(add_media(mm.group(2), kind))
        return (html_block_sub(m)
                + "\n".join(markers)
                + ("\n" if markers else ""))

    src = re.sub(r"\[\[html[^\]]*\]\](.*?)\[\[/html\]\]",
                 html_sub, src, flags=re.S | re.I)
    src = re.sub(r"\[\[iframe\s+(\S+)[^\]]*\]\]",
                 lambda m: "\n" + add_media(
                     m.group(1), "video") + "\n",
                 src, flags=re.I)
    def note_sub(m):
        body = m.group(1).strip("\n")
        return "\n" + "\n".join(
            "> " + l if l.strip() else ">"
            for l in body.split("\n")) + "\n"

    src = re.sub(r"\[\[note\]\](.*?)\[\[/note\]\]",
                 note_sub, src, flags=re.S | re.I)
    def embed_sub(m):
        kind = "audio" if (m.group(1) or "").lower() \
            == "audio" else "video"
        um = re.search(r"https?://[^\s\"'<>\]]+"
                       r"|//[^\s\"'<>\]]+", m.group(2))
        if um is None:
            return ("\n" + M_OMIT
                    + "EMBEDDED MEDIA UNRESOLVED\n")
        return "\n" + add_media(um.group(0), kind) + "\n"

    src = re.sub(r"\[\[embed(video|audio)?[^\]]*\]\]"
                 r"(.*?)\[\[/embed(?:video|audio)?\]\]",
                 embed_sub, src, flags=re.S | re.I)

    def gal_sub(m):
        out = []
        for lm in re.finditer(
                r"^\s*:\s*(\S+)(?:[ \t]+(.*))?$",
                m.group(1), re.M):
            out.append(M_IMG + lm.group(1) + "|"
                       + (lm.group(2) or ""))
        if len(out) == 0:
            return ("\n" + M_OMIT
                    + "IMAGE GALLERY UNRESOLVED\n")
        return "\n" + "\n".join(out) + "\n"

    src = re.sub(r"\[\[gallery[^\]]*\]\](.*?)"
                 r"\[\[/gallery\]\]",
                 gal_sub, src, flags=re.S | re.I)
    src = re.sub(r"\[\[collapsible([^\]]*)\]\](.*?)"
                 r"\[\[/collapsible\]\]",
                 col_sub, src, flags=re.S | re.I)
    src = re.sub(r"\[\[tabview[^\]]*\]\](.*?)\[\[/tabview\]\]",
                 tab_sub, src, flags=re.S | re.I)
    src = re.sub(r"\[\[table[^\]]*\]\](.*?)\[\[/table\]\]",
                 table_sub, src, flags=re.S | re.I)
    src = re.sub(r"\[\[math[^\]]*\]\](.*?)\[\[/math\]\]",
                 DIM + r"\1" + RESET, src, flags=re.S | re.I)
    src = re.sub(r"\[\[bibliography\]\](.*?)"
                 r"\[\[/bibliography\]\]",
                 "\n== REFERENCES ==\n" + r"\1", src,
                 flags=re.S | re.I)
    src = re.sub(r"\[\[include[^\]]*\]\]", "", src,
                 flags=re.S | re.I)
    src = re.sub(r"\[\[module[^\]]*\]\].*?\[\[/module\]\]", "",
                 src, flags=re.S | re.I)
    src = re.sub(r"\[\[module[^\]]*\]\]", "", src, flags=re.I)
    src = re.sub(r"\[\[/?(div|span|size|tabview|tab|footnote"
                 r"block|ul|li|a|iframe|css|date|=|<|>|==)"
                 r"[^\]]*\]\]",
                 "", src, flags=re.I)
    DOC["src"] = src
    names = [ln[len(M_IMG):].partition("|")[0].strip()
             for ln in src.split("\n")
             if ln.startswith(M_IMG)]
    prefetch_images([n for n in names if n], DOC["slug"])


