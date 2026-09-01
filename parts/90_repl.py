AMBIENCE_PROC = None
PRELOGIN_PROC = None
PRELOGIN_SOCK = os.path.join(CACHE, "prelogin.sock")
PRELOGIN_VOL = 22


def audio_ok():
    silent = os.environ.get("SCIPNET_SILENT") == "1"
    return (TTY and silent is False
            and shutil.which("mpv") is not None
            and os.path.exists(AMBIENCE))


def start_prelogin():
    """Quiet mid-track segment under the boot screen."""
    global PRELOGIN_PROC
    if audio_ok() is False:
        return
    os.makedirs(CACHE, exist_ok=True)
    try:
        os.remove(PRELOGIN_SOCK)
    except OSError:
        pass
    PRELOGIN_PROC = subprocess.Popen(
        ["mpv", "--no-video", "--really-quiet",
         "--start=1800", "--end=2400",
         "--volume=%d" % PRELOGIN_VOL,
         "--input-ipc-server=" + PRELOGIN_SOCK, AMBIENCE],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL)


def fade_prelogin(dur=3.0, steps=12):
    """Ramps the boot layer to zero, then stops it."""
    global PRELOGIN_PROC
    p = PRELOGIN_PROC
    PRELOGIN_PROC = None
    if p is None or p.poll() is not None:
        return
    try:
        s = socket.socket(socket.AF_UNIX)
        s.settimeout(1.0)
        s.connect(PRELOGIN_SOCK)
        for i in range(steps):
            vol = PRELOGIN_VOL * (steps - 1 - i) \
                / (steps - 1)
            s.sendall((json.dumps(
                {"command":
                 ["set_property", "volume", vol]})
                + "\n").encode())
            time.sleep(dur / steps)
        s.close()
    except Exception:
        pass
    if p.poll() is None:
        p.terminate()
        try:
            p.wait(2)
        except subprocess.TimeoutExpired:
            p.kill()


def kill_prelogin():
    global PRELOGIN_PROC
    p = PRELOGIN_PROC
    PRELOGIN_PROC = None
    if p and p.poll() is None:
        p.terminate()
        try:
            p.wait(2)
        except subprocess.TimeoutExpired:
            p.kill()


def start_ambience():
    global AMBIENCE_PROC
    if AMBIENCE_PROC and AMBIENCE_PROC.poll() is None:
        return
    silent = os.environ.get("SCIPNET_SILENT") == "1"
    if TTY is False or silent \
            or shutil.which("mpv") is None \
            or os.path.exists(AMBIENCE) is False:
        return
    AMBIENCE_PROC = subprocess.Popen(
        ["mpv", "--no-video", "--loop-file=inf",
         "--really-quiet", "--volume=40", AMBIENCE],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL)


def stop_ambience():
    global AMBIENCE_PROC
    p = AMBIENCE_PROC
    AMBIENCE_PROC = None
    if p and p.poll() is None:
        p.terminate()
        try:
            p.wait(2)
        except subprocess.TimeoutExpired:
            p.kill()


PLAY_PROC = None


def stop_play():
    global PLAY_PROC
    p = PLAY_PROC
    PLAY_PROC = None
    if p and p.poll() is None:
        p.terminate()
        try:
            p.wait(2)
        except subprocess.TimeoutExpired:
            p.kill()


def do_play(arg):
    global PLAY_PROC
    if need_doc() is False:
        return
    media = DOC["media"]
    if len(media) == 0:
        slow("THIS DOCUMENT HAS NO RECORDINGS ON FILE.")
        return
    try:
        n = int(arg) - 1
    except ValueError:
        slow("USE: play <number>")
        return
    if n < 0 or n >= len(media):
        slow("NO SUCH RECORDING. RECORDINGS: 1..%d"
             % len(media))
        return
    if shutil.which("mpv") is None:
        slow("PLAYBACK HARDWARE UNAVAILABLE.")
        return
    kind, url, label = media[n]
    stream = any(d in url for d in
                 ("youtube.com", "youtu.be", "vimeo.com"))
    if stream:
        target = url
    else:
        slow("RECOVERING RECORDING FROM ARCHIVE ...",
             style=DIM)
        target = fetch_image(url, DOC["slug"])
        if target is None:
            slow("RECORDING UNRECOVERABLE. MEDIA NODE "
                 "DARK.", style=BOLD)
            return
    stop_play()
    args = ["mpv", "--really-quiet", "--volume=70"]
    if kind == "audio":
        args.append("--no-video")
    PLAY_PROC = subprocess.Popen(
        args + [target],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL)
    slow("PLAYBACK OF %s STARTED. USE stop TO END."
         % label.upper(), style=DIM)


def do_access(arg):
    slug = arg.strip().lower().replace(" ", "-")
    if re.fullmatch(r"\d{1,4}", slug):
        slug = "scp-" + slug.zfill(3)
    slow("QUERYING ARCHIVE NODE FOR %s ..." % slug.upper(),
         style=DIM)
    if FAST is False:
        slow(random.choice(RETRIEVAL), style=DIM)
        pause(0.15)
    try:
        page = fetch_page(slug)
    except Exception:
        slow("ARCHIVE NODE UNREACHABLE. TRY AGAIN LATER.",
             style=BOLD)
        return
    if page is None:
        slow("NO RECORD FOUND. ACCESS ATTEMPT LOGGED.",
             style=BOLD)
        return
    raw_src = page["wikidotInfo"]["source"] or ""
    if TTY and COGNITO_RE.search(raw_src[:4000]):
        if cognitohazard_gate(raw_src, slug) is False:
            slow("EXPOSURE PREVENTED. RETRIEVAL ABORTED.",
                 style=BOLD)
            slow("THIS ABORT HAS BEEN NOTED ON YOUR FILE.",
                 style=DIM)
            if PROFILE:
                PROFILE["flags"] += 1
                save_profile()
            return
    SESSION.append(slug)
    load_doc(page)
    promo = None
    if PROFILE:
        lv = doc_clearance()
        if lv > PROFILE["clearance"]:
            slow("RECORD FLAGGED LEVEL %d. YOUR CLEARANCE: "
                 "LEVEL %d." % (lv, PROFILE["clearance"]),
                 style=BOLD)
            slow("OVERRIDE ACCEPTED. THIS ACCESS HAS BEEN "
                 "LOGGED AGAINST YOUR FILE.", style=DIM)
            PROFILE["flags"] += 1
            pause(0.5)
        PROFILE["reads"] += 1
        newlv = PROMOTIONS.get(PROFILE["reads"])
        if newlv and newlv > PROFILE["clearance"]:
            PROFILE["clearance"] = newlv
            promo = newlv
        save_profile()
    render_doc()
    if promo:
        slow("CLEARANCE REVIEW COMPLETE. LEVEL %d GRANTED. "
             "SOME RECORDS WILL NO LONGER FLAG YOUR FILE."
             % promo, style=BOLD)
    else:
        doc_epilogue()


def do_search(term):
    slow("SEARCHING ARCHIVE ...", style=DIM)
    try:
        d = query(SEARCH_Q, {"q": term})
    except Exception:
        slow("ARCHIVE NODE UNREACHABLE. TRY AGAIN LATER.",
             style=BOLD)
        return
    hits = (d.get("data") or {}).get("searchPages") or []
    if len(hits) == 0:
        slow("NO MATCHING RECORDS.")
        return
    for h in hits[:15]:
        slug = h["url"].rsplit("/", 1)[-1]
        info = h["wikidotInfo"] or {}
        print("  %-18s %s" % (slug, info.get("title", "")))
    print()
    slow("USE: access <designation>", style=DIM)


def do_random():
    for _ in range(6):
        n = random.randint(2, 7999)
        slug = "scp-" + str(n).zfill(3)
        try:
            page = fetch_page(slug)
        except Exception:
            slow("ARCHIVE NODE UNREACHABLE. TRY AGAIN LATER.",
                 style=BOLD)
            return
        if page:
            load_doc(page)
            render_doc()
            return
    slow("RETRIEVAL FAILED. TRY AGAIN.")


def need_doc():
    if DOC is None:
        slow("NO DOCUMENT LOADED. USE: access <n>")
        return False
    return True


def do_expand(arg, expand):
    if need_doc() is False:
        return
    msg = set_expand(arg, expand)
    if msg:
        slow(msg)
    else:
        render_doc()


def do_tab(arg):
    if need_doc() is False:
        return
    msg = set_tab(arg)
    if msg:
        slow(msg)
    else:
        render_doc()


def do_follow(arg):
    if need_doc() is False:
        return
    try:
        n = int(arg) - 1
    except ValueError:
        slow("USE: follow <number> (see [Ln] markers)")
        return
    if n < 0 or n >= len(DOC["links"]):
        slow("NO SUCH CROSS-REFERENCE.")
        return
    do_access(DOC["links"][n][0])


def do_step(delta):
    if need_doc() is False:
        return
    m = re.fullmatch(r"scp-0*(\d+)", DOC["slug"])
    if m is None:
        slow("SERIAL NAVIGATION UNAVAILABLE FOR THIS "
             "RECORD.")
        return
    n = int(m.group(1)) + delta
    if n < 2:
        slow("YOU HAVE REACHED THE EDGE OF THE ARCHIVE.")
        return
    do_access(str(n))


def do_history():
    if len(SESSION) == 0:
        slow("NO FILES ACCESSED THIS SESSION.")
        return
    for i, s in enumerate(SESSION, 1):
        print("  %2d. %s" % (i, s.upper()))
    print()


def do_links():
    if need_doc() is False:
        return
    if len(DOC["links"]) == 0:
        slow("NO CROSS-REFERENCES IN THIS DOCUMENT.")
        return
    for i, (slug, text) in enumerate(DOC["links"], 1):
        print("  [L%d] %-24s %s" % (i, slug, text))
    print()


def do_note(arg):
    if need_doc() is False:
        return
    fns = DOC["footnotes"]
    if len(fns) == 0:
        slow("NO NOTES IN THIS DOCUMENT.")
        return
    if arg.strip():
        try:
            i = int(arg) - 1
        except ValueError:
            slow("USE: note <number>")
            return
        if i < 0 or i >= len(fns):
            slow("NO SUCH NOTE.")
            return
        for ln in wrap_ansi(inline(fns[i]), 76):
            print("  " + ln + RESET)
        print()
        return
    for i, fn in enumerate(fns, 1):
        first = ANSI_RE.sub("", inline(fn))
        print("  [%d] %s" % (i, first[:70]))
    print()


def boot():
    cols = shutil.get_terminal_size().columns

    def center(s):
        return " " * max(0, (cols - len(s)) // 2) + s

    logo_lines = LOGO.split("\n")
    logo_w = max(len(l) for l in logo_lines)
    lm = " " * max(0, (cols - logo_w) // 2)
    print(BOLD)
    for ln in logo_lines:
        print(lm + ln)
    print(RESET, end="")
    slow(center("SCiPNET DIRECT ACCESS TERMINAL"),
         style=BOLD)
    slow(center("FOUNDATION INTRANET // SITE-19 NODE 04"),
         style=DIM)
    print()
    pause(0.4)
    for line in ("ESTABLISHING SECURE UPLINK ........ OK",
                 "VERIFYING NODE INTEGRITY .......... OK",
                 "LOADING ARCHIVE INDICES ........... OK"):
        slow(center(line), style=DIM)
        pause(0.2)
    print()
    try:
        user = input(
            center("IDENTIFY YOURSELF, OPERATOR: ")).strip()
    except EOFError:
        user = ""
    user = user or "agent"
    global PROFILE
    PROFILE = load_profile(user)
    pause(0.3)
    if PROFILE["_new"]:
        slow(center("NO OPERATOR FILE FOUND. PROVISIONAL "
                    "FILE CREATED."), style=DIM)
        slow(center("CLEARANCE LEVEL %d GRANTED. "
                    "WELCOME, %s."
                    % (PROFILE["clearance"], user.upper())))
    else:
        gap = time.time() - (PROFILE.get("last") or 0)
        days = int(gap // 86400)
        since = ("%d DAY(S)" % days if days > 0
                 else "%d HOUR(S)" % max(1, int(gap // 3600)))
        slow(center("WELCOME BACK, OPERATOR %s. %s SINCE "
                    "LAST UPLINK."
                    % (user.upper(), since)))
        slow(center("CLEARANCE LEVEL %d. FILES ON "
                    "RECORD: %d."
                    % (PROFILE["clearance"],
                       PROFILE["reads"])), style=DIM)
        if PROFILE.get("flags"):
            slow(center("%d UNRESOLVED ACCESS FLAG(S) ON "
                        "YOUR FILE." % PROFILE["flags"]),
                 style=DIM)
    save_profile()
    slow(center("UNAUTHORIZED ACCESS WILL BE MET WITH "
                "AMNESTICIZATION."), style=DIM)
    print()
    slow(center("COMMANDS: access <n> / search <term> / "
                "random / help / clear / logout"), style=DIM)
    print()
    return user


HELP = """
  access <n or slug>   retrieve a document (e.g. access 173)
  search <term>        search the archive
  random               retrieve a random document
  reread               reopen the current document
  next / prev          walk the SCP series in order
  history              list files accessed this session
  expand <n> | all     open a sealed (collapsible) section
  collapse <n> | all   reseal a section
  tab <n>              switch a tabbed view
  links                list cross-references in the document
  follow <n>           retrieve cross-reference [Ln]
  note [n]             list notes, or read one
  play <n> / stop      play a recording on file
  mute / unmute        toggle the site audio feed
  clear                clear the screen
  logout               end session

  Inside a document: arrows, space and PgUp/PgDn scroll,
  q closes, and typing any command + enter runs it there.
"""


def dispatch(raw):
    """Returns False when the session should end."""
    cmd, _, arg = raw.partition(" ")
    cmd = cmd.lower()
    if cmd in ("logout", "exit", "quit"):
        if SESSION:
            slow("%d FILE(S) ACCESSED THIS SESSION. RAISA "
                 "THANKS YOU." % len(SESSION), style=DIM)
        slow("SESSION TERMINATED. STAY VIGILANT.", style=DIM)
        return False
    if cmd == "help":
        print(HELP)
    elif cmd == "clear":
        os.system("clear")
    elif cmd == "random":
        do_random()
    elif cmd in ("reread", "doc"):
        if need_doc():
            render_doc()
    elif cmd == "expand":
        do_expand(arg, True)
    elif cmd == "collapse":
        do_expand(arg, False)
    elif cmd == "tab":
        do_tab(arg)
    elif cmd == "links":
        do_links()
    elif cmd == "next":
        do_step(1)
    elif cmd == "prev":
        do_step(-1)
    elif cmd == "history":
        do_history()
    elif cmd == "play":
        do_play(arg)
    elif cmd == "stop":
        stop_play()
        slow("PLAYBACK ENDED.", style=DIM)
    elif cmd == "mute":
        stop_ambience()
        slow("SITE AUDIO FEED MUTED.", style=DIM)
    elif cmd == "unmute":
        start_ambience()
        slow("SITE AUDIO FEED RESTORED.", style=DIM)
    elif cmd == "follow":
        do_follow(arg)
    elif cmd in ("note", "notes"):
        do_note(arg)
    elif cmd in ("access", "retrieve", "open", "scp"):
        if arg:
            do_access(arg)
        else:
            slow("SPECIFY A DESIGNATION.")
    elif cmd == "search":
        if arg:
            do_search(arg)
        else:
            slow("SPECIFY A SEARCH TERM.")
    elif re.fullmatch(r"(scp-)?\d{1,4}", cmd):
        do_access(cmd)
    else:
        slow("UNRECOGNIZED DIRECTIVE. TYPE help.")
    return True


def main():
    start_prelogin()
    try:
        user = boot()
        start_ambience()
        threading.Thread(target=fade_prelogin,
                         daemon=True).start()
        prompt = ("\001" + BOLD + "\002"
                  + "SCiPNET::%s@SITE-19 > " % user
                  + "\001" + RESET + "\002")
        while True:
            try:
                raw = input(prompt).strip()
            except (EOFError, KeyboardInterrupt):
                print()
                raw = "logout"
            if raw == "":
                continue
            if TTY and random.random() < 0.1:
                who = (PROFILE or {}).get("name", "operator")
                print(DIM + random.choice(BROADCASTS)
                      .replace("{name}", who.upper()) + RESET)
            if dispatch(raw) is False:
                return
            while PENDING:
                if dispatch(PENDING.pop(0)) is False:
                    return
    finally:
        stop_play()
        stop_ambience()
        kill_prelogin()


if __name__ == "__main__":
    main()
