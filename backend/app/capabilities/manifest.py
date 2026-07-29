from dataclasses import dataclass
from enum import StrEnum
class CapabilityVisibility(StrEnum): VISIBLE="visible"; HIDDEN="hidden"; MAINTENANCE="maintenance"; DISABLED="disabled"
@dataclass(frozen=True)
class CapabilityManifest:
 capability_id:str; display_name:str; description:str; owner:str; support_contact:str; category:str; maturity:str; visibility:CapabilityVisibility; lifecycle:str; rollout_state:str; feature_dependencies:tuple[str,...]=(); documentation:str=""; version:str="1.0"
