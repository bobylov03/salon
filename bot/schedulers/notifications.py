# notifications.py
import logging
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from ..database import Database
from ..messages import Messages
from ..config import Config

logger = logging.getLogger(__name__)
db = Database()

class NotificationScheduler:
    def __init__(self, bot):
        self.bot = bot
        self.scheduler = AsyncIOScheduler(timezone=Config.TIMEZONE)
    
    async def start(self):
        """Запуск планировщика уведомлений"""
        try:
            # Уведомления за 8 часов - запускаем каждые 30 минут
            self.scheduler.add_job(
                self.send_8h_notifications,
                CronTrigger(minute='*/30'),  # Каждые 30 минут
                id='8h_notifications',
                replace_existing=True
            )
            
            # Уведомления за 2 часа - запускаем каждые 15 минут
            self.scheduler.add_job(
                self.send_2h_notifications,
                CronTrigger(minute='*/15'),  # Каждые 15 минут
                id='2h_notifications',
                replace_existing=True
            )
            
            # Ежедневная проверка в 8 утра
            self.scheduler.add_job(
                self.send_daily_reminders,
                CronTrigger(hour=8, minute=0),
                id='daily_reminders',
                replace_existing=True
            )
            
            self.scheduler.start()
            logger.info("Планировщик уведомлений запущен")
            
        except Exception as e:
            logger.error(f"Ошибка при запуске планировщика: {e}")
    
    async def stop(self):
        """Остановка планировщика"""
        self.scheduler.shutdown()
        logger.info("Планировщик уведомлений остановлен")
    
    async def send_8h_notifications(self):
        """Отправка уведомлений за 8 часов до записи"""
        try:
            # Получаем текущее время
            now = datetime.now()
            
            # Рассчитываем временной диапазон: от 8 часов 15 минут до 7 часов 45 минут до начала
            time_window_start = now + timedelta(hours=8, minutes=15)
            time_window_end = now + timedelta(hours=7, minutes=45)
            
            # Ищем записи, которые начинаются в этом временном окне
            appointments = self.get_appointments_in_time_window(time_window_start, time_window_end)
            
            for appointment in appointments:
                try:
                    # Получаем telegram_id клиента
                    client_telegram_id = appointment.get('client_telegram_id')
                    language = appointment.get('client_language', 'ru')
                    
                    if client_telegram_id:
                        # Проверяем, не отправляли ли уже уведомление
                        if not self.check_notification_sent(appointment['id'], '8h'):
                            message = Messages.get_notification_8h_message(language, appointment)
                            await self.bot.send_message(client_telegram_id, message)
                            
                            # Отмечаем, что уведомление отправлено
                            self.mark_notification_sent(appointment['id'], '8h')
                            logger.info(f"8h уведомление отправлено клиенту {client_telegram_id}")
                    
                except Exception as e:
                    logger.error(f"Ошибка при отправке 8h уведомления: {e}")
            
        except Exception as e:
            logger.error(f"Ошибка в send_8h_notifications: {e}")
    
    async def send_2h_notifications(self):
        """Отправка уведомлений за 2 часа до записи"""
        try:
            # Получаем текущее время
            now = datetime.now()
            
            # Рассчитываем временной диапазон: от 2 часов 15 минут до 1 часа 45 минут до начала
            time_window_start = now + timedelta(hours=2, minutes=15)
            time_window_end = now + timedelta(hours=1, minutes=45)
            
            # Ищем записи, которые начинаются в этом временном окне
            appointments = self.get_appointments_in_time_window(time_window_start, time_window_end)
            
            for appointment in appointments:
                try:
                    # Получаем telegram_id клиента
                    client_telegram_id = appointment.get('client_telegram_id')
                    language = appointment.get('client_language', 'ru')
                    
                    if client_telegram_id:
                        # Проверяем, не отправляли ли уже уведомление
                        if not self.check_notification_sent(appointment['id'], '2h'):
                            message = Messages.get_notification_2h_message(language, appointment)
                            await self.bot.send_message(client_telegram_id, message)
                            
                            # Отмечаем, что уведомление отправлено
                            self.mark_notification_sent(appointment['id'], '2h')
                            logger.info(f"2h уведомление отправлено клиенту {client_telegram_id}")
                    
                except Exception as e:
                    logger.error(f"Ошибка при отправке 2h уведомления: {e}")
            
        except Exception as e:
            logger.error(f"Ошибка в send_2h_notifications: {e}")
    
    async def send_daily_reminders(self):
        """Ежедневные напоминания о записях на сегодня"""
        try:
            # Получаем записи на сегодня
            today = datetime.now().date()
            
            conn = db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT a.*, u.telegram_id, u.language
                FROM appointments a
                JOIN users u ON a.client_id = u.id
                WHERE DATE(a.appointment_date) = DATE(?)
                AND a.status IN ('pending', 'confirmed')
                AND a.start_time > ?
            """, (today.isoformat(), datetime.now().strftime('%H:%M:%S')))
            
            appointments = []
            for row in cursor.fetchall():
                appointments.append(dict(row))
            
            conn.close()
            
            for appointment in appointments:
                try:
                    telegram_id = appointment.get('telegram_id')
                    language = appointment.get('language', 'ru')
                    
                    if telegram_id:
                        date_str = appointment['appointment_date']
                        time_str = appointment['start_time']
                        
                        if language == 'ru':
                            message = f"🔔 Напоминание о записи на сегодня!\n\n📅 {date_str} в {time_str}"
                        elif language == 'en':
                            message = f"🔔 Reminder about today's appointment!\n\n📅 {date_str} at {time_str}"
                        else:  # tr
                            message = f"🔔 Bugünkü randevu hatırlatması!\n\n📅 {date_str} saat {time_str}"
                        
                        await self.bot.send_message(telegram_id, message)
                        logger.info(f"Ежедневное напоминание отправлено {telegram_id}")
                    
                except Exception as e:
                    logger.error(f"Ошибка при отправке ежедневного напоминания: {e}")
            
        except Exception as e:
            logger.error(f"Ошибка в send_daily_reminders: {e}")
    
    def get_appointments_in_time_window(self, start_time, end_time):
        """Получает записи, которые начинаются в указанном временном окне"""
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT a.*, u.telegram_id as client_telegram_id, u.language as client_language
            FROM appointments a
            JOIN users u ON a.client_id = u.id
            WHERE a.status IN ('pending', 'confirmed')
            AND datetime(a.appointment_date || ' ' || a.start_time) 
                BETWEEN datetime(?) AND datetime(?)
        """, (start_time.isoformat(), end_time.isoformat()))
        
        appointments = []
        for row in cursor.fetchall():
            appointments.append(dict(row))
        
        conn.close()
        return appointments
    
    def check_notification_sent(self, appointment_id, notification_type):
        """Проверяет, было ли уже отправлено уведомление"""
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT COUNT(*) as count FROM appointment_notifications
            WHERE appointment_id = ? AND notification_type = ?
        """, (appointment_id, notification_type))
        
        result = cursor.fetchone()
        conn.close()
        
        return result['count'] > 0 if result else False
    
    def mark_notification_sent(self, appointment_id, notification_type):
        """Отмечает, что уведомление было отправлено"""
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO appointment_notifications 
            (appointment_id, notification_type, sent_at)
            VALUES (?, ?, ?)
        """, (appointment_id, notification_type, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()