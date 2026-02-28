from aiogram import Router, types
from aiogram.filters import Text
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from ..database import Database
from ..keyboards import Keyboards
from ..messages import Messages
from ..states import UserStates
from ..utils import Utils

router = Router()
db = Database()

@router.message(UserStates.main_menu)
@router.message(Text(text=[
    "💇 Записаться на услугу", 
    "💇 Book a Service", 
    "💇 Randevu Al",
    "⬅️ Главное меню",
    "⬅️ Main Menu",
    "⬅️ Ana Menü"
]))
async def process_book_service(message: types.Message, state: FSMContext):
    """Обработка нажатия кнопки 'Записаться на услугу'"""
    
    # Получаем язык пользователя
    user_data = await state.get_data()
    user_id = user_data.get('user_id')
    language = Utils.get_user_language(user_id) if user_id else 'ru'
    
    # Получаем категории верхнего уровня
    categories = db.get_categories(language, parent_id=None)
    
    if not categories:
        await message.answer(Messages.get_no_categories_message(language))
        return
    
    # Переходим в состояние выбора категории
    await state.set_state(UserStates.category_selection)
    
    # Сохраняем родительскую категорию (None для корневых)
    await state.update_data(parent_category_id=None)
    
    # Показываем категории
    await message.answer(
        Messages.get_categories_message(language),
        reply_markup=Keyboards.get_categories_keyboard(categories, language)
    )

@router.callback_query(UserStates.category_selection, Text(startswith="category_"))
async def process_category_selection(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора категории"""
    
    # Получаем ID выбранной категории
    category_id = int(callback.data.split("_")[1])
    
    # Получаем язык пользователя
    user_data = await state.get_data()
    user_id = user_data.get('user_id')
    language = Utils.get_user_language(user_id) if user_id else 'ru'
    
    # Получаем информацию о категории
    category = db.get_category_by_id(category_id, language)
    
    if not category:
        await callback.answer(Messages.get_error_message(language))
        return
    
    # Проверяем, есть ли подкатегории
    subcategories = db.get_categories(language, parent_id=category_id)
    
    if subcategories:
        # Есть подкатегории - показываем их
        await state.update_data(parent_category_id=category_id)
        
        await callback.message.edit_text(
            Messages.get_categories_message(language),
            reply_markup=Keyboards.get_categories_keyboard(subcategories, language)
        )
    else:
        # Нет подкатегорий - переходим к выбору услуг
        await state.update_data(
            current_category_id=category_id,
            selected_services=[]  # Сбрасываем выбранные услуги
        )
        await state.set_state(UserStates.service_selection)
        
        # Получаем услуги в этой категории
        services = db.get_services_by_category(category_id, language)
        
        if not services:
            await callback.message.edit_text(
                Messages.get_no_services_message(language),
                reply_markup=Keyboards.get_categories_keyboard([], language)
            )
            return
        
        await callback.message.edit_text(
            Messages.get_services_message(language, category.get('title', '')),
            reply_markup=Keyboards.get_services_keyboard(services, language, [])
        )
    
    await callback.answer()

@router.callback_query(UserStates.category_selection, Text("back_to_categories"))
async def process_back_to_categories(callback: CallbackQuery, state: FSMContext):
    """Обработка кнопки 'Назад' в категориях"""
    
    # Получаем язык пользователя
    user_data = await state.get_data()
    user_id = user_data.get('user_id')
    language = Utils.get_user_language(user_id) if user_id else 'ru'
    
    # Получаем текущую родительскую категорию
    data = await state.get_data()
    parent_category_id = data.get('parent_category_id')
    
    if parent_category_id is None:
        # Уже на корневом уровне - возвращаем в главное меню
        await state.set_state(UserStates.main_menu)
        await callback.message.edit_text(
            Messages.get_language_set_message(language),
            reply_markup=Keyboards.get_main_menu_keyboard(language)
        )
    else:
        # Получаем родительскую категорию текущей
        parent_category = db.get_category_by_id(parent_category_id, language)
        
        if parent_category:
            # Получаем родительскую категорию родителя
            grandparent_id = parent_category.get('parent_id')
            
            # Получаем категории на этом уровне
            categories = db.get_categories(language, parent_id=grandparent_id)
            
            await state.update_data(parent_category_id=grandparent_id)
            
            await callback.message.edit_text(
                Messages.get_categories_message(language),
                reply_markup=Keyboards.get_categories_keyboard(categories, language)
            )
        else:
            # Возвращаемся к корневым категориям
            categories = db.get_categories(language, parent_id=None)
            await state.update_data(parent_category_id=None)
            
            await callback.message.edit_text(
                Messages.get_categories_message(language),
                reply_markup=Keyboards.get_categories_keyboard(categories, language)
            )
    
    await callback.answer()

def register_category_handlers(dp):
    """Регистрация обработчиков категорий"""
    dp.include_router(router)