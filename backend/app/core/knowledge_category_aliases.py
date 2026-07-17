from __future__ import annotations


CATEGORY_ALIASES: dict[str, tuple[str, ...]] = {
    "brand-guidelines": ("branding",),
    "project-references": ("branding",),
    "equipment-manuals": ("cameras",),
    "technical-documentation": ("cameras", "editing"),
    "production-sops": ("editing",),
    "training-materials": ("cameras", "editing"),
    "company-policy": ("company-policies",),
    "company-policies": ("company-policies",),
    "hr-policies": ("hr-policies",),
}


def resolve_category_alias(category: str | None) -> tuple[str | None, ...]:
    if category is None:
        return (None,)

    normalized = category.strip().lower()
    if not normalized:
        return (None,)

    return CATEGORY_ALIASES.get(normalized, (normalized,))


def resolved_category_label(requested: str | None, resolved: str | None) -> str | None:
    if requested is None:
        return None
    if resolved is None or requested == resolved:
        return requested
    return f"{requested}->{resolved}"
