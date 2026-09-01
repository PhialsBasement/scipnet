def ambient():
    idx = int(time.time() // 6) % len(AMBIENT)
    return AMBIENT[idx].replace(
        "{t}", time.strftime("%H:%M"))


def slow(text, delay=0.012, style=""):
    if style:
        sys.stdout.write(style)
    if FAST:
        sys.stdout.write(text)
    else:
        for ch in text:
            sys.stdout.write(ch)
            sys.stdout.flush()
            if ch != " ":
                time.sleep(delay)
    if style:
        sys.stdout.write(RESET)
    sys.stdout.write("\n")
    sys.stdout.flush()


def pause(t):
    if not FAST:
        time.sleep(t)


def query(gql, variables=None):
    body = json.dumps(
        {"query": gql, "variables": variables or {}}).encode()
    req = urllib.request.Request(
        API, data=body,
        headers={"Content-Type": "application/json",
                 "User-Agent": "scipnet-tui/1.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())


PAGE_Q = """
query($url: URL!) {
  page(url: $url) {
    url
    wikidotInfo { title rating source }
  }
}"""

SEARCH_Q = """
query($q: String!) {
  searchPages(query: $q,
      filter: {anyBaseUrl: "http://scp-wiki.wikidot.com"}) {
    url
    wikidotInfo { title rating }
  }
}"""


def fetch_page(slug):
    d = query(PAGE_Q, {"url": WIKI + "/" + slug})
    page = (d.get("data") or {}).get("page")
    if page and page.get("wikidotInfo"):
        return page
    return None


def vlen(s):
    return len(ANSI_RE.sub("", s))


def wrap_ansi(s, width):
    words = s.split(" ")
    lines, cur, cl = [], "", 0
    state = []

    def scan(w):
        for m in ANSI_RE.finditer(w):
            code = m.group(0)
            if code in (RESET, "\033[m"):
                del state[:]
            else:
                state.append(code)

    for w in words:
        if w == "":
            continue
        wl = vlen(w)
        if cl > 0 and cl + 1 + wl > width:
            lines.append(cur)
            cur, cl = "".join(state) + w, wl
        elif cl == 0:
            cur, cl = "".join(state) + w, wl
        else:
            cur += " " + w
            cl += 1 + wl
        scan(w)
    if cur:
        lines.append(cur)
    return lines or [""]


def parse_args(attrs):
    out = {}
    for part in attrs.split("|"):
        k, eq, v = part.partition("=")
        if eq:
            out[k.strip().lower()] = v.strip()
    return out


