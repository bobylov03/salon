# main.py
import logging
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any

from telegram import (
    Update, 
    InlineKeyboardButton, 
    InlineKeyboardMarkup, 
    ReplyKeyboardMarkup, 
    KeyboardButton,
    ReplyKeyboardRemove
)
from telegram.ext import (
    Application, 
    CommandHandler, 
    MessageHandler, 
    CallbackQueryHandler, 
    ContextTypes,
    ConversationHandler,
    filters
)

# Импорты из текущего пакета
from . import config
from . import database
from . import messages
from . import keyboards

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Инициализация объектов
db = database.Database()
Config = config.Config
Messages = messages.Messages
Keyboards = keyboards.UnifiedKeyboards

# Создаем класс Utils с привязкой к db
class UtilsWrapper:
    @staticmethod
    def calculate_total_duration(service_ids: List[int]) -> int:
        """Рассчитывает общую длительность услуг"""
        total = 0
        for service_id in service_ids:
            service = db.get_service_by_id(service_id, 'ru')
            if service and service.get('duration_minutes'):
                total += service['duration_minutes']
        return total
    
    @staticmethod
    def calculate_total_price(service_ids: List[int]) -> float:
        """Рассчитывает общую стоимость услуг"""
        total = 0
        for service_id in service_ids:
            service = db.get_service_by_id(service_id, 'ru')
            if service and service.get('price'):
                total += service['price']
        return total
    
    @staticmethod
    def get_available_time_slots_for_services(service_ids, appointment_date, master_telegram_id=None):
        """Получает доступные временные слоты для услуг по telegram_id мастера"""
        total_duration = UtilsWrapper.calculate_total_duration(service_ids)
        
        if master_telegram_id:
            # Для конкретного мастера по telegram_id
            # Сначала получаем master_id по telegram_id
            master = db.get_master_by_telegram_id(master_telegram_id)
            if not master:
                return []
            master_id = master['id']
            return db.get_available_time_slots(master_id, appointment_date, total_duration)
        else:
            # Для любого мастера
            # Получаем всех мастеров, которые предоставляют все услуги
            conn = db.get_connection()
            cursor = conn.cursor()
            
            # Запрос для поиска мастеров, которые предоставляют все выбранные услуги
            placeholders = ', '.join('?' for _ in service_ids)
            query = f"""
                SELECT m.id as master_id, u.telegram_id
                FROM master_services ms
                JOIN masters m ON ms.master_id = m.id
                JOIN users u ON m.user_id = u.id
                WHERE ms.service_id IN ({placeholders})
                GROUP BY m.id, u.telegram_id
                HAVING COUNT(DISTINCT ms.service_id) = ?
            """
            
            cursor.execute(query, tuple(service_ids) + (len(service_ids),))
            masters = cursor.fetchall()
            conn.close()
            
            # Получаем доступные слоты для каждого мастера
            all_slots = []
            for master in masters:
                master_id = master['master_id']
                telegram_id = master['telegram_id']
                slots = db.get_available_time_slots(master_id, appointment_date, total_duration)
                all_slots.extend([(telegram_id, slot) for slot in slots])
            
            # Преобразуем в нужный формат
            return [{'master_telegram_id': telegram_id, 'time': slot} for telegram_id, slot in all_slots]
    
    @staticmethod
    def find_master_for_time_slot(service_ids, appointment_date, time_slot):
        """Находит мастера (telegram_id) для заданного временного слота"""
        conn = db.get_connection()
        cursor = conn.cursor()
        
        total_duration = UtilsWrapper.calculate_total_duration(service_ids)
        
        # Ищем мастеров, которые предоставляют все услуги
        placeholders = ', '.join('?' for _ in service_ids)
        query = f"""
            SELECT m.id as master_id, u.telegram_id
            FROM master_services ms
            JOIN masters m ON ms.master_id = m.id
            JOIN users u ON m.user_id = u.id
            WHERE ms.service_id IN ({placeholders})
            GROUP BY m.id, u.telegram_id
            HAVING COUNT(DISTINCT ms.service_id) = ?
        """
        
        cursor.execute(query, tuple(service_ids) + (len(service_ids),))
        masters = cursor.fetchall()
        
        # Проверяем доступность слота у каждого мастера
        for master in masters:
            master_id = master['master_id']
            telegram_id = master['telegram_id']
            
            # Проверяем, свободен ли мастер в это время
            time_slots = db.get_available_time_slots(master_id, appointment_date, total_duration)
            if time_slot in time_slots:
                conn.close()
                return telegram_id  # Возвращаем telegram_id
        
        conn.close()
        return None
    
    @staticmethod
    def validate_time_slot(master_telegram_id, appointment_date, time_slot, service_ids):
        """Проверяет доступность временного слота для мастера по telegram_id"""
        # Сначала получаем master_id по telegram_id
        master = db.get_master_by_telegram_id(master_telegram_id)
        if not master:
            return False
        
        master_id = master['id']
        total_duration = UtilsWrapper.calculate_total_duration(service_ids)
        time_slots = db.get_available_time_slots(master_id, appointment_date, total_duration)
        return time_slot in time_slots
    
    @staticmethod
    def generate_appointment_summary(service_ids, appointment_date, time_slot, master_telegram_id, language):
        """Генерирует сводку бронирования по telegram_id мастера"""
        # Получаем информацию об услугах
        services = []
        for service_id in service_ids:
            service = db.get_service_by_id(service_id, language)
            if service:
                services.append(service)
        
        # Получаем информацию о мастере по telegram_id
        master_info = None
        master_name = None
        master_id = None
        
        if master_telegram_id:
            master = db.get_master_by_telegram_id(master_telegram_id)
            if master:
                master_info = master
                master_id = master.get('id')
                master_name = f"{master.get('first_name', '')} {master.get('last_name', '')}".strip()
        
        # Рассчитываем общую стоимость
        total_price = UtilsWrapper.calculate_total_price(service_ids)
        
        return {
            'date': appointment_date.isoformat() if isinstance(appointment_date, date) else appointment_date,
            'time': time_slot,
            'master_telegram_id': master_telegram_id,
            'master_id': master_id,
            'master': master_info,
            'master_name': master_name,
            'services': services,
            'total_price': total_price,
            'total_duration': UtilsWrapper.calculate_total_duration(service_ids)
        }
    
    @staticmethod
    def check_user_is_master(telegram_id):
        """Проверяет, является ли пользователь мастером по telegram_id"""
        return db.check_user_is_master(telegram_id)
    
    @staticmethod
    def get_user_language(user_id):
        """Получает язык пользователя"""
        return db.get_user_language(user_id)

Utils = UtilsWrapper

# Состояния
(
    LANGUAGE_SELECTION,
    MAIN_MENU,
    CATEGORY_SELECTION,
    SERVICE_SELECTION,
    DATE_SELECTION,
    MASTER_CHOICE,
    MASTER_SELECTION,
    TIME_SELECTION,
    APPOINTMENT_CONFIRMATION,
    MY_APPOINTMENTS,
    APPOINTMENT_DETAIL
) = range(11)

# ==================== ФУНКЦИИ УВЕДОМЛЕНИЙ ====================

async def notify_master_about_appointment(application, master_telegram_id: int, appointment_id: int, 
                                         client_name: str, appointment_date: str, 
                                         appointment_time: str, services_info: str, 
                                         language: str = 'ru', client_username: str = None):
    """Отправляет уведомление мастеру о новой записи по telegram_id"""
    try:
        if not master_telegram_id:
            logger.warning("Не указан telegram_id мастера для уведомления")
            return False
        
        logger.info(f"Отправка уведомления мастеру: TG_ID={master_telegram_id}")
        
        # Формируем отображаемое имя клиента
        client_display_name = client_name
        if client_username:
            client_display_name += f" (@{client_username})"
        
        # Формируем сообщение для мастера
        if language == 'ru':
            message = f"📱 *НОВАЯ ЗАПИСЬ #{appointment_id}*\n\n"
            message += f"👤 *Клиент:* {client_display_name}\n"
            message += f"📅 *Дата:* {appointment_date}\n"
            message += f"⏰ *Время:* {appointment_time}\n"
            message += f"💅 *Услуги:* {services_info}\n\n"
            message += "✅ Запись ожидает подтверждения"
            
            keyboard = [
                [InlineKeyboardButton("✅ Подтвердить", callback_data=f"master_confirm_{appointment_id}"),
                 InlineKeyboardButton("❌ Отклонить", callback_data=f"master_reject_{appointment_id}")],
                [InlineKeyboardButton("📋 Посмотреть все записи", callback_data="master_appointments")]
            ]
            
        elif language == 'en':
            message = f"📱 *NEW APPOINTMENT #{appointment_id}*\n\n"
            message += f"👤 *Client:* {client_display_name}\n"
            message += f"📅 *Date:* {appointment_date}\n"
            message += f"⏰ *Time:* {appointment_time}\n"
            message += f"💅 *Services:* {services_info}\n\n"
            message += "✅ Appointment is pending confirmation"
            
            keyboard = [
                [InlineKeyboardButton("✅ Confirm", callback_data=f"master_confirm_{appointment_id}"),
                 InlineKeyboardButton("❌ Reject", callback_data=f"master_reject_{appointment_id}")],
                [InlineKeyboardButton("📋 View All Appointments", callback_data="master_appointments")]
            ]
            
        else:  # tr
            message = f"📱 *YENİ RANDEVU #{appointment_id}*\n\n"
            message += f"👤 *Müşteri:* {client_display_name}\n"
            message += f"📅 *Tarih:* {appointment_date}\n"
            message += f"⏰ *Saat:* {appointment_time}\n"
            message += f"💅 *Hizmetler:* {services_info}\n\n"
            message += "✅ Randevu onay bekliyor"
            
            keyboard = [
                [InlineKeyboardButton("✅ Onayla", callback_data=f"master_confirm_{appointment_id}"),
                 InlineKeyboardButton("❌ Reddet", callback_data=f"master_reject_{appointment_id}")],
                [InlineKeyboardButton("📋 Tüm Randevular", callback_data="master_appointments")]
            ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Отправляем сообщение мастеру
        await application.bot.send_message(
            chat_id=int(master_telegram_id),
            text=message,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
        logger.info(f"Уведомление отправлено мастеру с Telegram ID {master_telegram_id} о записи #{appointment_id}")
        logger.info(f"Информация о клиенте: имя={client_name}, никнейм={client_username}")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка при отправке уведомления мастеру: {e}", exc_info=True)
        return False
async def notify_client_about_appointment_update(application, client_telegram_id: int, 
                                                appointment_id: int, status: str, 
                                                master_name: str = None, language: str = 'ru'):
    """Отправляет уведомление клиенту об изменении статуса записи"""
    try:
        if status == 'confirmed':
            if language == 'ru':
                message = f"✅ *Ваша запись #{appointment_id} подтверждена"
                if master_name:
                    message += f" мастером {master_name}"
                message += "*\n\nЖдем вас в указанное время!"
            elif language == 'en':
                message = f"✅ *Your appointment #{appointment_id} has been confirmed"
                if master_name:
                    message += f" by {master_name}"
                message += "*\n\nWe look forward to seeing you at the scheduled time!"
            else:  # tr
                message = f"✅ *Randevunuz #{appointment_id} onaylandı"
                if master_name:
                    message += f" {master_name} tarafından"
                message += "*\n\nBelirtilen saatte sizi bekliyoruz!"
                
        elif status == 'rejected':
            if language == 'ru':
                message = f"❌ *Ваша запись #{appointment_id} отклонена"
                if master_name:
                    message += f" мастером {master_name}"
                message += "*\n\nПожалуйста, выберите другое время или мастера."
            elif language == 'en':
                message = f"❌ *Your appointment #{appointment_id} has been rejected"
                if master_name:
                    message += f" by {master_name}"
                message += "*\n\nPlease choose another time or master."
            else:  # tr
                message = f"❌ *Randevunuz #{appointment_id} reddedildi"
                if master_name:
                    message += f" {master_name} tarafından"
                message += "*\n\nLütfen başka bir zaman veya usta seçin."
        
        else:
            return False
        
        await application.bot.send_message(
            chat_id=client_telegram_id,
            text=message,
            parse_mode='Markdown'
        )
        
        logger.info(f"Уведомление об изменении статуса отправлено клиенту {client_telegram_id} для записи #{appointment_id}")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка при отправке уведомления клиенту: {e}")
        return False

# ==================== ОБРАБОТЧИКИ МАСТЕРА ====================

async def handle_master_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка callback-запросов для мастера"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    language = context.user_data.get('language', 'ru')
    
    master_user = update.effective_user  # Получаем объект пользователя мастера
    telegram_id = master_user.id
    master_username = master_user.username  # Никнейм мастера (@username)
    master_first_name = master_user.first_name  # Имя мастера
    master_last_name = master_user.last_name  # Фамилия мастера
    
    logger.info(f"Master callback: user_id={telegram_id}, username={master_username}, data={data}")
    
    # Формируем отображаемое имя мастера
    master_display_name = ""
    if master_username:
        master_display_name = f"@{master_username}"
    elif master_first_name:
        master_display_name = master_first_name
        if master_last_name:
            master_display_name += f" {master_last_name}"
    else:
        master_display_name = f"Мастер {telegram_id}"
    
    # Подтверждение записи мастером
    if data.startswith("master_confirm_"):
        appointment_id = int(data.split("_")[2])
        
        try:
            conn = db.get_connection()
            cursor = conn.cursor()
            
            # Находим запись, привязанную к этому мастеру (по telegram_id)
            cursor.execute("""
                SELECT a.id, a.master_telegram_id, u.telegram_id as client_telegram_id,
                       u.language as client_language, u.first_name as client_first_name,
                       u.last_name as client_last_name
                FROM appointments a
                JOIN users u ON a.client_id = u.id
                WHERE a.id = ? AND a.master_telegram_id = ?
            """, (appointment_id, str(telegram_id)))
            
            appointment_info = cursor.fetchone()
            
            if not appointment_info:
                logger.error(f"Запись {appointment_id} не принадлежит мастеру {telegram_id}")
                await query.edit_message_text("❌ Ошибка: запись не найдена или не принадлежит вам")
                conn.close()
                return
            
            appointment_info_dict = dict(appointment_info)
            
            # Обновляем статус записи
            cursor.execute("""
                UPDATE appointments 
                SET status = 'confirmed', updated_at = ?
                WHERE id = ? AND master_telegram_id = ?
            """, (datetime.now(), appointment_id, str(telegram_id)))
            
            affected_rows = cursor.rowcount
            
            if affected_rows == 0:
                logger.warning(f"Не удалось подтвердить запись {appointment_id}")
                await query.edit_message_text("❌ Не удалось подтвердить запись")
                conn.rollback()
                conn.close()
                return
            
            conn.commit()
            
            # Отправляем уведомление клиенту
            client_name = f"{appointment_info_dict['client_first_name']} {appointment_info_dict['client_last_name']}".strip()
            await notify_client_about_appointment_update(
                application=context.application,
                client_telegram_id=appointment_info_dict['client_telegram_id'],
                appointment_id=appointment_id,
                status='confirmed',
                master_name=master_display_name,  # Используем имя/никнейм мастера из Telegram
                language=appointment_info_dict['client_language'] or 'ru'
            )
            
            conn.close()
            
            # Обновляем сообщение для мастера
            if language == 'ru':
                message = f"✅ Запись #{appointment_id} подтверждена!\n\nКлиент {client_name} получил уведомление."
            elif language == 'en':
                message = f"✅ Appointment #{appointment_id} confirmed!\n\nClient {client_name} has been notified."
            else:  # tr
                message = f"✅ Randevu #{appointment_id} onaylandı!\n\nMüşteri {client_name} bilgilendirildi."
            
            await query.edit_message_text(
                text=message,
                reply_markup=None
            )
            
        except Exception as e:
            logger.error(f"Ошибка при подтверждении записи мастером: {e}", exc_info=True)
            await query.edit_message_text("❌ Произошла ошибка при подтверждении записи")
    
    # Отклонение записи мастером
    elif data.startswith("master_reject_"):
        appointment_id = int(data.split("_")[2])
        
        try:
            conn = db.get_connection()
            cursor = conn.cursor()
            
            # Находим запись, привязанную к этому мастеру (по telegram_id)
            cursor.execute("""
                SELECT a.id, a.master_telegram_id, u.telegram_id as client_telegram_id,
                       u.language as client_language, u.first_name as client_first_name,
                       u.last_name as client_last_name
                FROM appointments a
                JOIN users u ON a.client_id = u.id
                WHERE a.id = ? AND a.master_telegram_id = ?
            """, (appointment_id, str(telegram_id)))
            
            appointment_info = cursor.fetchone()
            
            if not appointment_info:
                logger.error(f"Запись {appointment_id} не принадлежит мастеру {telegram_id}")
                await query.edit_message_text("❌ Ошибка: запись не найдена или не принадлежит вам")
                conn.close()
                return
            
            appointment_info_dict = dict(appointment_info)
            
            # Обновляем статус записи
            cursor.execute("""
                UPDATE appointments 
                SET status = 'rejected', updated_at = ?
                WHERE id = ? AND master_telegram_id = ?
            """, (datetime.now(), appointment_id, str(telegram_id)))
            
            affected_rows = cursor.rowcount
            
            if affected_rows == 0:
                logger.warning(f"Не удалось отклонить запись {appointment_id}")
                await query.edit_message_text("❌ Не удалось отклонить запись")
                conn.rollback()
                conn.close()
                return
            
            conn.commit()
            
            # Отправляем уведомление клиенту
            client_name = f"{appointment_info_dict['client_first_name']} {appointment_info_dict['client_last_name']}".strip()
            await notify_client_about_appointment_update(
                application=context.application,
                client_telegram_id=appointment_info_dict['client_telegram_id'],
                appointment_id=appointment_id,
                status='rejected',
                master_name=master_display_name,  # Используем имя/никнейм мастера из Telegram
                language=appointment_info_dict['client_language'] or 'ru'
            )
            
            conn.close()
            
            # Обновляем сообщение для мастера
            if language == 'ru':
                message = f"❌ Запись #{appointment_id} отклонена!\n\nКлиент {client_name} получил уведомление."
            elif language == 'en':
                message = f"❌ Appointment #{appointment_id} rejected!\n\nClient {client_name} has been notified."
            else:  # tr
                message = f"❌ Randevu #{appointment_id} reddedildi!\n\nMüşteri {client_name} bilgilendirildi."
            
            await query.edit_message_text(
                text=message,
                reply_markup=None
            )
            
        except Exception as e:
            logger.error(f"Ошибка при отклонении записи мастером: {e}", exc_info=True)
            await query.edit_message_text("❌ Произошла ошибка при отклонении записи")
    
    # Просмотр записей мастера
    elif data == "master_appointments":
        try:
            # Получаем записи мастера по telegram_id
            appointments = db.get_master_appointments_by_telegram_id(telegram_id)
            
            if not appointments:
                if language == 'ru':
                    await query.edit_message_text("📋 У вас пока нет записей.")
                elif language == 'en':
                    await query.edit_message_text("📋 You have no appointments yet.")
                else:  # tr
                    await query.edit_message_text("📋 Henüz randevunuz yok.")
                return
            
            if language == 'ru':
                message = "📋 Ваши записи:\n\n"
            elif language == 'en':
                message = "📋 Your appointments:\n\n"
            else:  # tr
                message = "📋 Randevularınız:\n\n"
            
            for i, appointment in enumerate(appointments, 1):
                date_str = appointment['appointment_date']
                time_str = appointment['start_time']
                client_name = f"{appointment['client_first_name']} {appointment['client_last_name']}".strip()
                services = appointment.get('services_titles', 'Не указаны')
                
                if len(services) > 30:
                    services = services[:30] + "..."
                
                status_emoji = {
                    'pending': '⏳',
                    'confirmed': '✅',
                    'rejected': '❌',
                    'cancelled': '🚫',
                    'completed': '🎉'
                }.get(appointment['status'], '❓')
                
                message += f"{i}. {status_emoji} 📅 {date_str} ⏰ {time_str}\n"
                message += f"   👤 {client_name}\n"
                message += f"   💅 {services}\n"
                message += f"   📊 Статус: {appointment['status']}\n\n"
            
            keyboard = [[InlineKeyboardButton(
                "⬅️ Назад" if language == 'ru' else 
                "⬅️ Back" if language == 'en' else 
                "⬅️ Geri", 
                callback_data="back_to_master_menu"
            )]]
            
            await query.edit_message_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            logger.error(f"Ошибка при показе записей мастера: {e}")
            await query.edit_message_text("❌ Произошла ошибка при получении записей")

# ==================== НОВАЯ ФУНКЦИЯ: ОБРАБОТКА КНОПОК ГЛАВНОГО МЕНЮ ====================

async def handle_main_menu_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстовых команд из главного меню из любого состояния"""
    text = update.message.text
    language = context.user_data.get('language', 'ru')
    is_master = context.user_data.get('is_master', False)
    
    # Проверяем, является ли команда из главного меню
    main_menu_commands = []
    if is_master:
        main_menu_commands = [
            "Мои записи на сегодня", "Today's Appointments", "Bugünkü Randevular",
            "Все записи", "All Appointments", "Tüm Randevular",
            "Свободные слоты", "Available Slots", "Uygun Zamanlar",
            "Профиль", "Profile", "Profil",
            "Сменить язык", "Change Language", "Dil Değiştir"
        ]
    else:
        main_menu_commands = [
            "💇 Записаться на услугу", "💇 Book a Service", "💇 Randevu Al",
            "📋 Мои записи", "📋 My Appointments", "📋 Randevularım",
            "👤 Мой профиль", "👤 My Profile", "👤 Profilim",
            "ℹ️ О салоне", "ℹ️ About Salon", "ℹ️ Salon Hakkında",
            "🌐 Сменить язык", "🌐 Change Language", "🌐 Dil Değiştir"
        ]
    
    if text in main_menu_commands:
        # Сбрасываем текущее состояние и возвращаем в главное меню
        context.user_data['selected_services'] = []
        context.user_data['appointment_date'] = None
        context.user_data['master_telegram_id'] = None
        context.user_data['appointment_summary'] = None
        context.user_data['state'] = MAIN_MENU
        
        # Вызываем обработку как в главном меню
        return await handle_main_menu(update, context)
    
    # Если команда не из главного меню, показываем сообщение
    if language == 'ru':
        await update.message.reply_text(
            "⚠️ Сначала завершите текущее действие или нажмите /cancel",
            reply_markup=ReplyKeyboardRemove()
        )
    elif language == 'en':
        await update.message.reply_text(
            "⚠️ Please finish current action or press /cancel",
            reply_markup=ReplyKeyboardRemove()
        )
    else:  # tr
        await update.message.reply_text(
            "⚠️ Lütfen mevcut işlemi tamamlayın veya /cancel tuşuna basın",
            reply_markup=ReplyKeyboardRemove()
        )
    
    # Возвращаем текущее состояние (не меняем его)
    return context.user_data.get('state', MAIN_MENU)

# ==================== ОСНОВНЫЕ ОБРАБОТЧИКИ ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка команды /start"""
    user = update.effective_user
    
    logger.info(f"Пользователь зашел: TG ID={user.id}, Имя={user.first_name}")
    
    try:
        # Получаем или создаем пользователя
        user_db = db.get_or_create_user(
            telegram_id=user.id,
            first_name=user.first_name or "Пользователь",
            last_name=user.last_name or "",
            username=user.username or ""
        )
        
        logger.info(f"Данные пользователя из БД: {user_db}")
        
        # Проверяем, является ли пользователь мастером
        master_info = Utils.check_user_is_master(user.id)
        
        if master_info:
            logger.info(f"Пользователь является мастером: {master_info}")
            
            # Пользователь - мастер
            context.user_data['is_master'] = True
            context.user_data['master_telegram_id'] = user.id
            context.user_data['master_id'] = master_info.get('master_id')
            context.user_data['user_id'] = master_info['user_id']
            context.user_data['language'] = master_info.get('language', 'ru')
            context.user_data['telegram_id'] = user.id
            
            welcome_message = f"👨‍💼 Добро пожаловать, мастер {master_info['first_name']}!"
            
            # Предлагаем мастерское меню
            reply_markup = Keyboards.get_master_menu_keyboard(context.user_data['language'])
            
        else:
            logger.info("Пользователь является клиентом")
            
            # Пользователь - клиент
            context.user_data['is_master'] = False
            context.user_data['user_id'] = user_db['id']
            context.user_data['language'] = user_db.get('language', 'ru')
            context.user_data['telegram_id'] = user.id
            
            welcome_message = f"👋 Добро пожаловать, {user_db['first_name']}!"
            reply_markup = Keyboards.get_main_menu_keyboard(context.user_data['language'])
        
        context.user_data['state'] = MAIN_MENU
        
        await update.message.reply_text(
            welcome_message + "\n\n" + Messages.get_language_set_message(context.user_data['language']),
            reply_markup=reply_markup
        )
        return MAIN_MENU
        
    except Exception as e:
        logger.error(f"Ошибка при старте: {e}", exc_info=True)
        await update.message.reply_text(
            "Произошла ошибка при запуске бота. Пожалуйста, попробуйте еще раз."
        )
        return ConversationHandler.END

async def handle_language_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора языка"""
    text = update.message.text
    
    if "Русский" in text or "Russian" in text:
        language = 'ru'
    elif "English" in text:
        language = 'en'
    elif "Türkçe" in text:
        language = 'tr'
    else:
        language = 'ru'
    
    user_id = context.user_data.get('user_id')
    
    if user_id:
        db.update_user_language(user_id, language)
    
    context.user_data['language'] = language
    context.user_data['state'] = MAIN_MENU
    
    # Выбираем правильное меню в зависимости от роли
    if context.user_data.get('is_master'):
        reply_markup = Keyboards.get_master_menu_keyboard(language)
    else:
        reply_markup = Keyboards.get_main_menu_keyboard(language)
    
    await update.message.reply_text(
        Messages.get_language_set_message(language),
        reply_markup=reply_markup
    )
    return MAIN_MENU

async def handle_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка главного меню"""
    text = update.message.text
    language = context.user_data.get('language', 'ru')
    is_master = context.user_data.get('is_master', False)
    
    if is_master:
        # Обработка меню мастера
        if "Мои записи на сегодня" in text or "Today's Appointments" in text or "Bugünkü Randevular" in text:
            # Показ записей мастера на сегодня
            master_telegram_id = context.user_data.get('telegram_id')
            if not master_telegram_id:
                await update.message.reply_text("Ошибка: не найден ID мастера")
                return MAIN_MENU
            
            today = date.today()
            appointments = db.get_master_appointments_by_telegram_id_and_date(master_telegram_id, today)
            
            if not appointments:
                if language == 'ru':
                    await update.message.reply_text("📅 У вас нет записей на сегодня.")
                elif language == 'en':
                    await update.message.reply_text("📅 You have no appointments for today.")
                else:  # tr
                    await update.message.reply_text("📅 Bugün için randevunuz yok.")
            else:
                if language == 'ru':
                    message = "📅 Ваши записи на сегодня:\n\n"
                elif language == 'en':
                    message = "📅 Your appointments for today:\n\n"
                else:  # tr
                    message = "📅 Bugünkü randevularınız:\n\n"
                
                for i, appointment in enumerate(appointments, 1):
                    time_str = appointment['start_time']
                    client_name = f"{appointment['client_first_name']} {appointment['client_last_name']}".strip()
                    services = appointment.get('services_titles', 'Не указаны')
                    
                    if len(services) > 30:
                        services = services[:30] + "..."
                    
                    message += f"{i}. ⏰ {time_str} - {client_name}\n"
                    message += f"   💅 {services}\n\n"
                
                await update.message.reply_text(message)
            
            return MAIN_MENU
            
        elif "Все записи" in text or "All Appointments" in text or "Tüm Randevular" in text:
            # Показать все записи мастера
            master_telegram_id = context.user_data.get('telegram_id')
            if not master_telegram_id:
                await update.message.reply_text("Ошибка: не найден ID мастера")
                return MAIN_MENU
            
            appointments = db.get_master_appointments_by_telegram_id(master_telegram_id)
            
            if not appointments:
                if language == 'ru':
                    await update.message.reply_text("📋 У вас пока нет записей.")
                elif language == 'en':
                    await update.message.reply_text("📋 You have no appointments yet.")
                else:  # tr
                    await update.message.reply_text("📋 Henüz randevunuz yok.")
            else:
                if language == 'ru':
                    message = "📋 Все ваши записи:\n\n"
                elif language == 'en':
                    message = "📋 All your appointments:\n\n"
                else:  # tr
                    message = "📋 Tüm randevularınız:\n\n"
                
                for i, appointment in enumerate(appointments, 1):
                    date_str = appointment['appointment_date']
                    time_str = appointment['start_time']
                    client_name = f"{appointment['client_first_name']} {appointment['client_last_name']}".strip()
                    services = appointment.get('services_titles', 'Не указаны')
                    
                    if len(services) > 30:
                        services = services[:30] + "..."
                    
                    message += f"{i}. 📅 {date_str} ⏰ {time_str}\n"
                    message += f"   👤 {client_name}\n"
                    message += f"   💅 {services}\n"
                    message += f"   📊 Статус: {appointment['status']}\n\n"
                
                await update.message.reply_text(message)
            
            return MAIN_MENU
            
        elif "Свободные слоты" in text or "Available Slots" in text or "Uygun Zamanlar" in text:
            # Показать свободные слоты мастера
            master_telegram_id = context.user_data.get('telegram_id')
            if not master_telegram_id:
                await update.message.reply_text("Ошибка: не найден ID мастера")
                return MAIN_MENU
            
            # Сначала получаем master_id по telegram_id
            master = db.get_master_by_telegram_id(master_telegram_id)
            if not master:
                await update.message.reply_text("Ошибка: мастер не найден")
                return MAIN_MENU
            
            master_id = master['id']
            
            # Показываем свободные слоты на сегодня
            today = date.today()
            # Получаем услуги мастера для расчета длительности
            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT service_id FROM master_services WHERE master_id = ?
            """, (master_id,))
            service_ids = [row['service_id'] for row in cursor.fetchall()]
            conn.close()
            
            # Берем минимальную длительность услуги для демонстрации
            min_duration = 60  # 1 час по умолчанию
            if service_ids:
                for service_id in service_ids:
                    service = db.get_service_by_id(service_id, 'ru')
                    if service and service.get('duration_minutes'):
                        if service['duration_minutes'] < min_duration:
                            min_duration = service['duration_minutes']
            
            time_slots = db.get_available_time_slots(master_id, today, min_duration)
            
            if not time_slots:
                if language == 'ru':
                    await update.message.reply_text("⏰ На сегодня нет свободных слотов.")
                elif language == 'en':
                    await update.message.reply_text("⏰ No available slots for today.")
                else:  # tr
                    await update.message.reply_text("⏰ Bugün için uygun zaman yok.")
            else:
                if language == 'ru':
                    message = f"⏰ Свободные слоты на сегодня ({today.strftime('%d.%m.%Y')}):\n\n"
                elif language == 'en':
                    message = f"⏰ Available slots for today ({today.strftime('%Y-%m-%d')}):\n\n"
                else:  # tr
                    message = f"⏰ Bugün için uygun zamanlar ({today.strftime('%d.%m.%Y')}):\n\n"
                
                for i in range(0, len(time_slots), 5):
                    slots = time_slots[i:i+5]
                    message += "  ".join(slots) + "\n"
                
                await update.message.reply_text(message)
            
            return MAIN_MENU
            
        elif "Профиль" in text or "Profile" in text or "Profil" in text:
            # Показ профиля мастера
            master_telegram_id = context.user_data.get('telegram_id')
            user_id = context.user_data.get('user_id')
            
            if not master_telegram_id or not user_id:
                await update.message.reply_text("Ошибка: не найден ID мастера")
                return MAIN_MENU
            
            master = db.get_master_by_telegram_id(master_telegram_id)
            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT first_name, last_name, phone, email FROM users WHERE id = ?", (user_id,))
            user = cursor.fetchone()
            conn.close()
            
            if master and user:
                user_dict = dict(user)
                if language == 'ru':
                    message = f"👨‍💼 Ваш профиль мастера:\n\n"
                    message += f"Имя: {user_dict['first_name']}\n"
                    if user_dict['last_name']:
                        message += f"Фамилия: {user_dict['last_name']}\n"
                    if user_dict['phone']:
                        message += f"Телефон: {user_dict['phone']}\n"
                    message += f"Telegram ID: {master_telegram_id}\n"
                    if master.get('qualification'):
                        message += f"Квалификация: {master['qualification']}\n"
                    if master.get('description'):
                        message += f"Описание: {master['description']}\n"
                elif language == 'en':
                    message = f"👨‍💼 Your master profile:\n\n"
                    message += f"First name: {user_dict['first_name']}\n"
                    if user_dict['last_name']:
                        message += f"Last name: {user_dict['last_name']}\n"
                    if user_dict['phone']:
                        message += f"Phone: {user_dict['phone']}\n"
                    message += f"Telegram ID: {master_telegram_id}\n"
                    if master.get('qualification'):
                        message += f"Qualification: {master['qualification']}\n"
                    if master.get('description'):
                        message += f"Description: {master['description']}\n"
                else:  # tr
                    message = f"👨‍💼 Usta profiliniz:\n\n"
                    message += f"Ad: {user_dict['first_name']}\n"
                    if user_dict['last_name']:
                        message += f"Soyad: {user_dict['last_name']}\n"
                    if user_dict['phone']:
                        message += f"Telefon: {user_dict['phone']}\n"
                    message += f"Telegram ID: {master_telegram_id}\n"
                    if master.get('qualification'):
                        message += f"Uzmanlık: {master['qualification']}\n"
                    if master.get('description'):
                        message += f"Açıklama: {master['description']}\n"
                
                await update.message.reply_text(message)
            
            return MAIN_MENU
            
        elif "Сменить язык" in text or "Change Language" in text or "Dil Değiştir" in text:
            # Смена языка
            context.user_data['state'] = LANGUAGE_SELECTION
            await update.message.reply_text(
                Messages.get_welcome_message(language),
                reply_markup=Keyboards.get_language_keyboard()
            )
            return LANGUAGE_SELECTION
            
        else:
            # Неизвестная команда для мастера
            await update.message.reply_text(
                "Неизвестная команда. Используйте кнопки меню.",
                reply_markup=Keyboards.get_master_menu_keyboard(language)
            )
            return MAIN_MENU
    
    else:
        # Обработка меню клиента
        if "Записаться на услугу" in text or "Book a Service" in text or "Randevu Al" in text:
            # Начало записи
            context.user_data['state'] = CATEGORY_SELECTION
            context.user_data['selected_services'] = []
            
            # Получаем категории верхнего уровня
            categories = db.get_categories(language, parent_id=None)
            
            if not categories:
                await update.message.reply_text(
                    Messages.get_no_categories_message(language)
                )
                return MAIN_MENU
            
            await update.message.reply_text(
                Messages.get_categories_message(language),
                reply_markup=Keyboards.get_categories_keyboard(categories, language)
            )
            return CATEGORY_SELECTION
        
        elif "Мои записи" in text or "My Appointments" in text or "Randevularım" in text:
            # Просмотр записей
            user_id = context.user_data.get('user_id')
            appointments = db.get_user_appointments(user_id, limit=10)
            
            if not appointments:
                await update.message.reply_text(
                    Messages.get_no_appointments_message(language)
                )
                return MAIN_MENU
            
            # Формируем сообщение с записями
            message_text = Messages.get_my_appointments_message(language) + "\n\n"
            
            for i, appointment in enumerate(appointments, 1):
                date_str = appointment['appointment_date']
                time_str = appointment['start_time']
                services = appointment.get('services_titles', 'Не указаны')
                
                if len(services) > 30:
                    services = services[:30] + "..."
                
                message_text += f"{i}. 📅 {date_str} ⏰ {time_str}\n"
                message_text += f"   💅 {services}\n"
                message_text += f"   📊 Статус: {appointment['status']}\n\n"
            
            await update.message.reply_text(message_text)
            return MAIN_MENU
        
        elif "Сменить язык" in text or "Change Language" in text or "Dil Değiştir" in text:
            # Смена языка
            context.user_data['state'] = LANGUAGE_SELECTION
            await update.message.reply_text(
                Messages.get_welcome_message(language),
                reply_markup=Keyboards.get_language_keyboard()
            )
            return LANGUAGE_SELECTION
        
        elif "Мой профиль" in text or "My Profile" in text or "Profilim" in text:
            # Показ профиля
            user_id = context.user_data.get('user_id')
            conn = db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT first_name, last_name, phone, email, created_at FROM users WHERE id = ?", (user_id,))
            result = cursor.fetchone()
            conn.close()
            
            if result:
                user = dict(result)
                if language == 'ru':
                    message = f"👤 Ваш профиль:\n\nИмя: {user['first_name']}\n"
                    if user['last_name']:
                        message += f"Фамилия: {user['last_name']}\n"
                    if user['phone']:
                        message += f"Телефон: {user['phone']}\n"
                    if user['email']:
                        message += f"Email: {user['email']}\n"
                    message += f"Telegram ID: {context.user_data['telegram_id']}\n"
                    message += f"Язык: {language}"
                elif language == 'en':
                    message = f"👤 Your profile:\n\nFirst name: {user['first_name']}\n"
                    if user['last_name']:
                        message += f"Last name: {user['last_name']}\n"
                    if user['phone']:
                        message += f"Phone: {user['phone']}\n"
                    if user['email']:
                        message += f"Email: {user['email']}\n"
                    message += f"Telegram ID: {context.user_data['telegram_id']}\n"
                    message += f"Language: {language}"
                else:  # tr
                    message = f"👤 Profiliniz:\n\nAd: {user['first_name']}\n"
                    if user['last_name']:
                        message += f"Soyad: {user['last_name']}\n"
                    if user['phone']:
                        message += f"Telefon: {user['phone']}\n"
                    if user['email']:
                        message += f"E-posta: {user['email']}\n"
                    message += f"Telegram ID: {context.user_data['telegram_id']}\n"
                    message += f"Dil: {language}"
                
                await update.message.reply_text(message)
            
            return MAIN_MENU
        
        elif "О салоне" in text or "About Salon" in text or "Salon Hakkında" in text:
            # Информация о салоне
            if language == 'ru':
                info = """
                💈 Салон красоты "Элегант"

                🕐 Часы работы:
                Пн-Пт: 9:00 - 20:00
                Сб-Вс: 10:00 - 18:00

                📍 Адрес:
                ул. Красивая, д. 123

                📞 Телефон:
                +7 (999) 123-45-67
                """
            elif language == 'en':
                info = """
                💈 Beauty Salon "Elegant"

                🕐 Working hours:
                Mon-Fri: 9:00 AM - 8:00 PM
                Sat-Sun: 10:00 AM - 6:00 PM

                📍 Address:
                Beautiful Street, 123

                📞 Phone:
                +7 (999) 123-45-67
                """
            else:  # tr
                info = """
                💈 Güzellik Salonu "Elegant"

                🕐 Çalışma saatleri:
                Pzt-Cum: 9:00 - 20:00
                Cmt-Paz: 10:00 - 18:00

                📍 Adres:
                Güzel Sokak, No: 123

                📞 Telefon:
                +7 (999) 123-45-67
                """
            
            await update.message.reply_text(info)
            return MAIN_MENU
        
        else:
            # Неизвестная команда для клиента
            await update.message.reply_text(
                "Неизвестная команда. Используйте кнопки меню.",
                reply_markup=Keyboards.get_main_menu_keyboard(language)
            )
            return MAIN_MENU

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка callback-запросов"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    language = context.user_data.get('language', 'ru')
    state = context.user_data.get('state', MAIN_MENU)
    
    # Сначала проверяем, не является ли это callback для мастера
    if data.startswith("master_"):
        await handle_master_callback(update, context)
        return state
    
    # Обработка выбора категории
    if data.startswith("category_"):
        category_id = int(data.split("_")[1])
        category = db.get_category_by_id(category_id, language)
        
        if not category:
            await query.edit_message_text(Messages.get_error_message(language))
            return state
        
        # Проверяем, есть ли подкатегории
        subcategories = db.get_categories(language, parent_id=category_id)
        
        if subcategories:
            # Есть подкатегории
            context.user_data['parent_category_id'] = category_id
            await query.edit_message_text(
                Messages.get_categories_message(language),
                reply_markup=Keyboards.get_categories_keyboard(subcategories, language)
            )
            return CATEGORY_SELECTION
        else:
            # Нет подкатегории - переходим к услугам
            context.user_data['current_category_id'] = category_id
            context.user_data['state'] = SERVICE_SELECTION
            
            services = db.get_services_by_category(category_id, language)
            
            if not services:
                await query.edit_message_text(
                    Messages.get_no_services_message(language),
                    reply_markup=Keyboards.get_categories_keyboard([], language)
                )
                return SERVICE_SELECTION
            
            await query.edit_message_text(
                Messages.get_services_message(language, category.get('title', '')),
                reply_markup=Keyboards.get_services_keyboard(services, language, context.user_data.get('selected_services', []))
            )
            return SERVICE_SELECTION
    
    # Обработка выбора услуги
    elif data.startswith("toggle_service_"):
        service_id = int(data.split("_")[2])
        selected_services = context.user_data.get('selected_services', [])
        
        if service_id in selected_services:
            selected_services.remove(service_id)
        else:
            selected_services.append(service_id)
        
        context.user_data['selected_services'] = selected_services
        
        # Обновляем клавиатуру
        category_id = context.user_data.get('current_category_id')
        services = db.get_services_by_category(category_id, language)
        category = db.get_category_by_id(category_id, language)
        
        await query.edit_message_text(
            Messages.get_services_message(language, category.get('title', '') if category else ''),
            reply_markup=Keyboards.get_services_keyboard(services, language, selected_services)
        )
        return SERVICE_SELECTION
    
    # Завершение выбора услуг
    elif data == "finish_selection":
        selected_services = context.user_data.get('selected_services', [])
        
        if not selected_services:
            await query.answer("Выберите хотя бы одну услугу")
            return SERVICE_SELECTION
        
        # Показываем сводку
        services_info = []
        total_price = 0
        
        for service_id in selected_services:
            service = db.get_service_by_id(service_id, language)
            if service:
                services_info.append(service)
                total_price += service.get('price', 0)
        
        await query.edit_message_text(
            Messages.get_selected_services_message(language, services_info, total_price)
        )
        
        # Переходим к выбору даты
        context.user_data['state'] = DATE_SELECTION
        today = datetime.now()
        
        await query.message.reply_text(
            Messages.get_date_selection_message(language),
            reply_markup=Keyboards.get_calendar_keyboard(today.year, today.month, language)
        )
        return DATE_SELECTION
    
    # Выбор даты из календаря
    elif data.startswith("select_date_"):
        date_str = data.split("_")[2]
        appointment_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        
        # Проверяем, что дата не в прошлом
        today = date.today()
        if appointment_date < today:
            await query.answer("Нельзя выбрать прошедшую дату")
            return DATE_SELECTION
        
        context.user_data['appointment_date'] = date_str
        context.user_data['state'] = MASTER_CHOICE
        
        await query.edit_message_text(
            Messages.get_master_choice_message(language),
            reply_markup=Keyboards.get_master_choice_keyboard(language)
        )
        return MASTER_CHOICE
    
    # Выбор конкретного мастера
    elif data == "choose_master":
        selected_services = context.user_data.get('selected_services', [])
        appointment_date_str = context.user_data.get('appointment_date')
        
        if not selected_services or not appointment_date_str:
            await query.answer(Messages.get_error_message(language))
            return MASTER_CHOICE
        
        # Ищем мастеров (по telegram_id), которые предоставляют все услуги
        all_masters = {}
        
        for service_id in selected_services:
            masters_for_service = db.get_masters_for_service(service_id, language)
            
            for master in masters_for_service:
                master_id = master['id']
                telegram_id = master.get('telegram_id')
                
                if telegram_id:
                    if telegram_id not in all_masters:
                        all_masters[telegram_id] = {
                            'master': master,
                            'services_count': 1,
                            'telegram_id': telegram_id
                        }
                    else:
                        all_masters[telegram_id]['services_count'] += 1
        
        # Фильтруем мастеров
        suitable_masters = []
        for telegram_id, data in all_masters.items():
            if data['services_count'] == len(selected_services):
                suitable_masters.append(data['master'])
        
        if not suitable_masters:
            await query.edit_message_text(
                Messages.get_no_masters_message(language),
                reply_markup=Keyboards.get_master_choice_keyboard(language)
            )
            return MASTER_CHOICE
        
        context.user_data['suitable_masters'] = [m['telegram_id'] for m in suitable_masters if m.get('telegram_id')]
        context.user_data['state'] = MASTER_SELECTION
        
        await query.edit_message_text(
            Messages.get_masters_list_message(language),
            reply_markup=Keyboards.get_masters_keyboard(suitable_masters, language)
        )
        return MASTER_SELECTION
    
    # Выбор любого мастера
    elif data == "any_master":
        selected_services = context.user_data.get('selected_services', [])
        appointment_date_str = context.user_data.get('appointment_date')
        
        if not selected_services or not appointment_date_str:
            await query.answer(Messages.get_error_message(language))
            return MASTER_CHOICE
        
        appointment_date = date.fromisoformat(appointment_date_str)
        
        # Получаем доступные слоты для любого мастера (по telegram_id)
        time_slots_data = Utils.get_available_time_slots_for_services(
            selected_services, appointment_date, master_telegram_id=None
        )
        
        if not time_slots_data:
            await query.edit_message_text(
                Messages.get_no_time_slots_message(language),
                reply_markup=Keyboards.get_master_choice_keyboard(language)
            )
            return MASTER_CHOICE
        
        time_slots = [item['time'] for item in time_slots_data]
        context.user_data['master_telegram_id'] = None
        context.user_data['state'] = TIME_SELECTION
        
        await query.edit_message_text(
            Messages.get_time_selection_message(language, appointment_date_str),
            reply_markup=Keyboards.get_time_slots_keyboard(time_slots, language)
        )
        return TIME_SELECTION
    
    # Выбор конкретного мастера из списка
    elif data.startswith("select_master_"):
        master_id = int(data.split("_")[2])
        selected_services = context.user_data.get('selected_services', [])
        appointment_date_str = context.user_data.get('appointment_date')
        
        if not selected_services or not appointment_date_str:
            await query.answer(Messages.get_error_message(language))
            return MASTER_SELECTION
        
        appointment_date = date.fromisoformat(appointment_date_str)
        master = db.get_master_by_id(master_id)
        
        if not master or not master.get('telegram_id'):
            await query.answer(Messages.get_error_message(language))
            return MASTER_SELECTION
        
        # Получаем доступные слоты по master_id
        total_duration = Utils.calculate_total_duration(selected_services)
        time_slots = db.get_available_time_slots(master_id, appointment_date, total_duration)
        
        if not time_slots:
            await query.edit_message_text(
                Messages.get_no_time_slots_message(language),
                reply_markup=Keyboards.get_masters_keyboard([], language)
            )
            return MASTER_SELECTION
        
        context.user_data['master_telegram_id'] = master['telegram_id']
        context.user_data['master_id'] = master_id
        context.user_data['state'] = TIME_SELECTION
        
        master_name = f"{master.get('first_name', '')} {master.get('last_name', '')}".strip()
        
        await query.edit_message_text(
            Messages.get_time_selection_message(language, appointment_date_str, master_name),
            reply_markup=Keyboards.get_time_slots_keyboard(time_slots, language)
        )
        return TIME_SELECTION
    
    # Выбор времени
    elif data.startswith("select_time_"):
        time_slot = data.split("_")[2]
        selected_services = context.user_data.get('selected_services', [])
        appointment_date_str = context.user_data.get('appointment_date')
        master_telegram_id = context.user_data.get('master_telegram_id')
        
        if not selected_services or not appointment_date_str:
            await query.answer(Messages.get_error_message(language))
            return TIME_SELECTION
        
        appointment_date = date.fromisoformat(appointment_date_str)
        
        # Если выбран "любой мастер", ищем подходящего по telegram_id
        if master_telegram_id is None:
            master_telegram_id = Utils.find_master_for_time_slot(
                selected_services, appointment_date, time_slot
            )
            
            if not master_telegram_id:
                await query.answer("Это время уже занято")
                return TIME_SELECTION
            
            # Сохраняем найденного мастера
            context.user_data['master_telegram_id'] = master_telegram_id
        
        else:
            # Проверяем доступность для конкретного мастера по telegram_id
            is_available = Utils.validate_time_slot(
                master_telegram_id, appointment_date, time_slot, selected_services
            )
            
            if not is_available:
                await query.answer("Это время уже занято")
                return TIME_SELECTION
        
        # Получаем информацию о мастере
        master_name = None
        if master_telegram_id:
            master = db.get_master_by_telegram_id(master_telegram_id)
            if master:
                master_name = f"{master.get('first_name', '')} {master.get('last_name', '')}".strip()
        
        # Если имя мастера не получено, используем заглушку
        if not master_name:
            master_name = (
                "Любой доступный мастер" if language == 'ru' else
                "Any available master" if language == 'en' else
                "Uygun herhangi usta"
            )
        
        # Генерируем сводку по telegram_id мастера
        appointment_summary = Utils.generate_appointment_summary(
            selected_services,
            appointment_date,
            time_slot,
            master_telegram_id,
            language
        )
        
        context.user_data['appointment_summary'] = appointment_summary
        context.user_data['state'] = APPOINTMENT_CONFIRMATION
        
        # Формируем сообщение подтверждения
        confirmation_details = {
            'date': appointment_date_str,
            'time': time_slot,
            'master_name': master_name,
            'services': appointment_summary['services'],
            'total_price': appointment_summary['total_price']
        }
        
        await query.edit_message_text(
            Messages.get_appointment_confirmation_message(language, confirmation_details),
            reply_markup=Keyboards.get_confirmation_keyboard(language)
        )
        return APPOINTMENT_CONFIRMATION
    
    # Подтверждение записи
    elif data == "confirm_appointment":
        appointment_summary = context.user_data.get('appointment_summary')
        user_id = context.user_data.get('user_id')
        
        if not appointment_summary or not user_id:
            await query.edit_message_text(Messages.get_error_message(language))
            return APPOINTMENT_CONFIRMATION
        
        # Извлекаем данные
        appointment_date = date.fromisoformat(appointment_summary['date'])
        appointment_time = appointment_summary['time']
        master_telegram_id = appointment_summary.get('master_telegram_id')
        service_ids = [s['id'] for s in appointment_summary['services']]
        
        # Получаем информацию о пользователе для уведомления
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT first_name, last_name FROM users WHERE id = ?", (user_id,))
        user_info = cursor.fetchone()
        conn.close()
        
        client_name = ""
        if user_info:
            client_name = f"{user_info['first_name']} {user_info['last_name']}".strip()
        
        # Получаем username клиента из Telegram API
        client_username = None
        try:
            # Получаем telegram_id клиента из context.user_data
            client_telegram_id = context.user_data.get('telegram_id')
            if client_telegram_id:
                # Получаем информацию о пользователе из Telegram
                user_chat = await context.bot.get_chat(client_telegram_id)
                client_username = user_chat.username
                logger.info(f"Получен username клиента: {client_username}, Telegram ID: {client_telegram_id}")
        except Exception as e:
            logger.error(f"Ошибка при получении username клиента: {e}")
        
        # Создаем запись - используем master_telegram_id вместо master_id
        appointment_id, master_user_id = db.create_appointment_by_telegram_id(
            client_id=user_id,
            master_telegram_id=master_telegram_id,
            appointment_date=appointment_date,
            start_time=appointment_time,
            service_ids=service_ids,
            status='pending'
        )
        
        if not appointment_id:
            # Закрываем клавиатуру и отправляем новое сообщение с ошибкой
            try:
                await query.edit_message_reply_markup(reply_markup=None)
            except:
                pass
            
            await query.message.reply_text(
                Messages.get_error_message(language),
                reply_markup=Keyboards.get_main_menu_keyboard(language)
            )
            return MAIN_MENU
        
        # Отправляем уведомление мастеру по telegram_id
        if master_telegram_id:
            services_info = ", ".join([s.get('title', 'Услуга') for s in appointment_summary['services']])
            await notify_master_about_appointment(
                application=context.application,
                master_telegram_id=master_telegram_id,
                appointment_id=appointment_id,
                client_name=client_name or "Клиент",
                client_username=client_username,  # Передаем username клиента
                appointment_date=appointment_date.strftime('%d.%m.%Y'),
                appointment_time=appointment_time,
                services_info=services_info,
                language=language
            )
        
        # Очищаем временные данные
        context.user_data['selected_services'] = []
        context.user_data['appointment_date'] = None
        context.user_data['master_telegram_id'] = None
        context.user_data['appointment_summary'] = None
        context.user_data['state'] = MAIN_MENU
        
        # Используем клавиатуру после успешного бронирования
        await query.edit_message_text(
            text=Messages.get_appointment_success_message(language, appointment_id),
            reply_markup=Keyboards.get_after_booking_keyboard(language)
        )
        return MAIN_MENU
    
    # Отмена записи - ИСПРАВЛЕННЫЙ ВАРИАНТ
    elif data == "cancel_appointment":
        # Очищаем временные данные
        context.user_data['selected_services'] = []
        context.user_data['appointment_date'] = None
        context.user_data['master_telegram_id'] = None
        context.user_data['appointment_summary'] = None
        context.user_data['state'] = MAIN_MENU
        
        # Получаем текст сообщения в зависимости от языка
        if language == 'ru':
            message_text = "❌ Запись отменена"
        elif language == 'en':
            message_text = "❌ Booking cancelled"
        else:  # tr
            message_text = "❌ Randevu iptal edildi"
        
        # Удаляем инлайн-клавиатуру и отправляем новое сообщение
        try:
            # Сначала удаляем клавиатуру из текущего сообщения
            await query.edit_message_reply_markup(reply_markup=None)
        except:
            pass  # Игнорируем ошибку, если не удалось изменить клавиатуру
        
        # Отправляем новое сообщение с главным меню
        await query.message.reply_text(
            message_text,
            reply_markup=Keyboards.get_main_menu_keyboard(language)
        )
        
        return MAIN_MENU
    
    # Навигация назад
    elif data == "back_to_categories":
        parent_id = context.user_data.get('parent_category_id')
        
        if parent_id is None:
            # Возврат в главное меню
            context.user_data['state'] = MAIN_MENU
            
            # Используем reply_text вместо edit_message_text для создания нового сообщения
            if context.user_data.get('is_master'):
                reply_markup = Keyboards.get_master_menu_keyboard(language)
            else:
                reply_markup = Keyboards.get_main_menu_keyboard(language)
            
            # Закрываем текущее сообщение с инлайн-клавиатурой
            try:
                await query.edit_message_reply_markup(reply_markup=None)
            except:
                pass  # Игнорируем ошибку
            
            # Отправляем новое сообщение с реплай-клавиатурой
            await query.message.reply_text(
                Messages.get_language_set_message(language),
                reply_markup=reply_markup
            )
            return MAIN_MENU
        else:
            # Получаем родительскую категорию
            category = db.get_category_by_id(parent_id, language)
            grandparent_id = category.get('parent_id') if category else None
            
            categories = db.get_categories(language, parent_id=grandparent_id)
            context.user_data['parent_category_id'] = grandparent_id
            
            await query.edit_message_text(
                Messages.get_categories_message(language),
                reply_markup=Keyboards.get_categories_keyboard(categories, language)
            )
            return CATEGORY_SELECTION
    
    elif data == "back_to_services":
        category_id = context.user_data.get('current_category_id')
        selected_services = context.user_data.get('selected_services', [])
        
        services = db.get_services_by_category(category_id, language)
        category = db.get_category_by_id(category_id, language)
        
        context.user_data['state'] = SERVICE_SELECTION
        
        await query.edit_message_text(
            Messages.get_services_message(language, category.get('title', '') if category else ''),
            reply_markup=Keyboards.get_services_keyboard(services, language, selected_services)
        )
        return SERVICE_SELECTION
    
    elif data == "back_to_date":
        today = datetime.now()
        context.user_data['state'] = DATE_SELECTION
        
        await query.edit_message_text(
            Messages.get_date_selection_message(language),
            reply_markup=Keyboards.get_calendar_keyboard(today.year, today.month, language)
        )
        return DATE_SELECTION
    
    elif data == "back_to_master_choice":
        context.user_data['state'] = MASTER_CHOICE
        
        await query.edit_message_text(
            Messages.get_master_choice_message(language),
            reply_markup=Keyboards.get_master_choice_keyboard(language)
        )
        return MASTER_CHOICE
    
    elif data == "back_to_masters":
        master_telegram_id = context.user_data.get('master_telegram_id')
        
        if master_telegram_id is None:
            # Возврат к выбору типа записи
            context.user_data['state'] = MASTER_CHOICE
            await query.edit_message_text(
                Messages.get_master_choice_message(language),
                reply_markup=Keyboards.get_master_choice_keyboard(language)
            )
        else:
            # Возврат к выбору конкретного мастера
            suitable_masters_telegram_ids = context.user_data.get('suitable_masters', [])
            suitable_masters = []
            
            for telegram_id in suitable_masters_telegram_ids:
                master = db.get_master_by_telegram_id(telegram_id)
                if master:
                    suitable_masters.append(master)
            
            context.user_data['state'] = MASTER_SELECTION
            await query.edit_message_text(
                Messages.get_masters_list_message(language),
                reply_markup=Keyboards.get_masters_keyboard(suitable_masters, language)
            )
        return MASTER_SELECTION
    
    # Смена месяца в календаре - ИСПРАВЛЕННЫЙ ВАРИАНТ
    elif data.startswith("change_month_"):
        logger.info(f"Получен callback change_month_: {data}")
        try:
            # Разбиваем по "_" и берем последние 2 части как год и месяц
            parts = data.split("_")
            logger.info(f"Части после split: {parts}, количество: {len(parts)}")
            
            if len(parts) >= 3:
                # Берем последние 2 элемента как год и месяц
                year_str, month_str = parts[-2], parts[-1]
                logger.info(f"Год: {year_str}, Месяц: {month_str}")
                year = int(year_str)
                month = int(month_str)
                logger.info(f"Успешно распарсено: год={year}, месяц={month}")
            else:
                # Если формат неверный, используем текущий год/месяц
                today = datetime.now()
                year, month = today.year, today.month
                logger.warning(f"Неправильный формат change_month_: {data}")
        except (ValueError, IndexError) as e:
            # Если ошибка парсинга, используем текущий год/месяц
            today = datetime.now()
            year, month = today.year, today.month
            logger.error(f"Ошибка парсинга change_month_: {e}, data={data}")
        
        # Генерируем новую клавиатуру календаря
        logger.info(f"Генерируем календарь для года={year}, месяца={month}")
        new_keyboard = Keyboards.get_calendar_keyboard(year, month, language)
        
        try:
            await query.edit_message_reply_markup(
                reply_markup=new_keyboard
            )
            logger.info(f"Календарь успешно обновлен на год={year}, месяц={month}")
        except Exception as e:
            # Игнорируем ошибку "message not modified"
            if "Message is not modified" not in str(e):
                logger.error(f"Ошибка при обновлении календаря: {e}")
            else:
                logger.info("Календарь уже обновлен (message not modified)")
        
        return DATE_SELECTION
    
    # Выбор сегодняшней даты
    elif data == "select_today":
        today = date.today()
        context.user_data['appointment_date'] = today.isoformat()
        context.user_data['state'] = MASTER_CHOICE
        
        await query.edit_message_text(
            Messages.get_master_choice_message(language),
            reply_markup=Keyboards.get_master_choice_keyboard(language)
        )
        return MASTER_CHOICE
    
    # Прямой переход к выбору даты
    elif data == "select_date":
        selected_services = context.user_data.get('selected_services', [])
        
        if not selected_services:
            await query.answer("Выберите хотя бы одну услугу")
            return SERVICE_SELECTION
        
        # Показываем сводку
        services_info = []
        total_price = 0
        
        for service_id in selected_services:
            service = db.get_service_by_id(service_id, language)
            if service:
                services_info.append(service)
                total_price += service.get('price', 0)
        
        await query.edit_message_text(
            Messages.get_selected_services_message(language, services_info, total_price)
        )
        
        # Переходим к выбору даты
        context.user_data['state'] = DATE_SELECTION
        today = datetime.now()
        
        await query.message.reply_text(
            Messages.get_date_selection_message(language),
            reply_markup=Keyboards.get_calendar_keyboard(today.year, today.month, language)
        )
        return DATE_SELECTION
    
    # Обработка кнопок после успешного бронирования
    elif data == "my_appointments":
        user_id = context.user_data.get('user_id')
        appointments = db.get_user_appointments(user_id, limit=10)
        
        if not appointments:
            # Закрываем клавиатуру и отправляем новое сообщение
            try:
                await query.edit_message_reply_markup(reply_markup=None)
            except:
                pass
            
            await query.message.reply_text(
                Messages.get_no_appointments_message(language)
            )
        else:
            message_text = Messages.get_my_appointments_message(language) + "\n\n"
            
            for i, appointment in enumerate(appointments, 1):
                date_str = appointment['appointment_date']
                time_str = appointment['start_time']
                services = appointment.get('services_titles', 'Не указаны')
                
                if len(services) > 30:
                    services = services[:30] + "..."
                
                message_text += f"{i}. 📅 {date_str} ⏰ {time_str}\n"
                message_text += f"   💅 {services}\n"
                message_text += f"   📊 Статус: {appointment['status']}\n\n"
            
            # Редактируем текущее сообщение без клавиатуры
            await query.edit_message_text(
                message_text,
                reply_markup=None
            )
        
        return MAIN_MENU
    
    elif data == "new_appointment":
        context.user_data['state'] = CATEGORY_SELECTION
        context.user_data['selected_services'] = []
        
        # Получаем категории верхнего уровня
        categories = db.get_categories(language, parent_id=None)
        
        if not categories:
            # Закрываем клавиатуру и отправляем новое сообщение
            try:
                await query.edit_message_reply_markup(reply_markup=None)
            except:
                pass
            
            await query.message.reply_text(
                Messages.get_no_categories_message(language)
            )
            return MAIN_MENU
        
        await query.edit_message_text(
            Messages.get_categories_message(language),
            reply_markup=Keyboards.get_categories_keyboard(categories, language)
        )
        return CATEGORY_SELECTION
    
    # Обработка возврата в главное меню
    elif data == "back_to_main":
        context.user_data['state'] = MAIN_MENU
        
        if context.user_data.get('is_master'):
            reply_markup = Keyboards.get_master_menu_keyboard(language)
        else:
            reply_markup = Keyboards.get_main_menu_keyboard(language)
        
        # Закрываем инлайн-клавиатуру и отправляем новое сообщение
        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except:
            pass
        
        await query.message.reply_text(
            Messages.get_language_set_message(language),
            reply_markup=reply_markup
        )
        return MAIN_MENU
    
    # Обработка возврата к списку записей
    elif data == "back_to_appointments":
        user_id = context.user_data.get('user_id')
        appointments = db.get_user_appointments(user_id, limit=10)
        
        if not appointments:
            # Закрываем клавиатуру и отправляем новое сообщение
            try:
                await query.edit_message_reply_markup(reply_markup=None)
            except:
                pass
            
            await query.message.reply_text(
                Messages.get_no_appointments_message(language)
            )
        else:
            message_text = Messages.get_my_appointments_message(language) + "\n\n"
            
            for i, appointment in enumerate(appointments, 1):
                date_str = appointment['appointment_date']
                time_str = appointment['start_time']
                services = appointment.get('services_titles', 'Не указаны')
                
                if len(services) > 30:
                    services = services[:30] + "..."
                
                message_text += f"{i}. 📅 {date_str} ⏰ {time_str}\n"
                message_text += f"   💅 {services}\n"
                message_text += f"   📊 Статус: {appointment['status']}\n\n"
            
            # Редактируем сообщение без клавиатуры
            await query.edit_message_text(
                message_text,
                reply_markup=None
            )
        
        return MAIN_MENU
    
    # Обработка деталей записи (если используется)
    elif data.startswith("appointment_detail_"):
        appointment_id = int(data.split("_")[2])
        appointment = db.get_appointment_by_id(appointment_id)
        
        if appointment:
            if language == 'ru':
                message = f"📋 Детали записи #{appointment_id}\n\n"
                message += f"📅 Дата: {appointment['appointment_date']}\n"
                message += f"⏰ Время: {appointment['start_time']}\n"
                message += f"👤 Мастер: {appointment.get('master_name', 'Не указан')}\n"
                message += f"💅 Услуги: {appointment.get('services_titles', 'Не указаны')}\n"
                message += f"💰 Стоимость: {appointment.get('total_price', 0)}₺\n"
                message += f"📊 Статус: {appointment['status']}\n"
            elif language == 'en':
                message = f"📋 Appointment details #{appointment_id}\n\n"
                message += f"📅 Date: {appointment['appointment_date']}\n"
                message += f"⏰ Time: {appointment['start_time']}\n"
                message += f"👤 Master: {appointment.get('master_name', 'Not specified')}\n"
                message += f"💅 Services: {appointment.get('services_titles', 'Not specified')}\n"
                message += f"💰 Price: {appointment.get('total_price', 0)}₺\n"
                message += f"📊 Status: {appointment['status']}\n"
            else:  # tr
                message = f"📋 Randevu detayları #{appointment_id}\n\n"
                message += f"📅 Tarih: {appointment['appointment_date']}\n"
                message += f"⏰ Saat: {appointment['start_time']}\n"
                message += f"👤 Usta: {appointment.get('master_name', 'Belirtilmedi')}\n"
                message += f"💅 Hizmetler: {appointment.get('services_titles', 'Belirtilmedi')}\n"
                message += f"💰 Fiyat: {appointment.get('total_price', 0)}₺\n"
                message += f"📊 Durum: {appointment['status']}\n"
            
            await query.edit_message_text(
                message,
                reply_markup=Keyboards.get_appointment_detail_keyboard(appointment_id, language)
            )
        return APPOINTMENT_DETAIL
    
    # Отмена конкретной записи
    elif data.startswith("cancel_"):
        appointment_id = int(data.split("_")[1])
        
        # Обновляем статус записи в базе данных
        success = db.cancel_appointment(appointment_id)
        
        if success:
            if language == 'ru':
                message_text = f"✅ Запись #{appointment_id} успешно отменена"
            elif language == 'en':
                message_text = f"✅ Appointment #{appointment_id} successfully cancelled"
            else:  # tr
                message_text = f"✅ Randevu #{appointment_id} başarıyla iptal edildi"
        else:
            if language == 'ru':
                message_text = f"❌ Не удалось отменить запись #{appointment_id}"
            elif language == 'en':
                message_text = f"❌ Failed to cancel appointment #{appointment_id}"
            else:  # tr
                message_text = f"❌ Randevu #{appointment_id} iptal edilemedi"
        
        # Закрываем инлайн-клавиатуру и отправляем новое сообщение
        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except:
            pass
        
        await query.message.reply_text(
            message_text,
            reply_markup=Keyboards.get_main_menu_keyboard(language)
        )
        
        context.user_data['state'] = MAIN_MENU
        return MAIN_MENU
    
    # Перенос записи
    elif data.startswith("reschedule_"):
        appointment_id = int(data.split("_")[1])
        
        # Получаем информацию о записи
        appointment = db.get_appointment_by_id(appointment_id)
        
        if appointment:
            # Сохраняем ID записи для переноса
            context.user_data['reschedule_appointment_id'] = appointment_id
            context.user_data['state'] = DATE_SELECTION
            
            # Начинаем процесс выбора новой даты
            today = datetime.now()
            
            await query.edit_message_text(
                "Выберите новую дату для записи:" if language == 'ru' else
                "Select a new date for the appointment:" if language == 'en' else
                "Randevu için yeni bir tarih seçin:",
                reply_markup=Keyboards.get_calendar_keyboard(today.year, today.month, language)
            )
            return DATE_SELECTION
    
    # Обработка для сообщений без клавиатуры
    elif not query.message.reply_markup and data != "ignore":
        # Если сообщение без клавиатуры, возвращаем в главное меню
        logger.warning(f"Получен callback {data} на сообщении без клавиатуры")
        context.user_data['state'] = MAIN_MENU
        
        if context.user_data.get('is_master'):
            reply_markup = Keyboards.get_master_menu_keyboard(language)
        else:
            reply_markup = Keyboards.get_main_menu_keyboard(language)
        
        await query.message.reply_text(
            Messages.get_language_set_message(language),
            reply_markup=reply_markup
        )
        return MAIN_MENU
    
    return state
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка команды /help"""
    await update.message.reply_text(
        "ℹ️ Помощь по боту:\n\n"
        "/start - Начать работу с ботом\n"
        "/help - Показать это сообщение\n"
        "/cancel - Отменить текущее действие\n\n"
        "Используйте кнопки меню для навигации."
    )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка команды /cancel"""
    language = context.user_data.get('language', 'ru')
    
    # Сбрасываем состояние
    context.user_data.clear()
    
    await update.message.reply_text(
        "Действие отменено. Используйте /start для начала.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

def main():
    """Основная функция запуска бота"""
    
    # Проверка конфигурации
    try:
        Config.validate()
        logger.info("Конфигурация проверена успешно")
    except Exception as e:
        logger.error(f"Ошибка конфигурации: {e}")
        return
    
    # Создаем приложение
    application = Application.builder().token(Config.BOT_TOKEN).build()
    
    # Добавляем обработчик для callback-запросов мастера
    application.add_handler(CallbackQueryHandler(handle_master_callback, pattern="^master_"))
    
    # Создаем ConversationHandler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            LANGUAGE_SELECTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_language_selection)
            ],
            MAIN_MENU: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_main_menu)
            ],
            CATEGORY_SELECTION: [
                CallbackQueryHandler(handle_callback_query),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_main_menu_text)
            ],
            SERVICE_SELECTION: [
                CallbackQueryHandler(handle_callback_query),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_main_menu_text)
            ],
            DATE_SELECTION: [
                CallbackQueryHandler(handle_callback_query),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_main_menu_text)
            ],
            MASTER_CHOICE: [
                CallbackQueryHandler(handle_callback_query),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_main_menu_text)
            ],
            MASTER_SELECTION: [
                CallbackQueryHandler(handle_callback_query),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_main_menu_text)
            ],
            TIME_SELECTION: [
                CallbackQueryHandler(handle_callback_query),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_main_menu_text)
            ],
            APPOINTMENT_CONFIRMATION: [
                CallbackQueryHandler(handle_callback_query),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_main_menu_text)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel), CommandHandler("help", help_command)],
    )
    
    # Добавляем обработчики
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("cancel", cancel))
    
    # Запускаем бота
    logger.info("Бот запускается...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()