class CompanyBrainServiceError(RuntimeError):
    category = "service_unavailable"
    status_code = 503
    safe_detail = "Company Brain service is temporarily unavailable."

    def __init__(
        self,
        message: str | None = None,
        *,
        category: str | None = None,
        status_code: int | None = None,
        safe_detail: str | None = None,
        diagnostics: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message or safe_detail or self.safe_detail)
        if category is not None:
            self.category = category
        if status_code is not None:
            self.status_code = status_code
        if safe_detail is not None:
            self.safe_detail = safe_detail
        self.diagnostics = diagnostics or {}
