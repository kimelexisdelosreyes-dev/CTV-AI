from app.core.context_requirements import ContextRequirements
from app.schemas.knowledge import KnowledgeSource
from app.services.knowledge_service import (
    _apply_total_prompt_budget,
    _select_knowledge_sources,
)


def source(index: int, text: str, score: float = 0.9) -> KnowledgeSource:
    return KnowledgeSource(
        document_id=f"doc-{index}",
        filename=f"doc-{index}.pdf",
        category="policy",
        chunk_index=index,
        page_number=index,
        text=text,
        score=score,
    )


def test_knowledge_chunk_limiting_and_duplicate_suppression() -> None:
    requirements = ContextRequirements(
        include_knowledge=True,
        max_knowledge_chunks=2,
        max_knowledge_chars=500,
    )
    sources = [
        source(1, "Approved leave policy applies to all employees."),
        source(2, "Approved leave policy applies to all employees."),
        source(3, "Overtime approvals require manager review."),
    ]

    selected, text, stats, truncated = _select_knowledge_sources(
        sources,
        requirements,
    )

    assert len(selected) == 2
    assert text.count("[Source") == 2
    assert stats["knowledge_chunks_original"] == 3
    assert stats["knowledge_chunks_final"] == 2
    assert truncated == []


def test_total_prompt_budget_truncates_context_sections() -> None:
    sections = [
        ("Knowledge Context", "K" * 1000),
        ("Operational Context", "O" * 1000),
        ("Employee Context", "E" * 1000),
    ]

    adjusted, truncated, applied = _apply_total_prompt_budget(
        system_prompt="system",
        sections=sections,
        question="What now?",
        max_chars=1300,
    )

    combined = "\n\n".join(content for _, content in adjusted)
    assert applied is True
    assert truncated
    assert len(combined) < 3000
