from app.enterprise_intelligence.contracts import ContextBudget
from .decision import BudgetResult
class ContextBudgetPolicy:
 def apply(self, characters:int,budget:ContextBudget): return BudgetResult(max(0,budget.max_total_characters-characters),min(characters,budget.max_total_characters),characters>budget.max_total_characters)
