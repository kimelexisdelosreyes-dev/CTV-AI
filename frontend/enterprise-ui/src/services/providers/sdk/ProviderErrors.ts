export class ProviderError extends Error { constructor(message: string, readonly code: string, options?: { cause?: unknown }) { super(message, options); this.name = "ProviderError"; } }
export class ProviderTimeoutError extends ProviderError { constructor(message = "Provider timed out") { super(message, "PROVIDER_TIMEOUT"); this.name = "ProviderTimeoutError"; } }
export class ProviderConfigurationError extends ProviderError { constructor(message: string) { super(message, "PROVIDER_CONFIGURATION"); this.name = "ProviderConfigurationError"; } }
export class ProviderUnavailableError extends ProviderError { constructor(message = "Provider unavailable") { super(message, "PROVIDER_UNAVAILABLE"); this.name = "ProviderUnavailableError"; } }
export class ProviderUnauthorizedError extends ProviderError { constructor(message = "Provider unauthorized") { super(message, "PROVIDER_UNAUTHORIZED"); this.name = "ProviderUnauthorizedError"; } }
export class ProviderCancelledError extends ProviderError { constructor(message = "Provider cancelled") { super(message, "PROVIDER_CANCELLED"); this.name = "ProviderCancelledError"; } }
export class ProviderExecutionError extends ProviderError { constructor(message = "Provider execution failed", options?: { cause?: unknown }) { super(message, "PROVIDER_EXECUTION", options); this.name = "ProviderExecutionError"; } }
