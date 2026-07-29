from .decision import ContextFilterResult
class DepartmentScopePolicy:
 def evaluate(self,items): return ContextFilterResult(tuple(items),(),"placeholder-accept-all")
class EmployeeScopePolicy(DepartmentScopePolicy): pass
