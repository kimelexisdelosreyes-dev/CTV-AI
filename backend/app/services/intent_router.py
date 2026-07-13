import re
from dataclasses import dataclass


@dataclass(frozen=True)
class IntentResult:
    assistant: str
    confidence: float
    reason: str


RULES: dict[str, tuple[str, ...]] = {
    "comedy": (
        "make me laugh",
        "tell me a joke",
        "joke",
        "roast me",
        "roast us",
        "roast the team",
        "burned out",
        "burnt out",
        "burnout",
        "stress break",
        "funny",
        "humor",
        "comedy",
        "team banter",
        "fake awards",
        "office jokes",
    ),
    "graphics": (
        "adobe firefly",
        "firefly prompt",
        "poster",
        "thumbnail",
        "branding",
        "graphic design",
        "photoshop",
        "after effects",
        "typography",
        "logo",
        "banner",
    ),
    "production": (
        "documentary",
        "shot list",
        "call sheet",
        "interview questions",
        "voice-over",
        "voice over",
        "cinematography",
        "davinci resolve",
        "premiere pro",
        "editing workflow",
        "production schedule",
        "storyboard",
        "b-roll",
        "b roll",
    ),
    "drone": (
        "drone",
        "aerial",
        "flight plan",
        "battery flight",
        "mavic",
        "dji",
        "no-fly",
        "no fly",
        "wind speed",
        "takeoff",
    ),
    "it": (
        "nas",
        "network",
        "docker",
        "windows",
        "postgresql",
        "qdrant",
        "server",
        "router",
        "switch",
        "smb",
        "storage",
        "backup",
        "ip address",
        "firewall",
    ),
    "coder": (
        "python",
        "powershell",
        "javascript",
        "typescript",
        "fastapi",
        "sqlalchemy",
        "api endpoint",
        "write code",
        "debug code",
        "stack trace",
        "github",
        "git ",
    ),
}


class IntentRouter:
    def route(self, message: str, override: str = "auto") -> IntentResult:
        if override != "auto":
            return IntentResult(
                assistant=override,
                confidence=1.0,
                reason="Manual assistant override",
            )

        normalized = re.sub(r"\s+", " ", message.lower()).strip()
        scores: dict[str, int] = {key: 0 for key in RULES}
        matched: dict[str, list[str]] = {key: [] for key in RULES}

        for assistant, phrases in RULES.items():
            for phrase in phrases:
                if phrase in normalized:
                    scores[assistant] += 1
                    matched[assistant].append(phrase)

        best_assistant = max(scores, key=scores.get)
        best_score = scores[best_assistant]

        if best_score == 0:
            return IntentResult(
                assistant="general",
                confidence=0.55,
                reason="No specialist keywords matched; using general assistant",
            )

        total_matches = sum(scores.values())
        confidence = min(0.98, 0.65 + (best_score / max(total_matches, 1)) * 0.3)

        return IntentResult(
            assistant=best_assistant,
            confidence=round(confidence, 2),
            reason=f"Matched: {', '.join(matched[best_assistant][:4])}",
        )


intent_router = IntentRouter()
