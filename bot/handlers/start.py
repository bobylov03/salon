from aiogram import Router, types
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext

from ..database import Database
from ..keyboards import Keyboards
from ..messages import Messages
from ..states import UserStates, MasterStates
from ..utils import Utils

router = Router()
db = Database()

@router.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    """Обработка команды /start"""
    
    # Проверяем, является ли пользователь мастером
    master_info = Utils.check_user_is_master(message.from_user.id)
    
    if master_info:
        # Пользователь - мастер
        await state.set_state(MasterStates.main_menu)
        language = master_info.get('language', 'ru')
        
        await message.answer(
            Messages.get_welcome_message(language),
            reply_markup=Keyboards.get_master_menu_keyboard(language)
        )
    else:
        # Пользователь - клиент
        # Создаем или получаем пользователя
        user = db.get_or_create_user(
            telegram_id=message.from_user.id,
            first_name=message.from_user.first_name or "Пользователь",
            last_name=message.from_user.last_name or "",
            username=message.from_user.username or ""
        )
        
        # Сохраняем данные пользователя в состоянии
        await state.update_data(user_id=user['id'])
        
        # Проверяем, установлен ли уже язык
        if user.get('language') and user['language'] != 'ru':
            # Язык уже установлен
            language = user['language']
            await state.set_state(UserStates.main_menu)
            await message.answer(
                Messages.get_language_set_message(language),
                reply_markup=Keyboards.get_main_menu_keyboard(language)
            )
        else:
            # Предлагаем выбрать язык
            await state.set_state(UserStates.language_selection)
            await message.answer(
                Messages.get_welcome_message('ru'),
                reply_markup=Keyboards.get_language_keyboard()
            )

@router.message(Command("help"))
async def cmd_help(message: types.Message):
    """Обработка команды /help"""
    await message.answer(
        "ℹ️ Помощь по боту:\n\n"
        "/start - Начать работу с ботом\n"
        "/help - Показать это сообщение\n"
        "/language - Сменить язык\n"
        "/cancel - Отменить текущее действие\n\n"
        "Используйте кнопки меню для навигации."
    )

@router.message(Command("cancel"))
async def cmd_cancel(message: types.Message, state: FSMContext):
    """Обработка команды /cancel"""
    current_state = await state.get_state()
    
    if current_state is None:
        await message.answer("Нет активных действий для отмены.")
        return
    
    # Возвращаем в главное меню в зависимости от типа пользователя
    master_info = Utils.check_user_is_master(message.from_user.id)
    
    if master_info:
        language = master_info.get('language', 'ru')
        await state.set_state(MasterStates.main_menu)
        await message.answer(
            "Действие отменено.",
            reply_markup=Keyboards.get_master_menu_keyboard(language)
        )
    else:
        # Получаем данные пользователя
        user_data = await state.get_data()
        user_id = user_data.get('user_id')
        
        if user_id:
            language = Utils.get_user_language(user_id)
        else:
            language = 'ru'
        
        await state.set_state(UserStates.main_menu)
        await message.answer(
            "Действие отменено.",
            reply_markup=Keyboards.get_main_menu_keyboard(language)
        )

def register_start_handlers(dp):
    """Регистрация обработчиков старта"""
    dp.include_router(router)