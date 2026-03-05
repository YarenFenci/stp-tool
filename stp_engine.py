"""
STP Engine — BiP messaging app QA priority assignment.
Based on actual QA manual: Gating / High / Medium / Low
Priority logic follows the official BiP criteria document.
"""

import re
from typing import Tuple, Optional

# ─────────────────────────────────────────────────────────────
# Priority order (highest → lowest)
# ─────────────────────────────────────────────────────────────
PRIORITY_ORDER = ["Gating", "High", "Medium", "Low"]

# ─────────────────────────────────────────────────────────────
# GATING — only truly blocking issues
# Core functions that must work: messaging, calling, login, media send
# ─────────────────────────────────────────────────────────────
GATING_TERMS = [
    # Core messaging broken
    "mesaj gönderilemiyor", "mesaj gönderme çalışmıyor", "mesaj atılamıyor",
    "mesaj gönderilemedi", "mesajlaşma çalışmıyor", "chat açılmıyor",
    "sohbet başlatılamıyor", "mesaj iletilmiyor",
    "message not sending", "message send fail", "cannot send message",
    "messaging not working", "chat not working", "chat crash",

    # Core calling broken
    "arama yapılamıyor", "arama çalışmıyor", "arama başlatılamıyor",
    "sesli arama çalışmıyor", "görüntülü arama çalışmıyor",
    "call not working", "call fails", "call cannot be started",
    "voice call broken", "video call broken",

    # Login / auth completely broken
    "giriş yapılamıyor", "uygulamaya girilemiyor", "login olunmuyor",
    "oturum açılamıyor", "kayıt olunamıyor", "doğrulama yapılamıyor",
    "cannot login", "login fails", "cannot open app", "app won't open",
    "registration failed", "otp gelmiyor", "otp çalışmıyor",

    # App crash on core scenario (reproducible)
    "her zaman crash", "her seferinde crash", "her açılışta crash",
    "always crashes", "consistently crashes", "crash on every",
    "belirli senaryo ile crash", "reproducible crash",
    "uygulama açılmıyor crash", "app crashes on launch",
    "app crash on start", "force close",

    # Fraud / financial risk
    "fraud", "maddi kayıp", "ücretlendirme hatası", "faturalama hatası",
    "para çekildi", "ödeme hatası", "billing error", "unauthorized charge",

    # Data loss
    "kalıcı veri kaybı", "mesajlar silindi", "data kaybı",
    "permanent data loss", "messages lost", "data corruption",

    # Media send on core flow
    "resim gönderilemiyor", "video gönderilemiyor", "dosya gönderilemiyor",
    "medya gönderilemedi", "image send fail", "file send fail",
]

# ─────────────────────────────────────────────────────────────
# HIGH — important but not fully blocking
# ─────────────────────────────────────────────────────────────
HIGH_TERMS = [
    # Intermittent core feature issues
    "bazen çalışmıyor", "zaman zaman crash", "arada crash",
    "occasional crash", "intermittent crash", "sometimes fails",
    "sometimes crash",

    # Notification issues
    "bildirim gelmiyor", "push notification çalışmıyor", "bildirimler çalışmıyor",
    "notification not working", "push notification fail", "bildirimler gelmiyor",
    "grup mesajı gönderilemiyor", "grup sohbeti açılmıyor",
    "group message fail", "group chat not working",

    # Story / status broken
    "hikaye paylaşılamıyor", "story paylaşılamıyor", "story görüntülenemiyor",
    "story not loading", "story upload fail",

    # Sticker / emoji broken in core flow
    "sticker gönderilemiyor", "sticker çalışmıyor", "emoji gönderilemiyor",

    # Profile / settings blocking usage
    "profil güncellenemiyor", "ayarlar kaydedilemiyor",
    "profile update fail", "settings not saving",

    # Media viewing broken
    "resim açılmıyor", "video oynatılamıyor", "medya görüntülenemiyor",
    "image not loading", "video not playing", "media not loading",

    # Sync issues
    "mesajlar senkronize olmuyor", "mesajlar gecikiyor",
    "message sync fail", "messages not syncing", "messages delayed",

    # High-end device specific crash
    "samsung crash", "iphone crash", "flagship crash",
]

# ─────────────────────────────────────────────────────────────
# MEDIUM — secondary UX issues, non-blocking
# ─────────────────────────────────────────────────────────────
MEDIUM_TERMS = [
    # UI/UX issues that affect experience
    "yanlış görüntüleniyor", "hatalı gösteriliyor", "ekran donuyor",
    "arayüz bozuk", "ui hatası", "layout bozuk",
    "incorrect display", "wrong layout", "screen freezes", "ui glitch",

    # Localization
    "çeviri hatası", "yanlış çeviri", "dil sorunu", "lokalizasyon",
    "translation error", "localization issue", "wrong language",

    # Minor functional issues with workaround
    "workaround ile çalışıyor", "farklı yoldan yapılabiliyor",
    "has workaround", "alternative path works",

    # Search / discovery issues
    "arama sonuçları yanlış", "kişi bulunamıyor", "arama çalışmıyor kısmen",
    "search results wrong", "contact search issue",

    # Read receipts / delivery status
    "okundu bilgisi gelmiyor", "iletildi göstermiyor",
    "read receipt missing", "delivery status wrong",

    # Minor crash (not reproducible consistently)
    "nadir crash", "rare crash", "random crash", "ara sıra crash",

    # Performance (notable slowness is Medium not Low)
    "yavaş yükleniyor", "geç açılıyor", "gecikme var", "yavaş açılıyor",
    "slow loading", "performance issue", "lag", "slow",

    # Settings minor issues
    "ses ayarı çalışmıyor", "titreşim ayarı", "tema değişmiyor",
    "sound setting issue", "vibration issue",
]

# ─────────────────────────────────────────────────────────────
# LOW / COSMETIC — no functional impact
# ─────────────────────────────────────────────────────────────
LOW_COSMETIC_TERMS = [
    # Pure UI cosmetic
    "yazım hatası", "metin yanlış", "hizalama bozuk", "renk yanlış",
    "font sorunu", "spacing sorunu", "padding yanlış", "ikon yanlış",
    "typo", "spelling error", "alignment issue", "color wrong",
    "wrong font", "wrong icon", "wrong spacing",

    # Minor text/content issues
    "metin eksik", "placeholder hatalı", "tooltip yanlış",
    "missing text", "wrong placeholder", "wrong tooltip",

    # Non-critical cosmetic
    "animasyon bozuk", "geçiş animasyonu", "blink",
    "animation glitch", "transition issue",
]

# ─────────────────────────────────────────────────────────────
# HARD CRASH terms (reproducible) → always Gating
# ─────────────────────────────────────────────────────────────
HARD_CRASH_TERMS = [
    "crash", "force close", "çöküyor", "kapanıyor",
    "uygulama kapandı", "app closed", "fatal error",
    "anr", "not responding",
]

# Freeze/hang terms → Medium level, not auto-Gating
FREEZE_TERMS = [
    "donuyor", "freeze", "takılıyor", "yanıt vermiyor", "askıda kalıyor",
    "hangs", "stuck", "not responsive",
]

# ─────────────────────────────────────────────────────────────
# Device/OS scope detection
# ─────────────────────────────────────────────────────────────
DEVICE_PATTERNS = [
    r"\bredmi\s*\d+\b", r"\bxiaomi\b", r"\bsamsung\s+[a-z]\d+", r"\bhuawei\b",
    r"\biphone\s*\d+", r"\bpixel\s*\d+", r"\bonePlus\b", r"\boppo\b",
    r"\brealme\b", r"\bvivo\b", r"\bnokia\b", r"\blg\b",
    r"\bpoco\b", r"\bmoto\b", r"\bmotorola\b",
    r"\bgalaxy\s+[a-z]\d+",
]

OS_PATTERNS = [
    r"\bandroid\s*\d+", r"\bios\s*\d+", r"\bmiui\s*\d+",
    r"\bone\s*ui\s*\d+", r"\bharmonyos\b", r"\bcoloros\b",
    r"\bandroid\s+1[0-9]\b", r"\bandroid\s+[89]\b",
]

CHIPSET_PATTERNS = [
    r"\bsnapdragon\s*\d+", r"\bexynos\s*\d+", r"\bdimensity\s*\d+",
    r"\bkirin\s*\d+", r"\ba\d+\s*chip", r"\bbionic\b",
    r"\bmediatek\b", r"\bhelio\b",
]


def detect_device_os_scope(text: str) -> Tuple[bool, str, str]:
    """
    Returns (is_scoped, scope_type, scope_detail)
    scope_type: 'device' | 'os_version' | 'chipset' | 'single_device_repro'
    """
    t = text.lower()

    for pat in CHIPSET_PATTERNS:
        m = re.search(pat, t, re.IGNORECASE)
        if m:
            return True, "chipset", m.group(0)

    for pat in OS_PATTERNS:
        m = re.search(pat, t, re.IGNORECASE)
        if m:
            return True, "os_version", m.group(0)

    device_matches = []
    for pat in DEVICE_PATTERNS:
        m = re.search(pat, t, re.IGNORECASE)
        if m:
            device_matches.append(m.group(0))

    if len(device_matches) == 1:
        return True, "single_device_repro", device_matches[0]
    if len(device_matches) > 1:
        return True, "device", ", ".join(device_matches[:2])

    return False, "", ""


# ─────────────────────────────────────────────────────────────
# Reason map
# ─────────────────────────────────────────────────────────────
REASON_MAP = {
    "Gating": (
        "This bug makes one of BiP's core functions (messaging, calling, login) completely unusable, "
        "or contains a consistently reproducible crash. "
        "Must be resolved before the release can ship."
    ),
    "High": (
        "An important feature is affected but the app is not entirely unusable. "
        "The main flow is impaired — fix within 2 weeks. "
        "PO and QA Lead must evaluate whether the release can ship as-is."
    ),
    "Medium": (
        "A secondary function or UX issue. The user is impacted but a workaround exists "
        "or this is not a high-frequency flow. Fix within 6 weeks."
    ),
    "Low": (
        "Cosmetic or minor edge case. No functional impact — "
        "does not meaningfully affect user experience. Lowest priority."
    ),
}


# ─────────────────────────────────────────────────────────────
# Core decision logic
# ─────────────────────────────────────────────────────────────
def decide_priority(
    text: str,
    actual_result: str = "",
    expected_result: str = "",
) -> Tuple[str, bool, str, str, str]:
    """
    Returns (priority, is_scoped, scope_type, scope_detail, reason)
    
    Priority logic (BiP QA Manual):
    - Gating: core function broken OR reproducible crash OR fraud/data loss
    - High: important secondary feature broken, intermittent crashes
    - Medium: UI issues, rare crashes, partial features with workaround
    - Low: cosmetic, trivial
    
    Device scope can lower priority by one level (except if already Low).
    """
    combined = (text + " " + actual_result + " " + expected_result).lower()
    is_scoped, scope_type, scope_detail = detect_device_os_scope(combined)

    # ── Detect crash presence ────────────────────────────────
    has_crash = any(term in combined for term in HARD_CRASH_TERMS)
    has_freeze = any(term in combined for term in FREEZE_TERMS)
    
    # ── Check if crash is reproducible (Gating) or intermittent ──
    reproducible_crash_signals = [
        "her zaman", "her seferinde", "always", "consistently",
        "her açılışta", "every time", "100%", "belirli senaryo",
        "specific scenario", "force close", "uygulama açılmıyor",
    ]
    intermittent_crash_signals = [
        "bazen", "zaman zaman", "ara sıra", "nadir", "sometimes",
        "occasionally", "random", "rarely", "intermittent",
    ]
    
    is_reproducible_crash = has_crash and any(s in combined for s in reproducible_crash_signals)
    is_intermittent_crash = has_crash and any(s in combined for s in intermittent_crash_signals)
    # Crash with no qualifier → treat as reproducible (conservative)
    is_unqualified_crash = has_crash and not is_reproducible_crash and not is_intermittent_crash

    # ── Determine base priority ──────────────────────────────
    if any(term in combined for term in GATING_TERMS) or is_reproducible_crash or is_unqualified_crash:
        priority = "Gating"
        reason = REASON_MAP["Gating"]
    elif any(term in combined for term in HIGH_TERMS) or is_intermittent_crash:
        priority = "High"
        reason = REASON_MAP["High"]
    elif any(term in combined for term in MEDIUM_TERMS) or has_freeze:
        priority = "Medium"
        reason = REASON_MAP["Medium"]
    else:
        priority = "Low"
        reason = REASON_MAP["Low"]

    # ── Device scope adjustment ──────────────────────────────
    # Single device / low-end device repro → lower priority one level
    # High-end devices (flagship) → keep priority
    flagship_signals = ["iphone", "samsung galaxy s", "pixel", "flagship", "high end", "üst segment"]
    is_flagship = any(s in combined for s in flagship_signals)
    
    if is_scoped and not is_flagship and scope_type in ("single_device_repro", "device"):
        idx = PRIORITY_ORDER.index(priority)
        if idx < len(PRIORITY_ORDER) - 1:
            priority = PRIORITY_ORDER[idx + 1]
            reason += (
                f" ⚠ Reproduced only on specific device ({scope_detail}) — "
                f"priority lowered by one level. Should be escalated if confirmed on other devices."
            )
    elif is_scoped and scope_type == "os_version":
        reason += (
            f" ⚠ Seen only on OS version ({scope_detail}) — "
            f"limited impact, but worth monitoring if that OS version has wide adoption."
        )

    return priority, is_scoped, scope_type, scope_detail, reason
