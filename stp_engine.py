"""
STP Engine — platform-aware, scenario-based, deterministic.
Same CSV -> same output every time.

Key rules:
1. Platform detection: Android / iOS / Both (from text signals)
2. UI edge cases -> forced Low (visual glitches, alignment, cosmetic issues)
3. Device-specific signals -> informational only (flag shown, priority NOT changed)
4. Priority decision tree: Gating > High > Medium > Low via keyword matching
"""

import re
from typing import List, Tuple

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

PRIORITY_ORDER = ["Gating", "High", "Medium", "Low"]

REASON_MAP = {
    "Gating": "Core functionality broken",
    "High":   "Core feature validation",
    "Medium": "UX / secondary behaviour",
    "Low":    "Edge / UI validation",
}

# ─────────────────────────────────────────────────────────────
# Platform detection signals
# ─────────────────────────────────────────────────────────────
ANDROID_SIGNALS = [
    "android", "google play", "play store",
    "apk", "aab", "back button", "back key",
    "notification drawer", "status bar", "navigation bar",
    "samsung", "xiaomi", "huawei", "oppo", "vivo", "realme",
    "redmi", "poco", "oneplus", "motorola", "nokia android",
    "tecno", "infinix", "itel",
    "api level", "anr", "dalvik",
]

IOS_SIGNALS = [
    "ios", "iphone", "ipad", "ipod",
    "app store", "testflight",
    "swipe back", "swipe from edge",
    "face id", "touch id",
    "home indicator", "safe area", "notch",
    "haptic", "3d touch", "force touch",
    "siri", "airdrop", "imessage",
    "xcode", "swift", "objective-c",
]

OS_VERSION_PATTERNS = [
    r"android\s*\d+",
    r"ios\s*\d+",
    r"api\s*(?:level\s*)?\d+",
]

# ─────────────────────────────────────────────────────────────
# Device-specific signals (informational only)
# ─────────────────────────────────────────────────────────────
LOW_END_DEVICES = [
    "samsung a02", "samsung a03", "samsung a04", "samsung a05",
    "samsung a13", "samsung a14", "samsung m13", "samsung m14",
    "galaxy a02", "galaxy a03", "galaxy a04", "galaxy a05",
    "galaxy a13", "galaxy a14", "galaxy m13", "galaxy m14",
    "redmi 9", "redmi 10", "redmi 12",
    "redmi note 9", "redmi note 10",
    "poco m2", "poco m3", "poco m4",
    "poco c3", "poco c4", "poco c5",
    "tecno spark", "tecno pop", "tecno camon",
    "infinix hot", "infinix smart", "infinix note",
    "itel a", "itel p",
    "realme c11", "realme c21", "realme c31", "realme c51",
    "low end", "low-end", "budget device",
    "entry level", "entry-level",
    "1gb ram", "2gb ram", "32gb storage",
]

CHIPSET_SIGNALS = [
    "snapdragon 4", "snapdragon 6",
    "mediatek helio g", "mediatek helio a",
    "unisoc", "spreadtrum",
    "exynos 7", "exynos 8",
]

SINGLE_DEVICE_SIGNALS = [
    "only on this device", "this specific device",
    "reproduces on", "reproduced on", "repro on",
    "device specific", "device-specific",
    "one device only", "single device",
    "cannot reproduce on other",
    "affects only this",
]

LATEST_VERSION_SIGNALS = [
    "latest version", "latest build", "latest release",
    "beta version", "beta build", "release candidate", "rc build",
    "canary build", "nightly build",
    "after update", "after upgrade", "since update", "since upgrade",
]

# ─────────────────────────────────────────────────────────────
# UI edge case signals → forced Low
# Pure cosmetic / visual glitch / alignment issues
# ─────────────────────────────────────────────────────────────
UI_EDGE_TERMS = [
    # Layout & alignment
    "misalign", "misaligned", "overlap", "overlapping",
    "truncat", "cut off", "clipped", "overflow",
    "padding", "margin", "spacing issue",
    "not centered", "off center", "alignment",
    # Visual cosmetic
    "color wrong", "wrong color", "wrong colour", "colour wrong",
    "font size", "wrong font", "text size",
    "icon missing", "icon wrong", "wrong icon",
    "image not loading", "image broken", "broken image",
    "placeholder visible", "shimmer",
    # Minor UI glitch
    "ui glitch", "visual glitch", "flicker", "flickering",
    "blink", "blinking",
    "layout issue", "layout bug", "ui issue", "ui bug",
    "rendering issue", "render glitch",
    # Cosmetic scroll / animation
    "scroll animation", "animation glitch", "transition glitch",
    "scroll lag", "janky", "jank",
    # Dark mode cosmetic
    "dark mode color", "dark mode icon", "dark mode text",
    "theme color", "incorrect theme",
    # Minor label / string
    "wrong label", "label missing", "string missing",
    "typo", "spelling",
    "wrong string", "incorrect string",
]

# Important UI things that should NOT be forced Low
# (if these appear alongside UI_EDGE_TERMS, UI edge rule is skipped)
UI_EDGE_EXCEPTIONS = [
    "crash", "freeze", "hang", "anr",
    "cannot", "can't", "unable", "fail", "failed",
    "not working", "broken", "error", "does not work",
    "not sent", "not received", "not delivered",
    "black screen", "white screen", "blank screen",
]

# ─────────────────────────────────────────────────────────────
# Core scenario keyword sets
# ─────────────────────────────────────────────────────────────
GATING_TERMS = [
    # App lifecycle
    "crash", "freeze", "hang", "stuck", "anr",
    "black screen", "white screen", "blank screen",
    "force close", "not responding", "app not responding",
    # Open / launch
    "cannot open", "can't open", "not open", "fails to open",
    "app not launching", "splash screen stuck",
    # Messaging
    "cannot send", "can't send", "message not sent", "fails to send",
    "cannot receive", "can't receive", "not received",
    "message failed", "chat not loading", "cannot open chat",
    "messages not delivered", "data loss", "message lost", "messages missing",
    # Auth
    "login fail", "cannot login", "login error", "sign in fail",
    "cannot register", "registration fail",
    # Calls
    "cannot start call", "call not started", "cannot call", "call fail",
    "call dropped", "call disconnected", "no audio", "no video",
    "mic not working", "camera not working", "cannot join call",
    # Other core
    "cannot save", "settings not saved", "cannot logout",
    "status not loading", "cannot upload", "cannot post",
    "cannot open channel", "channel not loading", "feed not loading",
    "cannot view", "not loading",
]

HIGH_TERMS = [
    # Messaging
    "send message", "message sent", "receive message", "message received",
    "forward message", "reply message", "delete message", "unsend",
    "send emoji", "emoji sent", "send sticker", "sticker sent",
    "send file", "send photo", "send video", "send document",
    "reaction", "delivered", "read receipt", "typing",
    "voice message", "attachment", "media message",
    # Calls
    "voice call", "video call", "call started", "incoming call", "outgoing call",
    "answer call", "decline call", "missed call", "end call",
    "mute", "speaker", "switch camera", "call quality",
    "hold", "resume call", "ringing",
    # Auth & account
    "login", "sign in", "register", "sign up",
    "change password", "two-step", "two factor", "privacy",
    "block user", "report user",
    # Story / status
    "post story", "view story", "reply story", "story reaction",
    "upload photo", "upload video",
    # Channel
    "follow", "unfollow", "join channel", "leave channel",
    "channel post", "channel message",
    # Notification (functional)
    "push notification", "receive notification",
]

MEDIUM_TERMS = [
    "search", "category", "panel", "picker", "keyboard", "tab", "scroll",
    "display", "shown", "settings", "profile", "notification settings", "ui",
    "history", "log", "list", "filter", "duration", "timer",
    "toggle", "badge", "banner", "preview",
    "contact", "group", "archive", "mute",
    "seen", "last seen", "chat info", "chat list",
    "story viewer", "story list", "story duration",
    "call history", "call log", "call screen", "dialpad",
    "channel list", "member list", "channel info",
    "linked devices", "storage", "backup",
    "discover", "explore",
]


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
    if sl in {"gating", "gate", "blocker"}:           return "Gating"
    if sl in {"high", "p1", "h", "critical"}:         return "High"
    if sl in {"medium", "med", "p2", "m", "normal"}:  return "Medium"
    if sl in {"low", "p3", "l", "minor"}:             return "Low"
    return s[:1].upper() + s[1:] if s else ""


def contains_any(text: str, terms: List[str]) -> bool:
    for t in terms:
        if t and t in text:
            return True
    return False


def matches_pattern(text: str, patterns: List[str]) -> bool:
    for pat in patterns:
        if re.search(pat, text, re.IGNORECASE):
            return True
    return False


# ─────────────────────────────────────────────────────────────
# Platform detection
# ─────────────────────────────────────────────────────────────
def detect_platform(text: str) -> str:
    """Returns 'Android' | 'iOS' | 'Both' | ''"""
    t   = text.lower()
    has_android = contains_any(t, ANDROID_SIGNALS) or matches_pattern(t, OS_VERSION_PATTERNS[:3])
    has_ios     = contains_any(t, IOS_SIGNALS)     or matches_pattern(t, OS_VERSION_PATTERNS[3:])

    # Version pattern check more carefully
    if re.search(r"android\s*\d+", t):     has_android = True
    if re.search(r"ios\s*\d+", t):         has_ios     = True

    if has_android and has_ios: return "Both"
    if has_android:             return "Android"
    if has_ios:                 return "iOS"
    return ""


# ─────────────────────────────────────────────────────────────
# Device-specific detection (informational only)
# ─────────────────────────────────────────────────────────────
def detect_device_scope(text: str) -> Tuple[bool, str]:
    """Returns (is_device_specific, scope_label)."""
    t = text.lower()
    if contains_any(t, LOW_END_DEVICES):     return True, "low_end_device"
    if contains_any(t, CHIPSET_SIGNALS):     return True, "chipset"
    if contains_any(t, SINGLE_DEVICE_SIGNALS): return True, "single_device"
    if contains_any(t, LATEST_VERSION_SIGNALS): return True, "latest_version"
    if re.search(r"android\s*\d+|ios\s*\d+|api\s*(?:level\s*)?\d+", t):
        return True, "os_version"
    return False, ""


# ─────────────────────────────────────────────────────────────
# UI edge case detection
# ─────────────────────────────────────────────────────────────
def is_ui_edge_case(text: str) -> bool:
    """
    True if scenario is a pure cosmetic/visual edge case.
    Skipped if any functional failure keyword is present.
    """
    t = text.lower()
    if not contains_any(t, UI_EDGE_TERMS):
        return False
    # Don't force Low if there's also a real functional failure
    if contains_any(t, UI_EDGE_EXCEPTIONS):
        return False
    return True


# ─────────────────────────────────────────────────────────────
# Per-row decision
# ─────────────────────────────────────────────────────────────
def decide_priority(text: str) -> Tuple[str, str, bool, str, str]:
    """
    Returns:
        stp_priority   : Gating | High | Medium | Low
        platform       : Android | iOS | Both | ''
        is_device_spec : bool
        device_scope   : str
        reason         : str
    """
    t = text.lower()

    platform              = detect_platform(t)
    is_device, dev_scope  = detect_device_scope(t)
    ui_edge               = is_ui_edge_case(t)

    # Priority decision tree
    if ui_edge:
        priority = "Low"
        reason   = "UI / cosmetic edge case — visual only"
    elif contains_any(t, GATING_TERMS):
        priority = "Gating"
        reason   = REASON_MAP["Gating"]
    elif contains_any(t, HIGH_TERMS):
        priority = "High"
        reason   = REASON_MAP["High"]
    elif contains_any(t, MEDIUM_TERMS):
        priority = "Medium"
        reason   = REASON_MAP["Medium"]
    else:
        priority = "Low"
        reason   = REASON_MAP["Low"]

    # Append device-specific note to reason (no priority change)
    if is_device:
        reason = f"{reason} [device: {dev_scope}]"

    return priority, platform, is_device, dev_scope, reason


# ─────────────────────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────────────────────
def run_stp(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Returns (analysis_df, summary_df, diff_df).
    No feature param needed — platform-based, not feature-based.
    """
    validate_columns(df)

    out = pd.DataFrame()
    out["Issue Key"]        = df["Issue key"].astype(str)
    out["Current Priority"] = df["Priority"].apply(normalize_priority)
    out["Summary"]          = df["Summary"].fillna("").astype(str)
    out["Steps"]            = df["Custom field (Manual Test Steps)"].fillna("").astype(str)
    out["Expected"]         = df["Custom field (Scenario Expected Result)"].fillna("").astype(str)

    text_col = (out["Summary"] + " " + out["Steps"] + " " + out["Expected"]).str.lower()

    results = text_col.apply(decide_priority)

    out["STP Priority"]    = results.apply(lambda r: r[0])
    out["Platform"]        = results.apply(lambda r: r[1])
    out["Device Specific"] = results.apply(lambda r: "Yes" if r[2] else "")
    out["Device Scope"]    = results.apply(lambda r: r[3])
    out["Changed"]         = out["Current Priority"] != out["STP Priority"]
    out["Reason"]          = results.apply(lambda r: r[4])

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
