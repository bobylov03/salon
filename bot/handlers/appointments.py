# appointment.py
from aiogram import Router, types
from aiogram.filters import Text
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from datetime import datetime, date, timedelta
from typing import Optional
import logging
import traceback

from ..database import Database
from ..keyboards import Keyboards
from ..messages import Messages
from ..states import UserStates, MasterStates
from ..utils import Utils

router = Router()
db = Database()
logger = logging.getLogger(__name__)

def clean_phone_for_telegram(phone_str: str) -> Optional[int]:
    """Очищает строку phone и преобразует в integer для Telegram ID"""
    if not phone_str:
        return None
    # Удаляем все нецифровые символы
    digits = ''.join(filter(str.isdigit, str(phone_str)))
    if not digits:
        return None
    try:
        return int(digits)
    except ValueError:
        return None

# Обработчики выбора времени
@router.callback_query(UserStates.time_selection, Text(startswith="select_time_"))
async def process_select_time(callback: CallbackQuery, state: FSMContext):
    """Выбор временного слота"""
    
    # Получаем выбранное время
    time_slot = callback.data.split("_")[2]
    
    # Получаем язык пользователя
    user_data = await state.get_data()
    user_id = user_data.get('user_id')
    language = Utils.get_user_language(user_id) if user_id else 'ru'
    
    # Получаем данные о записи
    data = await state.get_data()
    selected_services = data.get('selected_services', [])
    appointment_date_str = data.get('appointment_date')
    master_id = data.get('master_id')  # Может быть None для "любого мастера"
    
    if not selected_services or not appointment_date_str:
        await callback.answer(Messages.get_error_message(language))
        return
    
    appointment_date = date.fromisoformat(appointment_date_str)
    
    # Если выбран "любой мастер", ищем подходящего мастера для этого времени
    if master_id is None:
        master_id = Utils.find_master_for_time_slot(
            selected_services, appointment_date, time_slot
        )
        
        if not master_id:
            await callback.answer(
                "Это время уже занято" if language == 'ru' else
                "This time slot is already taken" if language == 'en' else
                "Bu saat dolu"
            )
            return
        
        # Сохраняем найденного мастера
        await state.update_data(master_id=master_id)
    
    else:
        # Проверяем, доступно ли время для конкретного мастера
        is_available = Utils.validate_time_slot(
            master_id, appointment_date, time_slot, selected_services
        )
        
        if not is_available:
            await callback.answer(
                "Это время уже занято" if language == 'ru' else
                "This time slot is already taken" if language == 'en' else
                "Bu saat dolu"
            )
            return
    
    # Сохраняем выбранное время
    await state.update_data(appointment_time=time_slot)
    
    # Генерируем сводку по записи
    appointment_summary = Utils.generate_appointment_summary(
        selected_services,
        appointment_date,
        time_slot,
        master_id,
        language
    )
    
    # Сохраняем сводку для подтверждения
    await state.update_data(appointment_summary=appointment_summary)
    
    # Переходим к подтверждению записи
    await state.set_state(UserStates.appointment_confirmation)
    
    # Формируем данные для сообщения подтверждения
    master_info = appointment_summary.get('master')
    if master_info:
        master_name = f"{master_info.get('first_name', '')} {master_info.get('last_name', '')}".strip()
    else:
        master_name = (
            "Любой доступный мастер" if language == 'ru' else
            "Any available master" if language == 'en' else
            "Uygun herhangi usta"
        )
    
    confirmation_details = {
        'date': appointment_date_str,
        'time': time_slot,
        'master_name': master_name,
        'services': appointment_summary['services'],
        'total_price': appointment_summary['total_price']
    }
    
    await callback.message.edit_text(
        Messages.get_appointment_confirmation_message(language, confirmation_details),
        reply_markup=Keyboards.get_confirmation_keyboard(language)
    )
    
    await callback.answer()

@router.callback_query(UserStates.time_selection, Text("back_to_masters"))
async def process_back_to_masters_from_time(callback: CallbackQuery, state: FSMContext):
    """Возврат от выбора времени к выбору мастера"""
    
    # Получаем язык пользователя
    user_data = await state.get_data()
    user_id = user_data.get('user_id')
    language = Utils.get_user_language(user_id) if user_id else 'ru'
    
    # Получаем данные
    data = await state.get_data()
    master_id = data.get('master_id')
    
    if master_id is None:
        # Возвращаемся к выбору типа записи
        await state.set_state(UserStates.master_choice)
        await callback.message.edit_text(
            Messages.get_master_choice_message(language),
            reply_markup=Keyboards.get_master_choice_keyboard(language)
        )
    else:
        # Возвращаемся к выбору конкретного мастера
        # Получаем подходящих мастеров
        suitable_masters_ids = data.get('suitable_masters', [])
        suitable_masters = []
        
        for master_id in suitable_masters_ids:
            master = db.get_master_by_id(master_id)
            if master:
                suitable_masters.append(master)
        
        await state.set_state(UserStates.master_selection)
        await callback.message.edit_text(
            Messages.get_masters_list_message(language),
            reply_markup=Keyboards.get_masters_keyboard(suitable_masters, language)
        )
    
    await callback.answer()

# Обработчики подтверждения записи
@router.callback_query(UserStates.appointment_confirmation, Text("confirm_appointment"))
async def process_confirm_appointment(callback: CallbackQuery, state: FSMContext):
    """Подтверждение создания записи"""
    
    # Получаем bot из callback
    bot = callback.bot
    
    # Получаем язык пользователя
    user_data = await state.get_data()
    user_id = user_data.get('user_id')
    language = Utils.get_user_language(user_id) if user_id else 'ru'
    
    # Получаем данные записи
    data = await state.get_data()
    appointment_summary = data.get('appointment_summary')
    
    logger.info(f"Начинаем создание записи. User ID: {user_id}, Data: {data}")
    
    if not appointment_summary:
        logger.error("Appointment summary is None!")
        await callback.answer(Messages.get_error_message(language))
        return
    
    # Извлекаем данные из сводки
    appointment_date = date.fromisoformat(appointment_summary['date'])
    appointment_time = appointment_summary['time']
    master_id = appointment_summary.get('master_id')  # Получаем master_id напрямую из summary
    service_ids = [s['id'] for s in appointment_summary['services']]
    
    logger.info(f"Проверяем данные перед созданием записи:")
    logger.info(f"  client_id: {user_id} (type: {type(user_id)})")
    logger.info(f"  master_id: {master_id} (type: {type(master_id)})")
    logger.info(f"  appointment_date: {appointment_date} (type: {type(appointment_date)})")
    logger.info(f"  start_time: {appointment_time} (type: {type(appointment_time)})")
    logger.info(f"  service_ids: {service_ids} (type: {type(service_ids)})")
    
    # Создаем запись в БД
    appointment_id, master_phone = db.create_appointment(
        client_id=user_id,
        master_id=master_id,
        appointment_date=appointment_date,
        start_time=appointment_time,
        service_ids=service_ids,
        status='pending'
    )
    
    logger.info(f"Создана запись: ID={appointment_id}, Мастер ID={master_id}, Phone (Telegram ID)={master_phone}")
    
    if not appointment_id or appointment_id is None:
        logger.error("Ошибка: appointment_id is None! Запись не создана.")
        await callback.message.edit_text(
            Messages.get_error_message(language),
            reply_markup=Keyboards.get_main_menu_keyboard(language)
        )
        return
    
    # Отправляем уведомление мастеру, если он выбран
    logger.info(f"Проверяем условия для уведомления: master_phone={master_phone}, master_id={master_id}")
    
    if master_phone and master_id:
        logger.info(f"Условия выполнены. Отправляем уведомление мастеру: phone={master_phone}")
        
        try:
            # Преобразуем phone в telegram_id
            master_telegram_id = clean_phone_for_telegram(master_phone)
            
            if not master_telegram_id:
                logger.error(f"Не удалось преобразовать phone '{master_phone}' в telegram_id")
                master_telegram_id = None
            else:
                logger.info(f"Преобразован phone в telegram_id: '{master_phone}' -> {master_telegram_id}")
            
            if master_telegram_id:
                logger.info(f"Получаем информацию о записи для уведомления мастера {master_telegram_id}")
                
                # Получаем информацию о записи
                conn = db.get_connection()
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT a.*, 
                           u.first_name as client_first_name, 
                           u.last_name as client_last_name,
                           u.phone as client_phone,
                           GROUP_CONCAT(DISTINCT COALESCE(st.title, 'Услуга ' || s.id), ', ') as services_titles
                    FROM appointments a
                    JOIN users u ON a.client_id = u.id
                    LEFT JOIN appointment_services aps ON a.id = aps.appointment_id
                    LEFT JOIN services s ON aps.service_id = s.id
                    LEFT JOIN service_translations st ON s.id = st.service_id AND st.language = 'ru'
                    WHERE a.id = ?
                    GROUP BY a.id
                """, (appointment_id,))
                
                appointment_info = cursor.fetchone()
                conn.close()
                
                if appointment_info:
                    appointment_dict = dict(appointment_info)
                    logger.info(f"Информация о записи для уведомления мастера: {appointment_dict}")
                    
                    # Определяем язык мастера
                    master_language = 'ru'  # По умолчанию
                    try:
                        conn = db.get_connection()
                        cursor = conn.cursor()
                        cursor.execute("""
                            SELECT u.language FROM masters m
                            JOIN users u ON m.user_id = u.id
                            WHERE m.id = ?
                        """, (master_id,))
                        master_result = cursor.fetchone()
                        conn.close()
                        if master_result:
                            master_result_dict = dict(master_result)
                            if master_result_dict.get('language') in ['ru', 'en', 'tr']:
                                master_language = master_result_dict['language']
                                logger.info(f"Язык мастера: {master_language}")
                    except Exception as lang_err:
                        logger.error(f"Ошибка при получении языка мастера: {lang_err}")
                    
                    # Формируем сообщение для мастера
                    date_str = appointment_dict['appointment_date']
                    time_str = appointment_dict['start_time']
                    client_name = f"{appointment_dict.get('client_first_name', '')} {appointment_dict.get('client_last_name', '')}".strip()
                    services = appointment_dict.get('services_titles', 'Услуги не указаны')
                    client_phone = appointment_dict.get('client_phone', '')
                    
                    # Формируем сообщение на языке мастера
                    if master_language == 'ru':
                        message = f"📅 Новая запись!\n\n"
                        message += f"📅 Дата: {date_str}\n"
                        message += f"⏰ Время: {time_str}\n"
                        message += f"👤 Клиент: {client_name}\n"
                        if client_phone:
                            message += f"📞 Телефон: {client_phone}\n"
                        message += f"💅 Услуги: {services}\n\n"
                        message += f"ID записи: {appointment_id}"
                    elif master_language == 'en':
                        message = f"📅 New Appointment!\n\n"
                        message += f"📅 Date: {date_str}\n"
                        message += f"⏰ Time: {time_str}\n"
                        message += f"👤 Client: {client_name}\n"
                        if client_phone:
                            message += f"📞 Phone: {client_phone}\n"
                        message += f"💅 Services: {services}\n\n"
                        message += f"Appointment ID: {appointment_id}"
                    else:  # tr
                        message = f"📅 Yeni Randevu!\n\n"
                        message += f"📅 Tarih: {date_str}\n"
                        message += f"⏰ Saat: {time_str}\n"
                        message += f"👤 Müşteri: {client_name}\n"
                        if client_phone:
                            message += f"📞 Telefon: {client_phone}\n"
                        message += f"💅 Hizmetler: {services}\n\n"
                        message += f"Randevu ID: {appointment_id}"
                    
                    # Отправляем сообщение мастеру
                    try:
                        logger.info(f"Пытаемся отправить сообщение мастеру: ID={master_telegram_id}, тип={type(master_telegram_id)}")
                        await bot.send_message(master_telegram_id, message)
                        logger.info(f"✅ Уведомление успешно отправлено мастеру {master_telegram_id}")
                    except Exception as send_error:
                        logger.error(f"❌ Ошибка отправки сообщения мастеру {master_telegram_id}: {send_error}")
                        logger.error(f"Трассировка ошибки: {traceback.format_exc()}")
                        
                        # Попробуем отправить как строку
                        try:
                            logger.info(f"Пробуем отправить как строку: {str(master_telegram_id)}")
                            await bot.send_message(str(master_telegram_id), message)
                            logger.info(f"✅ Уведомление отправлено мастеру как строке")
                        except Exception as str_error:
                            logger.error(f"❌ Ошибка отправки мастеру как строке: {str_error}")
                else:
                    logger.error(f"❌ Не удалось получить информацию о записи {appointment_id}")
            else:
                logger.error(f"❌ master_telegram_id is None для master_phone={master_phone}")
                
        except Exception as e:
            logger.error(f"❌ Общая ошибка при отправке уведомления мастеру: {e}")
            logger.error(f"Трассировка ошибки: {traceback.format_exc()}")
    else:
        logger.warning(f"⚠️ Уведомление мастеру не отправлено: master_phone={master_phone}, master_id={master_id}")
    
    # Показываем сообщение об успехе клиенту
    await callback.message.edit_text(
        Messages.get_appointment_success_message(language, appointment_id),
        reply_markup=Keyboards.get_main_menu_keyboard(language)
    )
    
    # Возвращаем в главное меню
    await state.set_state(UserStates.main_menu)
    
    # Очищаем временные данные
    await state.update_data(
        selected_services=[],
        appointment_date=None,
        appointment_time=None,
        master_id=None,
        appointment_summary=None,
        suitable_masters=[]
    )
    
    await callback.answer()

@router.callback_query(UserStates.appointment_confirmation, Text("cancel_appointment"))
async def process_cancel_appointment_creation(callback: CallbackQuery, state: FSMContext):
    """Отмена создания записи"""
    
    # Получаем язык пользователя
    user_data = await state.get_data()
    user_id = user_data.get('user_id')
    language = Utils.get_user_language(user_id) if user_id else 'ru'
    
    # Возвращаем в главное меню
    await state.set_state(UserStates.main_menu)
    
    # Очищаем временные данные
    await state.update_data(
        selected_services=[],
        appointment_date=None,
        appointment_time=None,
        master_id=None,
        appointment_summary=None,
        suitable_masters=[]
    )
    
    await callback.message.edit_text(
        "Запись отменена" if language == 'ru' else
        "Booking cancelled" if language == 'en' else
        "Randevu iptal edildi",
        reply_markup=Keyboards.get_main_menu_keyboard(language)
    )
    
    await callback.answer()

# Обработчики для мастеров (просмотр записей)
@router.message(MasterStates.main_menu)
@router.message(Text(text=[
    "📅 Записи на сегодня", "📅 Today's Appointments", "📅 Bugünkü Randevular",
    "📅 Записи на завтра", "📅 Tomorrow's Appointments", "📅 Yarınki Randevular",
    "📅 Записи по дате", "📅 Appointments by Date", "📅 Tarihe Göre Randevular"
]))
async def process_master_view_appointments(message: types.Message, state: FSMContext):
    """Обработка запроса мастера на просмотр записей"""
    
    # Проверяем, является ли пользователь мастером
    master_info = Utils.check_user_is_master(message.from_user.id)
    
    logger.info(f"Проверка мастера: TG_ID={message.from_user.id}, результат={master_info}")
    
    if not master_info:
        await message.answer("Вы не являетесь мастером.")
        return
    
    master_id = master_info['master_id']
    language = master_info.get('language', 'ru')
    text = message.text
    
    today = date.today()
    
    if "сегодня" in text.lower() or "today" in text.lower() or "bugün" in text.lower():
        # Записи на сегодня
        appointments = db.get_master_appointments(master_id, today)
        target_date = today
        
    elif "завтра" in text.lower() or "tomorrow" in text.lower() or "yarın" in text.lower():
        # Записи на завтра
        tomorrow = today + timedelta(days=1)
        appointments = db.get_master_appointments(master_id, tomorrow)
        target_date = tomorrow
        
    else:
        # Записи по дате - переходим в состояние выбора даты
        await state.set_state(MasterStates.select_appointment_date)
        
        # Показываем календарь
        await message.answer(
            "Выберите дату для просмотра записей:" if language == 'ru' else
            "Select date to view appointments:" if language == 'en' else
            "Randevuları görüntülemek için tarih seçin:",
            reply_markup=Keyboards.get_calendar_keyboard(today.year, today.month, language)
        )
        return
    
    # Формируем сообщение с записями
    if not appointments:
        date_str = Utils.format_date(target_date, language)
        
        if language == 'ru':
            message_text = f"📅 На {date_str} записей нет."
        elif language == 'en':
            message_text = f"📅 No appointments for {date_str}."
        else:  # tr
            message_text = f"📅 {date_str} için randevu yok."
        
        await message.answer(message_text)
        return
    
    # Формируем список записей
    if language == 'ru':
        message_text = f"📅 Записи на {Utils.format_date(target_date, language)}:\n\n"
    elif language == 'en':
        message_text = f"📅 Appointments for {Utils.format_date(target_date, language)}:\n\n"
    else:  # tr
        message_text = f"📅 {Utils.format_date(target_date, language)} tarihi için randevular:\n\n"
    
    for i, appointment in enumerate(appointments, 1):
        client_name = f"{appointment.get('client_first_name', '')} {appointment.get('client_last_name', '')}".strip()
        time_str = appointment['start_time']
        services = appointment.get('services_titles', '')
        
        message_text += f"{i}. ⏰ {time_str} - 👤 {client_name}\n"
        message_text += f"   💅 {services}\n"
        
        if appointment.get('client_phone'):
            message_text += f"   📞 {appointment['client_phone']}\n"
        
        message_text += "\n"
    
    await message.answer(message_text)

@router.callback_query(MasterStates.select_appointment_date, Text(startswith="select_date_"))
async def process_master_select_date(callback: CallbackQuery, state: FSMContext):
    """Выбор даты мастером для просмотра записей"""
    
    # Получаем информацию о мастере
    master_info = Utils.check_user_is_master(callback.from_user.id)
    
    if not master_info:
        await callback.answer("Ошибка доступа")
        return
    
    master_id = master_info['master_id']
    language = master_info.get('language', 'ru')
    
    # Получаем выбранную дату
    date_str = callback.data.split("_")[2]
    appointment_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    
    # Получаем записи мастера на эту дату
    appointments = db.get_master_appointments(master_id, appointment_date)
    
    # Формируем сообщение
    if not appointments:
        date_formatted = Utils.format_date(appointment_date, language)
        
        if language == 'ru':
            message_text = f"📅 На {date_formatted} записей нет."
        elif language == 'en':
            message_text = f"📅 No appointments for {date_formatted}."
        else:  # tr
            message_text = f"📅 {date_formatted} için randevu yok."
        
        await callback.message.edit_text(message_text)
        await state.set_state(MasterStates.main_menu)
    else:
        # Формируем список записей
        if language == 'ru':
            message_text = f"📅 Записи на {Utils.format_date(appointment_date, language)}:\n\n"
        elif language == 'en':
            message_text = f"📅 Appointments for {Utils.format_date(appointment_date, language)}:\n\n"
        else:  # tr
            message_text = f"📅 {Utils.format_date(appointment_date, language)} tarihi için randevular:\n\n"
        
        for i, appointment in enumerate(appointments, 1):
            client_name = f"{appointment.get('client_first_name', '')} {appointment.get('client_last_name', '')}".strip()
            time_str = appointment['start_time']
            services = appointment.get('services_titles', '')
            
            message_text += f"{i}. ⏰ {time_str} - 👤 {client_name}\n"
            message_text += f"   💅 {services}\n"
            
            if appointment.get('client_phone'):
                message_text += f"   📞 {appointment['client_phone']}\n"
            
            message_text += "\n"
        
        await callback.message.edit_text(message_text)
        await state.set_state(MasterStates.main_menu)
    
    await callback.answer()

# Обработчик смены месяца в календаре для мастера
@router.callback_query(MasterStates.select_appointment_date, Text(startswith="change_month_"))
async def process_master_change_month(callback: CallbackQuery, state: FSMContext):
    """Смена месяца в календаре для мастера"""
    
    # Получаем информацию о мастере
    master_info = Utils.check_user_is_master(callback.from_user.id)
    
    if not master_info:
        await callback.answer("Ошибка доступа")
        return
    
    language = master_info.get('language', 'ru')
    
    # Получаем год и месяц из callback данных
    try:
        parts = callback.data.split("_")
        if len(parts) == 3:
            year_str, month_str = parts[1], parts[2]
            year = int(year_str)
            month = int(month_str)
        else:
            # Если формат неверный, используем текущий год/месяц
            today = datetime.now()
            year, month = today.year, today.month
    except (ValueError, IndexError) as e:
        logger.error(f"Ошибка парсинга даты: {e}")
        today = datetime.now()
        year, month = today.year, today.month
    
    # Обновляем клавиатуру календаря
    await callback.message.edit_reply_markup(
        reply_markup=Keyboards.get_calendar_keyboard(year, month, language)
    )
    
    await callback.answer()

def register_appointment_handlers(dp):
    """Регистрация обработчиков записей"""
    dp.include_router(router)