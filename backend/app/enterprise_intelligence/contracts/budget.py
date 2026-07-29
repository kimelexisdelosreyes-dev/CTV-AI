from dataclasses import dataclass
@dataclass(frozen=True)
class ContextBudget:
 max_knowledge_items:int=4; max_memory_items:int=4; max_total_characters:int=4000; per_source_characters:int=2000
 def __post_init__(self):
  if any(not isinstance(x,int) or x<0 for x in (self.max_knowledge_items,self.max_memory_items,self.max_total_characters,self.per_source_characters)): raise TypeError("invalid context budget")
