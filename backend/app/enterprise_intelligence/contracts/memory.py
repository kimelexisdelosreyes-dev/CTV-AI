from dataclasses import asdict, dataclass
@dataclass(frozen=True)
class MemoryItem:
 memory_id:str; scope:str; content:str; confidence:float; metadata:tuple[tuple[str,str],...]=()
 def __post_init__(self):
  if not all(isinstance(v,str) for v in (self.memory_id,self.scope,self.content)) or not isinstance(self.confidence,(int,float)) or not 0<=self.confidence<=1: raise TypeError("invalid memory item")
@dataclass(frozen=True)
class MemoryContext:
 items:tuple[MemoryItem,...]=()
 def __post_init__(self):
  if not isinstance(self.items,tuple) or not all(isinstance(x,MemoryItem) for x in self.items): raise TypeError("invalid memory context")
 def to_dict(self): return asdict(self)
