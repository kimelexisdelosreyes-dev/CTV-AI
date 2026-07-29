from app.enterprise_intelligence.contracts import MemoryContext, MemoryItem
class MemoryAdapter:
 def adapt(self, values)->MemoryContext:
  items=[]
  for value in values or ():
   if isinstance(value,MemoryItem): items.append(value); continue
   if isinstance(value,dict): items.append(MemoryItem(str(value.get("memory_id",value.get("id",""))),str(value.get("scope","employee")),str(value.get("content","")),float(value.get("confidence",0)),tuple((str(k),str(v)) for k,v in value.get("metadata",{}).items())))
   else: raise TypeError("unsupported memory result")
  return MemoryContext(tuple(items))
