from app.prompt_engine.contracts import PromptStage


class PromptStageRegistry:
    """An immutable, deterministic stage sequence with no dynamic registration."""
    def __init__(self, stages: tuple[PromptStage, ...]) -> None:
        if not isinstance(stages, tuple):
            raise TypeError("stages must be an immutable tuple")
        stage_ids = tuple(stage.stage_id for stage in stages)
        if len(set(stage_ids)) != len(stage_ids):
            raise ValueError("duplicate prompt stage id")
        self._stages = stages
        self._stage_ids = stage_ids

    @property
    def stages(self) -> tuple[PromptStage, ...]:
        return self._stages

    @property
    def stage_ids(self) -> tuple[str, ...]:
        return self._stage_ids
