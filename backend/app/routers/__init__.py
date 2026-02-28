# backend/app/routers/__init__.py
from .analytics import router as analytics_router
from .appointments import router as appointments_router
from .clients import router as clients_router
from .masters import router as masters_router
from .services import router as services_router
from .bonuses import router as bonuses_router
from .schedule import router as schedule_router
from .admin_logs import router as admin_logs_router

__all__ = [
    'analytics_router',
    'appointments_router',
    'clients_router',
    'masters_router',
    'services_router',
    'bonuses_router',
    'schedule_router',
    'admin_logs_router',
]