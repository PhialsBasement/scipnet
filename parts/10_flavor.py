RETRIEVAL = (
    "ROUTING REQUEST THROUGH SITE-19 RELAY ...",
    "NEGOTIATING RAISA ARCHIVE HANDSHAKE ...",
    "DECRYPTING RECORD BLOCK ...",
    "VERIFYING CLEARANCE AGAINST RECORD FLAGS ...",
    "COLD STORAGE SPIN-UP, PLEASE HOLD ...",
    "SCREENING PAYLOAD FOR MEMETIC HAZARDS ...",
    "COUNTERSIGNING ACCESS WITH SITE AI ...",
)

BROADCASTS = (
    "[SITE BROADCAST] Scheduled amnestic inventory at "
    "1900 site time.",
    "[SITE BROADCAST] Cafeteria B remains off limits "
    "pending decontamination.",
    "[SITE BROADCAST] Reminder: report recurring dreams "
    "to your supervisor.",
    "[SITE BROADCAST] Hall C lighting flicker is "
    "documented. Do not investigate.",
    "[SITE BROADCAST] Mandatory memetic hygiene "
    "refresher due Friday.",
    "[SITE BROADCAST] If you can read this twice, "
    "alert Site Security.",
    "[SITE BROADCAST] Lost keycard L-4? Contact RAISA "
    "before it contacts you.",
    "[SITE BROADCAST] The level 3 coffee machine is not "
    "anomalous. Stop filing reports.",
    "[SITE BROADCAST] Operator {name}, your workstation "
    "posture has been noted.",
    "[SITE BROADCAST] {name}, your wellness check is "
    "overdue. Attendance is mandatory.",
)

AMBIENT = (
    "UPLINK STABLE",
    "NO ACTIVE BREACHES",
    "MEMETIC FILTERS ONLINE",
    "ARCHIVE LOAD NOMINAL",
    "CONTAINMENT INTEGRITY 99.7%",
    "SITE TIME {t}",
    "COGNITOHAZARD SCAN CLEAN",
    "RAISA AUDIT IN PROGRESS",
)

SESSION = []
PROFILE = None
STATE_DIR = os.path.expanduser("~/.local/state/scipnet")
PROMOTIONS = {10: 3, 30: 4, 75: 5}

EPILOGUES = {
    "hazard": (
        "POST-EXPOSURE CHECK: count your fingers. Twice.",
        "If any of that text appeared to read back, "
        "file form MH-9 immediately.",
        "Baseline check: what color were your eyes "
        "this morning?",
    ),
    "keter": (
        "This access has been appended to your psych "
        "review file.",
        "You are advised to vary your route home tonight.",
        "Site Command was copied on this retrieval. "
        "Do not be alarmed.",
    ),
    "euclid": (
        "Containment holds. Today.",
        "Reading comprehension improves survival odds. "
        "Keep going.",
        "That file was updated more recently than its "
        "timestamp suggests.",
    ),
    "safe": (
        "Safe does not mean harmless. It never did.",
        "Routine record. Routine is a privilege.",
    ),
    "generic": (
        "Retrieval closed cleanly. RAISA appreciates "
        "tidy readers.",
        "Nothing followed you out of that file. "
        "Probably.",
    ),
}

STREAKS = {
    3: "RAISA NOTES SUSTAINED CURIOSITY.",
    7: "SEVEN FILES THIS SESSION. YOUR DEDICATION HAS "
       "BEEN FLAGGED AS COMMENDABLE.",
    15: "FIFTEEN FILES. PLEASE CONFIRM YOU HAVE TAKEN "
        "YOUR SCHEDULED BREAK. THIS IS A WELLNESS "
        "REQUIREMENT.",
}


