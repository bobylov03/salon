import logging
from aiogram import Router, types
from aiogram.filters import Text
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InputMediaPhoto
from datetime import datetime, date

from ..database import Database
from ..keyboards import Keyboards
from ..messages import Messages
from ..states import UserStates
from ..utils import Utils

router = Router()
db = Database()
logger = logging.getLogger(__name__)

# Обработчики календаря
@router.callback_query(UserStates.date_selection, Text(startswith="change_month_"))
async def process_change_month(callback: CallbackQuery, state: FSMContext):
    """Смена месяца в календаре"""
    
    # Получаем язык пользователя
    user_data = await state.get_data()
    user_id = user_data.get('user_id')
    language = Utils.get_user_language(user_id) if user_id else 'ru'
    
    # Получаем год и месяц
    _, year_str, month_str = callback.data.split("_")
    year = int(year_str)
    month = int(month_str)
    
    # Обновляем календарь
    await callback.message.edit_reply_markup(
        reply_markup=Keyboards.get_calendar_keyboard(year, month, language)
    )
    
    await callback.answer()

@router.callback_query(UserStates.date_selection, Text(startswith="select_date_"))
async def process_select_date(callback: CallbackQuery, state: FSMContext):
    """Выбор даты из календаря"""
    
    # Получаем язык пользователя
    user_data = await state.get_data()
    user_id = user_data.get('user_id')
    language = Utils.get_user_language(user_id) if user_id else 'ru'
    
    # Получаем выбранную дату
    date_str = callback.data.split("_")[2]
    appointment_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    
    # Проверяем, что дата не в прошлом
    today = date.today()
    if appointment_date < today:
        await callback.answer(
            "Нельзя выбрать прошедшую дату" if language == 'ru' else
            "Cannot select past date" if language == 'en' else
            "Geçmiş tarih seçilemez"
        )
        return
    
    # Сохраняем выбранную дату
    await state.update_data(appointment_date=appointment_date.isoformat())
    
    # Переходим к выбору мастера
    await state.set_state(UserStates.master_choice)
    
    await callback.message.edit_text(
        Messages.get_master_choice_message(language),
        reply_markup=Keyboards.get_master_choice_keyboard(language)
    )
    
    await callback.answer()

@router.callback_query(UserStates.date_selection, Text("select_today"))
async def process_select_today(callback: CallbackQuery, state: FSMContext):
    """Выбор сегодняшней даты"""
    
    # Получаем язык пользователя
    user_data = await state.get_data()
    user_id = user_data.get('user_id')
    language = Utils.get_user_language(user_id) if user_id else 'ru'
    
    # Устанавливаем сегодняшнюю дату
    today = date.today()
    
    # Сохраняем дату
    await state.update_data(appointment_date=today.isoformat())
    
    # Переходим к выбору мастера
    await state.set_state(UserStates.master_choice)
    
    await callback.message.edit_text(
        Messages.get_master_choice_message(language),
        reply_markup=Keyboards.get_master_choice_keyboard(language)
    )
    
    await callback.answer()

@router.callback_query(UserStates.date_selection, Text("back_to_services"))
async def process_back_to_services_from_date(callback: CallbackQuery, state: FSMContext):
    """Возврат от даты к услугам"""
    
    # Получаем язык пользователя
    user_data = await state.get_data()
    user_id = user_data.get('user_id')
    language = Utils.get_user_language(user_id) if user_id else 'ru'
    
    # Получаем текущую категорию и выбранные услуги
    data = await state.get_data()
    current_category_id = data.get('current_category_id')
    selected_services = data.get('selected_services', [])
    
    # Получаем услуги в категории
    services = db.get_services_by_category(current_category_id, language)
    
    if not services:
        await callback.answer(Messages.get_error_message(language))
        return
    
    # Получаем информацию о категории
    category = db.get_category_by_id(current_category_id, language)
    category_title = category.get('title', '') if category else ''
    
    # Возвращаемся к выбору услуг
    await state.set_state(UserStates.service_selection)
    
    await callback.message.edit_text(
        Messages.get_services_message(language, category_title),
        reply_markup=Keyboards.get_services_keyboard(services, language, selected_services)
    )
    
    await callback.answer()

# Обработчики выбора мастера
@router.callback_query(UserStates.master_choice, Text("choose_master"))
async def process_choose_master(callback: CallbackQuery, state: FSMContext):
    """Выбор конкретного мастера"""
    
    # Получаем язык пользователя
    user_data = await state.get_data()
    user_id = user_data.get('user_id')
    language = Utils.get_user_language(user_id) if user_id else 'ru'
    
    # Получаем выбранные услуги и дату
    data = await state.get_data()
    selected_services = data.get('selected_services', [])
    appointment_date_str = data.get('appointment_date')
    
    if not selected_services or not appointment_date_str:
        await callback.answer(Messages.get_error_message(language))
        return
    
    # Ищем мастеров, которые предоставляют ВСЕ выбранные услуги
    all_masters = {}

    logger.info(f"[choose_master] selected_services={selected_services}, date={appointment_date_str}")

    for service_id in selected_services:
        masters_for_service = db.get_masters_for_service(service_id)
        logger.info(f"[choose_master] service_id={service_id} → masters={[m.get('id') for m in masters_for_service]}")

        for master in masters_for_service:
            master_id = master['id']
            if master_id not in all_masters:
                all_masters[master_id] = {
                    'master': master,
                    'services_count': 1
                }
            else:
                all_masters[master_id]['services_count'] += 1

    # Фильтруем мастеров, которые предоставляют все услуги
    suitable_masters = []
    for master_id, data in all_masters.items():
        if data['services_count'] == len(selected_services):
            suitable_masters.append(data['master'])

    logger.info(f"[choose_master] all_masters={list(all_masters.keys())}, suitable_masters={[m.get('id') for m in suitable_masters]}")

    if not suitable_masters:
        await callback.message.edit_text(
            Messages.get_no_masters_message(language),
            reply_markup=Keyboards.get_master_choice_keyboard(language)
        )
        return
    
    # Сохраняем список подходящих мастеров
    await state.update_data(suitable_masters=[m['id'] for m in suitable_masters])
    
    # Переходим к выбору мастера
    await state.set_state(UserStates.master_selection)
    
    await callback.message.edit_text(
        Messages.get_masters_list_message(language),
        reply_markup=Keyboards.get_masters_keyboard(suitable_masters, language)
    )
    
    await callback.answer()

@router.callback_query(UserStates.master_choice, Text("any_master"))
async def process_any_master(callback: CallbackQuery, state: FSMContext):
    """Выбор любого доступного мастера"""
    
    # Получаем язык пользователя
    user_data = await state.get_data()
    user_id = user_data.get('user_id')
    language = Utils.get_user_language(user_id) if user_id else 'ru'
    
    # Получаем выбранные услуги и дату
    data = await state.get_data()
    selected_services = data.get('selected_services', [])
    appointment_date_str = data.get('appointment_date')
    
    if not selected_services or not appointment_date_str:
        await callback.answer(Messages.get_error_message(language))
        return
    
    appointment_date = date.fromisoformat(appointment_date_str)
    
    # Получаем доступные временные слоты для любого мастера
    time_slots_data = Utils.get_available_time_slots_for_services(
        selected_services, appointment_date, master_id=None
    )
    
    if not time_slots_data:
        await callback.message.edit_text(
            Messages.get_no_time_slots_message(language),
            reply_markup=Keyboards.get_master_choice_keyboard(language)
        )
        return
    
    # Извлекаем только временные слоты
    time_slots = [item['time'] for item in time_slots_data]
    
    # Сохраняем информацию, что выбран "любой мастер"
    await state.update_data(master_id=None)
    
    # Переходим к выбору времени
    await state.set_state(UserStates.time_selection)
    
    await callback.message.edit_text(
        Messages.get_time_selection_message(language, appointment_date_str),
        reply_markup=Keyboards.get_time_slots_keyboard(time_slots, language)
    )
    
    await callback.answer()

@router.callback_query(UserStates.master_choice, Text("back_to_date"))
async def process_back_to_date(callback: CallbackQuery, state: FSMContext):
    """Возврат от выбора мастера к выбору даты"""
    
    # Получаем язык пользователя
    user_data = await state.get_data()
    user_id = user_data.get('user_id')
    language = Utils.get_user_language(user_id) if user_id else 'ru'
    
    # Переходим к выбору даты
    await state.set_state(UserStates.date_selection)
    
    # Показываем календарь текущего месяца
    today = datetime.now()
    await callback.message.edit_text(
        Messages.get_date_selection_message(language),
        reply_markup=Keyboards.get_calendar_keyboard(today.year, today.month, language)
    )
    
    await callback.answer()

# Обработчики выбора конкретного мастера
@router.callback_query(UserStates.master_selection, Text(startswith="select_master_"))
async def process_select_specific_master(callback: CallbackQuery, state: FSMContext):
    """Выбор конкретного мастера"""
    
    # Получаем ID мастера
    master_id = int(callback.data.split("_")[2])
    
    # Получаем язык пользователя
    user_data = await state.get_data()
    user_id = user_data.get('user_id')
    language = Utils.get_user_language(user_id) if user_id else 'ru'
    
    # Получаем выбранные услуги и дату
    data = await state.get_data()
    selected_services = data.get('selected_services', [])
    appointment_date_str = data.get('appointment_date')
    suitable_masters = data.get('suitable_masters', [])
    
    if not selected_services or not appointment_date_str or master_id not in suitable_masters:
        await callback.answer(Messages.get_error_message(language))
        return
    
    appointment_date = date.fromisoformat(appointment_date_str)
    
    # Получаем информацию о мастере
    master = db.get_master_by_id(master_id)
    if not master:
        await callback.answer(Messages.get_error_message(language))
        return
    
    # Получаем доступные временные слоты для этого мастера
    total_duration = Utils.calculate_total_duration(selected_services)
    time_slots = db.get_available_time_slots(master_id, appointment_date, total_duration)
    
    if not time_slots:
        await callback.message.edit_text(
            Messages.get_no_time_slots_message(language),
            reply_markup=Keyboards.get_masters_keyboard([], language)
        )
        return
    
    # Сохраняем ID мастера
    await state.update_data(master_id=master_id)
    
    # Переходим к выбору времени
    await state.set_state(UserStates.time_selection)
    
    master_name = f"{master.get('first_name', '')} {master.get('last_name', '')}".strip()
    
    await callback.message.edit_text(
        Messages.get_time_selection_message(language, appointment_date_str, master_name),
        reply_markup=Keyboards.get_time_slots_keyboard(time_slots, language)
    )
    
    await callback.answer()

@router.callback_query(UserStates.master_selection, Text("back_to_master_choice"))
async def process_back_to_master_choice(callback: CallbackQuery, state: FSMContext):
    """Возврат от выбора конкретного мастера к выбору типа"""
    
    # Получаем язык пользователя
    user_data = await state.get_data()
    user_id = user_data.get('user_id')
    language = Utils.get_user_language(user_id) if user_id else 'ru'
    
    # Возвращаемся к выбору типа записи
    await state.set_state(UserStates.master_choice)
    
    await callback.message.edit_text(
        Messages.get_master_choice_message(language),
        reply_markup=Keyboards.get_master_choice_keyboard(language)
    )
    
    await callback.answer()

def register_master_handlers(dp):
    """Регистрация обработчиков мастеров"""
    dp.include_router(router)