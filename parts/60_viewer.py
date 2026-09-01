class Pager:
    """Collects rendered lines for the viewer."""

    def __init__(self, margin, width=0):
        self.margin = margin
        self.width = width
        self.gutter = margin >= 8 and width > 0
        self.lines = []

    def line(self, s=""):
        if self.gutter is False:
            self.lines.append(" " * self.margin + s + RESET)
            return
        n = len(self.lines) + 1
        num = "%04d" % n if n % 5 == 0 else "    "
        tick = "+" if n % 10 == 0 else "|"
        body = (s + RESET
                + " " * max(0, self.width - vlen(s)))
        self.lines.append(
            " " * (self.margin - 7) + DIM + num + " |"
            + RESET + " " + body + RESET + " " + DIM + tick
            + RESET)


KEYBUF = b""

CSI_KEYS = {"A": "UP", "B": "DOWN", "H": "HOME",
            "F": "END", "5~": "PGUP", "6~": "PGDN"}


def read_key(fd):
    """Buffered key reader: one key or sequence per call."""
    global KEYBUF
    while True:
        if KEYBUF:
            if KEYBUF[0:1] != b"\x1b":
                ch = KEYBUF[0:1]
                KEYBUF = KEYBUF[1:]
                return ch.decode(errors="ignore")
            if len(KEYBUF) >= 2 and KEYBUF[1:2] == b"[":
                for i in range(2, min(len(KEYBUF), 24)):
                    if 0x40 <= KEYBUF[i] <= 0x7e:
                        code = KEYBUF[2:i + 1].decode(
                            errors="ignore")
                        KEYBUF = KEYBUF[i + 1:]
                        return CSI_KEYS.get(code, "OTHER")
                if len(KEYBUF) >= 24:
                    KEYBUF = b""
                    return "OTHER"
            elif len(KEYBUF) >= 2:
                KEYBUF = KEYBUF[1:]
                return "ESC"
            r, _, _ = select.select([fd], [], [], 0.05)
            if len(r) == 0:
                KEYBUF = KEYBUF[1:]
                return "ESC"
        else:
            select.select([fd], [], [])
        data = os.read(fd, 4096)
        if data == b"":
            return "EOF"
        KEYBUF += data


def viewer(rebuild, lines):
    """Interactive document view with an inline command
    prompt. Returns a command for the REPL, or None."""
    import termios
    import tty
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    off = 0
    msg = ""
    entry = None
    sys.stdout.write("\033[?1049h\033[?25l")
    sys.stdout.flush()
    try:
        tty.setcbreak(fd)
        while True:
            size = shutil.get_terminal_size()
            page = size.lines - 1
            maxoff = max(0, len(lines) - page)
            off = max(0, min(off, maxoff))
            out = ["\033[H"]
            for i in range(page):
                idx = off + i
                text = lines[idx] if idx < len(lines) else ""
                out.append(text + "\033[K\n")
            pct = 100 if maxoff == 0 \
                else int(off * 100 / maxoff)
            if entry is None:
                bar = msg if msg else (
                    "SCiPNET ARCHIVE  %3d%%  //  %s  //  "
                    "q closes, type a command + enter"
                    % (pct, ambient()))
                out.append(DIM + " " + bar + RESET + "\033[K")
            else:
                out.append(BOLD + " > " + entry + RESET
                           + "\033[K")
            logo_rows = [l.rstrip() for l in LOGO.split("\n")
                         if l.strip()]
            lw = max(len(l) for l in logo_rows)
            width2 = min(size.columns - 4, 88)
            margin2 = max(0, (size.columns - width2) // 2)
            larea = margin2 - 9
            if larea >= lw + 2:
                top = 1 + max(0, (page - len(logo_rows)) // 2)
                lcol = 1 + max(0, (larea - lw) // 2)
                rstart = margin2 + width2 + 4
                rarea = size.columns - rstart
                rcol = rstart + max(0, (rarea - lw) // 2)
                for k2, ll in enumerate(logo_rows):
                    out.append("\033[%d;%dH%s%s%s"
                               % (top + k2, lcol, DIM, ll,
                                  RESET))
                    out.append("\033[%d;%dH%s%s%s"
                               % (top + k2, rcol, DIM, ll,
                                  RESET))
            if entry is None:
                out.append("\033[%d;1H\033[?25l"
                           % size.lines)
            else:
                out.append("\033[%d;%dH\033[?25h"
                           % (size.lines, 4 + len(entry)))
            sys.stdout.write("".join(out))
            sys.stdout.flush()
            k = read_key(fd)
            if k == "EOF":
                return None
            if entry is not None:
                if k in ("\r", "\n"):
                    cmdline = entry.strip()
                    entry = None
                    msg = ""
                    if cmdline == "":
                        continue
                    c, _, a = cmdline.partition(" ")
                    c = c.lower()
                    if c in ("q", "quit", "close"):
                        return None
                    if c == "expand":
                        msg = set_expand(a, True) or ""
                        lines = rebuild()
                    elif c == "collapse":
                        msg = set_expand(a, False) or ""
                        lines = rebuild()
                    elif c == "tab":
                        msg = set_tab(a) or ""
                        lines = rebuild()
                    elif c in ("reread", "doc"):
                        lines = rebuild()
                    elif c == "top":
                        off = 0
                    elif c in ("end", "bottom"):
                        off = maxoff
                    elif c in ("access", "retrieve", "open",
                               "scp", "follow", "search",
                               "random", "note", "notes",
                               "links", "help", "clear",
                               "next", "prev", "history",
                               "mute", "unmute",
                               "play", "stop",
                               "logout", "exit") \
                            or re.fullmatch(
                                r"(scp-)?\d{1,4}", c):
                        return cmdline
                    else:
                        msg = ("UNRECOGNIZED DIRECTIVE: %s"
                               % c.upper())
                elif k == "ESC":
                    entry = None
                elif k in ("\x7f", "\b"):
                    entry = entry[:-1]
                elif len(k) == 1 and k.isprintable():
                    entry += k
                continue
            if k == "q":
                return None
            if k == "UP":
                off -= 1
            elif k in ("DOWN", "\r", "\n"):
                off += 1
            elif k == "PGUP":
                off -= page - 1
            elif k in ("PGDN", " "):
                off += page - 1
            elif k == "HOME":
                off = 0
            elif k == "END":
                off = maxoff
            elif len(k) == 1 and k.isprintable():
                entry = k
                msg = ""
    except KeyboardInterrupt:
        return None
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
        sys.stdout.write("\033[?25h\033[?1049l")
        sys.stdout.flush()


