from aiogram import Router, types
from aiogram.filters import Text
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from datetime import datetime

from ..database import Database
from ..keyboards import Keyboards
from ..messages import Messages
from ..states import UserStates
from ..utils import Utils

router = Router()
db = Database()

@router.callback_query(UserStates.service_selection, Text(startswith="toggle_service_"))
async def process_toggle_service(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора/отмены выбора услуги"""
    
    # Получаем ID услуги
    service_id = int(callback.data.split("_")[2])
    
    # Получаем язык пользователя
    user_data = await state.get_data()
    user_id = user_data.get('user_id')
    language = Utils.get_user_language(user_id) if user_id else 'ru'
    
    # Получаем текущие данные
    data = await state.get_data()
    current_category_id = data.get('current_category_id')
    selected_services = data.get('selected_services', [])
    
    # Добавляем или удаляем услугу из списка
    if service_id in selected_services:
        selected_services.remove(service_id)
    else:
        selected_services.append(service_id)
    
    # Обновляем состояние
    await state.update_data(selected_services=selected_services)
    
    # Получаем услуги в категории
    services = db.get_services_by_category(current_category_id, language)
    
    if not services:
        await callback.answer(Messages.get_error_message(language))
        return
    
    # Получаем информацию о категории
    category = db.get_category_by_id(current_category_id, language)
    category_title = category.get('title', '') if category else ''
    
    # Обновляем сообщение с новым списком услуг
    await callback.message.edit_text(
        Messages.get_services_message(language, category_title),
        reply_markup=Keyboards.get_services_keyboard(services, language, selected_services)
    )
    
    await callback.answer()

@router.callback_query(UserStates.service_selection, Text("finish_selection"))
async def process_finish_selection(callback: CallbackQuery, state: FSMContext):
    """Обработка завершения выбора услуг"""
    
    # Получаем язык пользователя
    user_data = await state.get_data()
    user_id = user_data.get('user_id')
    language = Utils.get_user_language(user_id) if user_id else 'ru'
    
    # Получаем выбранные услуги
    data = await state.get_data()
    selected_services = data.get('selected_services', [])
    
    if not selected_services:
        # Нет выбранных услуг
        await callback.answer(
            "Пожалуйста, выберите хотя бы одну услугу" if language == 'ru' else 
            "Please select at least one service" if language == 'en' else 
            "Lütfen en az bir hizmet seçin"
        )
        return
    
    # Сохраняем выбранные услуги
    await state.update_data(selected_services=selected_services)
    
    # Показываем сводку по выбранным услугам
    services_info = []
    total_price = 0
    
    for service_id in selected_services:
        service = db.get_service_by_id(service_id, language)
        if service:
            services_info.append(service)
            total_price += service.get('price', 0)
    
    await callback.message.edit_text(
        Messages.get_selected_services_message(language, services_info, total_price)
    )
    
    # Переходим к выбору даты
    await state.set_state(UserStates.date_selection)
    
    # Показываем календарь
    today = datetime.now()
    await callback.message.answer(
        Messages.get_date_selection_message(language),
        reply_markup=Keyboards.get_calendar_keyboard(today.year, today.month, language)
    )
    
    await callback.answer()

@router.callback_query(UserStates.service_selection, Text("select_date"))
async def process_select_date_direct(callback: CallbackQuery, state: FSMContext):
    """Прямой переход к выбору даты"""
    await process_finish_selection(callback, state)

@router.callback_query(UserStates.service_selection, Text("back_to_categories"))
async def process_back_from_services(callback: CallbackQuery, state: FSMContext):
    """Возврат из услуг к категориям"""
    
    # Получаем язык пользователя
    user_data = await state.get_data()
    user_id = user_data.get('user_id')
    language = Utils.get_user_language(user_id) if user_id else 'ru'
    
    # Получаем текущую категорию
    data = await state.get_data()
    current_category_id = data.get('current_category_id')
    
    # Получаем родительскую категорию текущей
    current_category = db.get_category_by_id(current_category_id, language) if current_category_id else None
    parent_id = current_category.get('parent_id') if current_category else None
    
    # Получаем категории на нужном уровне
    categories = db.get_categories(language, parent_id=parent_id)
    
    if not categories:
        # Возвращаем к корневым категориям
        categories = db.get_categories(language, parent_id=None)
        parent_id = None
    
    await state.set_state(UserStates.category_selection)
    await state.update_data(parent_category_id=parent_id)
    
    await callback.message.edit_text(
        Messages.get_categories_message(language),
        reply_markup=Keyboards.get_categories_keyboard(categories, language)
    )
    
    await callback.answer()

def register_service_handlers(dp):
    """Регистрация обработчиков услуг"""
    dp.include_router(router)