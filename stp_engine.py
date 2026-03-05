"""
STP Engine — BiP QA priority assignment.
Uses weighted signal scoring across categories instead of exact keyword matching.
Prevents over-assigning Low when no specific keyword matches.
"""

import re
from typing import Tuple, List

PRIORITY_ORDER = ["Gating", "High", "Medium", "Low"]

# ─────────────────────────────────────────────────────────────
# WEIGHTED SIGNALS
# (term, weight, bucket)  bucket: gating | high | medium | low
# Scoring: sum weights per bucket → highest bucket wins
# ─────────────────────────────────────────────────────────────
SIGNALS = [

    # ══════════════════════════════════════════
    # GATING — Core function completely broken
    # ══════════════════════════════════════════

    # Messaging core
    ("mesaj gönderilemiyor",        10, "gating"),
    ("mesaj gönderme çalışmıyor",   10, "gating"),
    ("mesaj atılamıyor",            10, "gating"),
    ("mesaj gönderilemedi",         10, "gating"),
    ("mesajlaşma çalışmıyor",       10, "gating"),
    ("chat açılmıyor",              10, "gating"),
    ("sohbet başlatılamıyor",       10, "gating"),
    ("mesaj iletilmiyor",            9, "gating"),
    ("message not sending",         10, "gating"),
    ("message send fail",           10, "gating"),
    ("cannot send message",         10, "gating"),
    ("messaging not working",       10, "gating"),
    ("chat not working",            10, "gating"),
    ("messages not delivered",       9, "gating"),

    # Calling core
    ("arama yapılamıyor",           10, "gating"),
    ("arama çalışmıyor",            10, "gating"),
    ("arama başlatılamıyor",        10, "gating"),
    ("sesli arama çalışmıyor",      10, "gating"),
    ("görüntülü arama çalışmıyor",  10, "gating"),
    ("call not working",            10, "gating"),
    ("call fails",                  10, "gating"),
    ("cannot start call",           10, "gating"),
    ("voice call broken",           10, "gating"),
    ("video call broken",           10, "gating"),
    ("call drops",                   8, "gating"),
    ("arama düşüyor",                8, "gating"),

    # Login / auth
    ("giriş yapılamıyor",           10, "gating"),
    ("uygulamaya girilemiyor",      10, "gating"),
    ("login olunmuyor",             10, "gating"),
    ("oturum açılamıyor",           10, "gating"),
    ("kayıt olunamıyor",            10, "gating"),
    ("doğrulama yapılamıyor",       10, "gating"),
    ("cannot login",                10, "gating"),
    ("login fails",                 10, "gating"),
    ("login fail",                  10, "gating"),
    ("app won't open",              10, "gating"),
    ("registration failed",         10, "gating"),
    ("otp gelmiyor",                10, "gating"),
    ("otp çalışmıyor",              10, "gating"),
    ("verification failed",         10, "gating"),
    ("sign in fails",               10, "gating"),

    # Reproducible crash
    ("her zaman crash",             10, "gating"),
    ("her seferinde crash",         10, "gating"),
    ("her açılışta crash",          10, "gating"),
    ("always crashes",              10, "gating"),
    ("consistently crashes",        10, "gating"),
    ("crash on every",              10, "gating"),
    ("reproducible crash",          10, "gating"),
    ("app crashes on launch",       10, "gating"),
    ("app crash on start",          10, "gating"),
    ("force close",                 10, "gating"),
    ("fatal error",                  9, "gating"),
    ("anr",                          8, "gating"),

    # Fraud / financial
    ("fraud",                       10, "gating"),
    ("maddi kayıp",                 10, "gating"),
    ("ücretlendirme hatası",        10, "gating"),
    ("faturalama hatası",           10, "gating"),
    ("para çekildi",                10, "gating"),
    ("ödeme hatası",                10, "gating"),
    ("billing error",               10, "gating"),
    ("unauthorized charge",         10, "gating"),
    ("payment error",               10, "gating"),

    # Data loss
    ("kalıcı veri kaybı",          10, "gating"),
    ("mesajlar silindi",            10, "gating"),
    ("veri kaybı",                  10, "gating"),
    ("permanent data loss",         10, "gating"),
    ("messages lost",               10, "gating"),
    ("data corruption",             10, "gating"),
    ("data loss",                   10, "gating"),

    # Core media send
    ("resim gönderilemiyor",         9, "gating"),
    ("video gönderilemiyor",         9, "gating"),
    ("dosya gönderilemiyor",         9, "gating"),
    ("medya gönderilemedi",          9, "gating"),
    ("image send fail",              9, "gating"),
    ("file send fail",               9, "gating"),
    ("media upload fails",           9, "gating"),

    # ══════════════════════════════════════════
    # HIGH — Important feature broken / impaired
    # ══════════════════════════════════════════

    # Intermittent core crashes
    ("bazen çalışmıyor",             7, "high"),
    ("zaman zaman crash",            7, "high"),
    ("arada crash",                  7, "high"),
    ("occasional crash",             7, "high"),
    ("intermittent crash",           7, "high"),
    ("sometimes fails",              7, "high"),
    ("sometimes crashes",            7, "high"),

    # Notifications
    ("bildirim gelmiyor",            8, "high"),
    ("bildirimler gelmiyor",         8, "high"),
    ("push notification çalışmıyor", 8, "high"),
    ("bildirimler çalışmıyor",       8, "high"),
    ("notification not working",     8, "high"),
    ("push notification fail",       8, "high"),
    ("notifications broken",         8, "high"),
    ("no notifications",             7, "high"),

    # Group features
    ("grup mesajı gönderilemiyor",   8, "high"),
    ("grup sohbeti açılmıyor",       8, "high"),
    ("group message fail",           8, "high"),
    ("group chat not working",       8, "high"),
    ("group call not working",       8, "high"),
    ("grup araması çalışmıyor",      8, "high"),

    # Story / status
    ("hikaye paylaşılamıyor",        7, "high"),
    ("story paylaşılamıyor",         7, "high"),
    ("story görüntülenemiyor",       7, "high"),
    ("story not loading",            7, "high"),
    ("story upload fail",            7, "high"),
    ("stories not working",          7, "high"),
    ("durum paylaşılamıyor",         7, "high"),

    # Media viewing
    ("resim açılmıyor",              8, "high"),
    ("video oynatılamıyor",          8, "high"),
    ("medya görüntülenemiyor",       8, "high"),
    ("image not loading",            8, "high"),
    ("video not playing",            8, "high"),
    ("media not loading",            8, "high"),
    ("photos not opening",           8, "high"),
    ("fotoğraf açılmıyor",           8, "high"),

    # Message sync / delivery
    ("mesajlar senkronize olmuyor",  7, "high"),
    ("mesajlar geç geliyor",         7, "high"),
    ("message sync fail",            7, "high"),
    ("messages not syncing",         7, "high"),
    ("messages delayed",             6, "high"),
    ("mesajlar gecikiyor",           6, "high"),

    # Contact / profile actions
    ("kişi eklenemiyor",             7, "high"),
    ("profil güncellenemiyor",       7, "high"),
    ("ayarlar kaydedilemiyor",       7, "high"),
    ("contact cannot be added",      7, "high"),
    ("profile update fail",          7, "high"),
    ("settings not saving",          7, "high"),
    ("cannot block user",            7, "high"),
    ("kullanıcı engellenemiyor",     7, "high"),

    # Sticker / reactions
    ("sticker gönderilemiyor",       6, "high"),
    ("sticker çalışmıyor",           6, "high"),
    ("emoji gönderilemiyor",         6, "high"),
    ("reactions not working",        6, "high"),
    ("tepki eklenemiyor",            6, "high"),

    # Audio / video quality in call
    ("ses gelmiyor",                 8, "high"),
    ("mikrofon çalışmıyor",          8, "high"),
    ("kamera çalışmıyor",            8, "high"),
    ("no audio",                     8, "high"),
    ("microphone not working",       8, "high"),
    ("camera not working",           8, "high"),
    ("black screen call",            8, "high"),
    ("görüntü gelmiyor",             8, "high"),

    # Search broken
    ("arama sonuçları gelmiyor",     7, "high"),
    ("kişi araması çalışmıyor",      7, "high"),
    ("search not working",           7, "high"),
    ("search returns nothing",       7, "high"),

    # Flagship device crash
    ("samsung crash",                7, "high"),
    ("iphone crash",                 7, "high"),
    ("flagship crash",               7, "high"),

    # ══════════════════════════════════════════
    # MEDIUM — Secondary UX issue, workaround exists
    # ══════════════════════════════════════════

    # UI functional errors
    ("yanlış görüntüleniyor",        5, "medium"),
    ("hatalı gösteriliyor",          5, "medium"),
    ("arayüz bozuk",                 5, "medium"),
    ("layout bozuk",                 5, "medium"),
    ("ekran bozuk",                  5, "medium"),
    ("incorrect display",            5, "medium"),
    ("wrong layout",                 5, "medium"),
    ("ui broken",                    5, "medium"),
    ("interface broken",             5, "medium"),
    ("screen glitch",                5, "medium"),
    ("görsel bozukluk",              5, "medium"),
    ("ui hatası",                    5, "medium"),
    ("ui error",                     5, "medium"),

    # Freeze / hang (not crash)
    ("donuyor",                      5, "medium"),
    ("takılıyor",                    5, "medium"),
    ("yanıt vermiyor",               5, "medium"),
    ("askıda kalıyor",               5, "medium"),
    ("freeze",                       5, "medium"),
    ("hangs",                        5, "medium"),
    ("stuck",                        5, "medium"),
    ("not responding",               5, "medium"),
    ("app freezes",                  5, "medium"),

    # Localization
    ("çeviri hatası",                4, "medium"),
    ("yanlış çeviri",                4, "medium"),
    ("dil sorunu",                   4, "medium"),
    ("lokalizasyon",                 4, "medium"),
    ("translation error",            4, "medium"),
    ("localization issue",           4, "medium"),
    ("wrong language",               4, "medium"),
    ("yanlış dil",                   4, "medium"),

    # Contact / search partial
    ("arama sonuçları yanlış",       5, "medium"),
    ("kişi bulunamıyor",             5, "medium"),
    ("contact search issue",         5, "medium"),
    ("search results wrong",         5, "medium"),
    ("yanlış sonuç",                 4, "medium"),

    # Read receipt / delivery
    ("okundu bilgisi gelmiyor",      4, "medium"),
    ("iletildi göstermiyor",         4, "medium"),
    ("read receipt missing",         4, "medium"),
    ("delivery status wrong",        4, "medium"),
    ("çift tık gelmiyor",            4, "medium"),

    # Rare / random crash
    ("nadir crash",                  5, "medium"),
    ("rare crash",                   5, "medium"),
    ("random crash",                 5, "medium"),
    ("ara sıra crash",               5, "medium"),
    ("crashes sometimes",            5, "medium"),

    # Performance
    ("yavaş yükleniyor",             4, "medium"),
    ("geç açılıyor",                 4, "medium"),
    ("gecikme var",                  4, "medium"),
    ("yavaş açılıyor",               4, "medium"),
    ("slow loading",                 4, "medium"),
    ("performance issue",            4, "medium"),
    ("lag",                          4, "medium"),
    ("geç yükleniyor",               4, "medium"),
    ("takes too long",               4, "medium"),
    ("uzun sürüyor",                 4, "medium"),

    # Settings minor
    ("ses ayarı çalışmıyor",         4, "medium"),
    ("titreşim çalışmıyor",          4, "medium"),
    ("tema değişmiyor",              4, "medium"),
    ("sound setting issue",          4, "medium"),
    ("vibration not working",        4, "medium"),
    ("dark mode not working",        4, "medium"),
    ("karanlık mod çalışmıyor",      4, "medium"),
    ("font size not changing",       4, "medium"),
    ("yazı boyutu değişmiyor",       4, "medium"),

    # Minor media
    ("küçük resim görünmüyor",       4, "medium"),
    ("thumbnail not showing",        4, "medium"),
    ("önizleme gelmiyor",            4, "medium"),
    ("preview not loading",          4, "medium"),

    # Workaround available
    ("workaround",                   3, "medium"),
    ("alternative path",             3, "medium"),
    ("farklı yoldan",                3, "medium"),

    # Badge / counter wrong
    ("bildirim sayısı yanlış",       4, "medium"),
    ("okunmamış sayısı hatalı",      4, "medium"),
    ("badge count wrong",            4, "medium"),
    ("unread count wrong",           4, "medium"),

    # ══════════════════════════════════════════
    # LOW — Purely cosmetic, zero functional impact
    # ══════════════════════════════════════════

    ("yazım hatası",                 2, "low"),
    ("typo",                         2, "low"),
    ("spelling error",               2, "low"),
    ("yanlış metin",                 2, "low"),
    ("wrong text",                   2, "low"),
    ("metin hatası",                 2, "low"),
    ("hizalama bozuk",               2, "low"),
    ("alignment issue",              2, "low"),
    ("spacing sorunu",               2, "low"),
    ("padding yanlış",               2, "low"),
    ("wrong spacing",                2, "low"),
    ("margin hatası",                2, "low"),
    ("renk yanlış",                  2, "low"),
    ("color wrong",                  2, "low"),
    ("wrong color",                  2, "low"),
    ("ikon yanlış",                  2, "low"),
    ("wrong icon",                   2, "low"),
    ("font sorunu",                  2, "low"),
    ("wrong font",                   2, "low"),
    ("font yanlış",                  2, "low"),
    ("placeholder hatalı",           2, "low"),
    ("wrong placeholder",            2, "low"),
    ("tooltip yanlış",               2, "low"),
    ("wrong tooltip",                2, "low"),
    ("label yanlış",                 2, "low"),
    ("wrong label",                  2, "low"),
    ("animasyon bozuk",              2, "low"),
    ("animation glitch",             2, "low"),
    ("geçiş animasyonu",             2, "low"),
    ("transition issue",             2, "low"),
    ("blink",                        1, "low"),
    ("gölge yanlış",                 1, "low"),
    ("border hatalı",                1, "low"),
    ("shadow wrong",                 1, "low"),
    ("border issue",                 1, "low"),
    ("eksik metin",                  2, "low"),
    ("missing text",                 2, "low"),
    ("boş alan görünüyor",           2, "low"),
    ("empty space",                  1, "low"),
    ("cosmetic",                     2, "low"),
    ("kozmetik",                     2, "low"),
]

# Export flat term lists for keyword highlighting in UI
GATING_TERMS       = [s[0] for s in SIGNALS if s[2] == "gating"]
HIGH_TERMS         = [s[0] for s in SIGNALS if s[2] == "high"]
MEDIUM_TERMS       = [s[0] for s in SIGNALS if s[2] == "medium"]
LOW_COSMETIC_TERMS = [s[0] for s in SIGNALS if s[2] == "low"]

HARD_CRASH_TERMS = [
    "crash", "force close", "çöküyor", "kapanıyor",
    "uygulama kapandı", "app closed", "fatal error", "anr",
]
FREEZE_TERMS = [
    "donuyor", "freeze", "takılıyor", "yanıt vermiyor",
    "askıda kalıyor", "hangs", "stuck", "not responding",
]

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
        "Purely cosmetic issue — typo, wrong color, alignment, or minor visual glitch. "
        "No functional impact. Lowest priority."
    ),
}


def detect_device_os_scope(text: str) -> Tuple[bool, str, str]:
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


DEVICE_PATTERNS = [
    r"\bredmi\s*\d+\b", r"\bxiaomi\b", r"\bsamsung\s+[a-z]\d+", r"\bhuawei\b",
    r"\biphone\s*\d+\b", r"\bpixel\s*\d+\b", r"\boneplus\b", r"\boppo\b",
    r"\brealme\b", r"\bvivo\b", r"\bnokia\b", r"\blg\b",
    r"\bpoco\b", r"\bmoto\b", r"\bmotorola\b", r"\bgalaxy\s+[a-z]\d+\b",
]
OS_PATTERNS = [
    r"\bandroid\s*\d+", r"\bios\s*\d+", r"\bmiui\s*\d+",
    r"\bone\s*ui\s*\d+", r"\bharmonyos\b", r"\bcoloros\b",
]
CHIPSET_PATTERNS = [
    r"\bsnapdragon\s*\d+", r"\bexynos\s*\d+", r"\bdimensity\s*\d+",
    r"\bkirin\s*\d+", r"\ba\d+\s*chip\b", r"\bbionic\b",
    r"\bmediatek\b", r"\bhelio\b",
]


def _score(text: str) -> dict:
    t = text.lower()
    scores = {"gating": 0, "high": 0, "medium": 0, "low": 0}
    for term, weight, bucket in SIGNALS:
        if term in t:
            scores[bucket] += weight
    return scores


def decide_priority(
    text: str,
    actual_result: str = "",
    expected_result: str = "",
) -> Tuple[str, bool, str, str, str]:
    """
    Returns (priority, is_scoped, scope_type, scope_detail, reason)
    Scoring: sum signal weights per bucket → highest bucket wins.
    Default on zero signal → Medium (unknown, needs investigation).
    """
    combined = (text + " " + actual_result + " " + expected_result).lower()
    is_scoped, scope_type, scope_detail = detect_device_os_scope(combined)

    # ── Crash qualifier ──────────────────────────────────────
    has_crash = any(term in combined for term in HARD_CRASH_TERMS)
    reproducible_signals = [
        "her zaman", "her seferinde", "always", "consistently",
        "every time", "100%", "force close", "uygulama açılmıyor",
        "app crash on start", "app crashes on launch",
    ]
    intermittent_signals = [
        "bazen", "zaman zaman", "ara sıra", "nadir", "sometimes",
        "occasionally", "random", "rarely", "intermittent",
    ]
    if has_crash:
        is_repro = any(s in combined for s in reproducible_signals)
        is_intermit = any(s in combined for s in intermittent_signals)
        if is_repro:
            combined += " reproducible crash always crashes"
        elif is_intermit:
            combined += " intermittent crash"
        else:
            combined += " reproducible crash always crashes"  # conservative

    # ── Score ────────────────────────────────────────────────
    scores = _score(combined)
    total_signal = sum(scores.values())

    if total_signal == 0:
        priority = "Medium"
        reason = (
            "No specific keyword signals matched. Defaulting to Medium — "
            "the description suggests a functional problem worth investigating. "
            "Please review and adjust manually if needed."
        )
        return priority, is_scoped, scope_type, scope_detail, reason

    bucket_order = ["gating", "high", "medium", "low"]
    best_bucket = max(bucket_order, key=lambda b: (scores[b], -bucket_order.index(b)))

    # Pure cosmetic → stay Low. Only bump if mixed with functional signals.
    if best_bucket == "low" and (scores["gating"] + scores["high"] + scores["medium"]) > 0:
        best_bucket = max(["gating", "high", "medium"],
                          key=lambda b: (scores[b], -["gating","high","medium"].index(b)))

    priority_map = {"gating": "Gating", "high": "High", "medium": "Medium", "low": "Low"}
    priority = priority_map[best_bucket]
    reason = REASON_MAP[priority]

    sig_parts = [f"{b.capitalize()}: {scores[b]}" for b in bucket_order if scores[b] > 0]
    if sig_parts:
        reason += f" [Scores — {' · '.join(sig_parts)}]"

    # ── Device scope adjustment ──────────────────────────────
    flagship_signals = ["iphone", "samsung galaxy s", "pixel", "flagship"]
    is_flagship = any(s in combined for s in flagship_signals)

    if is_scoped and not is_flagship and scope_type in ("single_device_repro", "device"):
        idx = PRIORITY_ORDER.index(priority)
        if idx < len(PRIORITY_ORDER) - 1:
            priority = PRIORITY_ORDER[idx + 1]
            reason += (
                f" ⚠ Reproduced only on specific device ({scope_detail}) — "
                f"priority lowered by one level. Escalate if confirmed on other devices."
            )
    elif is_scoped and scope_type == "os_version":
        reason += (
            f" ⚠ Seen only on OS version ({scope_detail}) — "
            f"limited impact, but monitor if that OS has wide adoption."
        )

    return priority, is_scoped, scope_type, scope_detail, reason
