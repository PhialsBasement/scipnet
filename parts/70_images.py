IMG_RENDERS = {}

CSI_ANY = re.compile(r"\x1b\[([0-9;?]*)([a-zA-Z])")


def art_lines(text):
    """Chafa output with only SGR color codes kept."""
    out = []
    for ln in text.split("\n"):
        buf = []
        pos = 0
        for m in CSI_ANY.finditer(ln):
            buf.append(ln[pos:m.start()])
            if m.group(2) == "m":
                buf.append(m.group(0))
            elif m.group(2) == "C" and m.group(1).isdigit():
                buf.append(" " * int(m.group(1)))
            pos = m.end()
        buf.append(ln[pos:])
        s = "".join(buf)
        if ANSI_RE.sub("", s) != "":
            out.append(s)
    return out


def image_path(name, slug):
    label = name.rsplit("/", 1)[-1]
    safe = re.sub(r"[^A-Za-z0-9._-]", "_",
                  slug + "_" + label)
    return os.path.join(CACHE, safe)


def fetch_image(name, slug):
    """Returns a local path, or None. Caches failures."""
    path = image_path(name, slug)
    if os.path.exists(path):
        return path
    miss = path + ".missing"
    if os.path.exists(miss) \
            and time.time() - os.path.getmtime(miss) < 86400:
        return None
    url = name if name.startswith("http") \
        else "%s/%s/%s" % (FILES, slug, name)
    candidates = (
        (url, 6),
        ("https://web.archive.org/web/2024id_/" + url, 20),
    )
    os.makedirs(CACHE, exist_ok=True)
    data = None
    for u, tmo in candidates:
        try:
            req = urllib.request.Request(
                u, headers={"User-Agent": "scipnet-tui/1.0"})
            with urllib.request.urlopen(req, timeout=tmo) as r:
                data = r.read()
            break
        except Exception:
            continue
    if data is None:
        with open(miss, "wb"):
            pass
        return None
    with open(path, "wb") as fh:
        fh.write(data)
    return path


def prefetch_images(names, slug):
    todo = [n for n in dict.fromkeys(names)
            if os.path.exists(image_path(n, slug)) is False]
    if len(todo) == 0:
        return
    slow("RETRIEVING %d ATTACHMENT(S) ..." % len(todo),
         style=DIM)
    threads = [threading.Thread(
        target=fetch_image, args=(n, slug), daemon=True)
        for n in todo]
    for t in threads:
        t.start()
    for t in threads:
        t.join(45)


def show_image(name, caption, slug, pager, width):
    label = name.rsplit("/", 1)[-1]
    if shutil.which("chafa") is None:
        pager.line(DIM + "[IMAGE: %s]" % label)
        return
    imgw = min(width, 64)
    pad = " " * max(0, (width - imgw) // 2)
    key = (name, slug, imgw)
    out = IMG_RENDERS.get(key)
    if out is None:
        path = fetch_image(name, slug)
        if path is None:
            pager.line(DIM + "[IMAGE UNAVAILABLE: %s]" % label)
            return
        gray = path + ".gray.png"
        src = path
        if os.path.exists(gray):
            src = gray
        elif shutil.which("magick"):
            r = subprocess.run(
                ["magick", path, "-colorspace", "Gray", gray],
                capture_output=True)
            if r.returncode == 0:
                src = gray
        r = subprocess.run(
            ["chafa", "-f", "symbols", "--size",
             "%dx26" % imgw, src],
            capture_output=True, text=True)
        if r.returncode != 0:
            pager.line(DIM + "[IMAGE UNAVAILABLE: %s]" % label)
            return
        out = art_lines(r.stdout)
        IMG_RENDERS[key] = out
    for ln in out:
        pager.line(pad + ln)
    if caption:
        for cl in wrap_ansi(DIM + caption, imgw):
            pager.line(pad + DIM + cl)
    pager.line()


