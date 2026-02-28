from .start import register_start_handlers
from .language import register_language_handlers
from .categories import register_category_handlers
from .services import register_service_handlers
from .masters import register_master_handlers
from .appointments import register_appointment_handlers
from .user_profile import register_user_profile_handlers

def register_all_handlers(dp):
    """Регистрация всех обработчиков"""
    register_start_handlers(dp)
    register_language_handlers(dp)
    register_category_handlers(dp)
    register_service_handlers(dp)
    register_master_handlers(dp)
    register_appointment_handlers(dp)
    register_user_profile_handlers(dp)