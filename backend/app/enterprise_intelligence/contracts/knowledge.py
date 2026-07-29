from dataclasses import asdict, dataclass
@dataclass(frozen=True)
class KnowledgeItem:
 source_id:str; title:str; content:str; source_type:str; metadata:tuple[tuple[str,str],...]=(); relevance:float|None=None
 def __post_init__(self):
  if not all(isinstance(v,str) for v in (self.source_id,self.title,self.content,self.source_type)) or not isinstance(self.metadata,tuple) or (self.relevance is not None and not isinstance(self.relevance,(int,float))): raise TypeError("invalid knowledge item")
@dataclass(frozen=True)
class KnowledgeContext:
 items:tuple[KnowledgeItem,...]=()
 def __post_init__(self):
  if not isinstance(self.items,tuple) or not all(isinstance(x,KnowledgeItem) for x in self.items): raise TypeError("invalid knowledge context")
 def to_dict(self): return asdict(self)
