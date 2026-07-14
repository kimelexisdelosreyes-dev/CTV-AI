from app.db.models.employee import (
    DetailLevel,
    ExperienceLevel,
    MemoryStatus,
    MemoryVisibility,
    ResponseStyle,
)


def test_employee_enums() -> None:
    assert ExperienceLevel.advanced.value == "advanced"
    assert ResponseStyle.step_by_step.value == "step_by_step"
    assert DetailLevel.standard.value == "standard"
    assert MemoryVisibility.employee.value == "employee"
    assert MemoryStatus.confirmed.value == "confirmed"
