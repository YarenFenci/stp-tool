"""
STP Engine — deterministic, scenario-based priority assignment.

Priority logic (in order):
  1. Gating  — app/feature completely broken, crash, freeze, cannot perform core action
  2. High    — core feature works but has a meaningful defect affecting user flow
  3. Medium  — secondary UX, non-blocking issues, minor functional gaps
  4. Low     — cosmetic, text, icon, layout issues with no functional impact

Device/OS scope:
  - Detected separately and stored in "Device Scope" column
  - Priority is ADJUSTED based on scope:
      * Generic (no device/OS signal) → priority as-is
      * OS-specific (e.g. iOS 15, Android 12) → Gating→High, High→Medium (not Low)
      * Device-specific (e.g. Redmi 10, Samsung A13) → same as OS-specific
      * EXCEPTION: crash/ANR/freeze on a specific device/OS still stays Gating
        because a crash is never acceptable regardless of scope
"""

import re
from typing import List, Optional, Tuple

import pandas as pd

# ─────────────────────────────────────────────────────────────
# Required columns
# ─────────────────────────────────────────────────────────────
REQUIRED_COLS = [
    "Issue key",
    "Priority",
    "Summary",
    "Custom field (Manual Test Steps)",
    "Custom field (Scenario Expected Result)",
]

PRIORITY_ORDER     = ["Gating", "High", "Medium", "Low"]
PRIORITY_RANK      = {"Gating": 0, "High": 1, "Medium": 2, "Low": 3}
PRIORITY_FROM_RANK = {0: "Gating", 1: "High", 2: "Medium", 3: "Low"}

REASON_MAP = {
    "Gating": "Core functionality broken — blocks user",
    "High":   "Core feature defect — affects main user flow",
    "Medium": "Secondary UX issue — non-blocking",
    "Low":    "Cosmetic / minor edge — no functional impact",
}

# ─────────────────────────────────────────────────────────────
# GATING terms — app/feature completely non-functional
# ─────────────────────────────────────────────────────────────
GATING_TERMS = [
    # Hard crashes
    "crash", "crashes", "force close", "force-close",
    "freeze", "frozen", "hang", "hangs", "hung",
    "anr", "not responding", "app not responding",
    "black screen", "white screen", "blank screen",
    # Cannot open / launch
    "cannot open", "can't open", "not open", "fails to open",
    "app not launching", "does not launch", "won't launch",
    "splash screen stuck", "stuck on splash",
    # Cannot send / receive (messaging)
    "cannot send", "can't send", "message not sent", "fails to send",
    "cannot receive", "can't receive", "not received",
    "messages not delivered", "message failed to send",
    "chat not loading", "cannot open chat",
    # Data loss
    "data loss", "messages missing", "message lost", "messages lost",
    # Auth completely broken
    "cannot login", "login fail", "login error", "login failed",
    "sign in fail", "sign in failed", "cannot sign in",
    "cannot register", "registration failed",
    "otp not received", "otp not working",
    # Call completely broken
    "cannot start call", "call not started", "cannot call", "call failed",
    "call not connecting", "cannot join call",
    "no audio", "no video", "mic not working", "camera not working",
    # Other core broken
    "cannot upload", "upload failed", "upload not working",
    "cannot post", "post failed",
    "cannot open channel", "channel not loading",
    "status not loading", "cannot view status",
    "cannot save", "save failed", "settings not saved",
    "cannot logout", "logout failed",
    "feed not loading", "content not loading",
    "not working", "does not work",
]

# ─────────────────────────────────────────────────────────────
# HIGH terms — core feature works but has meaningful defect
# ─────────────────────────────────────────────────────────────
HIGH_TERMS = [
    # Messaging functional
    "send message", "message sent", "receive message",
    "forward message", "reply", "delete message", "unsend",
    "voice message", "send file", "send photo", "send video",
    "send document", "send attachment", "send sticker", "send emoji",
    "delivered", "read receipt", "typing indicator",
    # Calls functional
    "voice call", "video call", "call started", "incoming call", "outgoing call",
    "answer call", "decline call", "missed call", "end call",
    "mute", "unmute", "speaker", "switch camera", "call quality",
    "hold call", "resume call", "ringing",
    # Auth functional
    "login", "sign in", "sign up", "register",
    "two-step", "two factor", "biometric", "fingerprint", "face id",
    "change password", "reset password",
    # Story / status functional
    "post story", "view story", "reply to story", "story reaction",
    "upload photo", "upload video", "story seen",
    # Channel functional
    "follow channel", "unfollow", "join channel", "leave channel",
    "channel post", "subscribe",
    # Notification functional
    "push notification", "receive notification", "notification not received",
    # Privacy / account
    "block user", "unblock", "report user",
    "privacy settings", "account settings",
    # Media playback
    "media not playing", "video not playing", "audio not playing",
    "playback issue", "cannot play",
]

# ─────────────────────────────────────────────────────────────
# MEDIUM terms — secondary UX, non-blocking
# ─────────────────────────────────────────────────────────────
MEDIUM_TERMS = [
    # Lists & navigation
    "search", "filter", "sort", "list", "chat list", "contact list",
    "channel list", "history", "call log", "call history",
    "story list", "story viewer", "story duration",
    # UI components (functional)
    "tab", "menu", "panel", "picker", "keyboard",
    "scroll", "swipe", "gesture", "navigation",
    # Settings & profile (non-critical)
    "settings", "profile", "preferences", "toggle", "switch",
    "notification settings", "storage", "backup", "linked devices",
    "language", "theme", "font",
    # Secondary info
    "last seen", "online status", "chat info", "group info",
    "member list", "channel info", "discovery",
    "badge", "unread count", "preview",
    "archive", "mute chat", "pin chat",
    # Timer / duration display
    "timer", "duration", "timestamp", "date",
    # Minor functional gaps
    "not shown", "not displayed", "missing",
    "incorrect", "wrong",
]

# ─────────────────────────────────────────────────────────────
# LOW — purely cosmetic, no functional impact
# Only applied when NO High/Gating signal is present
# ─────────────────────────────────────────────────────────────
LOW_COSMETIC_TERMS = [
    # Alignment & layout
    "misalign", "misaligned", "not aligned", "off center",
    "overlap", "overlapping", "overlaps",
    "truncat", "cut off", "clipped",
    "padding", "margin issue", "spacing",
    # Visual
    "wrong color", "incorrect color", "wrong colour",
    "wrong font", "font size issue",
    "icon missing", "wrong icon", "broken image",
    "placeholder", "shimmer stuck",
    "ui glitch", "visual glitch", "render glitch",
    "flicker", "blink",
    # Cosmetic animation
    "animation glitch", "transition glitch", "scroll animation",
    "janky", "jank",
    # Dark mode cosmetic
    "dark mode color", "dark mode icon",
    "theme color wrong", "incorrect theme color",
    # Text / string cosmetic
    "typo", "spelling mistake", "wrong label",
    "incorrect string", "wrong string", "string issue",
    "label missing",
]

# Hard crash terms — these override device-specific downgrade
HARD_CRASH_TERMS = [
    "crash", "freeze", "hang", "anr", "not responding",
    "force close", "black screen", "white screen", "blank screen",
]

# ─────────────────────────────────────────────────────────────
# Device / OS scope detection
# ─────────────────────────────────────────────────────────────

# Specific device models (low-end or notable)
SPECIFIC_DEVICES = [
    # Samsung
    "samsung a02", "samsung a03", "samsung a04", "samsung a05",
    "samsung a13", "samsung a14", "samsung a23", "samsung a24",
    "samsung a32", "samsung a33", "samsung a52", "samsung a53",
    "samsung m13", "samsung m14", "samsung m23",
    "galaxy a02", "galaxy a03", "galaxy a04", "galaxy a05",
    "galaxy a13", "galaxy a14", "galaxy a23", "galaxy a33",
    "galaxy m13", "galaxy m14",
    # Xiaomi / Redmi / POCO
    "redmi 9", "redmi 10", "redmi 12", "redmi 13",
    "redmi note 9", "redmi note 10", "redmi note 11", "redmi note 12",
    "poco m2", "poco m3", "poco m4", "poco m5",
    "poco c3", "poco c4", "poco c5",
    "poco x3", "poco x4", "poco x5",
    "xiaomi 11 lite", "xiaomi 12 lite",
    # Tecno / Infinix / Itel
    "tecno spark", "tecno pop", "tecno camon",
    "infinix hot", "infinix smart", "infinix note",
    "itel a", "itel p",
    # Realme
    "realme c11", "realme c21", "realme c31", "realme c51",
    "realme c55", "realme narzo",
    # iPhone models
    "iphone 6", "iphone 7", "iphone 8", "iphone se",
    "iphone x", "iphone xr", "iphone xs",
    "iphone 11", "iphone 12", "iphone 13", "iphone 14", "iphone 15",
    # iPad
    "ipad mini", "ipad air", "ipad pro",
    # Generic budget signals
    "low end device", "low-end device", "budget device",
    "entry level device", "entry-level device",
]

SPECIFIC_CHIPSETS = [
    "snapdragon 4", "snapdragon 6", "snapdragon 480",
    "mediatek helio g", "mediatek helio a", "mediatek helio p",
    "unisoc", "spreadtrum",
    "exynos 7", "exynos 8", "exynos 850",
]

# OS version patterns
OS_VERSION_RE = [
    r"android\s*(\d+)",
    r"ios\s*(\d+)",
    r"api\s*(?:level\s*)?(\d+)",
    r"ipados\s*(\d+)",
]

# Single-device repro signals
SINGLE_DEVICE_RE = [
    r"only on .{3,40}",
    r"repro(?:duce[sd]?)? on .{3,40}",
    r"observed on .{3,40}",
    r"tested on .{3,40} only",
    r"specific to .{3,40}",
    r"cannot reproduce on other",
    r"only this device",
    r"device[- ]specific",
    r"single device",
]


def detect_device_os_scope(text: str) -> Tuple[bool, str, str]:
    """
    Returns (is_scoped, scope_type, scope_detail).
    scope_type: 'device' | 'os_version' | 'chipset' | 'single_device_repro' | ''
    scope_detail: human-readable label e.g. 'Samsung A13' or 'Android 12'
    """
    t = text.lower()

    # 1. Specific device
    for dev in SPECIFIC_DEVICES:
        if dev in t:
            return True, "device", dev.title()

    # 2. Chipset
    for chip in SPECIFIC_CHIPSETS:
        if chip in t:
            return True, "chipset", chip.title()

    # 3. OS version
    for pat in OS_VERSION_RE:
        m = re.search(pat, t, re.IGNORECASE)
        if m:
            full = m.group(0).strip()
            return True, "os_version", full.title()

    # 4. Single-device repro phrase
    for pat in SINGLE_DEVICE_RE:
        m = re.search(pat, t, re.IGNORECASE)
        if m:
            return True, "single_device_repro", m.group(0).strip().title()

    return False, "", ""


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────
def validate_columns(df: pd.DataFrame) -> None:
    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        raise ValueError("Missing required columns:\n  " + "\n  ".join(missing))


def normalize_priority(p) -> str:
    if pd.isna(p):
        return ""
    s  = str(p).strip()
    sl = s.lower()
    if sl in {"gating", "gate", "blocker", "critical", "p0"}:   return "Gating"
    if sl in {"high", "p1", "h"}:                                return "High"
    if sl in {"medium", "med", "p2", "m", "normal", "moderate"}: return "Medium"
    if sl in {"low", "p3", "l", "minor", "trivial"}:             return "Low"
    return s[:1].upper() + s[1:] if s else ""


def contains_any(text: str, terms: List[str]) -> bool:
    for t in terms:
        if t and t in text:
            return True
    return False


def is_hard_crash(text: str) -> bool:
    return contains_any(text, HARD_CRASH_TERMS)


# ─────────────────────────────────────────────────────────────
# Priority decision
# ─────────────────────────────────────────────────────────────
def decide_priority(text: str) -> Tuple[str, bool, str, str, str]:
    """
    Returns:
        stp_priority  : Gating | High | Medium | Low
        is_scoped     : bool
        scope_type    : device | os_version | chipset | single_device_repro | ''
        scope_detail  : e.g. 'Android 12', 'Samsung A13'
        reason        : human-readable explanation
    """
    t = text.lower()

    # Step 1 — detect device/OS scope
    is_scoped, scope_type, scope_detail = detect_device_os_scope(t)

    # Step 2 — base priority from keywords
    # Cosmetic check: if ONLY cosmetic signals present (no Gating/High signal), force Low
    # Medium terms are secondary — cosmetic overrides them if nothing functional is present
    has_gating   = contains_any(t, GATING_TERMS)
    has_high     = contains_any(t, HIGH_TERMS)
    has_medium   = contains_any(t, MEDIUM_TERMS)
    has_cosmetic = contains_any(t, LOW_COSMETIC_TERMS)

    if has_gating:
        base = "Gating"
    elif has_high:
        base = "High"
    elif has_cosmetic and not has_gating and not has_high:
        # Pure cosmetic: medium signals like "settings", "wrong" don't override cosmetic
        base = "Low"
    elif has_medium:
        base = "Medium"
    else:
        base = "Low"

    # Step 3 — adjust for device/OS scope
    if not is_scoped:
        priority = base
        reason   = REASON_MAP[priority]
    else:
        scope_note = f"{scope_type.replace('_', ' ').title()}: {scope_detail}"

        if is_hard_crash(t):
            # Crash on any device/OS stays Gating — a crash is never acceptable
            priority = "Gating"
            reason   = f"{REASON_MAP['Gating']} — crash on specific scope [{scope_note}]"
        elif base == "Gating":
            # Non-crash Gating on specific device/OS → High
            # (e.g. "cannot send on Samsung A13" — bad but not universal blocker)
            priority = "High"
            reason   = f"{REASON_MAP['High']} — scoped issue, not universal [{scope_note}]"
        elif base == "High":
            # High on specific device/OS → Medium
            priority = "Medium"
            reason   = f"{REASON_MAP['Medium']} — scoped to specific device/OS [{scope_note}]"
        else:
            # Medium/Low stays as-is, just annotated
            priority = base
            reason   = f"{REASON_MAP[base]} [{scope_note}]"

    return priority, is_scoped, scope_type, scope_detail, reason


# ─────────────────────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────────────────────
PRIORITY_ORDER = ["Gating", "High", "Medium", "Low"]

def run_stp(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Returns (analysis_df, summary_df, diff_df).
    """
    validate_columns(df)

    out = pd.DataFrame()
    out["Issue Key"]        = df["Issue key"].astype(str)
    out["Current Priority"] = df["Priority"].apply(normalize_priority)
    out["Summary"]          = df["Summary"].fillna("").astype(str)
    out["Steps"]            = df["Custom field (Manual Test Steps)"].fillna("").astype(str)
    out["Expected"]         = df["Custom field (Scenario Expected Result)"].fillna("").astype(str)

    text_col = (out["Summary"] + " " + out["Steps"] + " " + out["Expected"]).str.lower()
    results  = text_col.apply(decide_priority)

    out["STP Priority"] = results.apply(lambda r: r[0])
    out["Scoped"]       = results.apply(lambda r: "Yes" if r[1] else "")
    out["Scope Type"]   = results.apply(lambda r: r[2].replace("_", " ").title() if r[2] else "")
    out["Scope Detail"] = results.apply(lambda r: r[3])
    out["Changed"]      = out["Current Priority"] != out["STP Priority"]
    out["Reason"]       = results.apply(lambda r: r[4])

    # Summary
    cur_c = out["Current Priority"].value_counts(dropna=False).to_dict()
    stp_c = out["STP Priority"].value_counts(dropna=False).to_dict()

    rows = []
    for pr in PRIORITY_ORDER:
        cur     = int(cur_c.get(pr, 0))
        stp     = int(stp_c.get(pr, 0))
        chg     = stp - cur
        chg_pct = round(chg / cur * 100.0, 2) if cur != 0 else (0.0 if chg == 0 else 100.0)
        rows.append([pr, cur, stp, chg, chg_pct])

    summary_df = pd.DataFrame(rows, columns=["Priority", "Current", "STP", "Change", "Change %"])
    diff_df    = out[out["Changed"]].copy().reset_index(drop=True)

    return out, summary_df, diff_df
