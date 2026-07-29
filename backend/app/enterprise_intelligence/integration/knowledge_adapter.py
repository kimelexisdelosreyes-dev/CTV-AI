from app.enterprise_intelligence.contracts import KnowledgeContext, KnowledgeItem
class KnowledgeAdapter:
 def adapt(self, values)->KnowledgeContext:
  items=[]
  for value in values or ():
   if isinstance(value,KnowledgeItem): items.append(value); continue
   if isinstance(value,dict): items.append(KnowledgeItem(str(value.get("source_id",value.get("id",""))),str(value.get("title","")),str(value.get("content","")),str(value.get("source_type","knowledge")),tuple((str(k),str(v)) for k,v in value.get("metadata",{}).items()),value.get("relevance")))
   else: raise TypeError("unsupported knowledge result")
  return KnowledgeContext(tuple(items))
