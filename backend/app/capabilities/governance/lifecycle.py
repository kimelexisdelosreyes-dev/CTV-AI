from dataclasses import dataclass
from enum import StrEnum
class CapabilityLifecycle(StrEnum): REGISTERED="registered"; VALIDATED="validated"; AVAILABLE="available"; DISABLED="disabled"; DEPRECATED="deprecated"
