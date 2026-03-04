"""
STP Engine — deterministic, scenario-aware, device-specific detection.
Same CSV -> same output every time.

Device-specific logic:
  If a test case contains device-specific signals (low-end device names,
  specific OS versions, chipsets, single-device mentions, latest-version scope)
  the base STP priority is DOWNGRADED one level:
    Gating -> High, High -> Medium, Medium -> Low

  Exception: crash/freeze/hang on any device stays Gating.
  (Controlled by DEVICE_CRASH_STAYS_GATING flag.)
"""

import re
from typing import Dict, List, Tuple

import pandas as pd

# ─────────────────────────────────────────────────────────────
# Required columns — exact match, no fallback
# ─────────────────────────────────────────────────────────────
REQUIRED_COLS = [
    "Issue key",
    "Priority",
    "Summary",
    "Custom field (Manual Test Steps)",
    "Custom field (Scenario Expected Result)",
]

PRIORITY_ORDER    = ["Gating", "High", "Medium", "Low"]
PRIORITY_RANK     = {"Gating": 0, "High": 1, "Medium": 2, "Low": 3}
PRIORITY_FROM_RANK = {0: "Gating", 1: "High", 2: "Medium", 3: "Low"}

REASON_MAP = {
    "Gating": "Core functionality broken",
    "High":   "Core feature validation",
    "Medium": "UX / secondary behaviour",
    "Low":    "Edge validation",
}

# Crash on a specific device still stays Gating — a crash is a crash
DEVICE_CRASH_STAYS_GATING = True

# ─────────────────────────────────────────────────────────────
# Device-specific signal lists
# ─────────────────────────────────────────────────────────────
LOW_END_DEVICES = [
    # Samsung budget
    "samsung a03", "samsung a04", "samsung a05", "samsung a13", "samsung a14",
    "galaxy a03", "galaxy a04", "galaxy a05", "galaxy a13", "galaxy a14",
    "samsung m13", "samsung m14", "galaxy m13", "galaxy m14",
    "samsung a02", "galaxy a02",
    # Xiaomi / Redmi / POCO budget
    "redmi 9", "redmi 10", "redmi 12", "redmi note 9", "redmi note 10",
    "poco m2", "poco m3", "poco m4", "poco c3", "poco c4", "poco c5",
    "xiaomi 12 lite", "xiaomi redmi",
    # Tecno / Infinix / Itel
    "tecno spark", "tecno pop", "tecno camon",
    "infinix hot", "infinix smart", "infinix note",
    "itel a", "itel p",
    # Realme budget
    "realme c11", "realme c21", "realme c31", "realme c51",
    # General budget signals
    "low end", "low-end", "budget device", "entry level", "entry-level",
    "2gb ram", "1gb ram", "32gb storage", "16gb storage",
]

OS_VERSION_PATTERNS = [
    r"android\s*(4|5|6|7|8|9|10|11|12|13|14)[\.\s]",
    r"android\s*(4|5|6|7|8|9|10|11|12|13|14)$",
    r"api\s*(?:level\s*)?(19|21|22|23|24|25|26|27|28|29|30|31|32|33|34)\b",
    r"ios\s*(12|13|14|15|16|17)[\.\s]",
    r"ios\s*(12|13|14|15|16|17)$",
    r"on (?:android|ios) \d+",
    r"(?:android|ios) version \d+",
]

CHIPSET_SIGNALS = [
    "snapdragon 4", "snapdragon 6",
    "mediatek helio g", "mediatek helio a",
    "unisoc", "spreadtrum",
    "exynos 7", "exynos 8",
]

SINGLE_DEVICE_SIGNALS = [
    "only on", "only this device", "this specific device",
    "reproduces on", "reproduced on", "repro on",
    "tested on specific", "observed on specific",
    "device specific", "device-specific",
    "one device only", "single device",
    "specific to device", "affects only this",
    "cannot reproduce on other",
]

LATEST_VERSION_SIGNALS = [
    "latest version", "latest build", "latest release",
    "beta version", "beta build", "release candidate", "rc build",
    "canary build", "nightly build",
    "new version", "new update", "after update", "after upgrade",
    "since update", "since upgrade", "version update",
]

HARD_CRASH_TERMS = [
    "crash", "freeze", "hang", "anr", "not responding",
    "force close", "black screen", "blank screen", "white screen",
]

# ─────────────────────────────────────────────────────────────
# Base scenario keyword sets
# ─────────────────────────────────────────────────────────────
BASE_GATING = [
    "crash", "freeze", "hang", "stuck", "anr",
    "cannot open", "can't open", "not open", "fails to open",
    "cannot send", "can't send", "message not sent", "fails to send",
    "cannot receive", "can't receive", "not received",
    "login fail", "cannot login", "login error", "sign in fail",
    "cannot start call", "call not started", "cannot call", "call fail",
    "black screen", "white screen", "blank screen",
    "force close", "not responding", "app not responding",
    "data loss", "message lost", "messages missing",
]

BASE_HIGH = [
    "send message", "message sent", "receive message", "message received",
    "voice call", "video call", "call started", "incoming call", "outgoing call",
    "send emoji", "emoji sent", "send sticker", "sticker sent",
    "reaction", "delivered", "read receipt",
    "login", "sign in", "register", "sign up",
    "send file", "send photo", "send video", "send document",
    "forward message", "reply message",
]

BASE_MEDIUM = [
    "search", "category", "panel", "picker", "keyboard", "tab", "icon", "scroll",
    "display", "shown", "settings", "profile", "notification", "ui",
    "history", "log", "list", "filter", "duration", "timer",
    "toggle", "badge", "banner", "preview",
    "contact", "group", "archive", "mute",
]

# ─────────────────────────────────────────────────────────────
# Feature-specific keyword expansions
# ─────────────────────────────────────────────────────────────
FEATURE_TERMS: Dict[str, Dict[str, List[str]]] = {
    "calls": {
        "gating": ["no audio", "no video", "mic not working", "camera not working",
                   "cannot join call", "call dropped", "call disconnected",
                   "audio not working", "can't hear", "cannot hear"],
        "high":   ["mute", "speaker", "switch camera", "call ended", "ringing",
                   "hold", "resume call", "call quality", "end call",
                   "answer call", "decline call", "missed call"],
        "medium": ["call screen", "dialpad", "call history", "call ui", "call log",
                   "call duration", "end call button", "call timer", "call notification"],
    },
    "chats": {
        "gating": ["cannot message", "messages not delivered", "chat not loading",
                   "cannot open chat", "message failed", "chat error"],
        "high":   ["typing", "seen", "forward", "reply", "pin message", "delete message",
                   "unsend", "attachment", "media message", "voice message"],
        "medium": ["chat list", "conversation", "unread", "pin chat", "archive",
                   "mute chat", "search message", "chat info", "last seen"],
    },
    "channels": {
        "gating": ["cannot open channel", "channel not loading", "cannot post",
                   "channel error", "feed not loading"],
        "high":   ["follow", "unfollow", "join channel", "leave channel", "subscribe",
                   "channel post", "channel message", "share channel"],
        "medium": ["discover", "category list", "search channel", "channel list",
                   "channel info", "member list", "channel settings"],
    },
    "status": {
        "gating": ["status not loading", "cannot upload story", "story not posted",
                   "status error", "cannot view status"],
        "high":   ["post story", "view story", "reply story", "story reaction",
                   "story seen", "upload photo", "upload video", "story viewers"],
        "medium": ["story viewer", "status ui", "story list", "story duration",
                   "story privacy", "story settings", "my status"],
    },
    "story": {
        "gating": ["status not loading", "cannot upload story", "story not posted"],
        "high":   ["post story", "view story", "reply story", "story reaction"],
        "medium": ["story viewer", "status ui", "story list"],
    },
    "more": {
        "gating": ["cannot save settings", "settings not saved", "cannot logout",
                   "logout fail", "cannot delete account"],
        "high":   ["change language", "change theme", "privacy", "block user",
                   "report user", "account", "two-step verification", "backup"],
        "medium": ["toggle", "switch", "preference", "help", "about", "storage usage",
                   "notification settings", "linked devices"],
    },
    "settings": {
        "gating": ["cannot save settings", "settings not saved", "settings crash"],
        "high":   ["change language", "change theme", "privacy", "two factor",
                   "two-step", "account info", "change number"],
        "medium": ["toggle", "preference", "notification settings", "storage",
                   "chat backup", "chat history"],
    },
    "others": {
        "gating": ["app not launching", "splash screen stuck", "onboarding fail"],
        "high":   ["deep link", "push notification", "share", "qr code"],
        "medium": ["widget", "shortcut", "app icon", "language", "theme"],
    },
}


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────
def normalize_feature(feature: str) -> str:
    return re.sub(r"\s+", "", (feature or "").strip())


def get_terms(feature: str) -> Tuple[List[str], List[str], List[str]]:
    key = normalize_feature(feature).lower()
    extra  = FEATURE_TERMS.get(key, {"gating": [], "high": [], "medium": []})
    gating = [t.lower() for t in BASE_GATING + extra.get("gating", [])]
    high   = [t.lower() for t in BASE_HIGH   + extra.get("high",   [])]
    medium = [t.lower() for t in BASE_MEDIUM + extra.get("medium", [])]
    return gating, high, medium


def validate_columns(df: pd.DataFrame) -> None:
    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        raise ValueError("Missing required columns:\n  " + "\n  ".join(missing))


def normalize_priority(p) -> str:
    if pd.isna(p):
        return ""
    s  = str(p).strip()
    sl = s.lower()
    if sl in {"gating", "gate", "blocker"}:            return "Gating"
    if sl in {"high", "p1", "h", "critical"}:          return "High"
    if sl in {"medium", "med", "p2", "m", "normal"}:   return "Medium"
    if sl in {"low", "p3", "l", "minor"}:              return "Low"
    return s[:1].upper() + s[1:] if s else ""


def contains_any(text: str, terms: List[str]) -> bool:
    for t in terms:
        if t and t in text:
            return True
    return False


def matches_any_pattern(text: str, patterns: List[str]) -> bool:
    for pat in patterns:
        if re.search(pat, text, re.IGNORECASE):
            return True
    return False


# ─────────────────────────────────────────────────────────────
# Device-specific detection
# ─────────────────────────────────────────────────────────────
def detect_device_scope(text: str) -> Tuple[bool, str]:
    """Returns (is_device_specific, scope_label)."""
    t = text.lower()
    if contains_any(t, LOW_END_DEVICES):         return True, "low_end_device"
    if matches_any_pattern(t, OS_VERSION_PATTERNS): return True, "os_version"
    if contains_any(t, CHIPSET_SIGNALS):         return True, "chipset"
    if contains_any(t, SINGLE_DEVICE_SIGNALS):   return True, "single_device"
    if contains_any(t, LATEST_VERSION_SIGNALS):  return True, "latest_version"
    return False, ""


def is_hard_crash(text: str) -> bool:
    return contains_any(text.lower(), HARD_CRASH_TERMS)


# ─────────────────────────────────────────────────────────────
# Per-row decision
# ─────────────────────────────────────────────────────────────
def decide_priority(
    text: str,
    gating_terms: List[str],
    high_terms: List[str],
    medium_terms: List[str],
) -> Tuple[str, bool, str, str]:
    """Returns (stp_priority, is_device_specific, device_scope, reason)."""

    # 1 — base priority from scenario keywords
    if contains_any(text, gating_terms):   base = "Gating"
    elif contains_any(text, high_terms):   base = "High"
    elif contains_any(text, medium_terms): base = "Medium"
    else:                                  base = "Low"

    # 2 — device-specific detection (informational only, priority unchanged)
    is_device, scope = detect_device_scope(text)

    reason = REASON_MAP.get(base, "Edge validation")
    if is_device:
        reason = f"{reason} — device-specific [{scope}]"

    return base, is_device, scope, reason


# ─────────────────────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────────────────────
def run_stp(df: pd.DataFrame, feature: str) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Returns (analysis_df, summary_df, diff_df).
    analysis_df : one row per test case with full STP output
    summary_df  : priority-level counts (Current vs STP)
    diff_df     : only rows where priority changed
    """
    validate_columns(df)
    gating_terms, high_terms, medium_terms = get_terms(feature)

    out = pd.DataFrame()
    out["Issue Key"]        = df["Issue key"].astype(str)
    out["Current Priority"] = df["Priority"].apply(normalize_priority)
    out["Summary"]          = df["Summary"].fillna("").astype(str)
    out["Steps"]            = df["Custom field (Manual Test Steps)"].fillna("").astype(str)
    out["Expected"]         = df["Custom field (Scenario Expected Result)"].fillna("").astype(str)

    text_col = (out["Summary"] + " " + out["Steps"] + " " + out["Expected"]).str.lower()

    results = text_col.apply(
        lambda t: decide_priority(t, gating_terms, high_terms, medium_terms)
    )

    out["STP Priority"]    = results.apply(lambda r: r[0])
    out["Device Specific"] = results.apply(lambda r: "Yes" if r[1] else "")
    out["Device Scope"]    = results.apply(lambda r: r[2])
    out["Changed"]         = out["Current Priority"] != out["STP Priority"]
    out["Reason"]          = results.apply(lambda r: r[3])

    # Summary table
    cur_c = out["Current Priority"].value_counts(dropna=False).to_dict()
    stp_c = out["STP Priority"].value_counts(dropna=False).to_dict()

    rows = []
    for pr in PRIORITY_ORDER:
        cur = int(cur_c.get(pr, 0))
        stp = int(stp_c.get(pr, 0))
        chg = stp - cur
        chg_pct = round(chg / cur * 100.0, 2) if cur != 0 else (0.0 if chg == 0 else 100.0)
        rows.append([pr, cur, stp, chg, chg_pct])

    summary_df = pd.DataFrame(rows, columns=["Priority", "Current", "STP", "Change", "Change %"])
    diff_df    = out[out["Changed"]].copy().reset_index(drop=True)

    return out, summary_df, diff_df
