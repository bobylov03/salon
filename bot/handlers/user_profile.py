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

@router.message(UserStates.main_menu)
@router.message(Text(text=[
    "📋 Мои записи", "📋 My Appointments", "📋 Randevularım",
    "⬅️ Назад к записям", "⬅️ Back to Appointments", "⬅️ Randevulara Geri Dön"
]))
async def process_my_appointments(message: types.Message, state: FSMContext):
    """Обработка запроса на просмотр своих записей"""
    
    # Получаем язык пользователя
    user_data = await state.get_data()
    user_id = user_data.get('user_id')
    language = Utils.get_user_language(user_id) if user_id else 'ru'
    
    # Получаем записи пользователя
    appointments = db.get_user_appointments(user_id, limit=10)
    
    if not appointments:
        await message.answer(
            Messages.get_no_appointments_message(language),
            reply_markup=Keyboards.get_main_menu_keyboard(language)
        )
        return
    
    # Переходим в состояние просмотра записей
    await state.set_state(UserStates.my_appointments)
    
    await message.answer(
        Messages.get_my_appointments_message(language),
        reply_markup=Keyboards.get_appointments_keyboard(appointments, language)
    )

@router.callback_query(UserStates.my_appointments, Text(startswith="appointment_detail_"))
async def process_appointment_detail(callback: CallbackQuery, state: FSMContext):
    """Просмотр деталей конкретной записи"""
    
    # Получаем ID записи
    appointment_id = int(callback.data.split("_")[2])
    
    # Получаем язык пользователя
    user_data = await state.get_data()
    user_id = user_data.get('user_id')
    language = Utils.get_user_language(user_id) if user_id else 'ru'
    
    # Получаем информацию о записи
    conn = db.get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT a.*, 
               u1.first_name as master_first_name, u1.last_name as master_last_name,
               GROUP_CONCAT(st.title, ', ') as services_titles
        FROM appointments a
        LEFT JOIN masters m ON a.master_id = m.id
        LEFT JOIN users u1 ON m.user_id = u1.id
        LEFT JOIN appointment_services aps ON a.id = aps.appointment_id
        LEFT JOIN services s ON aps.service_id = s.id
        LEFT JOIN service_translations st ON s.id = st.service_id AND st.language = ?
        WHERE a.id = ? AND a.client_id = ?
        GROUP BY a.id
    """, (language, appointment_id, user_id))
    
    appointment = cursor.fetchone()
    conn.close()
    
    if not appointment:
        await callback.answer(Messages.get_error_message(language))
        return
    
    # Переходим в состояние деталей записи
    await state.set_state(UserStates.appointment_detail)
    await state.update_data(current_appointment_id=appointment_id)
    
    await callback.message.edit_text(
        Messages.get_appointment_detail_message(language, dict(appointment)),
        reply_markup=Keyboards.get_appointment_detail_keyboard(appointment_id, language)
    )
    
    await callback.answer()

@router.callback_query(UserStates.appointment_detail, Text(startswith="cancel_"))
async def process_cancel_existing_appointment(callback: CallbackQuery, state: FSMContext):
    """Отмена существующей записи"""
    
    # Получаем ID записи
    appointment_id = int(callback.data.split("_")[1])
    
    # Получаем язык пользователя
    user_data = await state.get_data()
    user_id = user_data.get('user_id')
    language = Utils.get_user_language(user_id) if user_id else 'ru'
    
    # Проверяем, что запись принадлежит пользователю
    conn = db.get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id FROM appointments 
        WHERE id = ? AND client_id = ? AND status IN ('pending', 'confirmed')
    """, (appointment_id, user_id))
    
    appointment = cursor.fetchone()
    conn.close()
    
    if not appointment:
        await callback.answer(
            "Нельзя отменить эту запись" if language == 'ru' else
            "Cannot cancel this appointment" if language == 'en' else
            "Bu randevu iptal edilemez"
        )
        return
    
    # Отменяем запись
    success = db.cancel_appointment(appointment_id, user_id)
    
    if success:
        # Получаем обновленный список записей
        appointments = db.get_user_appointments(user_id, limit=10)
        
        if appointments:
            await callback.message.edit_text(
                Messages.get_cancel_success_message(language),
                reply_markup=Keyboards.get_appointments_keyboard(appointments, language)
            )
        else:
            await callback.message.edit_text(
                Messages.get_cancel_success_message(language),
                reply_markup=Keyboards.get_main_menu_keyboard(language)
            )
            await state.set_state(UserStates.main_menu)
    else:
        await callback.message.edit_text(
            Messages.get_error_message(language),
            reply_markup=Keyboards.get_main_menu_keyboard(language)
        )
        await state.set_state(UserStates.main_menu)
    
    await callback.answer()

@router.callback_query(UserStates.appointment_detail, Text(startswith="reschedule_"))
async def process_reschedule_appointment(callback: CallbackQuery, state: FSMContext):
    """Начало процесса переноса записи"""
    
    # Получаем ID записи
    appointment_id = int(callback.data.split("_")[1])
    
    # Получаем язык пользователя
    user_data = await state.get_data()
    user_id = user_data.get('user_id')
    language = Utils.get_user_language(user_id) if user_id else 'ru'
    
    # Сохраняем ID записи для переноса
    await state.update_data(reschedule_appointment_id=appointment_id)
    
    # Получаем услуги из этой записи для поиска доступных дат
    conn = db.get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT service_id FROM appointment_services
        WHERE appointment_id = ?
    """, (appointment_id,))
    
    service_ids = [row['service_id'] for row in cursor.fetchall()]
    
    # Получаем информацию о мастере из записи
    cursor.execute("SELECT master_id FROM appointments WHERE id = ?", (appointment_id,))
    appointment = cursor.fetchone()
    master_id = appointment['master_id'] if appointment else None
    
    conn.close()
    
    if not service_ids:
        await callback.answer(Messages.get_error_message(language))
        return
    
    # Сохраняем данные для поиска доступных слотов
    await state.update_data(
        reschedule_service_ids=service_ids,
        reschedule_master_id=master_id
    )
    
    # Переходим к выбору новой даты
    await state.set_state(UserStates.reschedule_date)
    
    # Показываем календарь
    today = datetime.now()
    await callback.message.edit_text(
        "Выберите новую дату для записи:" if language == 'ru' else
        "Select new date for appointment:" if language == 'en' else
        "Randevu için yeni tarih seçin:",
        reply_markup=Keyboards.get_calendar_keyboard(today.year, today.month, language)
    )
    
    await callback.answer()

@router.callback_query(UserStates.appointment_detail, Text("back_to_appointments"))
@router.callback_query(UserStates.my_appointments, Text("back_to_main"))
async def process_back_from_appointments(callback: CallbackQuery, state: FSMContext):
    """Возврат из просмотра записей в главное меню"""
    
    # Получаем язык пользователя
    user_data = await state.get_data()
    user_id = user_data.get('user_id')
    language = Utils.get_user_language(user_id) if user_id else 'ru'
    
    # Возвращаем в главное меню
    await state.set_state(UserStates.main_menu)
    
    await callback.message.edit_text(
        Messages.get_language_set_message(language),
        reply_markup=Keyboards.get_main_menu_keyboard(language)
    )
    
    await callback.answer()

# Обработчики переноса записи
@router.callback_query(UserStates.reschedule_date, Text(startswith="select_date_"))
async def process_reschedule_select_date(callback: CallbackQuery, state: FSMContext):
    """Выбор новой даты для переноса записи"""
    
    # Получаем язык пользователя
    user_data = await state.get_data()
    user_id = user_data.get('user_id')
    language = Utils.get_user_language(user_id) if user_id else 'ru'
    
    # Получаем выбранную дату
    date_str = callback.data.split("_")[2]
    appointment_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    
    # Получаем данные для переноса
    data = await state.get_data()
    service_ids = data.get('reschedule_service_ids', [])
    master_id = data.get('reschedule_master_id')
    
    # Получаем доступные временные слоты
    if master_id:
        # Для конкретного мастера
        total_duration = Utils.calculate_total_duration(service_ids)
        time_slots = db.get_available_time_slots(master_id, appointment_date, total_duration)
        
        if not time_slots:
            await callback.answer(
                "На эту дату нет свободного времени" if language == 'ru' else
                "No available time slots for this date" if language == 'en' else
                "Bu tarih için uygun saat yok"
            )
            return
        
        await state.update_data(reschedule_date=appointment_date.isoformat())
        await state.set_state(UserStates.reschedule_time)
        
        # Получаем информацию о мастере
        master = db.get_master_by_id(master_id)
        master_name = f"{master.get('first_name', '')} {master.get('last_name', '')}".strip() if master else ""
        
        await callback.message.edit_text(
            f"Выберите новое время на {Utils.format_date(appointment_date, language)} для мастера {master_name}:" if language == 'ru' else
            f"Select new time for {Utils.format_date(appointment_date, language)} with master {master_name}:" if language == 'en' else
            f"{Utils.format_date(appointment_date, language)} tarihi için {master_name} usta ile yeni saat seçin:",
            reply_markup=Keyboards.get_time_slots_keyboard(time_slots, language)
        )
    
    else:
        # Для любого мастера
        time_slots_data = Utils.get_available_time_slots_for_services(
            service_ids, appointment_date, master_id=None
        )
        
        if not time_slots_data:
            await callback.answer(
                "На эту дату нет свободного времени" if language == 'ru' else
                "No available time slots for this date" if language == 'en' else
                "Bu tarih için uygun saat yok"
            )
            return
        
        time_slots = [item['time'] for item in time_slots_data]
        
        await state.update_data(reschedule_date=appointment_date.isoformat())
        await state.set_state(UserStates.reschedule_time)
        
        await callback.message.edit_text(
            f"Выберите новое время на {Utils.format_date(appointment_date, language)} (любой доступный мастер):" if language == 'ru' else
            f"Select new time for {Utils.format_date(appointment_date, language)} (any available master):" if language == 'en' else
            f"{Utils.format_date(appointment_date, language)} tarihi için yeni saat seçin (uygun herhangi bir usta):",
            reply_markup=Keyboards.get_time_slots_keyboard(time_slots, language)
        )
    
    await callback.answer()

@router.callback_query(UserStates.reschedule_time, Text(startswith="select_time_"))
async def process_reschedule_select_time(callback: CallbackQuery, state: FSMContext):
    """Выбор нового времени для переноса записи"""
    
    # Получаем выбранное время
    time_slot = callback.data.split("_")[2]
    
    # Получаем язык пользователя
    user_data = await state.get_data()
    user_id = user_data.get('user_id')
    language = Utils.get_user_language(user_id) if user_id else 'ru'
    
    # Получаем данные для переноса
    data = await state.get_data()
    appointment_id = data.get('reschedule_appointment_id')
    service_ids = data.get('reschedule_service_ids', [])
    master_id = data.get('reschedule_master_id')
    appointment_date_str = data.get('reschedule_date')
    
    if not appointment_date_str:
        await callback.answer(Messages.get_error_message(language))
        return
    
    appointment_date = date.fromisoformat(appointment_date_str)
    
    # Если выбран "любой мастер", ищем подходящего
    if master_id is None:
        master_id = Utils.find_master_for_time_slot(
            service_ids, appointment_date, time_slot
        )
        
        if not master_id:
            await callback.answer(
                "Это время уже занято" if language == 'ru' else
                "This time slot is already taken" if language == 'en' else
                "Bu saat dolu"
            )
            return
    
    # Обновляем запись в БД
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # Рассчитываем время окончания
    total_duration = Utils.calculate_total_duration(service_ids)
    start_dt = datetime.strptime(time_slot, '%H:%M')
    end_dt = datetime.combine(date.today(), start_dt.time()) + timedelta(minutes=total_duration)
    end_time = end_dt.strftime('%H:%M')
    
    cursor.execute("""
        UPDATE appointments 
        SET master_id = ?, appointment_date = ?, start_time = ?, end_time = ?, status = 'confirmed'
        WHERE id = ? AND client_id = ?
    """, (master_id, appointment_date.isoformat(), time_slot, end_time, appointment_id, user_id))
    
    conn.commit()
    conn.close()
    
    # Показываем сообщение об успехе
    await callback.message.edit_text(
        "✅ Запись успешно перенесена!" if language == 'ru' else
        "✅ Appointment successfully rescheduled!" if language == 'en' else
        "✅ Randevu başarıyla yeniden planlandı!",
        reply_markup=Keyboards.get_main_menu_keyboard(language)
    )
    
    # Возвращаем в главное меню
    await state.set_state(UserStates.main_menu)
    
    # Очищаем временные данные
    await state.update_data(
        reschedule_appointment_id=None,
        reschedule_service_ids=[],
        reschedule_master_id=None,
        reschedule_date=None
    )
    
    await callback.answer()

# Обработчики других пунктов меню
@router.message(UserStates.main_menu)
@router.message(Text(text=[
    "👤 Мой профиль", "👤 My Profile", "👤 Profilim",
    "ℹ️ О салоне", "ℹ️ About Salon", "ℹ️ Salon Hakkında"
]))
async def process_other_menu_items(message: types.Message, state: FSMContext):
    """Обработка других пунктов главного меню"""
    
    # Получаем язык пользователя
    user_data = await state.get_data()
    user_id = user_data.get('user_id')
    language = Utils.get_user_language(user_id) if user_id else 'ru'
    
    text = message.text
    
    if "профиль" in text.lower() or "profile" in text.lower() or "profil" in text.lower():
        # Показываем профиль пользователя
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT first_name, last_name, phone, email, created_at
            FROM users WHERE id = ?
        """, (user_id,))
        
        user = cursor.fetchone()
        conn.close()
        
        if user:
            user_dict = dict(user)
            created_at = datetime.strptime(user_dict['created_at'], '%Y-%m-%d %H:%M:%S')
            
            if language == 'ru':
                message_text = f"👤 Ваш профиль:\n\n"
                message_text += f"Имя: {user_dict['first_name']}\n"
                if user_dict['last_name']:
                    message_text += f"Фамилия: {user_dict['last_name']}\n"
                if user_dict['phone']:
                    message_text += f"Телефон: {user_dict['phone']}\n"
                if user_dict['email']:
                    message_text += f"Email: {user_dict['email']}\n"
                message_text += f"Дата регистрации: {created_at.strftime('%d.%m.%Y')}\n"
                message_text += f"Язык: {Messages.LANGUAGES.get(language, language)}"
            
            elif language == 'en':
                message_text = f"👤 Your profile:\n\n"
                message_text += f"First name: {user_dict['first_name']}\n"
                if user_dict['last_name']:
                    message_text += f"Last name: {user_dict['last_name']}\n"
                if user_dict['phone']:
                    message_text += f"Phone: {user_dict['phone']}\n"
                if user_dict['email']:
                    message_text += f"Email: {user_dict['email']}\n"
                message_text += f"Registration date: {created_at.strftime('%Y-%m-%d')}\n"
                message_text += f"Language: {Messages.LANGUAGES.get(language, language)}"
            
            else:  # tr
                message_text = f"👤 Profiliniz:\n\n"
                message_text += f"Ad: {user_dict['first_name']}\n"
                if user_dict['last_name']:
                    message_text += f"Soyad: {user_dict['last_name']}\n"
                if user_dict['phone']:
                    message_text += f"Telefon: {user_dict['phone']}\n"
                if user_dict['email']:
                    message_text += f"E-posta: {user_dict['email']}\n"
                message_text += f"Kayıt tarihi: {created_at.strftime('%d.%m.%Y')}\n"
                message_text += f"Dil: {Messages.LANGUAGES.get(language, language)}"
            
            await message.answer(message_text)
    
    else:
        # Показываем информацию о салоне
        if language == 'ru':
            salon_info = """
            💈 Салон красоты "Элегант"

            🕐 Часы работы:
            Пн-Пт: 9:00 - 20:00
            Сб-Вс: 10:00 - 18:00

            📍 Адрес:
            ул. Красивая, д. 123

            📞 Телефон:
            +7 (999) 123-45-67

            ✨ Мы предлагаем:
            • Парикмахерские услуги
            • Маникюр и педикюр
            • Косметологические услуги
            • Массаж

            Записывайтесь онлайн - это быстро и удобно!
            """
        
        elif language == 'en':
            salon_info = """
            💈 Beauty Salon "Elegant"

            🕐 Working hours:
            Mon-Fri: 9:00 AM - 8:00 PM
            Sat-Sun: 10:00 AM - 6:00 PM

            📍 Address:
            Beautiful Street, 123

            📞 Phone:
            +7 (999) 123-45-67

            ✨ We offer:
            • Hair services
            • Manicure & Pedicure
            • Cosmetic services
            • Massage

            Book online - it's fast and convenient!
            """
        
        else:  # tr
            salon_info = """
            💈 Güzellik Salonu "Elegant"

            🕐 Çalışma saatleri:
            Pzt-Cum: 9:00 - 20:00
            Cmt-Paz: 10:00 - 18:00

            📍 Adres:
            Güzel Sokak, No: 123

            📞 Telefon:
            +7 (999) 123-45-67

            ✨ Sunduklarımız:
            • Kuaför hizmetleri
            • Manikür & Pedikür
            • Kozmetik hizmetler
            • Masaj

            Çevrimiçi randevu alın - hızlı ve kolay!
            """
        
        await message.answer(salon_info)

def register_user_profile_handlers(dp):
    """Регистрация обработчиков профиля пользователя"""
    dp.include_router(router)