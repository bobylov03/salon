from aiogram.fsm.state import State, StatesGroup

class UserStates(StatesGroup):
    """Состояния для пользователей"""
    
    # Выбор языка
    language_selection = State()
    
    # Главное меню
    main_menu = State()
    
    # Выбор категорий и услуг
    category_selection = State()
    service_selection = State()
    
    # Выбор даты
    date_selection = State()
    
    # Выбор мастера
    master_choice = State()  # Выбор типа (мастер/любой)
    master_selection = State()  # Выбор конкретного мастера
    
    # Выбор времени
    time_selection = State()
    
    # Подтверждение записи
    appointment_confirmation = State()
    
    # Просмотр записей
    my_appointments = State()
    appointment_detail = State()
    
    # Перенос записи
    reschedule_date = State()
    reschedule_time = State()
    reschedule_confirmation = State()

class MasterStates(StatesGroup):
    """Состояния для мастеров"""
    
    # Главное меню мастера
    main_menu = State()
    
    # Просмотр записей
    view_appointments = State()
    select_appointment_date = State()