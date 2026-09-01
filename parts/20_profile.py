def profile_path(name):
    safe = re.sub(r"[^a-z0-9-]", "_", name.lower())
    return os.path.join(STATE_DIR,
                        "operator-%s.json" % safe)


def load_profile(name):
    os.makedirs(STATE_DIR, exist_ok=True)
    path = profile_path(name)
    if os.path.exists(path):
        try:
            with open(path) as fh:
                d = json.load(fh)
            d["_new"] = False
            d["name"] = name
            return d
        except Exception:
            pass
    return {"name": name, "clearance": 2, "reads": 0,
            "flags": 0, "last": 0.0, "_new": True}


def save_profile():
    if PROFILE is None:
        return
    PROFILE["last"] = time.time()
    d = {k: v for k, v in PROFILE.items()
         if k.startswith("_") is False}
    with open(profile_path(PROFILE["name"]), "w") as fh:
        json.dump(d, fh)


def doc_clearance():
    lv = 0
    for a in DOC["acs"]:
        try:
            lv = max(lv, int(a.get("clearance", "0")))
        except ValueError:
            pass
    return lv


def doc_epilogue():
    n = len(SESSION)
    if n in STREAKS:
        slow(STREAKS[n], style=DIM)
        return
    if random.random() > 0.5:
        return
    srcl = DOC["src"].lower()
    if re.search(r"memetic|cognitohazard|infohazard", srcl):
        pool = EPILOGUES["hazard"]
    elif "keter" in srcl:
        pool = EPILOGUES["keter"]
    elif "euclid" in srcl:
        pool = EPILOGUES["euclid"]
    elif re.search(r"object class[^\n]*safe", srcl):
        pool = EPILOGUES["safe"]
    else:
        pool = EPILOGUES["generic"]
    slow(random.choice(pool), style=DIM)


