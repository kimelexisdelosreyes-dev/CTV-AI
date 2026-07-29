class KnowledgeSelectionPolicy:
 def select(self,items): return tuple(items)
class MemorySelectionPolicy(KnowledgeSelectionPolicy): pass
class SourcePriorityPolicy:
 def order(self,items): return tuple(items)
