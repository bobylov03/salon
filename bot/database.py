# database.py
import sqlite3
import logging
import os
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, date, time, timedelta

# Импортируем Config правильно
try:
    from .config import Config
except ImportError:
    # Для прямого запуска из папки bot
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from config import Config

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path: str = None):
        if db_path is None:
            if Config.DATABASE_PATH:
                # Используем путь из переменной окружения (Docker/Railway)
                db_path = Config.DATABASE_PATH
            else:
                # Автоматически определяем путь к БД для локальной разработки
                current_dir = os.path.dirname(os.path.abspath(__file__))
                project_root = os.path.dirname(current_dir)
                db_path = os.path.join(project_root, 'salon.db')
                if not os.path.exists(db_path):
                    db_path = os.path.join(project_root, 'backend', 'salon.db')

        self.db_path = db_path
        logger.info(f"Используется база данных: {self.db_path}")
    
    def get_connection(self):
        """Получение соединения с БД"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    # ==================== ПОЛЬЗОВАТЕЛИ ====================
    
    def get_or_create_user(self, telegram_id: int, first_name: str, last_name: str = "", username: str = "") -> Dict[str, Any]:
        """Получение или создание пользователя"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            telegram_id_str = str(telegram_id)
            logger.info(f"get_or_create_user: TG_ID={telegram_id}, TG_ID_STR={telegram_id_str}")
            
            # Сначала проверяем, может ли это быть мастер (по полю phone)
            cursor.execute("""
                SELECT * FROM users 
                WHERE phone = ? AND role = 'master'
            """, (telegram_id_str,))
            
            user = cursor.fetchone()
            
            if user:
                # Нашли мастера по phone (Telegram ID)
                user_dict = dict(user)
                conn.close()
                logger.info(f"Найден мастер по phone: ID={user_dict['id']}, Phone/TG={telegram_id_str}, Role={user_dict.get('role')}")
                return user_dict
            
            # Если не мастер, ищем обычного пользователя по telegram_id
            cursor.execute("""
                SELECT * FROM users 
                WHERE telegram_id = ?
            """, (telegram_id,))
            
            user = cursor.fetchone()
            
            if user:
                # Пользователь найден
                user_dict = dict(user)
                conn.close()
                logger.info(f"Найден существующий пользователь: ID={user_dict['id']}, TG ID={telegram_id}, Role={user_dict.get('role')}")
                return user_dict
            
            # Пользователь не найден - создаем нового клиента
            cursor.execute("""
                INSERT INTO users (telegram_id, role, first_name, last_name, language, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                telegram_id,
                'client', 
                first_name, 
                last_name or '', 
                Config.DEFAULT_LANGUAGE, 
                datetime.now()
            ))
            
            user_id = cursor.lastrowid
            conn.commit()
            
            # Получаем созданного пользователя
            cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            new_user = cursor.fetchone()
            
            user_dict = dict(new_user)
            conn.close()
            
            logger.info(f"Создан новый пользователь: ID={user_id}, Telegram ID={telegram_id}, Role=client")
            return user_dict
            
        except Exception as e:
            logger.error(f"Ошибка при создании пользователя: {e}", exc_info=True)
            raise
    
    def update_user_language(self, user_id: int, language: str) -> bool:
        """Обновление языка пользователя"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE users SET language = ? WHERE id = ?
            """, (language, user_id))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при обновлении языка: {e}")
            return False
    
    # ==================== КАТЕГОРИИ ====================
    
    def get_categories(self, language: str, parent_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Получение категорий услуг с переводами"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            query = """
                SELECT 
                    sc.id, 
                    sc.parent_id, 
                    sc.is_active,
                    COALESCE(sct.title, 'Категория ' || sc.id) as title
                FROM service_categories sc
                LEFT JOIN service_category_translations sct 
                    ON sc.id = sct.category_id AND sct.language = ?
                WHERE sc.is_active = 1
            """
            
            params = [language]
            
            if parent_id is None:
                query += " AND sc.parent_id IS NULL"
            else:
                query += " AND sc.parent_id = ?"
                params.append(parent_id)
            
            query += " ORDER BY sc.id"
            
            cursor.execute(query, tuple(params))
            
            categories = []
            for row in cursor.fetchall():
                categories.append(dict(row))
            
            conn.close()
            return categories
            
        except Exception as e:
            logger.error(f"Ошибка при получении категорий: {e}")
            return []
    
    def get_category_by_id(self, category_id: int, language: str) -> Optional[Dict[str, Any]]:
        """Получение категории по ID с переводом"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    sc.id, 
                    sc.parent_id, 
                    sc.is_active,
                    COALESCE(sct.title, 'Категория ' || sc.id) as title
                FROM service_categories sc
                LEFT JOIN service_category_translations sct 
                    ON sc.id = sct.category_id AND sct.language = ?
                WHERE sc.id = ? AND sc.is_active = 1
            """, (language, category_id))
            
            row = cursor.fetchone()
            conn.close()
            
            return dict(row) if row else None
            
        except Exception as e:
            logger.error(f"Ошибка при получении категории: {e}")
            return None
    
    # ==================== УСЛУГИ ====================
    
    def get_services_by_category(self, category_id: int, language: str) -> List[Dict[str, Any]]:
        """Получение услуг в категории с переводами"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    s.id, 
                    s.category_id, 
                    s.duration_minutes, 
                    s.price, 
                    s.is_active,
                    COALESCE(st.title, 'Услуга ' || s.id) as title,
                    st.description
                FROM services s
                LEFT JOIN service_translations st 
                    ON s.id = st.service_id AND st.language = ?
                WHERE s.category_id = ? AND s.is_active = 1
                ORDER BY s.price
            """, (language, category_id))
            
            services = []
            for row in cursor.fetchall():
                services.append(dict(row))
            
            conn.close()
            return services
            
        except Exception as e:
            logger.error(f"Ошибка при получении услуг: {e}")
            return []
    
    def get_service_by_id(self, service_id: int, language: str) -> Optional[Dict[str, Any]]:
        """Получение услуги по ID с переводом"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    s.id, 
                    s.category_id, 
                    s.duration_minutes, 
                    s.price, 
                    s.is_active,
                    COALESCE(st.title, 'Услуга ' || s.id) as title,
                    st.description
                FROM services s
                LEFT JOIN service_translations st 
                    ON s.id = st.service_id AND st.language = ?
                WHERE s.id = ? AND s.is_active = 1
            """, (language, service_id))
            
            row = cursor.fetchone()
            conn.close()
            
            return dict(row) if row else None
            
        except Exception as e:
            logger.error(f"Ошибка при получении услуги: {e}")
            return None
    
    # ==================== МАСТЕРЫ ====================
    
    def get_master_by_phone(self, phone: str) -> Optional[Dict[str, Any]]:
        """Получение мастера по номеру телефона (который используется как Telegram ID)"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    m.id as master_id,
                    u.first_name, 
                    u.last_name, 
                    u.phone,
                    u.telegram_id,
                    m.photo,
                    m.qualification,
                    m.description,
                    m.is_active,
                    u.id as user_id,
                    u.language
                FROM masters m
                JOIN users u ON m.user_id = u.id
                WHERE u.phone = ? AND m.is_active = 1
            """, (phone,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                master = dict(row)
                if master.get('photo'):
                    master['photo_url'] = f"{Config.BASE_URL}/uploads/masters/{master['photo']}"
                return master
            return None
            
        except Exception as e:
            logger.error(f"Ошибка при получении мастера по phone: {e}")
            return None
    
    def get_master_by_telegram_id(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        """Получение мастера по Telegram ID"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    m.id, 
                    m.photo, 
                    m.qualification, 
                    m.description, 
                    m.is_active,
                    u.first_name, 
                    u.last_name, 
                    u.telegram_id,
                    u.id as user_id
                FROM masters m
                JOIN users u ON m.user_id = u.id
                WHERE u.telegram_id = ? AND m.is_active = 1
            """, (telegram_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                master = dict(row)
                if master.get('photo'):
                    master['photo_url'] = f"{Config.BASE_URL}/uploads/masters/{master['photo']}"
                logger.info(f"Найден мастер по telegram_id {telegram_id}: ID={master['id']}")
                return master
            logger.warning(f"Мастер с telegram_id {telegram_id} не найден")
            return None
            
        except Exception as e:
            logger.error(f"Ошибка при получении мастера по telegram_id: {e}")
            return None
    
    def check_user_is_master(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        """Проверяет, является ли пользователь мастером (ищет по telegram_id)"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            logger.info(f"Поиск мастера по telegram_id: {telegram_id}")
            
            # Ищем пользователя с таким telegram_id
            cursor.execute("""
                SELECT 
                    u.id as user_id, 
                    m.id as master_id, 
                    u.first_name, 
                    u.last_name, 
                    u.language,
                    u.telegram_id
                FROM users u
                LEFT JOIN masters m ON u.id = m.user_id
                WHERE u.telegram_id = ?
            """, (telegram_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                user_info = dict(result)
                # Проверяем, является ли пользователь мастером (есть запись в таблице masters)
                if user_info.get('master_id') and user_info.get('master_id') != 'None':
                    logger.info(f"Найден мастер: {user_info}")
                    return user_info
                else:
                    logger.info(f"Пользователь найден, но не является мастером: {user_info}")
                    return None
            
            logger.info(f"Пользователь с telegram_id {telegram_id} не найден")
            return None
            
        except Exception as e:
            logger.error(f"Ошибка при проверке мастера: {e}", exc_info=True)
            return None
    
    def get_masters_for_service(self, service_id: int, language: str = 'ru') -> List[Dict[str, Any]]:
        """Получение мастеров, которые предоставляют услугу"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    m.id, 
                    m.photo, 
                    m.qualification, 
                    m.description, 
                    m.is_active,
                    u.first_name, 
                    u.last_name, 
                    u.phone,
                    ms.is_primary,
                    u.telegram_id
                FROM master_services ms
                JOIN masters m ON ms.master_id = m.id
                JOIN users u ON m.user_id = u.id
                WHERE ms.service_id = ? AND m.is_active = 1
                ORDER BY ms.is_primary DESC, u.first_name
            """, (service_id,))
            
            masters = []
            for row in cursor.fetchall():
                master = dict(row)
                # Добавляем URL фото
                if master.get('photo'):
                    master['photo_url'] = f"{Config.BASE_URL}/uploads/masters/{master['photo']}"
                masters.append(master)
            
            conn.close()
            return masters
            
        except Exception as e:
            logger.error(f"Ошибка при получении мастеров для услуги: {e}")
            return []
    
    def get_master_by_id(self, master_id: int) -> Optional[Dict[str, Any]]:
        """Получение мастера по ID"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # ПРОСТОЙ ЗАПРОС без сложных условий
            cursor.execute("""
                SELECT 
                    m.id, 
                    m.photo, 
                    m.qualification, 
                    m.description, 
                    m.is_active,
                    u.first_name, 
                    u.last_name, 
                    u.telegram_id,
                    u.id as user_id
                FROM masters m
                JOIN users u ON m.user_id = u.id
                WHERE m.id = ?
            """, (master_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                master = dict(row)
                if master.get('photo'):
                    master['photo_url'] = f"{Config.BASE_URL}/uploads/masters/{master['photo']}"
                logger.info(f"Найден мастер ID={master_id}: user_id={master.get('user_id')}, telegram_id={master.get('telegram_id')}")
                return master
            
            logger.warning(f"Мастер ID={master_id} не найден в базе")
            return None
            
        except Exception as e:
            logger.error(f"Ошибка при получении мастера {master_id}: {e}", exc_info=True)
            return None
    
    def get_master_schedule(self, master_id: int, day_of_week: int) -> Optional[Dict[str, Any]]:
        """Получение графика работы мастера на конкретный день"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM master_work_schedule
                WHERE master_id = ? AND day_of_week = ?
            """, (master_id, day_of_week))
            
            row = cursor.fetchone()
            conn.close()
            
            return dict(row) if row else None
            
        except Exception as e:
            logger.error(f"Ошибка при получении графика мастера: {e}")
            return None
    
    # ==================== ЗАНЯТОЕ ВРЕМЯ ====================
    
    def get_busy_time_slots(self, master_id: int, appointment_date: date) -> List[str]:
        """Получение занятых временных слотов мастера на дату"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT start_time, end_time FROM appointments
                WHERE master_id = ? AND appointment_date = ? 
                AND status IN ('pending', 'confirmed', 'in_progress')
                ORDER BY start_time
            """, (master_id, appointment_date.isoformat()))
            
            busy_slots = []
            for row in cursor.fetchall():
                busy_slots.append({
                    'start': row['start_time'],
                    'end': row['end_time']
                })
            
            conn.close()
            return busy_slots
            
        except Exception as e:
            logger.error(f"Ошибка при получении занятых слотов: {e}")
            return []
    
    def get_available_time_slots(self, master_id: int, appointment_date: date, service_duration: int) -> List[str]:
        """Получение доступных временных слотов для мастера"""
        try:
            # Получаем график работы мастера на этот день недели
            day_of_week = appointment_date.weekday()  # 0-понедельник, 6-воскресенье
            schedule = self.get_master_schedule(master_id, day_of_week)
            
            if not schedule:
                return []  # Мастер не работает в этот день
            
            # Получаем занятые слоты
            busy_slots = self.get_busy_time_slots(master_id, appointment_date)
            
            # Генерируем доступные слоты
            start_time = datetime.strptime(schedule['start_time'], '%H:%M').time()
            end_time = datetime.strptime(schedule['end_time'], '%H:%M').time()
            
            available_slots = []
            current_time = datetime.combine(appointment_date, start_time)
            end_datetime = datetime.combine(appointment_date, end_time)
            
            # Шаг - 15 минут
            while current_time + timedelta(minutes=service_duration) <= end_datetime:
                slot_start = current_time.time()
                slot_end = (current_time + timedelta(minutes=service_duration)).time()
                
                # Проверяем, не пересекается ли слот с занятыми
                is_available = True
                for busy in busy_slots:
                    busy_start = datetime.strptime(busy['start'], '%H:%M').time()
                    busy_end = datetime.strptime(busy['end'], '%H:%M').time()
                    
                    # Проверка пересечения интервалов
                    if not (slot_end <= busy_start or slot_start >= busy_end):
                        is_available = False
                        break
                
                if is_available:
                    available_slots.append(slot_start.strftime('%H:%M'))
                
                current_time += timedelta(minutes=15)
            
            return available_slots
            
        except Exception as e:
            logger.error(f"Ошибка при получении доступных слотов: {e}")
            return []
    
    # ==================== ЗАПИСИ ====================
    
    def create_appointment(self, client_id: int, master_id: Optional[int], 
                      appointment_date: date, start_time: str, 
                      service_ids: List[int], status: str = 'pending') -> Tuple[Optional[int], Optional[int]]:
        """Создание новой записи"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Рассчитываем время окончания
            total_duration = 0
            for service_id in service_ids:
                cursor.execute("SELECT duration_minutes FROM services WHERE id = ?", (service_id,))
                service = cursor.fetchone()
                if service:
                    service_dict = dict(service)
                    total_duration += service_dict.get('duration_minutes', 0)
            
            start_dt = datetime.strptime(start_time, '%H:%M')
            end_dt = datetime.combine(date.today(), start_dt.time()) + timedelta(minutes=total_duration)
            end_time_str = end_dt.strftime('%H:%M')
            
            logger.info(f"Создание записи: клиент={client_id}, мастер={master_id}, дата={appointment_date}, время={start_time}, услуги={service_ids}")
            
            # ПРОВЕРКА: Существует ли мастер
            if master_id:
                cursor.execute("SELECT id, user_id FROM masters WHERE id = ?", (master_id,))
                master_check = cursor.fetchone()
                if not master_check:
                    logger.error(f"Мастер ID={master_id} не существует в таблице masters!")
                    return None, None
                logger.info(f"Мастер ID={master_id} существует, user_id={master_check['user_id']}")
            
            # Создаем запись
            cursor.execute("""
                INSERT INTO appointments 
                (client_id, master_id, appointment_date, start_time, end_time, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                client_id, 
                master_id, 
                appointment_date.isoformat(), 
                start_time, 
                end_time_str, 
                status,
                datetime.now()
            ))
            
            appointment_id = cursor.lastrowid
            
            if not appointment_id:
                logger.error("Не удалось получить appointment_id после создания записи!")
                conn.rollback()
                conn.close()
                return None, None
            
            logger.info(f"Запись создана с ID: {appointment_id}")
            
            # Добавляем услуги к записи
            for service_id in service_ids:
                cursor.execute("""
                    INSERT INTO appointment_services (appointment_id, service_id)
                    VALUES (?, ?)
                """, (appointment_id, service_id))
                logger.info(f"Добавлена услуга {service_id} к записи {appointment_id}")
            
            # Получаем user_id мастера для уведомления
            master_user_id = None
            if master_id:
                cursor.execute("""
                    SELECT u.id as user_id, u.telegram_id 
                    FROM masters m
                    JOIN users u ON m.user_id = u.id
                    WHERE m.id = ?
                """, (master_id,))
                
                result = cursor.fetchone()
                
                if result:
                    result_dict = dict(result)
                    master_user_id = result_dict['user_id']
                    telegram_id = result_dict.get('telegram_id')
                    logger.info(f"Найден user_id мастера: {master_user_id}, telegram_id={telegram_id}")
                    
                    # ПРОВЕРКА: есть ли telegram_id у мастера
                    if not telegram_id:
                        logger.warning(f"У мастера ID={master_id} нет telegram_id в базе!")
                else:
                    logger.error(f"Мастер с ID {master_id} не найден в связке masters-users")
            
            conn.commit()
            conn.close()
            
            logger.info(f"Создана запись ID={appointment_id} для клиента {client_id}, master_user_id={master_user_id}")
            return appointment_id, master_user_id
            
        except Exception as e:
            logger.error(f"Ошибка при создании записи: {e}", exc_info=True)
            if 'conn' in locals():
                conn.rollback()
                conn.close()
            return None, None
    
    def create_appointment_by_telegram_id(self, client_id: int, master_telegram_id: Optional[int], 
                                         appointment_date: date, start_time: str, 
                                         service_ids: List[int], status: str = 'pending') -> Tuple[Optional[int], Optional[int]]:
        """Создание записи по telegram_id мастера"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Получаем master_id по telegram_id (если указан)
            master_id = None
            if master_telegram_id:
                cursor.execute("""
                    SELECT m.id 
                    FROM masters m
                    JOIN users u ON m.user_id = u.id
                    WHERE u.telegram_id = ?
                """, (master_telegram_id,))
                
                result = cursor.fetchone()
                if result:
                    master_id = result['id']
                    logger.info(f"Найден мастер ID={master_id} по telegram_id={master_telegram_id}")
            
            # Рассчитываем время окончания
            total_duration = 0
            for service_id in service_ids:
                cursor.execute("SELECT duration_minutes FROM services WHERE id = ?", (service_id,))
                service = cursor.fetchone()
                if service:
                    service_dict = dict(service)
                    total_duration += service_dict.get('duration_minutes', 0)
            
            start_dt = datetime.strptime(start_time, '%H:%M')
            end_dt = datetime.combine(date.today(), start_dt.time()) + timedelta(minutes=total_duration)
            end_time_str = end_dt.strftime('%H:%M')
            
            logger.info(f"Создание записи по telegram_id: клиент={client_id}, мастер (telegram_id)={master_telegram_id}, дата={appointment_date}")
            
            # Создаем запись с master_telegram_id
            cursor.execute("""
                INSERT INTO appointments 
                (client_id, master_id, master_telegram_id, appointment_date, start_time, end_time, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                client_id, 
                master_id,  # Может быть NULL
                str(master_telegram_id) if master_telegram_id else None,
                appointment_date.isoformat(), 
                start_time, 
                end_time_str, 
                status,
                datetime.now()
            ))
            
            appointment_id = cursor.lastrowid
            
            if not appointment_id:
                logger.error("Не удалось получить appointment_id после создания записи!")
                conn.rollback()
                conn.close()
                return None, None
            
            logger.info(f"Запись создана с ID: {appointment_id}")
            
            # Добавляем услуги к записи
            for service_id in service_ids:
                cursor.execute("""
                    INSERT INTO appointment_services (appointment_id, service_id)
                    VALUES (?, ?)
                """, (appointment_id, service_id))
                logger.info(f"Добавлена услуга {service_id} к записи {appointment_id}")
            
            conn.commit()
            conn.close()
            
            logger.info(f"Создана запись ID={appointment_id} для клиента {client_id}, master_telegram_id={master_telegram_id}")
            return appointment_id, master_telegram_id
            
        except Exception as e:
            logger.error(f"Ошибка при создании записи по telegram_id: {e}", exc_info=True)
            if 'conn' in locals():
                conn.rollback()
                conn.close()
            return None, None
    
    def get_user_appointments(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Получение записей пользователя"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    a.id,
                    a.appointment_date,
                    a.start_time,
                    a.end_time,
                    a.status,
                    a.created_at,
                    u1.first_name as master_first_name, 
                    u1.last_name as master_last_name,
                    GROUP_CONCAT(DISTINCT COALESCE(st.title, 'Услуга ' || s.id)) as services_titles
                FROM appointments a
                LEFT JOIN masters m ON a.master_id = m.id
                LEFT JOIN users u1 ON m.user_id = u1.id
                LEFT JOIN appointment_services aps ON a.id = aps.appointment_id
                LEFT JOIN services s ON aps.service_id = s.id
                LEFT JOIN service_translations st ON s.id = st.service_id AND st.language = 'ru'
                WHERE a.client_id = ?
                GROUP BY a.id
                ORDER BY a.appointment_date DESC, a.start_time DESC
                LIMIT ?
            """, (user_id, limit))
            
            appointments = []
            for row in cursor.fetchall():
                appointments.append(dict(row))
            
            conn.close()
            return appointments
            
        except Exception as e:
            logger.error(f"Ошибка при получении записей пользователя: {e}")
            return []
    
    def cancel_appointment(self, appointment_id: int) -> bool:
        """Отмена записи"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Обновляем статус
            cursor.execute("""
                UPDATE appointments 
                SET status = 'cancelled' 
                WHERE id = ?
            """, (appointment_id,))
            
            affected_rows = cursor.rowcount
            conn.commit()
            conn.close()
            
            return affected_rows > 0
            
        except Exception as e:
            logger.error(f"Ошибка при отмене записи: {e}")
            return False
    
    # ==================== МАСТЕР: ПОЛУЧЕНИЕ ЗАПИСЕЙ ====================
    
    def get_master_appointments(self, master_id: int, target_date: Optional[date] = None) -> List[Dict[str, Any]]:
        """Получение записей мастера по master_id"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            query = """
                SELECT 
                    a.*, 
                    u.first_name as client_first_name, 
                    u.last_name as client_last_name,
                    u.phone as client_phone,
                    GROUP_CONCAT(DISTINCT COALESCE(st.title, 'Услуга ' || s.id)) as services_titles
                FROM appointments a
                JOIN users u ON a.client_id = u.id
                LEFT JOIN appointment_services aps ON a.id = aps.appointment_id
                LEFT JOIN services s ON aps.service_id = s.id
                LEFT JOIN service_translations st ON s.id = st.service_id AND st.language = 'ru'
                WHERE a.master_id = ? AND a.status IN ('pending', 'confirmed')
            """
            
            params = [master_id]
            
            if target_date:
                query += " AND a.appointment_date = ?"
                params.append(target_date.isoformat())
            
            query += " GROUP BY a.id ORDER BY a.start_time"
            
            logger.info(f"Выполняем запрос для мастера {master_id} на дату {target_date}")
            cursor.execute(query, tuple(params))
            
            appointments = []
            for row in cursor.fetchall():
                appointments.append(dict(row))
            
            conn.close()
            logger.info(f"Найдено записей для мастера {master_id}: {len(appointments)}")
            return appointments
            
        except Exception as e:
            logger.error(f"Ошибка при получении записей мастера: {e}", exc_info=True)
            return []
    
    def get_master_appointments_by_telegram_id(self, telegram_id: int) -> List[Dict[str, Any]]:
        """Получение записей мастера по telegram_id"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            query = """
                SELECT 
                    a.*, 
                    u.first_name as client_first_name, 
                    u.last_name as client_last_name,
                    u.phone as client_phone,
                    GROUP_CONCAT(DISTINCT COALESCE(st.title, 'Услуга ' || s.id)) as services_titles
                FROM appointments a
                JOIN users u ON a.client_id = u.id
                LEFT JOIN appointment_services aps ON a.id = aps.appointment_id
                LEFT JOIN services s ON aps.service_id = s.id
                LEFT JOIN service_translations st ON s.id = st.service_id AND st.language = 'ru'
                WHERE a.master_telegram_id = ? AND a.status IN ('pending', 'confirmed')
                GROUP BY a.id ORDER BY a.appointment_date DESC, a.start_time DESC
            """
            
            cursor.execute(query, (str(telegram_id),))
            
            appointments = []
            for row in cursor.fetchall():
                appointments.append(dict(row))
            
            conn.close()
            logger.info(f"Найдено записей для мастера telegram_id={telegram_id}: {len(appointments)}")
            return appointments
            
        except Exception as e:
            logger.error(f"Ошибка при получении записей мастера по telegram_id: {e}", exc_info=True)
            return []
    
    def get_master_appointments_by_telegram_id_and_date(self, telegram_id: int, target_date: date) -> List[Dict[str, Any]]:
        """Получение записей мастера по telegram_id на конкретную дату"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            query = """
                SELECT 
                    a.*, 
                    u.first_name as client_first_name, 
                    u.last_name as client_last_name,
                    u.phone as client_phone,
                    GROUP_CONCAT(DISTINCT COALESCE(st.title, 'Услуга ' || s.id)) as services_titles
                FROM appointments a
                JOIN users u ON a.client_id = u.id
                LEFT JOIN appointment_services aps ON a.id = aps.appointment_id
                LEFT JOIN services s ON aps.service_id = s.id
                LEFT JOIN service_translations st ON s.id = st.service_id AND st.language = 'ru'
                WHERE a.master_telegram_id = ? AND a.appointment_date = ? 
                AND a.status IN ('pending', 'confirmed')
                GROUP BY a.id ORDER BY a.start_time
            """
            
            cursor.execute(query, (str(telegram_id), target_date.isoformat()))
            
            appointments = []
            for row in cursor.fetchall():
                appointments.append(dict(row))
            
            conn.close()
            return appointments
            
        except Exception as e:
            logger.error(f"Ошибка при получении записей мастера по telegram_id и дате: {e}")
            return []
    
    def get_upcoming_appointments_for_notification(self, hours_before: int) -> List[Dict[str, Any]]:
        """Получение записей для уведомлений"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Вычисляем время, до которого нужно отправлять уведомления
            now = datetime.now()
            notification_time = now + timedelta(hours=hours_before)
            
            # Получаем записи, которые начнутся в указанное время
            cursor.execute("""
                SELECT 
                    a.*, 
                    u.telegram_id as client_telegram_id,
                    u.language as client_language,
                    m.user_id as master_user_id
                FROM appointments a
                JOIN users u ON a.client_id = u.id
                LEFT JOIN masters m ON a.master_id = m.id
                WHERE a.status IN ('pending', 'confirmed')
                AND DATE(a.appointment_date) = DATE(?)
                AND TIME(a.start_time) BETWEEN TIME(?) AND TIME(?, '+1 hour')
            """, (
                notification_time.date().isoformat(),
                (notification_time - timedelta(minutes=30)).time().strftime('%H:%M'),
                notification_time.time().strftime('%H:%M')
            ))
            
            appointments = []
            for row in cursor.fetchall():
                appointments.append(dict(row))
            
            conn.close()
            return appointments
            
        except Exception as e:
            logger.error(f"Ошибка при получении записей для уведомлений: {e}")
            return []
    
    # ==================== ДОПОЛНИТЕЛЬНЫЕ МЕТОДЫ ====================
    
    def get_appointment_by_id(self, appointment_id: int) -> Optional[Dict[str, Any]]:
        """Получение записи по ID"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    a.*, 
                    u.first_name as client_first_name, 
                    u.last_name as client_last_name,
                    u.telegram_id as client_telegram_id,
                    m1.first_name as master_first_name,
                    m1.last_name as master_last_name,
                    GROUP_CONCAT(DISTINCT COALESCE(st.title, 'Услуга ' || s.id)) as services_titles
                FROM appointments a
                JOIN users u ON a.client_id = u.id
                LEFT JOIN masters m ON a.master_id = m.id
                LEFT JOIN users m1 ON m.user_id = m1.id
                LEFT JOIN appointment_services aps ON a.id = aps.appointment_id
                LEFT JOIN services s ON aps.service_id = s.id
                LEFT JOIN service_translations st ON s.id = st.service_id AND st.language = 'ru'
                WHERE a.id = ?
                GROUP BY a.id
            """, (appointment_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            return dict(row) if row else None
            
        except Exception as e:
            logger.error(f"Ошибка при получении записи: {e}")
            return None
    
    # ==================== ПОЛЬЗОВАТЕЛЬ ====================
    
    def get_user_language(self, user_id: int) -> str:
        """Получение языка пользователя"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT language FROM users WHERE id = ?", (user_id,))
            result = cursor.fetchone()
            conn.close()
            
            if result and result['language'] in Config.SUPPORTED_LANGUAGES:
                return result['language']
            return Config.DEFAULT_LANGUAGE
            
        except Exception as e:
            logger.error(f"Ошибка при получении языка пользователя: {e}")
            return Config.DEFAULT_LANGUAGE
    
    # ==================== УТИЛИТЫ ====================
    
    def get_user_by_telegram_id(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        """Получение пользователя по Telegram ID"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM users WHERE telegram_id = ? OR phone = ?", 
                          (telegram_id, str(telegram_id)))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return dict(result)
            return None
            
        except Exception as e:
            logger.error(f"Ошибка при получении пользователя: {e}")
            return None
    
    def debug_user_info(self, telegram_id: int) -> Dict[str, Any]:
        """Отладочная информация о пользователе"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Полная информация о пользователе
            cursor.execute("""
                SELECT 
                    u.*,
                    m.id as master_id,
                    m.qualification,
                    m.is_active as master_is_active,
                    CASE 
                        WHEN m.id IS NOT NULL THEN 'master'
                        ELSE 'client'
                    END as user_type
                FROM users u
                LEFT JOIN masters m ON u.id = m.user_id
                WHERE u.telegram_id = ? OR u.phone = ?
            """, (telegram_id, str(telegram_id)))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return dict(result)
            return {}
            
        except Exception as e:
            logger.error(f"Ошибка при получении отладочной информации: {e}")
            return {}