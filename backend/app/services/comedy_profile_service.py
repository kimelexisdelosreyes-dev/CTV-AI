import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.comedy_profile import ComedyProfile
from app.schemas.comedy import ComedyProfilePublic, ComedyProfileUpdate


def _decode_list(value: str) -> list[str]:
    try:
        decoded = json.loads(value)
        return decoded if isinstance(decoded, list) else []
    except json.JSONDecodeError:
        return []


def to_public(profile: ComedyProfile) -> ComedyProfilePublic:
    return ComedyProfilePublic(
        user_email=profile.user_email,
        preferred_language=profile.preferred_language,
        humor_level=profile.humor_level,
        likes=_decode_list(profile.likes_json),
        safe_roast_topics=_decode_list(profile.safe_roast_topics_json),
        off_limit_topics=_decode_list(profile.off_limit_topics_json),
        consent_to_roasting=profile.consent_to_roasting,
    )


async def get_profile(
    db: AsyncSession,
    user_email: str,
) -> ComedyProfile | None:
    result = await db.execute(
        select(ComedyProfile).where(ComedyProfile.user_email == user_email)
    )
    return result.scalar_one_or_none()


async def upsert_profile(
    db: AsyncSession,
    user_email: str,
    payload: ComedyProfileUpdate,
) -> ComedyProfile:
    profile = await get_profile(db, user_email)

    values = {
        "preferred_language": payload.preferred_language,
        "humor_level": payload.humor_level,
        "likes_json": json.dumps(payload.likes),
        "safe_roast_topics_json": json.dumps(payload.safe_roast_topics),
        "off_limit_topics_json": json.dumps(payload.off_limit_topics),
        "consent_to_roasting": payload.consent_to_roasting,
    }

    if profile is None:
        profile = ComedyProfile(user_email=user_email, **values)
        db.add(profile)
    else:
        for key, value in values.items():
            setattr(profile, key, value)

    await db.commit()
    await db.refresh(profile)
    return profile


def build_profile_context(profile: ComedyProfile | None) -> str:
    if profile is None:
        return (
            "No employee comedy profile is available. Use general workplace and "
            "multimedia humor. Do not target a specific employee."
        )

    public = to_public(profile)

    if not public.consent_to_roasting:
        roast_rule = (
            "The employee has not consented to personal roasting. Do not roast them. "
            "Use general humor only."
        )
    else:
        roast_rule = (
            "The employee consents to friendly roasting only within the approved "
            "safe roast topics."
        )

    return f"""
Employee comedy profile:
- Preferred language: {public.preferred_language}
- Humor level: {public.humor_level}
- Likes: {public.likes}
- Approved roast topics: {public.safe_roast_topics}
- Off-limits topics: {public.off_limit_topics}
- Consent to roasting: {public.consent_to_roasting}

Rules:
- {roast_rule}
- Never use any off-limits topic.
- Never infer additional private or sensitive traits.
""".strip()
