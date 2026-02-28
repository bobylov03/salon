from aiogram import Router, types
from aiogram.filters import Text
from aiogram.fsm.context import FSMContext

from ..database import Database
from ..keyboards import Keyboards
from ..messages import Messages
from ..states import UserStates, MasterStates
from ..utils import Utils

router = Router()
db = Database()

@router.message(UserStates.language_selection)
@router.message(Text(text=["🇷🇺 Русский", "🇬🇧 English", "🇹🇷 Türkçe", "🌐 Сменить язык", "🌐 Change Language", "🌐 Dil Değiştir"]))
async def process_language_selection(message: types.Message, state: FSMContext):
    """Обработка выбора языка"""
    
    # Определяем выбранный язык
    text = message.text
    if "Русский" in text or "Russian" in text:
        language = 'ru'
    elif "English" in text:
        language = 'en'
    elif "Türkçe" in text:
        language = 'tr'
    else:
        language = 'ru'  # По умолчанию
    
    # Получаем данные пользователя
    user_data = await state.get_data()
    user_id = user_data.get('user_id')
    
    # Проверяем, является ли пользователь мастером
    master_info = Utils.check_user_is_master(message.from_user.id)
    
    if master_info:
        # Обновляем язык мастера
        db.update_user_language(master_info['user_id'], language)
        
        await state.set_state(MasterStates.main_menu)
        await message.answer(
            Messages.get_language_set_message(language),
            reply_markup=Keyboards.get_master_menu_keyboard(language)
        )
    
    elif user_id:
        # Обновляем язык пользователя
        db.update_user_language(user_id, language)
        
        await state.set_state(UserStates.main_menu)
        await message.answer(
            Messages.get_language_set_message(language),
            reply_markup=Keyboards.get_main_menu_keyboard(language)
        )
    else:
        # Создаем нового пользователя
        user = db.get_or_create_user(
            telegram_id=message.from_user.id,
            first_name=message.from_user.first_name or "Пользователь",
            last_name=message.from_user.last_name or "",
            username=message.from_user.username or ""
        )
        
        # Обновляем язык
        db.update_user_language(user['id'], language)
        
        await state.update_data(user_id=user['id'])
        await state.set_state(UserStates.main_menu)
        await message.answer(
            Messages.get_language_set_message(language),
            reply_markup=Keyboards.get_main_menu_keyboard(language)
        )

def register_language_handlers(dp):
    """Регистрация обработчиков языка"""
    dp.include_router(router)