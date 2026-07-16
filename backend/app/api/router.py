from fastapi import APIRouter

from app.api.routes import (
    auth,
    chat,
    comedy,
    connectors,
    developer,
    employee_admin,
    employees,
    health,
    infrastructure,
    knowledge,
    knowledge_dashboard,
    openai_compat,
    orchestrator,
    version,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(version.router)
api_router.include_router(infrastructure.router)
api_router.include_router(auth.router)
api_router.include_router(comedy.router)
api_router.include_router(employees.router)
api_router.include_router(employee_admin.router)
api_router.include_router(connectors.router)
api_router.include_router(developer.router)
api_router.include_router(knowledge.router)
api_router.include_router(orchestrator.router)
api_router.include_router(chat.router)

openai_router = APIRouter()
openai_router.include_router(openai_compat.router)

dashboard_router = APIRouter()
dashboard_router.include_router(knowledge_dashboard.router)
