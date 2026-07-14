from dataclasses import dataclass


@dataclass(frozen=True)
class KnowledgeCollection:
    slug: str
    name: str
    description: str
    icon: str
    employee_visible: bool = True


KNOWLEDGE_COLLECTIONS: tuple[KnowledgeCollection, ...] = (
    KnowledgeCollection(
        slug="company-policies",
        name="Company Policies",
        description="Approved company-wide rules, governance, and operating policies.",
        icon="building",
    ),
    KnowledgeCollection(
        slug="hr-policies",
        name="HR Policies",
        description="Leave, attendance, benefits, conduct, and employee guidance.",
        icon="users",
    ),
    KnowledgeCollection(
        slug="production-sops",
        name="Production SOPs",
        description="Shoot preparation, ingestion, editing, delivery, and archive workflows.",
        icon="clapperboard",
    ),
    KnowledgeCollection(
        slug="equipment-manuals",
        name="Equipment Manuals",
        description="Camera, lighting, audio, drone, computer, and equipment manuals.",
        icon="camera",
    ),
    KnowledgeCollection(
        slug="brand-guidelines",
        name="Brand Guidelines",
        description="CTV ONE and ChinoyTV identity, visual, tone, and messaging standards.",
        icon="palette",
    ),
    KnowledgeCollection(
        slug="technical-documentation",
        name="Technical Documentation",
        description="Infrastructure, NAS, networking, software, and systems documentation.",
        icon="server",
    ),
    KnowledgeCollection(
        slug="training-materials",
        name="Training Materials",
        description="Internal learning guides, onboarding materials, and tutorials.",
        icon="graduation-cap",
    ),
    KnowledgeCollection(
        slug="project-references",
        name="Project References",
        description="Approved treatments, research, briefs, and reusable project references.",
        icon="folder",
    ),
    KnowledgeCollection(
        slug="general",
        name="General Archive",
        description="Legacy or uncategorized documents awaiting collection assignment.",
        icon="archive",
    ),
)


def collection_slugs() -> set[str]:
    return {item.slug for item in KNOWLEDGE_COLLECTIONS}


def normalize_collection(value: str | None) -> str | None:
    if value is None:
        return None

    cleaned = value.strip().lower()

    if not cleaned:
        return None

    aliases = {
        "policies": "company-policies",
        "company policy": "company-policies",
        "hr": "hr-policies",
        "manuals": "equipment-manuals",
        "equipment": "equipment-manuals",
        "sop": "production-sops",
        "sops": "production-sops",
        "branding": "brand-guidelines",
        "technical": "technical-documentation",
        "training": "training-materials",
        "projects": "project-references",
    }

    return aliases.get(cleaned, cleaned)
