# main.py (исправленная версия с исправлением синтаксической ошибки)
from app.auth import router as auth_router
from fastapi import FastAPI, UploadFile, File, HTTPException, Form, Depends, Query, Body, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import logging
import sqlite3
import os

DB_PATH = os.environ.get("DATABASE_PATH", "/data/salon.db")
from datetime import datetime, date, timedelta
import uuid
from pathlib import Path
import imghdr
import json

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Простая конфигурация
class Settings:
    APP_NAME = "Beauty Salon Admin API"
    APP_VERSION = "1.0.0"
    DEBUG = True
    HOST = "0.0.0.0"
    PORT = 8000
    BASE_URL = "http://localhost:8000"
    
    # CORS - разрешаем все для разработки
    CORS_ORIGINS = ["*"]
    
    UPLOAD_DIR = "uploads"
    
    # Настройки загрузки файлов
    MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10MB
    ALLOWED_IMAGE_TYPES = ["image/jpeg", "image/jpg", "image/png", "image/webp", "image/gif"]
    ALLOWED_EXTENSIONS = [".jpg", ".jpeg", ".png", ".webp", ".gif"]
    
    # Директории
    MASTERS_UPLOAD_DIR = "masters"
    
    @property
    def upload_base_dir(self):
        return self.UPLOAD_DIR
    
    @property
    def masters_upload_dir(self):
        return os.path.join(self.UPLOAD_DIR, self.MASTERS_UPLOAD_DIR)
    
    def create_upload_dirs(self):
        """Создать все необходимые директории для загрузок"""
        dirs_to_create = [
            self.upload_base_dir,
            self.masters_upload_dir,
        ]
        
        for directory in dirs_to_create:
            os.makedirs(directory, exist_ok=True)
            logger.info(f"Created directory: {directory}")

settings = Settings()

# Pydantic модели для категорий и услуг
class TranslationBase(BaseModel):
    language: str
    title: str
    description: Optional[str] = None

class CategoryCreate(BaseModel):
    parent_id: Optional[int] = None
    is_active: bool = True
    translations: List[TranslationBase]

class CategoryUpdate(BaseModel):
    parent_id: Optional[int] = None
    is_active: Optional[bool] = None
    translations: Optional[List[TranslationBase]] = None

class ServiceCreate(BaseModel):
    category_id: int
    duration_minutes: int
    price: float
    is_active: bool = True
    translations: List[TranslationBase]

class ServiceUpdate(BaseModel):
    category_id: Optional[int] = None
    duration_minutes: Optional[int] = None
    price: Optional[float] = None
    is_active: Optional[bool] = None
    translations: Optional[List[TranslationBase]] = None

# Pydantic модели для записей
class AppointmentCreate(BaseModel):
    client_id: int
    master_id: Optional[int] = None
    appointment_date: date
    start_time: str
    services: List[int]
    status: str = "pending"

class AppointmentUpdate(BaseModel):
    master_id: Optional[int] = None
    appointment_date: Optional[date] = None
    start_time: Optional[str] = None
    status: Optional[str] = None

# Pydantic модели для клиентов
class ClientCreate(BaseModel):
    first_name: str
    last_name: Optional[str] = ""
    phone: str
    email: Optional[str] = ""

class ClientUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None

# Pydantic модели для связи мастер-услуги
class MasterServiceLink(BaseModel):
    service_id: int
    category_id: int
    is_primary: bool = True

class MasterWithServices(BaseModel):
    id: int
    first_name: str
    last_name: str
    phone: Optional[str]
    photo_url: Optional[str]
    qualification: Optional[str]
    services: List[MasterServiceLink]
    telegram_id: Optional[str]
    
class ServiceWithMasters(BaseModel):
    id: int
    title: str
    description: Optional[str]
    price: float
    duration_minutes: int
    category_id: int
    masters: List[dict]

class MasterServicesBatchAdd(BaseModel):
    service_ids: List[int]
    is_primary: bool = False

# Создаем директорию для фото мастеров
MASTERS_PHOTO_DIR = Path(settings.masters_upload_dir)
MASTERS_PHOTO_DIR.mkdir(parents=True, exist_ok=True)

def validate_image_file(file_path: Path) -> bool:
    """Проверяет, является ли файл валидным изображением"""
    try:
        image_type = imghdr.what(file_path)
        if not image_type:
            return False
            
        allowed_types = ['jpeg', 'jpg', 'png', 'webp', 'gif']
        return image_type in allowed_types
        
    except Exception:
        return False

def save_master_photo(file: UploadFile) -> str:
    """Сохраняет загруженное фото мастера"""
    try:
        # Временный файл для проверки
        temp_filename = f"temp_{uuid.uuid4()}"
        temp_path = MASTERS_PHOTO_DIR / temp_filename
        
        # Сохраняем временно для проверки
        with open(temp_path, "wb") as buffer:
            content = file.file.read()
            buffer.write(content)
            file.file.seek(0)  # Возвращаем курсор в начало
        
        # Проверяем размер файла
        file_size = os.path.getsize(temp_path)
        if file_size > settings.MAX_UPLOAD_SIZE:
            os.remove(temp_path)
            raise HTTPException(status_code=400, detail=f"Файл слишком большой. Максимум: {settings.MAX_UPLOAD_SIZE / (1024 * 1024)}MB")
        
        # Проверяем расширение файла
        original_filename = file.filename or ""
        file_ext = Path(original_filename).suffix.lower()
        if file_ext not in settings.ALLOWED_EXTENSIONS:
            os.remove(temp_path)
            raise HTTPException(status_code=400, detail=f"Недопустимое расширение файла. Разрешены: {', '.join(settings.ALLOWED_EXTENSIONS)}")
        
        # Проверяем содержимое файла
        if not validate_image_file(temp_path):
            os.remove(temp_path)
            raise HTTPException(status_code=400, detail="Файл не является валидным изображением")
        
        # Определяем реальный тип изображения
        image_type = imghdr.what(temp_path)
        if image_type == 'jpeg':
            final_ext = '.jpg'
        elif image_type:
            final_ext = f'.{image_type}'
        else:
            final_ext = file_ext or '.jpg'
        
        # Генерируем окончательное имя файла
        final_filename = f"{uuid.uuid4()}{final_ext}"
        final_path = MASTERS_PHOTO_DIR / final_filename
        
        # Переименовываем временный файл в окончательный
        os.rename(temp_path, final_path)
        
        logger.info(f"Photo saved: {original_filename} -> {final_filename} ({file_size} bytes)")
        return final_filename
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving photo: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка при сохранении файла: {str(e)}")

def delete_master_photo(filename: str):
    """Удаляет фото мастера"""
    try:
        if filename:
            photo_path = MASTERS_PHOTO_DIR / filename
            if photo_path.exists():
                photo_path.unlink()
                logger.info(f"Deleted photo: {filename}")
    except Exception as e:
        logger.error(f"Error deleting photo {filename}: {e}")

def get_unique_telegram_id(cursor):
    """Генерирует уникальный telegram_id для мастера"""
    # Находим максимальный telegram_id среди мастеров
    cursor.execute("SELECT MAX(telegram_id) as max_id FROM users WHERE role = 'master'")
    result = cursor.fetchone()
    max_id = result[0] if result[0] else 1000  # Начинаем с 1000
    
    # Возвращаем следующий ID
    return max_id + 1

def get_unique_client_telegram_id(cursor):
    """Генерирует уникальный telegram_id для клиента"""
    # Находим максимальный telegram_id среди клиентов
    cursor.execute("SELECT MAX(telegram_id) as max_id FROM users WHERE role = 'client'")
    result = cursor.fetchone()
    max_id = result[0] if result[0] else 2000  # Начинаем с 2000
    
    # Возвращаем следующий ID
    return max_id + 1

def get_db_connection():
    """Создание соединения с БД"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    """Инициализация базы данных"""
    try:
        logger.info("Initializing database...")

        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

        if not os.path.exists(DB_PATH):
            logger.info(f"Database file not found, creating: {DB_PATH}")

        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # SQL команды для создания таблиц
        tables_sql = [
            # users
            """CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE,
                role TEXT NOT NULL,
                first_name TEXT,
                last_name TEXT,
                phone TEXT,
                email TEXT,
                language TEXT DEFAULT 'ru',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );""",
            
            # masters
            """CREATE TABLE IF NOT EXISTS masters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                photo TEXT,
                qualification TEXT,
                description TEXT,
                is_active INTEGER DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );""",
            
            # master_work_schedule
            """CREATE TABLE IF NOT EXISTS master_work_schedule (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                master_id INTEGER NOT NULL,
                day_of_week INTEGER NOT NULL,
                start_time TIME NOT NULL,
                end_time TIME NOT NULL,
                FOREIGN KEY (master_id) REFERENCES masters(id)
            );""",
            
            # service_categories
            """CREATE TABLE IF NOT EXISTS service_categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                parent_id INTEGER,
                is_active INTEGER DEFAULT 1,
                FOREIGN KEY (parent_id) REFERENCES service_categories(id)
            );""",
            
            # service_category_translations
            """CREATE TABLE IF NOT EXISTS service_category_translations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER NOT NULL,
                language TEXT NOT NULL,
                title TEXT NOT NULL,
                FOREIGN KEY (category_id) REFERENCES service_categories(id)
            );""",
            
            # services
            """CREATE TABLE IF NOT EXISTS services (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER NOT NULL,
                duration_minutes INTEGER NOT NULL,
                price REAL NOT NULL,
                is_active INTEGER DEFAULT 1,
                FOREIGN KEY (category_id) REFERENCES service_categories(id)
            );""",
            
            # service_translations
            """CREATE TABLE IF NOT EXISTS service_translations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                service_id INTEGER NOT NULL,
                language TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                FOREIGN KEY (service_id) REFERENCES services(id)
            );""",
            
            # appointments
            """CREATE TABLE IF NOT EXISTS appointments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER NOT NULL,
                master_id INTEGER,
                appointment_date DATE NOT NULL,
                start_time TIME NOT NULL,
                end_time TIME NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (client_id) REFERENCES users(id),
                FOREIGN KEY (master_id) REFERENCES masters(id)
            );""",
            
            # appointment_services
            """CREATE TABLE IF NOT EXISTS appointment_services (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                appointment_id INTEGER NOT NULL,
                service_id INTEGER NOT NULL,
                FOREIGN KEY (appointment_id) REFERENCES appointments(id),
                FOREIGN KEY (service_id) REFERENCES services(id)
            );""",
            
            # master_services (НОВАЯ таблица для связи мастер-услуги)
            """CREATE TABLE IF NOT EXISTS master_services (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                master_id INTEGER NOT NULL,
                service_id INTEGER NOT NULL,
                category_id INTEGER NOT NULL,
                is_primary INTEGER DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (master_id) REFERENCES masters(id),
                FOREIGN KEY (service_id) REFERENCES services(id),
                FOREIGN KEY (category_id) REFERENCES service_categories(id),
                UNIQUE(master_id, service_id)
            );""",
            
            # reviews
            """CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                appointment_id INTEGER NOT NULL,
                client_id INTEGER NOT NULL,
                master_id INTEGER NOT NULL,
                rating INTEGER NOT NULL,
                text TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (appointment_id) REFERENCES appointments(id),
                FOREIGN KEY (client_id) REFERENCES users(id),
                FOREIGN KEY (master_id) REFERENCES masters(id)
            );""",
            
            # review_photos
            """CREATE TABLE IF NOT EXISTS review_photos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                review_id INTEGER NOT NULL,
                photo_url TEXT NOT NULL,
                FOREIGN KEY (review_id) REFERENCES reviews(id)
            );""",
            
            # bonuses
            """CREATE TABLE IF NOT EXISTS bonuses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER NOT NULL UNIQUE,
                balance INTEGER DEFAULT 0,
                FOREIGN KEY (client_id) REFERENCES users(id)
            );""",
            
            # bonus_history
            """CREATE TABLE IF NOT EXISTS bonus_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER NOT NULL,
                amount INTEGER NOT NULL,
                reason TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (client_id) REFERENCES users(id)
            );""",
            
            # admin_logs
            """CREATE TABLE IF NOT EXISTS admin_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                details TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (admin_id) REFERENCES users(id)
            );"""
        ]
        
        # Создаем таблицы
        for sql in tables_sql:
            try:
                cursor.execute(sql)
            except Exception as e:
                logger.error(f"Error creating table: {e}")
        
        # Создаем индексы
        indexes_sql = [
            "CREATE INDEX IF NOT EXISTS idx_masters_user_id ON masters(user_id);",
            "CREATE INDEX IF NOT EXISTS idx_masters_is_active ON masters(is_active);",
            "CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);",
            "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);",
            "CREATE INDEX IF NOT EXISTS idx_service_categories_parent_id ON service_categories(parent_id);",
            "CREATE INDEX IF NOT EXISTS idx_service_categories_is_active ON service_categories(is_active);",
            "CREATE INDEX IF NOT EXISTS idx_services_category_id ON services(category_id);",
            "CREATE INDEX IF NOT EXISTS idx_services_is_active ON services(is_active);",
            # Индексы для новой таблицы master_services
            "CREATE INDEX IF NOT EXISTS idx_master_services_master_id ON master_services(master_id);",
            "CREATE INDEX IF NOT EXISTS idx_master_services_service_id ON master_services(service_id);",
            "CREATE INDEX IF NOT EXISTS idx_master_services_category_id ON master_services(category_id);",
        ]
        
        for sql in indexes_sql:
            try:
                cursor.execute(sql)
            except Exception as e:
                logger.error(f"Error creating index: {e}")
        
        conn.commit()
        
        # Создаем тестового мастера если таблица пуста
        cursor.execute("SELECT COUNT(*) as count FROM masters")
        count = cursor.fetchone()["count"]
        
        if count == 0:
            logger.info("Creating test master...")
            # Генерируем уникальный telegram_id для тестового мастера
            telegram_id = 1000
            
            # Проверяем, существует ли уже пользователь с таким telegram_id
            cursor.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,))
            existing_user = cursor.fetchone()
            
            if not existing_user:
                # Создаем пользователя для мастера
                cursor.execute("""
                    INSERT INTO users (telegram_id, role, first_name, last_name, phone, email, language)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (telegram_id, 'master', 'Иван', 'Иванов', '+79991234567', 'master@example.com', 'ru'))
                
                user_id = cursor.lastrowid
                
                # Создаем мастера
                cursor.execute("""
                    INSERT INTO masters (user_id, qualification, description, is_active)
                    VALUES (?, ?, ?, ?)
                """, (user_id, 'Топ-мастер', 'Опытный мастер с 10-летним стажем', 1))
                
                conn.commit()
                logger.info("Test master created successfully")
            else:
                logger.info("Test master already exists")
        
        # Создаем тестовые категории если таблица пуста
        cursor.execute("SELECT COUNT(*) as count FROM service_categories")
        category_count = cursor.fetchone()["count"]
        
        if category_count == 0:
            logger.info("Creating test categories...")
            
            # Создаем корневые категории
            cursor.execute("""
                INSERT INTO service_categories (parent_id, is_active) 
                VALUES (NULL, 1)
            """)
            hair_category_id = cursor.lastrowid
            
            cursor.execute("""
                INSERT INTO service_categories (parent_id, is_active) 
                VALUES (NULL, 1)
            """)
            nails_category_id = cursor.lastrowid
            
            # Создаем подкатегории
            cursor.execute("""
                INSERT INTO service_categories (parent_id, is_active) 
                VALUES (?, 1)
            """, (hair_category_id,))
            womens_hair_id = cursor.lastrowid
            
            cursor.execute("""
                INSERT INTO service_categories (parent_id, is_active) 
                VALUES (?, 1)
            """, (hair_category_id,))
            mens_hair_id = cursor.lastrowid
            
            # Добавляем переводы для категорий
            categories_translations = [
                (hair_category_id, 'ru', 'Парикмахерские услуги'),
                (hair_category_id, 'en', 'Hair Services'),
                (hair_category_id, 'tr', 'Kuaför Hizmetleri'),
                (nails_category_id, 'ru', 'Маникюр и педикюр'),
                (nails_category_id, 'en', 'Manicure & Pedicure'),
                (nails_category_id, 'tr', 'Manikür & Pedikür'),
                (womens_hair_id, 'ru', 'Женская стрижка'),
                (womens_hair_id, 'en', 'Women\'s Haircut'),
                (womens_hair_id, 'tr', 'Kadın Saç Kesimi'),
                (mens_hair_id, 'ru', 'Мужская стрижка'),
                (mens_hair_id, 'en', 'Men\'s Haircut'),
                (mens_hair_id, 'tr', 'Erkek Saç Kesimi'),
            ]
            
            for cat_id, lang, title in categories_translations:
                cursor.execute("""
                    INSERT INTO service_category_translations (category_id, language, title)
                    VALUES (?, ?, ?)
                """, (cat_id, lang, title))
            
            conn.commit()
            logger.info("Test categories created successfully")
        
        # Создаем тестового клиента если таблица пуста
        cursor.execute("SELECT COUNT(*) as count FROM users WHERE role = 'client'")
        client_count = cursor.fetchone()["count"]
        
        if client_count == 0:
            logger.info("Creating test clients...")
            
            # Создаем тестовых клиентов
            test_clients = [
                (2001, 'client', 'Мария', 'Петрова', '+79997654321', 'client1@example.com', 'ru'),
                (2002, 'client', 'Иван', 'Иванов', '+79991234567', 'client2@example.com', 'ru'),
                (2003, 'client', 'Анна', 'Сидорова', '+79992345678', 'client3@example.com', 'ru'),
            ]
            
            for telegram_id, role, first_name, last_name, phone, email, language in test_clients:
                cursor.execute("""
                    INSERT INTO users (telegram_id, role, first_name, last_name, phone, email, language)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (telegram_id, role, first_name, last_name, phone, email, language))
            
            conn.commit()
            logger.info("Test clients created successfully")

        # Создаем тестовые услуги если таблица пуста
        cursor.execute("SELECT COUNT(*) as count FROM services")
        services_count = cursor.fetchone()["count"]
        
        if services_count == 0 and 'womens_hair_id' in locals() and 'mens_hair_id' in locals():
            logger.info("Creating test services...")
            
            # Создаем тестовые услуги
            test_services = [
                (womens_hair_id, 60, 1500.0, 1),
                (womens_hair_id, 90, 2000.0, 1),
                (mens_hair_id, 30, 800.0, 1),
                (mens_hair_id, 45, 1200.0, 1),
            ]
            
            for category_id, duration, price, is_active in test_services:
                cursor.execute("""
                    INSERT INTO services (category_id, duration_minutes, price, is_active)
                    VALUES (?, ?, ?, ?)
                """, (category_id, duration, price, is_active))
                
                service_id = cursor.lastrowid
                
                # Добавляем переводы для услуги
                cursor.execute("""
                    INSERT INTO service_translations (service_id, language, title, description)
                    VALUES (?, ?, ?, ?)
                """, (service_id, 'ru', f'Тестовая услуга {service_id}', f'Описание тестовой услуги {service_id}'))
            
            conn.commit()
            logger.info("Test services created successfully")
        
        cursor.close()
        conn.close()
        
        logger.info("Database initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error initializing database: {e}", exc_info=True)
        return False

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения"""
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Server: http://{settings.HOST}:{settings.PORT}")
    
    # Создаем папку для загрузок
    settings.create_upload_dirs()
    
    # Инициализация базы данных
    if not init_database():
        logger.error("Failed to initialize database")
        raise RuntimeError("Database initialization failed")
    
    logger.info("Application initialized successfully")
    
    yield
    
    logger.info("Shutting down Beauty Salon Admin API")

# Создание FastAPI приложения
app = FastAPI(
    title=settings.APP_NAME,
    description="API для админ-панели салона красоты",
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# ==================== НАСТРОЙКА CORS ====================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Подключаем статические файлы для загруженных фото
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# ==================== ANALYTICS API ====================
from fastapi import APIRouter

analytics_router = APIRouter(prefix="/analytics", tags=["analytics"])

@analytics_router.get("/dashboard")
async def get_dashboard_stats(
    period_days: int = Query(30, ge=1, le=365)
):
    """
    Получение статистики для дашборда (реальные данные из БД)
    """
    logger.info(f"✅ Dashboard request")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Рассчитываем дату начала периода
        start_date = date.today() - timedelta(days=period_days)
        
        # 1. Статистика по записям
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
                SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END) as cancelled
            FROM appointments
            WHERE appointment_date >= ?
        """, (start_date.isoformat(),))
        
        appointment_stats = cursor.fetchone()
        
        # 2. Статистика по клиентам
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT client_id) as total_clients
            FROM appointments
            WHERE appointment_date >= ?
        """, (start_date.isoformat(),))
        
        total_clients_result = cursor.fetchone()
        total_clients = total_clients_result[0] if total_clients_result else 0
        
        # Новые клиенты (которые записались впервые в этот период)
        cursor.execute("""
            SELECT COUNT(DISTINCT client_id) as new_clients
            FROM appointments a
            WHERE appointment_date >= ?
            AND NOT EXISTS (
                SELECT 1 FROM appointments a2 
                WHERE a2.client_id = a.client_id 
                AND a2.appointment_date < ?
            )
        """, (start_date.isoformat(), start_date.isoformat()))
        
        new_clients_result = cursor.fetchone()
        new_clients = new_clients_result[0] if new_clients_result else 0
        
        # 3. Активные мастера
        cursor.execute("""
            SELECT COUNT(DISTINCT m.id) as active_masters
            FROM masters m
            JOIN appointments a ON m.id = a.master_id
            WHERE a.appointment_date >= ?
            AND m.is_active = 1
        """, (start_date.isoformat(),))
        
        active_masters_result = cursor.fetchone()
        active_masters = active_masters_result[0] if active_masters_result else 0
        
        # 4. Общая выручка
        cursor.execute("""
            SELECT COALESCE(SUM(s.price), 0) as total_revenue
            FROM appointments a
            JOIN appointment_services aps ON a.id = aps.appointment_id
            JOIN services s ON aps.service_id = s.id
            WHERE a.appointment_date >= ? 
            AND a.status = 'completed'
        """, (start_date.isoformat(),))
        
        revenue_result = cursor.fetchone()
        total_revenue = revenue_result[0] if revenue_result else 0
        
        # 5. Выручка за сегодня
        today = date.today()
        cursor.execute("""
            SELECT COALESCE(SUM(s.price), 0) as today_revenue
            FROM appointments a
            JOIN appointment_services aps ON a.id = aps.appointment_id
            JOIN services s ON aps.service_id = s.id
            WHERE a.appointment_date = ? 
            AND a.status = 'completed'
        """, (today.isoformat(),))
        
        today_revenue_result = cursor.fetchone()
        today_revenue = today_revenue_result[0] if today_revenue_result else 0
        
        # 6. Общее количество мастеров
        cursor.execute("SELECT COUNT(*) as total_masters FROM masters WHERE is_active = 1")
        total_masters_result = cursor.fetchone()
        total_masters = total_masters_result[0] if total_masters_result else 0
        
        # 7. Общее количество клиентов
        cursor.execute("SELECT COUNT(*) as all_clients FROM users WHERE role = 'client'")
        all_clients_result = cursor.fetchone()
        all_clients = all_clients_result[0] if all_clients_result else 0
        
        conn.close()
        
        return {
            "success": True,
            "period_days": period_days,
            "appointments": {
                "total": appointment_stats[0] if appointment_stats else 0,
                "completed": appointment_stats[1] if appointment_stats else 0,
                "pending": appointment_stats[2] if appointment_stats else 0,
                "cancelled": appointment_stats[3] if appointment_stats else 0
            },
            "clients": {
                "total": all_clients,
                "new": new_clients,
                "active": total_clients
            },
            "masters": {
                "total": total_masters,
                "active": active_masters,
                "available": total_masters  # Упрощенно - все активные мастера доступны
            },
            "revenue": {
                "total": total_revenue,
                "today": today_revenue,
                "change": 12.5  # TODO: Рассчитать реальный процент изменения
            }
        }
        
    except Exception as e:
        logger.error(f"Error fetching dashboard stats: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "appointments": {"total": 0, "completed": 0, "pending": 0, "cancelled": 0},
            "clients": {"total": 0, "new": 0, "active": 0},
            "masters": {"total": 0, "active": 0, "available": 0},
            "revenue": {"total": 0, "today": 0, "change": 0}
        }

@analytics_router.get("/masters-load")
async def get_masters_load(
    days: int = Query(7, ge=1, le=30)
):
    """
    Получение загрузки мастеров (реальные данные из БД)
    """
    logger.info(f"✅ Masters load request")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Рассчитываем дату начала периода
        start_date = date.today() - timedelta(days=days)
        
        # Получаем загрузку мастеров по количеству записей
        cursor.execute("""
            SELECT 
                u.first_name || ' ' || u.last_name as master_name,
                COUNT(a.id) as appointment_count,
                SUM(CASE WHEN a.status = 'completed' THEN 1 ELSE 0 END) as completed_count
            FROM masters m
            JOIN users u ON m.user_id = u.id
            LEFT JOIN appointments a ON m.id = a.master_id AND a.appointment_date >= ?
            WHERE m.is_active = 1
            GROUP BY m.id, u.first_name, u.last_name
            ORDER BY appointment_count DESC
        """, (start_date.isoformat(),))
        
        masters_data = cursor.fetchall()
        
        # Рассчитываем процент загрузки (условный, на основе количества записей)
        masters = []
        if masters_data:
            # Находим максимальное количество записей для расчета процентов
            max_appointments = max(row[1] for row in masters_data) if masters_data else 1
            
            for row in masters_data:
                master_name = row[0] or "Без имени"
                appointment_count = row[1] or 0
                completed_count = row[2] or 0
                
                # Расчет загрузки в процентах (0-100)
                if max_appointments > 0:
                    load_percent = min(100, int((appointment_count / max_appointments) * 100))
                else:
                    load_percent = 0
                
                masters.append({
                    "name": master_name,
                    "load": load_percent,
                    "appointment_count": appointment_count,
                    "completed_count": completed_count
                })
        
        conn.close()
        
        return {
            "success": True,
            "days": days,
            "masters": masters
        }
        
    except Exception as e:
        logger.error(f"Error fetching masters load: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "days": days,
            "masters": []
        }

@analytics_router.get("/services-popularity")
async def get_services_popularity(
    period_days: int = Query(30, ge=1, le=365)
):
    """
    Получение популярности услуг (реальные данные из БД)
    """
    logger.info(f"✅ Services popularity request")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        start_date = date.today() - timedelta(days=period_days)
        
        cursor.execute("""
            SELECT 
                st.title as service_title,
                COUNT(aps.service_id) as service_count,
                COALESCE(SUM(s.price), 0) as revenue
            FROM appointment_services aps
            JOIN appointments a ON aps.appointment_id = a.id
            JOIN services s ON aps.service_id = s.id
            LEFT JOIN service_translations st ON s.id = st.service_id AND st.language = 'ru'
            WHERE a.appointment_date >= ? AND a.status = 'completed'
            GROUP BY aps.service_id, st.title
            ORDER BY service_count DESC
            LIMIT 10
        """, (start_date.isoformat(),))
        
        services = []
        for row in cursor.fetchall():
            services.append({
                "title": row[0] or f"Услуга",
                "service_count": row[1],
                "revenue": row[2]
            })
        
        conn.close()
        
        return {
            "success": True,
            "period_days": period_days,
            "services": services
        }
        
    except Exception as e:
        logger.error(f"Error fetching services popularity: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "period_days": period_days,
            "services": []
        }

@analytics_router.get("/recent-appointments")
async def get_recent_appointments(
    limit: int = Query(10, ge=1, le=50)
):
    """
    Получение последних записей
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                a.id,
                a.appointment_date,
                a.start_time,
                a.status,
                u1.first_name as client_first_name,
                u1.last_name as client_last_name,
                u2.first_name as master_first_name,
                u2.last_name as master_last_name,
                (SELECT GROUP_CONCAT(st.title, ', ')
                 FROM appointment_services aps2
                 JOIN services s2 ON aps2.service_id = s2.id
                 LEFT JOIN service_translations st ON s2.id = st.service_id AND st.language = 'ru'
                 WHERE aps2.appointment_id = a.id) as services
            FROM appointments a
            JOIN users u1 ON a.client_id = u1.id
            LEFT JOIN masters m ON a.master_id = m.id
            LEFT JOIN users u2 ON m.user_id = u2.id
            ORDER BY a.appointment_date DESC, a.start_time DESC
            LIMIT ?
        """, (limit,))
        
        appointments = []
        for row in cursor.fetchall():
            appointments.append({
                "id": row[0],
                "date": row[1],
                "time": row[2],
                "status": row[3],
                "client_name": f"{row[4]} {row[5]}" if row[5] else row[4],
                "master_name": f"{row[6]} {row[7]}" if row[6] else "Не назначен",
                "services": row[8] or "Не указаны"
            })
        
        conn.close()
        
        return {
            "success": True,
            "appointments": appointments
        }
        
    except Exception as e:
        logger.error(f"Error fetching recent appointments: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "appointments": []
        }

@analytics_router.get("/test")
async def test_endpoint():
    """
    Простой тестовый endpoint для проверки
    """
    return {
        "success": True,
        "message": "Аналитика работает!",
        "timestamp": date.today().isoformat()
    }

# Регистрируем роутер аналитики
app.include_router(analytics_router)

# Регистрируем роутер аутентификации
app.include_router(auth_router)

# ==================== API ДЛЯ СВЯЗИ МАСТЕР-УСЛУГИ ====================

@app.get("/masters/{master_id}/services")
async def get_master_services(
    master_id: int,
    language: str = Query("ru")
):
    """Получение всех услуг мастера"""
    logger.info(f"Get services for master {master_id}")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Проверяем существование мастера
        cursor.execute("SELECT id FROM masters WHERE id = ?", (master_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Мастер не найден")
        
        cursor.execute("""
            SELECT 
                ms.service_id, ms.category_id, ms.is_primary,
                s.price, s.duration_minutes, s.is_active as service_active,
                st.title as service_title, st.description as service_description,
                sct.title as category_title
            FROM master_services ms
            JOIN services s ON ms.service_id = s.id
            LEFT JOIN service_translations st ON s.id = st.service_id AND st.language = ?
            LEFT JOIN service_categories sc ON ms.category_id = sc.id
            LEFT JOIN service_category_translations sct ON sc.id = sct.category_id AND sct.language = ?
            WHERE ms.master_id = ? AND s.is_active = 1
            ORDER BY ms.is_primary DESC, st.title
        """, (language, language, master_id))
        
        services = []
        for row in cursor.fetchall():
            services.append({
                "service_id": row[0],
                "category_id": row[1],
                "is_primary": bool(row[2]),
                "price": row[3],
                "duration_minutes": row[4],
                "service_active": bool(row[5]),
                "service_title": row[6],
                "service_description": row[7],
                "category_title": row[8]
            })
        
        conn.close()
        return {
            "success": True,
            "master_id": master_id,
            "services": services,
            "count": len(services)
        }
        
    except Exception as e:
        logger.error(f"Error fetching master services: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/masters/{master_id}/services")
async def add_service_to_master(
    master_id: int,
    service_id: str = Form(...),  # Получаем как строку
    is_primary: str = Form("false")  # Получаем как строку
):
    """Добавление услуги мастеру (FormData версия)"""
    
    # Конвертируем типы
    try:
        service_id_int = int(service_id)
        is_primary_bool = is_primary.lower() == "true"
    except ValueError:
        raise HTTPException(status_code=400, detail="Некорректные данные")
    
    logger.info(f"Add service {service_id_int} to master {master_id}, primary={is_primary_bool}")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Проверяем существование мастера
        cursor.execute("SELECT id FROM masters WHERE id = ?", (master_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Мастер не найден")
        
        # Проверяем существование услуги
        cursor.execute("""
            SELECT id, category_id FROM services 
            WHERE id = ? AND is_active = 1
        """, (service_id_int,))
        
        service = cursor.fetchone()
        if not service:
            raise HTTPException(status_code=404, detail="Услуга не найдена или не активна")
        
        category_id = service[1]
        
        # Проверяем, не привязана ли уже услуга
        cursor.execute("""
            SELECT id FROM master_services 
            WHERE master_id = ? AND service_id = ?
        """, (master_id, service_id_int))
        
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Услуга уже привязана к мастеру")
        
        # Добавляем связь
        cursor.execute("""
            INSERT INTO master_services (master_id, service_id, category_id, is_primary)
            VALUES (?, ?, ?, ?)
        """, (master_id, service_id_int, category_id, 1 if is_primary_bool else 0))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Service {service_id_int} added to master {master_id}")
        
        return {
            "success": True, 
            "message": "Услуга успешно привязана к мастеру",
            "master_id": master_id,
            "service_id": service_id_int
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding service to master: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    
@app.delete("/masters/{master_id}/services/{service_id}")
async def remove_service_from_master(
    master_id: int,
    service_id: int
):
    """Удаление услуги у мастера"""
    logger.info(f"Remove service {service_id} from master {master_id}")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            DELETE FROM master_services 
            WHERE master_id = ? AND service_id = ?
        """, (master_id, service_id))
        
        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        if not deleted:
            raise HTTPException(status_code=404, detail="Связь не найдена")
        
        logger.info(f"Service {service_id} removed from master {master_id}")
        
        return {
            "success": True, 
            "message": "Услуга удалена у мастера",
            "master_id": master_id,
            "service_id": service_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing service from master: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/services/{service_id}/masters")
async def get_service_masters(
    service_id: int,
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100)
):
    """Получение мастеров, которые предоставляют услугу"""
    logger.info(f"Get masters for service {service_id}")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        offset = (page - 1) * per_page
        
        # Получаем мастеров для услуги
        cursor.execute("""
            SELECT 
                m.id, m.is_active,
                u.first_name, u.last_name, u.phone, u.email,
                ms.is_primary,
                m.photo, m.qualification
            FROM master_services ms
            JOIN masters m ON ms.master_id = m.id
            JOIN users u ON m.user_id = u.id
            WHERE ms.service_id = ? AND m.is_active = 1
            ORDER BY ms.is_primary DESC, u.first_name
            LIMIT ? OFFSET ?
        """, (service_id, per_page, offset))
        
        masters = []
        for row in cursor.fetchall():
            master = {
                "id": row[0],
                "is_active": bool(row[1]),
                "first_name": row[2],
                "last_name": row[3],
                "phone": row[4],
                "email": row[5],
                "is_primary": bool(row[6]),
                "photo": row[7],
                "qualification": row[8],
                "photo_url": f"{settings.BASE_URL}/uploads/masters/{row[7]}" if row[7] else None
            }
            masters.append(master)
        
        # Общее количество
        cursor.execute("""
            SELECT COUNT(*) FROM master_services ms
            JOIN masters m ON ms.master_id = m.id
            WHERE ms.service_id = ? AND m.is_active = 1
        """, (service_id,))
        
        total = cursor.fetchone()[0]
        conn.close()
        
        return {
            "success": True,
            "service_id": service_id,
            "items": masters,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page if per_page > 0 else 0
        }
        
    except Exception as e:
        logger.error(f"Error fetching service masters: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/masters/{master_id}/services/batch")
async def add_services_to_master(
    master_id: int,
    batch_data: MasterServicesBatchAdd
):
    """Массовое добавление услуг мастеру"""
    logger.info(f"Batch add services to master {master_id}: {batch_data.service_ids}")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Проверяем существование мастера
        cursor.execute("SELECT id FROM masters WHERE id = ?", (master_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Мастер не найден")
        
        added_count = 0
        failed_services = []
        
        for service_id in batch_data.service_ids:
            try:
                # Проверяем существование услуги
                cursor.execute("""
                    SELECT id, category_id FROM services 
                    WHERE id = ? AND is_active = 1
                """, (service_id,))
                
                service = cursor.fetchone()
                if not service:
                    failed_services.append({"service_id": service_id, "reason": "Не найдена или не активна"})
                    continue
                
                category_id = service[1]
                
                # Проверяем, не привязана ли уже
                cursor.execute("""
                    SELECT id FROM master_services 
                    WHERE master_id = ? AND service_id = ?
                """, (master_id, service_id))
                
                if cursor.fetchone():
                    failed_services.append({"service_id": service_id, "reason": "Уже привязана"})
                    continue
                
                # Добавляем связь
                cursor.execute("""
                    INSERT INTO master_services (master_id, service_id, category_id, is_primary)
                    VALUES (?, ?, ?, ?)
                """, (master_id, service_id, category_id, 1 if batch_data.is_primary else 0))
                
                added_count += 1
                
            except Exception as e:
                failed_services.append({"service_id": service_id, "reason": str(e)})
        
        conn.commit()
        conn.close()
        
        logger.info(f"Added {added_count} services to master {master_id}")
        
        return {
            "success": True,
            "message": f"Добавлено {added_count} услуг",
            "added_count": added_count,
            "failed_services": failed_services
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in batch add services: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/masters/{master_id}/available-services")
async def get_available_services_for_master(
    master_id: int,
    language: str = Query("ru"),
    category_id: Optional[int] = None
):
    """Получение услуг, которые еще не привязаны к мастеру"""
    logger.info(f"Get available services for master {master_id}")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Проверяем существование мастера
        cursor.execute("SELECT id FROM masters WHERE id = ?", (master_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Мастер не найден")
        
        # Получаем ID услуг, которые уже привязаны
        cursor.execute("SELECT service_id FROM master_services WHERE master_id = ?", (master_id,))
        existing_service_ids = [row[0] for row in cursor.fetchall()]
        
        # Формируем запрос для доступных услуг
        query = """
            SELECT 
                s.id, s.category_id, s.duration_minutes, s.price, s.is_active,
                st.title, st.description,
                sct.title as category_title
            FROM services s
            LEFT JOIN service_translations st ON s.id = st.service_id AND st.language = ?
            LEFT JOIN service_categories sc ON s.category_id = sc.id
            LEFT JOIN service_category_translations sct ON sc.id = sct.category_id AND sct.language = ?
            WHERE s.is_active = 1
        """
        
        params = [language, language]
        
        if existing_service_ids:
            placeholders = ','.join(['?'] * len(existing_service_ids))
            query += f" AND s.id NOT IN ({placeholders})"
            params.extend(existing_service_ids)
        
        if category_id is not None:
            query += " AND s.category_id = ?"
            params.append(category_id)
        
        query += " ORDER BY sct.title, st.title"
        
        cursor.execute(query, tuple(params))
        
        services = []
        for row in cursor.fetchall():
            service = {
                "id": row[0],
                "category_id": row[1],
                "duration_minutes": row[2],
                "price": row[3],
                "is_active": bool(row[4]),
                "title": row[5],
                "description": row[6],
                "category_title": row[7]
            }
            services.append(service)
        
        conn.close()
        
        return {
            "success": True,
            "master_id": master_id,
            "available_services": services,
            "count": len(services)
        }
        
    except Exception as e:
        logger.error(f"Error fetching available services: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# ==================== ОБНОВЛЕННЫЕ ENDPOINT ДЛЯ МАСТЕРОВ ====================

@app.get("/masters")
async def get_masters(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
    with_services: bool = Query(False, description="Включать информацию об услугах")
):
    """Получение списка мастеров (обновлено с поддержкой услуг)"""
    logger.info(f"Get masters request with_services={with_services}")
    
    offset = (page - 1) * per_page
    
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Базовый запрос с количеством услуг
        query = """
            SELECT 
                m.*, 
                u.first_name, u.last_name, u.phone, u.email, u.telegram_id,
                (SELECT COUNT(*) FROM master_services ms WHERE ms.master_id = m.id) as services_count
            FROM masters m
            JOIN users u ON m.user_id = u.id
            WHERE u.role = 'master'
        """
        
        count_query = "SELECT COUNT(*) as count FROM masters m JOIN users u ON m.user_id = u.id WHERE u.role = 'master'"
        params = []
        count_params = []
        
        if is_active is not None:
            query += " AND m.is_active = ?"
            count_query += " AND m.is_active = ?"
            params.append(int(is_active))
            count_params.append(int(is_active))
        
        if search:
            query += " AND (u.first_name LIKE ? OR u.last_name LIKE ? OR u.phone LIKE ? OR m.qualification LIKE ? OR u.email LIKE ?)"
            count_query += " AND (u.first_name LIKE ? OR u.last_name LIKE ? OR u.phone LIKE ? OR m.qualification LIKE ? OR u.email LIKE ?)"
            search_term = f"%{search}%"
            params.extend([search_term, search_term, search_term, search_term, search_term])
            count_params.extend([search_term, search_term, search_term, search_term, search_term])
        
        query += " ORDER BY m.created_at DESC LIMIT ? OFFSET ?"
        params.extend([per_page, offset])
        
        cursor.execute(query, tuple(params))
        masters = []
        for row in cursor.fetchall():
            master_dict = {}
            for key in row.keys():
                master_dict[key] = row[key]
            
            # Добавляем URL фото
            if master_dict.get("photo"):
                master_dict["photo_url"] = f"{settings.BASE_URL}/uploads/masters/{master_dict['photo']}"
            else:
                master_dict["photo_url"] = None
            
            masters.append(master_dict)
        
        # Если запрошены услуги, загружаем их для каждого мастера
        if with_services:
            for master in masters:
                cursor.execute("""
                    SELECT 
                        ms.service_id, ms.category_id, ms.is_primary,
                        s.price, s.duration_minutes,
                        st.title as service_title
                    FROM master_services ms
                    JOIN services s ON ms.service_id = s.id
                    LEFT JOIN service_translations st ON s.id = st.service_id AND st.language = 'ru'
                    WHERE ms.master_id = ?
                    ORDER BY ms.is_primary DESC
                """, (master["id"],))
                
                services = []
                for service_row in cursor.fetchall():
                    service_dict = {}
                    for key in service_row.keys():
                        service_dict[key] = service_row[key]
                    services.append(service_dict)
                
                master["services"] = services
        
        # Общее количество
        cursor.execute(count_query, tuple(count_params))
        count_result = cursor.fetchone()
        total = count_result[0] if count_result else 0
        
        conn.close()
        
        logger.info(f"Found {len(masters)} masters, total: {total}")
        
        return {
            "items": masters,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page if per_page > 0 else 0
        }
        
    except Exception as e:
        logger.error(f"Error fetching masters: {e}", exc_info=True)
        return {
            "items": [],
            "total": 0,
            "page": page,
            "per_page": per_page,
            "total_pages": 0
        }

# ==================== APPOINTMENTS API ====================

@app.get("/appointments")
async def get_appointments(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    master_id: Optional[int] = None,
    client_id: Optional[int] = None,
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100)
):
    """Получение списка записей с фильтрацией"""
    logger.info(f"Get appointments request")
    
    offset = (page - 1) * per_page
    
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = """
            SELECT a.*, 
                   u1.first_name as client_first_name, u1.last_name as client_last_name,
                   u2.first_name as master_first_name, u2.last_name as master_last_name
            FROM appointments a
            LEFT JOIN users u1 ON a.client_id = u1.id
            LEFT JOIN masters m ON a.master_id = m.id
            LEFT JOIN users u2 ON m.user_id = u2.id
            WHERE 1=1
        """
        
        count_query = "SELECT COUNT(*) as count FROM appointments WHERE 1=1"
        params = []
        count_params = []
        
        if start_date:
            query += " AND a.appointment_date >= ?"
            count_query += " AND appointment_date >= ?"
            params.append(start_date)
            count_params.append(start_date)
        
        if end_date:
            query += " AND a.appointment_date <= ?"
            count_query += " AND appointment_date <= ?"
            params.append(end_date)
            count_params.append(end_date)
        
        if master_id:
            query += " AND a.master_id = ?"
            count_query += " AND master_id = ?"
            params.append(master_id)
            count_params.append(master_id)
        
        if client_id:
            query += " AND a.client_id = ?"
            count_query += " AND client_id = ?"
            params.append(client_id)
            count_params.append(client_id)
        
        if status:
            query += " AND a.status = ?"
            count_query += " AND status = ?"
            params.append(status)
            count_params.append(status)
        
        query += " ORDER BY a.appointment_date DESC, a.start_time DESC LIMIT ? OFFSET ?"
        params.extend([per_page, offset])
        
        cursor.execute(query, tuple(params))
        appointments = []
        for row in cursor.fetchall():
            appointment_dict = {}
            for key in row.keys():
                appointment_dict[key] = row[key]
            appointments.append(appointment_dict)
        
        # Добавляем услуги для каждой записи
        for appointment in appointments:
            cursor.execute("""
                SELECT s.id, st.title, s.duration_minutes, s.price
                FROM appointment_services aps
                JOIN services s ON aps.service_id = s.id
                LEFT JOIN service_translations st ON s.id = st.service_id AND st.language = 'ru'
                WHERE aps.appointment_id = ?
            """, (appointment["id"],))
            services = []
            for row in cursor.fetchall():
                service_dict = {}
                for key in row.keys():
                    service_dict[key] = row[key]
                services.append(service_dict)
            appointment["services"] = services
        
        # Общее количество
        cursor.execute(count_query, tuple(count_params))
        count_result = cursor.fetchone()
        total = count_result[0] if count_result else 0
        
        conn.close()
        
        logger.info(f"Found {len(appointments)} appointments, total: {total}")
        
        return {
            "items": appointments,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page if per_page > 0 else 0
        }
    
    except Exception as e:
        logger.error(f"Error fetching appointments: {e}", exc_info=True)
        return {
            "items": [],
            "total": 0,
            "page": page,
            "per_page": per_page,
            "total_pages": 0
        }

@app.post("/appointments")
async def create_appointment(appointment_data: AppointmentCreate):
    """Создание новой записи"""
    logger.info(f"Create appointment request: {appointment_data}")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Проверяем существование клиента
        cursor.execute("SELECT id FROM users WHERE id = ? AND role = 'client'", (appointment_data.client_id,))
        client = cursor.fetchone()
        if not client:
            raise HTTPException(status_code=400, detail="Клиент не найден")
        
        # Проверяем существование мастера если указан
        if appointment_data.master_id:
            cursor.execute("SELECT id FROM masters WHERE id = ? AND is_active = 1", (appointment_data.master_id,))
            master = cursor.fetchone()
            if not master:
                raise HTTPException(status_code=400, detail="Мастер не найден или не активен")
        
        # Рассчитываем общую длительность услуг
        total_duration = 0
        
        for service_id in appointment_data.services:
            cursor.execute("SELECT duration_minutes FROM services WHERE id = ? AND is_active = 1", (service_id,))
            service = cursor.fetchone()
            if not service:
                raise HTTPException(status_code=400, detail=f"Услуга с ID {service_id} не найдена или не активна")
            total_duration += service[0]
        
        # Рассчитываем время окончания
        start_dt = datetime.strptime(appointment_data.start_time, "%H:%M")
        end_dt = datetime.combine(date.today(), start_dt.time()) + timedelta(minutes=total_duration)
        end_time = end_dt.strftime("%H:%M")
        
        # Создаем запись
        cursor.execute("""
            INSERT INTO appointments 
            (client_id, master_id, appointment_date, start_time, end_time, status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            appointment_data.client_id,
            appointment_data.master_id,
            appointment_data.appointment_date,
            appointment_data.start_time,
            end_time,
            appointment_data.status
        ))
        
        appointment_id = cursor.lastrowid
        
        if not appointment_id:
            raise HTTPException(status_code=500, detail="Не удалось создать запись")
        
        # Добавляем услуги к записи
        for service_id in appointment_data.services:
            cursor.execute("""
                INSERT INTO appointment_services (appointment_id, service_id)
                VALUES (?, ?)
            """, (appointment_id, service_id))
        
        conn.commit()
        
        # Упрощенный ответ без сложного преобразования
        conn.close()
        
        logger.info(f"Appointment {appointment_id} created successfully")
        
        return {
            "success": True,
            "message": "Запись успешно создана",
            "appointment_id": appointment_id
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating appointment: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка при создании записи: {str(e)}")

@app.put("/appointments/{appointment_id}")
async def update_appointment(appointment_id: int, appointment_data: AppointmentUpdate):
    """Обновление записи"""
    logger.info(f"Update appointment {appointment_id} request")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Проверяем существование записи
        cursor.execute("SELECT * FROM appointments WHERE id = ?", (appointment_id,))
        existing_appointment = cursor.fetchone()
        if not existing_appointment:
            raise HTTPException(status_code=404, detail="Запись не найдена")
        
        update_fields = []
        params = []
        
        if appointment_data.master_id is not None:
            # Проверяем существование мастера
            cursor.execute("SELECT id FROM masters WHERE id = ? AND is_active = 1", (appointment_data.master_id,))
            master = cursor.fetchone()
            if not master:
                raise HTTPException(status_code=400, detail="Мастер не найден или не активен")
            update_fields.append("master_id = ?")
            params.append(appointment_data.master_id)
        
        if appointment_data.appointment_date is not None:
            update_fields.append("appointment_date = ?")
            params.append(appointment_data.appointment_date)
        
        if appointment_data.start_time is not None:
            update_fields.append("start_time = ?")
            params.append(appointment_data.start_time)
            
            # Пересчитываем время окончания
            cursor.execute("""
                SELECT s.duration_minutes
                FROM appointment_services aps
                JOIN services s ON aps.service_id = s.id
                WHERE aps.appointment_id = ?
            """, (appointment_id,))
            services_durations = cursor.fetchall()
            total_duration = sum(d[0] for d in services_durations)
            
            start_dt = datetime.strptime(appointment_data.start_time, "%H:%M")
            end_dt = datetime.combine(date.today(), start_dt.time()) + timedelta(minutes=total_duration)
            end_time = end_dt.strftime("%H:%M")
            
            update_fields.append("end_time = ?")
            params.append(end_time)
        
        if appointment_data.status is not None:
            valid_statuses = ["pending", "confirmed", "cancelled", "completed", "no_show", "in_progress", "rescheduled", "waitlisted"]
            if appointment_data.status not in valid_statuses:
                raise HTTPException(status_code=400, detail=f"Недопустимый статус. Допустимые значения: {', '.join(valid_statuses)}")
            update_fields.append("status = ?")
            params.append(appointment_data.status)
        
        if update_fields:
            params.append(appointment_id)
            cursor.execute(
                f"UPDATE appointments SET {', '.join(update_fields)} WHERE id = ?",
                tuple(params)
            )
        
        conn.commit()
        conn.close()
        
        logger.info(f"Appointment {appointment_id} updated successfully")
        return {"message": "Запись успешно обновлена"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating appointment: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка при обновлении записи: {str(e)}")

@app.put("/appointments/{appointment_id}/status")
async def update_appointment_status(
    appointment_id: int,
    status: str = Query(..., description="Новый статус")
):
    """Обновление статуса записи"""
    logger.info(f"Update appointment {appointment_id} status to {status}")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Проверяем существование записи
        cursor.execute("SELECT * FROM appointments WHERE id = ?", (appointment_id,))
        existing_appointment = cursor.fetchone()
        if not existing_appointment:
            raise HTTPException(status_code=404, detail="Запись не найдена")
        
        valid_statuses = ["pending", "confirmed", "cancelled", "completed", "no_show", "in_progress", "rescheduled", "waitlisted"]
        if status not in valid_statuses:
            raise HTTPException(status_code=400, detail=f"Недопустимый статус. Допустимые значения: {', '.join(valid_statuses)}")
        
        cursor.execute("""
            UPDATE appointments SET status = ? WHERE id = ?
        """, (status, appointment_id))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Appointment {appointment_id} status updated to {status}")
        return {"message": "Статус записи успешно обновлен"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating appointment status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка при обновлении статуса записи: {str(e)}")

@app.delete("/appointments/{appointment_id}")
async def delete_appointment(appointment_id: int):
    """Удаление записи"""
    logger.info(f"Delete appointment {appointment_id} request")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Проверяем существование записи
        cursor.execute("SELECT * FROM appointments WHERE id = ?", (appointment_id,))
        existing_appointment = cursor.fetchone()
        if not existing_appointment:
            raise HTTPException(status_code=404, detail="Запись не найдена")
        
        # Удаляем связанные услуги
        cursor.execute("DELETE FROM appointment_services WHERE appointment_id = ?", (appointment_id,))
        
        # Удаляем запись
        cursor.execute("DELETE FROM appointments WHERE id = ?", (appointment_id,))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Appointment {appointment_id} deleted successfully")
        return {"message": "Запись успешно удалена"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting appointment: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка при удалении записи: {str(e)}")

# ==================== ДОПОЛНИТЕЛЬНЫЕ ENDPOINTS ДЛЯ УПРАВЛЕНИЯ УСЛУГАМИ ЗАПИСИ ====================

@app.delete("/appointments/{appointment_id}/services")
async def delete_appointment_services(appointment_id: int):
    """Удаление всех услуг записи"""
    logger.info(f"Delete appointment {appointment_id} services")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Проверяем существование записи
        cursor.execute("SELECT id FROM appointments WHERE id = ?", (appointment_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Запись не найдена")
        
        # Удаляем услуги
        cursor.execute("DELETE FROM appointment_services WHERE appointment_id = ?", (appointment_id,))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Appointment {appointment_id} services deleted")
        return {"message": "Услуги записи удалены"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting appointment services: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка при удалении услуг: {str(e)}")

@app.post("/appointments/{appointment_id}/services")
async def add_appointment_service(appointment_id: int, service_data: dict):
    """Добавление услуги к записи"""
    logger.info(f"Add service to appointment {appointment_id}: {service_data}")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Проверяем существование записи
        cursor.execute("SELECT id FROM appointments WHERE id = ?", (appointment_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Запись не найдена")
        
        # Проверяем существование услуги
        service_id = service_data.get('service_id')
        if not service_id:
            raise HTTPException(status_code=400, detail="Не указан service_id")
        
        cursor.execute("SELECT id FROM services WHERE id = ? AND is_active = 1", (service_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=400, detail="Услуга не найдена или не активна")
        
        # Добавляем услугу
        cursor.execute("""
            INSERT INTO appointment_services (appointment_id, service_id)
            VALUES (?, ?)
        """, (appointment_id, service_id))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Service {service_id} added to appointment {appointment_id}")
        return {"message": "Услуга добавлена"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding appointment service: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка при добавлении услуги: {str(e)}")

# ==================== CLIENTS API ====================

@app.get("/clients")
async def get_clients(
    search: Optional[str] = Query(None, description="Поиск по имени, фамилии или телефону"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100)
):
    """Получение списка клиентов"""
    logger.info(f"Get clients request")
    
    offset = (page - 1) * per_page
    
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = """
            SELECT id, telegram_id, first_name, last_name, phone, email, created_at, language
            FROM users
            WHERE role = 'client'
        """
        
        count_query = "SELECT COUNT(*) as count FROM users WHERE role = 'client'"
        params = []
        count_params = []
        
        if search and search.strip():
            search_term = f"%{search.strip()}%"
            query += " AND (first_name LIKE ? OR last_name LIKE ? OR phone LIKE ? OR email LIKE ?)"
            count_query += " AND (first_name LIKE ? OR last_name LIKE ? OR phone LIKE ? OR email LIKE ?)"
            params.extend([search_term, search_term, search_term, search_term])
            count_params.extend([search_term, search_term, search_term, search_term])
        
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([per_page, offset])
        
        cursor.execute(query, tuple(params))
        clients = []
        for row in cursor.fetchall():
            client_dict = {}
            for key in row.keys():
                client_dict[key] = row[key]
            clients.append(client_dict)
        
        # Добавляем статистику для каждого клиента
        for client in clients:
            cursor.execute("""
                SELECT COUNT(*) as appointment_count,
                       SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_count
                FROM appointments
                WHERE client_id = ?
            """, (client["id"],))
            stats = cursor.fetchone()
            client["appointment_count"] = stats[0] if stats else 0
            client["completed_count"] = stats[1] if stats else 0
        
        # Общее количество
        cursor.execute(count_query, tuple(count_params))
        count_result = cursor.fetchone()
        total = count_result[0] if count_result else 0
        
        conn.close()
        
        logger.info(f"Found {len(clients)} clients, total: {total}")
        
        return {
            "items": clients,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page if per_page > 0 else 0
        }
    
    except Exception as e:
        logger.error(f"Error fetching clients: {e}", exc_info=True)
        return {
            "items": [],
            "total": 0,
            "page": page,
            "per_page": per_page,
            "total_pages": 0
        }

# Два варианта создания клиента для совместимости
@app.post("/clients")
async def create_client_json(client_data: ClientCreate):
    """Создание нового клиента (JSON версия)"""
    logger.info(f"Create client request (JSON): {client_data}")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Проверяем обязательные поля
        if not client_data.first_name or not client_data.first_name.strip():
            raise HTTPException(status_code=400, detail="Имя обязательно")
        
        if not client_data.phone or not client_data.phone.strip():
            raise HTTPException(status_code=400, detail="Телефон обязателен")
        
        first_name = client_data.first_name.strip()
        last_name = (client_data.last_name or "").strip()
        phone = client_data.phone.strip()
        email = (client_data.email or "").strip()
        
        # Проверяем уникальность телефона
        cursor.execute("SELECT id FROM users WHERE phone = ?", (phone,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Телефон уже используется")
        
        # Проверяем уникальность email если указан
        if email:
            cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
            if cursor.fetchone():
                raise HTTPException(status_code=400, detail="Email уже используется")
        
        # Генерируем уникальный telegram_id для клиента
        cursor.execute("SELECT MAX(telegram_id) as max_id FROM users WHERE role = 'client'")
        result = cursor.fetchone()
        telegram_id = result[0] + 1 if result[0] else 2000
        
        # Создаем клиента
        cursor.execute("""
            INSERT INTO users (telegram_id, role, first_name, last_name, phone, email, language)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (telegram_id, 'client', first_name, last_name, phone, email, 'ru'))
        
        client_id = cursor.lastrowid
        
        if not client_id:
            raise HTTPException(status_code=500, detail="Не удалось создать клиента")
        
        conn.commit()
        conn.close()
        
        logger.info(f"Client created: {first_name} {last_name} (ID: {client_id}, Telegram ID: {telegram_id})")
        
        return {
            "success": True,
            "message": "Клиент успешно создан",
            "client": {
                "id": client_id,
                "telegram_id": telegram_id,
                "first_name": first_name,
                "last_name": last_name,
                "phone": phone,
                "email": email
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating client: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка при создании клиента: {str(e)}")

@app.post("/clients/form")
async def create_client_form(
    first_name: str = Form(...),
    last_name: Optional[str] = Form(None),
    phone: Optional[str] = Form(None),
    email: Optional[str] = Form(None)
):
    """Создание нового клиента (Form версия для совместимости)"""
    logger.info(f"Create client request (Form): {first_name} {last_name}, {phone}, {email}")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Проверяем обязательные поля
        if not first_name or not first_name.strip():
            raise HTTPException(status_code=400, detail="Имя обязательно")
        
        if not phone or not phone.strip():
            raise HTTPException(status_code=400, detail="Телефон обязателен")
        
        first_name = first_name.strip()
        last_name = (last_name or "").strip()
        phone = phone.strip()
        email = (email or "").strip()
        
        # Проверяем уникальность телефона если указан
        if phone:
            cursor.execute("SELECT id FROM users WHERE phone = ?", (phone,))
            if cursor.fetchone():
                raise HTTPException(status_code=400, detail="Телефон уже используется")
        
        # Проверяем уникальность email если указан
        if email:
            cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
            if cursor.fetchone():
                raise HTTPException(status_code=400, detail="Email уже используется")
        
        # Генерируем уникальный telegram_id
        cursor.execute("SELECT MAX(telegram_id) as max_id FROM users WHERE role = 'client'")
        result = cursor.fetchone()
        telegram_id = result[0] + 1 if result[0] else 2000
        
        # Создаем клиента
        cursor.execute("""
            INSERT INTO users (telegram_id, role, first_name, last_name, phone, email, language)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (telegram_id, 'client', first_name, last_name, phone or '', email or '', 'ru'))
        
        client_id = cursor.lastrowid
        
        if not client_id:
            raise HTTPException(status_code=500, detail="Не удалось создать клиента")
        
        conn.commit()
        conn.close()
        
        logger.info(f"Client created: {first_name} {last_name} (ID: {client_id}, Telegram ID: {telegram_id})")
        
        return {
            "success": True,
            "message": "Клиент успешно создан",
            "client": {
                "id": client_id,
                "telegram_id": telegram_id,
                "first_name": first_name,
                "last_name": last_name,
                "phone": phone,
                "email": email
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating client: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка при создании клиента: {str(e)}")

@app.put("/clients/{client_id}")
async def update_client(client_id: int, client_data: ClientUpdate):
    """Обновление информации о клиенте"""
    logger.info(f"Update client {client_id} request: {client_data}")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Проверяем существование клиента
        cursor.execute("SELECT id FROM users WHERE id = ? AND role = 'client'", (client_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Клиент не найден")
        
        # Проверяем уникальность телефона если указан
        if client_data.phone is not None:
            phone = client_data.phone.strip()
            cursor.execute("SELECT id FROM users WHERE phone = ? AND id != ?", (phone, client_id))
            if cursor.fetchone():
                raise HTTPException(status_code=400, detail="Телефон уже используется другим пользователем")
        
        # Проверяем уникальность email если указан
        if client_data.email is not None:
            email = client_data.email.strip()
            cursor.execute("SELECT id FROM users WHERE email = ? AND id != ?", (email, client_id))
            if cursor.fetchone():
                raise HTTPException(status_code=400, detail="Email уже используется другим пользователем")
        
        # Формируем запрос на обновление
        update_fields = []
        params = []
        
        if client_data.first_name is not None:
            update_fields.append("first_name = ?")
            params.append(client_data.first_name.strip())
        
        if client_data.last_name is not None:
            update_fields.append("last_name = ?")
            params.append(client_data.last_name.strip())
        
        if client_data.phone is not None:
            update_fields.append("phone = ?")
            params.append(client_data.phone.strip())
        
        if client_data.email is not None:
            update_fields.append("email = ?")
            params.append(client_data.email.strip())
        
        if update_fields:
            params.append(client_id)
            cursor.execute(
                f"UPDATE users SET {', '.join(update_fields)} WHERE id = ?",
                tuple(params)
            )
        
        conn.commit()
        conn.close()
        
        logger.info(f"Client {client_id} updated successfully")
        
        return {
            "success": True,
            "message": "Информация о клиенте успешно обновлена"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating client: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка при обновлении клиента: {str(e)}")

@app.delete("/clients/{client_id}")
async def delete_client(client_id: int):
    """Удаление клиента"""
    logger.info(f"Delete client {client_id} request")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Проверяем существование клиента
        cursor.execute("SELECT id FROM users WHERE id = ? AND role = 'client'", (client_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Клиент не найден")
        
        # Проверяем, есть ли у клиента записи
        cursor.execute("SELECT id FROM appointments WHERE client_id = ? LIMIT 1", (client_id,))
        if cursor.fetchone():
            raise HTTPException(
                status_code=400, 
                detail="Невозможно удалить клиента, у которого есть записи. "
                       "Сначала удалите или отмените все записи клиента."
            )
        
        # Проверяем, есть ли у клиента отзывы
        cursor.execute("SELECT id FROM reviews WHERE client_id = ? LIMIT 1", (client_id,))
        if cursor.fetchone():
            raise HTTPException(
                status_code=400, 
                detail="Невозможно удалить клиента, у которого есть отзывы. "
                       "Сначала удалите все отзывы клиента."
            )
        
        # Проверяем, есть ли у клиента бонусы
        cursor.execute("SELECT id FROM bonuses WHERE client_id = ? LIMIT 1", (client_id,))
        if cursor.fetchone():
            raise HTTPException(
                status_code=400, 
                detail="Невозможно удалить клиента, у которого есть бонусы. "
                       "Сначала обнулите бонусный счет клиента."
            )
        
        # Удаляем клиента
        cursor.execute("DELETE FROM users WHERE id = ?", (client_id,))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Client {client_id} deleted successfully")
        
        return {
            "success": True,
            "message": "Клиент успешно удален"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting client: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка при удалении клиента: {str(e)}")

@app.get("/clients/{client_id}/stats")
async def get_client_stats(client_id: int):
    """Получение статистики клиента"""
    logger.info(f"Get client {client_id} stats")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Проверяем существование клиента
        cursor.execute("""
            SELECT id, first_name, last_name 
            FROM users 
            WHERE id = ? AND role = 'client'
        """, (client_id,))
        
        client = cursor.fetchone()
        if not client:
            raise HTTPException(status_code=404, detail="Клиент не найден")
        
        # Получаем статистику по записям
        cursor.execute("""
            SELECT 
                COUNT(*) as total_appointments,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_appointments,
                SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END) as cancelled_appointments,
                SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending_appointments,
                SUM(CASE WHEN status = 'no_show' THEN 1 ELSE 0 END) as no_show_appointments
            FROM appointments
            WHERE client_id = ?
        """, (client_id,))
        
        appointment_stats = cursor.fetchone()
        
        # Получаем общую сумму потраченных средств
        cursor.execute("""
            SELECT COALESCE(SUM(s.price), 0) as total_spent
            FROM appointments a
            JOIN appointment_services aps ON a.id = aps.appointment_id
            JOIN services s ON aps.service_id = s.id
            WHERE a.client_id = ? AND a.status = 'completed'
        """, (client_id,))
        
        spending_stats = cursor.fetchone()
        
        # Получаем последнюю запись
        cursor.execute("""
            SELECT appointment_date, start_time, status
            FROM appointments
            WHERE client_id = ?
            ORDER BY appointment_date DESC, start_time DESC
            LIMIT 1
        """, (client_id,))
        
        last_appointment = cursor.fetchone()
        
        # Получаем статистику по отзывам
        cursor.execute("""
            SELECT 
                COUNT(*) as total_reviews,
                AVG(rating) as avg_rating
            FROM reviews
            WHERE client_id = ?
        """, (client_id,))
        
        review_stats = cursor.fetchone()
        
        conn.close()
        
        stats = {
            "client_id": client_id,
            "client_name": f"{client[1]} {client[2]}" if client[2] else client[1],
            "appointments": {
                "total": appointment_stats[0] if appointment_stats else 0,
                "completed": appointment_stats[1] if appointment_stats else 0,
                "cancelled": appointment_stats[2] if appointment_stats else 0,
                "pending": appointment_stats[3] if appointment_stats else 0,
                "no_show": appointment_stats[4] if appointment_stats else 0
            },
            "spending": {
                "total": spending_stats[0] if spending_stats else 0,
                "average": round((spending_stats[0] if spending_stats else 0) / 
                               (appointment_stats[1] if appointment_stats and appointment_stats[1] else 1))
                if (appointment_stats and appointment_stats[1]) else 0
            },
            "last_appointment": {
                "date": last_appointment[0] if last_appointment else None,
                "time": last_appointment[1] if last_appointment else None,
                "status": last_appointment[2] if last_appointment else None
            },
            "reviews": {
                "total": review_stats[0] if review_stats else 0,
                "average_rating": round(review_stats[1] if review_stats and review_stats[1] else 0, 1)
            }
        }
        
        return stats
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting client stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка при получении статистики клиента: {str(e)}")

@app.get("/clients/{client_id}/recent-appointments")
async def get_client_recent_appointments(
    client_id: int,
    limit: int = Query(5, ge=1, le=20, description="Количество последних записей")
):
    """Получение последних записей клиента"""
    logger.info(f"Get client {client_id} recent appointments")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Проверяем существование клиента
        cursor.execute("SELECT id FROM users WHERE id = ? AND role = 'client'", (client_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Клиент не найден")
        
        cursor.execute("""
            SELECT a.*, 
                   u.first_name as master_first_name, u.last_name as master_last_name
            FROM appointments a
            LEFT JOIN masters m ON a.master_id = m.id
            LEFT JOIN users u ON m.user_id = u.id
            WHERE a.client_id = ?
            ORDER BY a.appointment_date DESC, a.start_time DESC
            LIMIT ?
        """, (client_id, limit))
        
        appointments = []
        for row in cursor.fetchall():
            appointment_dict = {}
            for key in row.keys():
                appointment_dict[key] = row[key]
            appointments.append(appointment_dict)
        
        # Добавляем услуги для каждой записи
        for appointment in appointments:
            cursor.execute("""
                SELECT s.id, st.title, s.duration_minutes, s.price
                FROM appointment_services aps
                JOIN services s ON aps.service_id = s.id
                LEFT JOIN service_translations st ON s.id = st.service_id AND st.language = 'ru'
                WHERE aps.appointment_id = ?
            """, (appointment["id"],))
            services = []
            for row in cursor.fetchall():
                service_dict = {}
                for key in row.keys():
                    service_dict[key] = row[key]
                services.append(service_dict)
            appointment["services"] = services
        
        conn.close()
        
        return {
            "success": True,
            "count": len(appointments),
            "appointments": appointments
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting client appointments: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка при получении записей клиента: {str(e)}")

# ==================== КАТЕГОРИИ УСЛУГ API ====================

@app.get("/services/categories")
async def get_categories(
    is_active: Optional[bool] = Query(None, description="Фильтр по активности"),
    language: str = Query("ru", description="Язык переводов"),
    include_children: bool = Query(True, description="Включать ли подкатегории в древовидную структуру")
):
    """Получение категорий услуг с переводами в древовидной структуре"""
    logger.info(f"Get categories request: language={language}, include_children={include_children}")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = """
            SELECT sc.*, sct.title,
                   (SELECT COUNT(*) FROM service_categories sc2 WHERE sc2.parent_id = sc.id) as child_count,
                   (SELECT COUNT(*) FROM services s WHERE s.category_id = sc.id AND s.is_active = 1) as service_count
            FROM service_categories sc
            LEFT JOIN service_category_translations sct 
                ON sc.id = sct.category_id AND sct.language = ?
            WHERE 1=1
        """
        params = [language]
        
        if is_active is not None:
            query += " AND sc.is_active = ?"
            params.append(int(is_active))
        
        query += " ORDER BY sc.parent_id NULLS FIRST, sc.id"
        
        cursor.execute(query, tuple(params))
        categories = []
        for row in cursor.fetchall():
            category_dict = {}
            for key in row.keys():
                category_dict[key] = row[key]
            categories.append(category_dict)
        
        conn.close()
        
        # Формируем древовидную структуру
        def build_tree(parent_id=None):
            tree = []
            for cat in categories:
                if cat.get("parent_id") == parent_id:
                    children = []
                    if include_children and cat.get("child_count", 0) > 0:
                        children = build_tree(cat["id"])
                    
                    category_response = {
                        "id": cat["id"],
                        "parent_id": cat.get("parent_id"),
                        "is_active": bool(cat.get("is_active", 1)),
                        "title": cat.get("title"),
                        "has_children": cat.get("child_count", 0) > 0,
                        "service_count": cat.get("service_count", 0)
                    }
                    
                    if children:
                        category_response["children"] = children
                    
                    tree.append(category_response)
            return tree
        
        result = build_tree()
        logger.info(f"Found {len(result)} root categories with tree structure")
        return result
    
    except Exception as e:
        logger.error(f"Error fetching categories: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка при загрузке категорий: {str(e)}")

@app.get("/services/categories/tree")
async def get_categories_tree(
    language: str = Query("ru", description="Язык переводов"),
    include_inactive: bool = Query(False, description="Включать неактивные категории")
):
    """Получение категорий в формате дерева для TreeSelect компонентов"""
    logger.info(f"Get categories tree request: language={language}")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = """
            SELECT sc.*, sct.title,
                   (SELECT COUNT(*) FROM service_categories sc2 WHERE sc2.parent_id = sc.id) as child_count
            FROM service_categories sc
            LEFT JOIN service_category_translations sct 
                ON sc.id = sct.category_id AND sct.language = ?
            WHERE 1=1
        """
        params = [language]
        
        if not include_inactive:
            query += " AND sc.is_active = 1"
        
        query += " ORDER BY sc.parent_id NULLS FIRST, sc.id"
        
        cursor.execute(query, tuple(params))
        categories = []
        for row in cursor.fetchall():
            category_dict = {}
            for key in row.keys():
                category_dict[key] = row[key]
            categories.append(category_dict)
        
        conn.close()
        
        # Формируем плоский список для древовидного выбора
        def build_tree_select_data(items, parent_id=None, level=0, prefix=""):
            tree_data = []
            for item in items:
                if item.get("parent_id") == parent_id:
                    title = item.get("title", f"Категория #{item['id']}")
                    full_title = f"{prefix}{title}" if prefix else title
                    
                    node = {
                        "id": item["id"],
                        "parent_id": item.get("parent_id"),
                        "is_active": bool(item.get("is_active", 1)),
                        "title": title,
                        "value": item["id"],
                        "label": full_title,
                        "is_leaf": item.get("child_count", 0) == 0,
                    }
                    
                    # Рекурсивно добавляем детей
                    children = build_tree_select_data(
                        items, 
                        item["id"], 
                        level + 1, 
                        f"{full_title} / "
                    )
                    if children:
                        node["children"] = children
                        node["is_leaf"] = False
                    
                    tree_data.append(node)
            return tree_data
        
        result = build_tree_select_data(categories)
        logger.info(f"Generated tree with {len(result)} root nodes")
        return result
    
    except Exception as e:
        logger.error(f"Error fetching categories tree: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка при построении дерева категорий: {str(e)}")

@app.get("/services/categories/{category_id}")
async def get_category(
    category_id: int,
    language: str = Query("ru", description="Язык переводов")
):
    """Получение информации о конкретной категории"""
    logger.info(f"Get category {category_id} request")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT sc.*, sct.title,
                   (SELECT COUNT(*) FROM service_categories sc2 WHERE sc2.parent_id = sc.id) as child_count,
                   (SELECT COUNT(*) FROM services s WHERE s.category_id = sc.id AND s.is_active = 1) as service_count
            FROM service_categories sc
            LEFT JOIN service_category_translations sct 
                ON sc.id = sct.category_id AND sct.language = ?
            WHERE sc.id = ?
        """, (language, category_id))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            raise HTTPException(
                status_code=404,
                detail="Категория не найдена"
            )
        
        category_dict = {}
        for key in row.keys():
            category_dict[key] = row[key]
        
        return {
            "id": category_dict["id"],
            "parent_id": category_dict.get("parent_id"),
            "is_active": bool(category_dict.get("is_active", 1)),
            "title": category_dict.get("title"),
            "has_children": category_dict.get("child_count", 0) > 0,
            "service_count": category_dict.get("service_count", 0)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching category: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка при загрузке категории: {str(e)}")

@app.post("/services/categories")
async def create_category(category_data: CategoryCreate):
    """Создание новой категории услуг"""
    logger.info(f"Create category request")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Проверяем parent_id если указан
        if category_data.parent_id is not None:
            cursor.execute(
                "SELECT id, is_active FROM service_categories WHERE id = ?",
                (category_data.parent_id,)
            )
            parent_category = cursor.fetchone()
            if not parent_category:
                raise HTTPException(
                    status_code=400,
                    detail="Родительская категория не найдена"
                )
        
        # Создаем категорию
        cursor.execute("""
            INSERT INTO service_categories (parent_id, is_active)
            VALUES (?, ?)
        """, (category_data.parent_id, int(category_data.is_active)))
        
        category_id = cursor.lastrowid
        
        if not category_id:
            raise HTTPException(
                status_code=500,
                detail="Не удалось создать категорию"
            )
        
        # Добавляем переводы
        for translation in category_data.translations:
            cursor.execute("""
                INSERT INTO service_category_translations (category_id, language, title)
                VALUES (?, ?, ?)
            """, (category_id, translation.language, translation.title))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Category {category_id} created successfully")
        return {
            "id": category_id, 
            "message": "Категория успешно создана",
            "has_children": False,
            "service_count": 0
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating category: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка при создании категории: {str(e)}")

@app.put("/services/categories/{category_id}")
async def update_category(category_id: int, category_data: CategoryUpdate):
    """Обновление категории услуг"""
    logger.info(f"Update category {category_id} request")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Проверяем существование категории
        cursor.execute("SELECT * FROM service_categories WHERE id = ?", (category_id,))
        existing_category = cursor.fetchone()
        if not existing_category:
            raise HTTPException(
                status_code=404,
                detail="Категория не найдена"
            )
        
        # Проверяем parent_id если указан
        if category_data.parent_id is not None:
            if category_data.parent_id == category_id:
                raise HTTPException(
                    status_code=400,
                    detail="Категория не может быть родителем самой себя"
                )
            
            # Проверяем существование родительской категории
            cursor.execute(
                "SELECT id, is_active FROM service_categories WHERE id = ?",
                (category_data.parent_id,)
            )
            parent_category = cursor.fetchone()
            if not parent_category:
                raise HTTPException(
                    status_code=400,
                    detail="Родительская категория не найдена"
                )
        
        # Обновляем основную информацию
        update_fields = []
        params = []
        
        if category_data.parent_id is not None:
            update_fields.append("parent_id = ?")
            params.append(category_data.parent_id)
        
        if category_data.is_active is not None:
            update_fields.append("is_active = ?")
            params.append(int(category_data.is_active))
        
        if update_fields:
            params.append(category_id)
            cursor.execute(
                f"UPDATE service_categories SET {', '.join(update_fields)} WHERE id = ?",
                tuple(params)
            )
        
        # Обновляем переводы
        if category_data.translations:
            for translation in category_data.translations:
                cursor.execute("""
                    SELECT id FROM service_category_translations 
                    WHERE category_id = ? AND language = ?
                """, (category_id, translation.language))
                
                existing_translation = cursor.fetchone()
                
                if existing_translation:
                    cursor.execute("""
                        UPDATE service_category_translations 
                        SET title = ?
                        WHERE id = ?
                    """, (translation.title, existing_translation[0]))
                else:
                    cursor.execute("""
                        INSERT INTO service_category_translations (category_id, language, title)
                        VALUES (?, ?, ?)
                    """, (category_id, translation.language, translation.title))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Category {category_id} updated successfully")
        return {"message": "Категория успешно обновлена"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating category: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка при обновлении категории: {str(e)}")

def get_all_subcategories(cursor, parent_id):
    """Рекурсивно получает все подкатегории заданной категории"""
    all_subcategories = []
    
    def get_subcategories(parent_id):
        cursor.execute("SELECT id FROM service_categories WHERE parent_id = ?", (parent_id,))
        subcategories = cursor.fetchall()
        
        for subcat in subcategories:
            subcat_id = subcat[0]
            all_subcategories.append(subcat_id)
            get_subcategories(subcat_id)
    
    get_subcategories(parent_id)
    return all_subcategories

@app.delete("/services/categories/{category_id}")
async def delete_category(
    category_id: int,
    recursive: bool = Query(False, description="Рекурсивное удаление с подкатегориями"),
    language: str = Query("ru", description="Язык для получения названий")
):
    """Удаление категории услуг
    Если recursive=true, удаляет категорию со всеми подкатегориями и услугами
    """
    logger.info(f"Delete category {category_id} request (recursive={recursive})")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Проверяем существование категории
        cursor.execute("SELECT * FROM service_categories WHERE id = ?", (category_id,))
        existing_category = cursor.fetchone()
        if not existing_category:
            raise HTTPException(
                status_code=404,
                detail="Категория не найдена"
            )
        
        # Получаем название категории для сообщений
        cursor.execute("""
            SELECT title FROM service_category_translations 
            WHERE category_id = ? AND language = ?
        """, (category_id, language))
        title_result = cursor.fetchone()
        category_name = title_result[0] if title_result and title_result[0] else f"Категория #{category_id}"
        
        if not recursive:
            # Проверяем наличие подкатегорий
            cursor.execute("SELECT id FROM service_categories WHERE parent_id = ?", (category_id,))
            child_categories = cursor.fetchall()
            
            if child_categories:
                # Получаем названия подкатегорий для сообщения
                child_names = []
                for child in child_categories[:3]:  # Ограничиваем 3 подкатегориями
                    cursor.execute("""
                        SELECT title FROM service_category_translations 
                        WHERE category_id = ? AND language = ?
                    """, (child[0], language))
                    child_title = cursor.fetchone()
                    if child_title and child_title[0]:
                        child_names.append(child_title[0])
                    else:
                        child_names.append(f"Категория #{child[0]}")
                
                raise HTTPException(
                    status_code=400,
                    detail=f"Невозможно удалить категорию '{category_name}', так как у неё есть подкатегории: {', '.join(child_names)}"
                    + ("..." if len(child_categories) > 3 else "")
                    + "\nИспользуйте параметр ?recursive=true для рекурсивного удаления."
                )
            
            # Проверяем наличие услуг в категории
            cursor.execute("SELECT id FROM services WHERE category_id = ?", (category_id,))
            services_in_category = cursor.fetchall()
            
            if services_in_category:
                service_count = len(services_in_category)
                raise HTTPException(
                    status_code=400,
                    detail=f"Невозможно удалить категорию '{category_name}', так как в ней есть услуги ({service_count} шт.)."
                    + "\nСначала удалите или переместите услуги."
                )
            
            # Если категория пустая - удаляем её
            # Удаляем переводы категории
            cursor.execute("DELETE FROM service_category_translations WHERE category_id = ?", (category_id,))
            
            # Удаляем саму категорию
            cursor.execute("DELETE FROM service_categories WHERE id = ?", (category_id,))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Category {category_id} deleted successfully (non-recursive)")
            return {"message": "Категория успешно удалена"}
        
        else:
            # РЕКУРСИВНОЕ УДАЛЕНИЕ
            
            # Получаем все ID категорий для удаления (включая текущую и все подкатегории)
            all_category_ids = [category_id] + get_all_subcategories(cursor, category_id)
            logger.info(f"Recursive delete: found {len(all_category_ids)} categories to delete")
            
            # Удаляем все услуги в этих категориях
            for cat_id in all_category_ids:
                # Получаем все услуги в этой категории
                cursor.execute("SELECT id FROM services WHERE category_id = ?", (cat_id,))
                services_in_category = cursor.fetchall()
                
                # Для каждой услуги проверяем, используется ли она в записях
                for service in services_in_category:
                    service_id = service[0]
                    
                    # Проверяем, есть ли связанные записи в appointment_services
                    cursor.execute("SELECT id FROM appointment_services WHERE service_id = ?", (service_id,))
                    appointments_with_service = cursor.fetchall()
                    
                    if appointments_with_service:
                        # Если услуга используется, просто деактивируем её
                        cursor.execute("UPDATE services SET is_active = 0 WHERE id = ?", (service_id,))
                        logger.info(f"Service {service_id} deactivated (used in appointments)")
                    else:
                        # Если не используется, удаляем полностью
                        # Удаляем переводы услуги
                        cursor.execute("DELETE FROM service_translations WHERE service_id = ?", (service_id,))
                        # Удаляем саму услугу
                        cursor.execute("DELETE FROM services WHERE id = ?", (service_id,))
                        logger.info(f"Service {service_id} deleted")
            
            # Удаляем все переводы категорий
            for cat_id in all_category_ids:
                cursor.execute("DELETE FROM service_category_translations WHERE category_id = ?", (cat_id,))
            
            # Удаляем все категории (начиная с самых глубоких)
            # Сортируем ID по убыванию, чтобы сначала удалить дочерние категории
            sorted_category_ids = sorted(all_category_ids, reverse=True)
            for cat_id in sorted_category_ids:
                cursor.execute("DELETE FROM service_categories WHERE id = ?", (cat_id,))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Category {category_id} and all subcategories deleted successfully (recursive)")
            return {"message": "Категория и все её подкатегории успешно удалены"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting category: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при удалении категории: {str(e)}"
        )

@app.get("/services/categories/{category_id}/stats")
async def get_category_stats(category_id: int, language: str = Query("ru")):
    """Получение статистики по категории"""
    logger.info(f"Get category stats for {category_id}")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT sc.id, sct.title,
                   (SELECT COUNT(*) FROM service_categories sc2 WHERE sc2.parent_id = sc.id) as subcategory_count,
                   (SELECT COUNT(*) FROM services s WHERE s.category_id = sc.id AND s.is_active = 1) as service_count
            FROM service_categories sc
            LEFT JOIN service_category_translations sct 
                ON sc.id = sct.category_id AND sct.language = ?
            WHERE sc.id = ?
        """, (language, category_id))
        
        category = cursor.fetchone()
        conn.close()
        
        if not category:
            raise HTTPException(
                status_code=404,
                detail="Категория не найдена"
            )
        
        return {
            "category_id": category[0],
            "title": category[1] or f"Категория #{category[0]}",
            "service_count": category[3] or 0,
            "subcategory_count": category[2] or 0
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching category stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка при получении статистики категории: {str(e)}")

# ==================== УСЛУГИ API ====================

@app.get("/services")
async def get_services(
    category_id: Optional[int] = Query(None, description="ID категории для фильтрации"),
    is_active: Optional[bool] = Query(None, description="Фильтр по активности"),
    language: str = Query("ru", description="Язык переводов"),
    page: int = Query(1, ge=1, description="Номер страницы"),
    per_page: int = Query(20, ge=1, le=100, description="Количество на странице"),
    search: Optional[str] = Query(None, description="Поиск по названию и описанию")
):
    """Получение услуг с фильтрацией и пагинацией"""
    logger.info(f"Get services request")
    
    offset = (page - 1) * per_page
    
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Основной запрос для получения услуг
        query = """
            SELECT s.*, st.title, st.description, sct.title as category_title
            FROM services s
            LEFT JOIN service_translations st 
                ON s.id = st.service_id AND st.language = ?
            LEFT JOIN service_categories sc ON s.category_id = sc.id
            LEFT JOIN service_category_translations sct 
                ON sc.id = sct.category_id AND sct.language = ?
            WHERE 1=1
        """
        
        # Запрос для подсчета общего количества
        count_query = """
            SELECT COUNT(*) as count 
            FROM services s
            LEFT JOIN service_translations st ON s.id = st.service_id AND st.language = ?
            WHERE 1=1
        """
        
        params = [language, language]
        count_params = [language]
        
        # Добавляем фильтр по категории
        if category_id is not None:
            query += " AND s.category_id = ?"
            count_query += " AND s.category_id = ?"
            params.append(category_id)
            count_params.append(category_id)
        
        # Фильтр по активности
        if is_active is not None:
            query += " AND s.is_active = ?"
            count_query += " AND s.is_active = ?"
            params.append(int(is_active))
            count_params.append(int(is_active))
        
        # Поиск
        if search and search.strip():
            search_term = f"%{search.strip()}%"
            query += " AND (st.title LIKE ? OR st.description LIKE ?)"
            count_query += " AND (st.title LIKE ? OR st.description LIKE ?)"
            params.extend([search_term, search_term])
            count_params.extend([search_term, search_term])
        
        # Сортировка и пагинация
        query += " ORDER BY s.id DESC LIMIT ? OFFSET ?"
        params.extend([per_page, offset])
        
        # Выполняем запросы
        cursor.execute(query, tuple(params))
        services = []
        for row in cursor.fetchall():
            service_dict = {}
            for key in row.keys():
                service_dict[key] = row[key]
            services.append(service_dict)
        
        # Общее количество
        cursor.execute(count_query, tuple(count_params))
        count_result = cursor.fetchone()
        total = count_result[0] if count_result else 0
        
        conn.close()
        
        logger.info(f"Found {len(services)} services, total: {total}")
        
        return {
            "items": services,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page if per_page > 0 else 0
        }
    
    except Exception as e:
        logger.error(f"Error fetching services: {e}", exc_info=True)
        return {
            "items": [],
            "total": 0,
            "page": page,
            "per_page": per_page,
            "total_pages": 0
        }

@app.post("/services")
async def create_service(service_data: ServiceCreate):
    """Создание новой услуги"""
    logger.info(f"Create service request")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Проверяем существование категории
        if service_data.category_id:
            cursor.execute("SELECT id, is_active FROM service_categories WHERE id = ?", (service_data.category_id,))
            category = cursor.fetchone()
            if not category:
                raise HTTPException(
                    status_code=400,
                    detail="Категория не найдена"
                )
        
        # Создаем услугу
        cursor.execute("""
            INSERT INTO services (category_id, duration_minutes, price, is_active)
            VALUES (?, ?, ?, ?)
        """, (
            service_data.category_id,
            service_data.duration_minutes,
            service_data.price,
            int(service_data.is_active)
        ))
        
        service_id = cursor.lastrowid
        
        if not service_id:
            raise HTTPException(
                status_code=500,
                detail="Не удалось создать услугу"
            )
        
        # Добавляем переводы
        for translation in service_data.translations:
            cursor.execute("""
                INSERT INTO service_translations (service_id, language, title, description)
                VALUES (?, ?, ?, ?)
            """, (
                service_id,
                translation.language,
                translation.title,
                translation.description or ""
            ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Service {service_id} created successfully")
        return {
            "id": service_id, 
            "message": "Услуга успешно создана",
            "category_id": service_data.category_id
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating service: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка при создании услуги: {str(e)}")

@app.get("/services/{service_id}")
async def get_service(service_id: int, language: str = Query("ru")):
    """Получение полной информации об услуге с переводами"""
    logger.info(f"Get service {service_id} request")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Основная информация об услуге
        cursor.execute("""
            SELECT s.*, sct.title as category_title
            FROM services s
            LEFT JOIN service_categories sc ON s.category_id = sc.id
            LEFT JOIN service_category_translations sct 
                ON sc.id = sct.category_id AND sct.language = ?
            WHERE s.id = ?
        """, (language, service_id))
        
        row = cursor.fetchone()
        
        if not row:
            raise HTTPException(
                status_code=404,
                detail="Услуга не найдена"
            )
        
        service_dict = {}
        for key in row.keys():
            service_dict[key] = row[key]
        
        # Все переводы услуги
        cursor.execute("""
            SELECT language, title, description 
            FROM service_translations 
            WHERE service_id = ?
            ORDER BY language
        """, (service_id,))
        
        translations = []
        for row in cursor.fetchall():
            translation_dict = {}
            for key in row.keys():
                translation_dict[key] = row[key]
            translations.append(translation_dict)
        
        conn.close()
        
        return {
            "id": service_dict["id"],
            "category_id": service_dict["category_id"],
            "duration_minutes": service_dict["duration_minutes"],
            "price": service_dict["price"],
            "is_active": bool(service_dict.get("is_active", 1)),
            "translations": translations,
            "category_title": service_dict.get("category_title"),
            "category_path": None  # Можно добавить логику для построения пути
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching service: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка при загрузке услуги: {str(e)}")

@app.put("/services/{service_id}")
async def update_service(service_id: int, service_data: ServiceUpdate):
    """Обновление услуги"""
    logger.info(f"Update service {service_id} request")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Проверяем существование услуги
        cursor.execute("SELECT * FROM services WHERE id = ?", (service_id,))
        existing_service = cursor.fetchone()
        if not existing_service:
            raise HTTPException(
                status_code=404,
                detail="Услуга не найдена"
            )
        
        # Проверяем категорию если указана
        if service_data.category_id is not None:
            cursor.execute("SELECT id FROM service_categories WHERE id = ?", (service_data.category_id,))
            category = cursor.fetchone()
            if not category:
                raise HTTPException(
                    status_code=400,
                    detail="Категория не найдена"
                )
        
        # Обновляем основную информацию
        update_fields = []
        params = []
        
        if service_data.category_id is not None:
            update_fields.append("category_id = ?")
            params.append(service_data.category_id)
        
        if service_data.duration_minutes is not None:
            update_fields.append("duration_minutes = ?")
            params.append(service_data.duration_minutes)
        
        if service_data.price is not None:
            update_fields.append("price = ?")
            params.append(service_data.price)
        
        if service_data.is_active is not None:
            update_fields.append("is_active = ?")
            params.append(int(service_data.is_active))
        
        if update_fields:
            params.append(service_id)
            cursor.execute(
                f"UPDATE services SET {', '.join(update_fields)} WHERE id = ?",
                tuple(params)
            )
        
        # Обновляем переводы
        if service_data.translations:
            for translation in service_data.translations:
                cursor.execute("""
                    SELECT id FROM service_translations 
                    WHERE service_id = ? AND language = ?
                """, (service_id, translation.language))
                
                existing_translation = cursor.fetchone()
                
                if existing_translation:
                    cursor.execute("""
                        UPDATE service_translations 
                        SET title = ?, description = ?
                        WHERE id = ?
                    """, (
                        translation.title,
                        translation.description or "",
                        existing_translation[0]
                    ))
                else:
                    cursor.execute("""
                        INSERT INTO service_translations (service_id, language, title, description)
                        VALUES (?, ?, ?, ?)
                    """, (
                        service_id,
                        translation.language,
                        translation.title,
                        translation.description or ""
                    ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Service {service_id} updated successfully")
        return {"message": "Услуга успешно обновлена"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating service: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка при обновлении услуги: {str(e)}")

@app.delete("/services/{service_id}")
async def delete_service(service_id: int):
    """Удаление/деактивация услуги"""
    logger.info(f"Delete service {service_id} request")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Проверяем существование услуги
        cursor.execute("SELECT * FROM services WHERE id = ?", (service_id,))
        existing_service = cursor.fetchone()
        if not existing_service:
            raise HTTPException(
                status_code=404,
                detail="Услуга не найдена"
            )
        
        # Вместо удаления деактивируем
        cursor.execute("UPDATE services SET is_active = 0 WHERE id = ?", (service_id,))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Service {service_id} deactivated")
        return {"message": "Услуга успешно деактивирована"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting service: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка при деактивации услуги: {str(e)}")

@app.delete("/services/{service_id}/force")
async def force_delete_service(service_id: int):
    """Полное удаление услуги (только если нет связанных записей)"""
    logger.info(f"Force delete service {service_id} request")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Проверяем существование услуги
        cursor.execute("SELECT * FROM services WHERE id = ?", (service_id,))
        existing_service = cursor.fetchone()
        if not existing_service:
            raise HTTPException(
                status_code=404,
                detail="Услуга не найдена"
            )
        
        # Проверяем, есть ли связанные записи в appointment_services
        cursor.execute("SELECT id FROM appointment_services WHERE service_id = ?", (service_id,))
        appointments_with_service = cursor.fetchall()
        
        if appointments_with_service:
            appointment_ids = [a[0] for a in appointments_with_service]
            raise HTTPException(
                status_code=400,
                detail=f"Невозможно удалить услугу, так как она используется в записях (ID записей: {', '.join(map(str, appointment_ids[:5]))})"
                + ("..." if len(appointment_ids) > 5 else "")
            )
        
        # Удаляем переводы
        cursor.execute("DELETE FROM service_translations WHERE service_id = ?", (service_id,))
        
        # Удаляем услугу
        cursor.execute("DELETE FROM services WHERE id = ?", (service_id,))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Service {service_id} permanently deleted")
        return {"message": "Услуга полностью удалена"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error force deleting service: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка при удалении услуги: {str(e)}")

# ==================== ОБНОВЛЕННЫЕ ENDPOINTS ДЛЯ МАСТЕРОВ ====================

@app.put("/masters/{master_id}")
async def update_master(
    master_id: int,
    first_name: Optional[str] = Form(None),
    last_name: Optional[str] = Form(None),
    phone: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    telegram_id: Optional[str] = Form(None),
    qualification: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    is_active: Optional[bool] = Form(None),
    photo: Optional[UploadFile] = File(None),
    remove_photo: Optional[bool] = Form(False)
):
    """Обновление данных мастера (БЕЗ АВТОРИЗАЦИИ)"""
    
    # ДОБАВЛЕНО ДЛЯ ОТЛАДКИ
    logger.info(f"====== UPDATE MASTER {master_id} ======")
    logger.info(f"Received telegram_id: '{telegram_id}'")
    logger.info(f"Type of telegram_id: {type(telegram_id)}")
    logger.info(f"telegram_id is None: {telegram_id is None}")
    
    conn = None
    
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Получаем текущие данные мастера
        cursor.execute("SELECT * FROM masters WHERE id = ?", (master_id,))
        row = cursor.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Мастер не найден")
        
        master_dict = {}
        for key in row.keys():
            master_dict[key] = row[key]
        
        master_user_id = master_dict["user_id"]
        old_photo = master_dict["photo"]
        new_photo_filename = None
        
        # Обработка фото
        if remove_photo:
            if old_photo:
                delete_master_photo(old_photo)
            cursor.execute("UPDATE masters SET photo = NULL WHERE id = ?", (master_id,))
            
        elif photo and photo.filename:
            new_photo_filename = save_master_photo(photo)
            cursor.execute("UPDATE masters SET photo = ? WHERE id = ?", (new_photo_filename, master_id))
            
            if old_photo:
                delete_master_photo(old_photo)
        
        # Обновляем данные пользователя
        user_updates = []
        user_params = []
        
        if first_name:
            user_updates.append("first_name = ?")
            user_params.append(first_name)
        if last_name:
            user_updates.append("last_name = ?")
            user_params.append(last_name)
        if phone is not None:
            cursor.execute("SELECT id FROM users WHERE phone = ? AND id != ?", (phone, master_user_id))
            if cursor.fetchone():
                raise HTTPException(status_code=400, detail="Телефон уже используется")
            user_updates.append("phone = ?")
            user_params.append(phone)
        if email is not None:
            cursor.execute("SELECT id FROM users WHERE email = ? AND id != ?", (email, master_user_id))
            if cursor.fetchone():
                raise HTTPException(status_code=400, detail="Email уже используется")
            user_updates.append("email = ?")
            user_params.append(email)
        
        # Обработка telegram_id - ИСПРАВЛЕННАЯ ВЕРСИЯ
        if telegram_id is not None:
            telegram_id_str = str(telegram_id).strip()
            logger.info(f"Processing telegram_id: '{telegram_id_str}'")
            
            if telegram_id_str:  # Если строка не пустая
                try:
                    # Пробуем преобразовать в число если это числовой ID
                    telegram_id_int = int(telegram_id_str)
                    telegram_id_value = telegram_id_int
                    logger.info(f"Telegram ID is numeric: {telegram_id_int}")
                except ValueError:
                    # Если не число, оставляем как строку (для @username)
                    telegram_id_value = telegram_id_str
                    logger.info(f"Telegram ID is string: {telegram_id_str}")
                
                # Проверяем уникальность
                cursor.execute("SELECT id FROM users WHERE telegram_id = ? AND id != ?", (telegram_id_value, master_user_id))
                if cursor.fetchone():
                    raise HTTPException(status_code=400, detail="Telegram ID уже используется")
                
                user_updates.append("telegram_id = ?")
                user_params.append(telegram_id_value)
                logger.info(f"Will update telegram_id to: {telegram_id_value}")
            else:
                # Если telegram_id пустая строка, устанавливаем NULL
                user_updates.append("telegram_id = NULL")
                logger.info("Setting telegram_id to NULL (empty string)")
        
        # Выполняем обновление пользователя
        if user_updates:
            # Формируем SQL запрос
            update_query_parts = []
            update_params = []
            
            for i, update in enumerate(user_updates):
                if update == "telegram_id = NULL":
                    update_query_parts.append("telegram_id = NULL")
                else:
                    update_query_parts.append(update)
                    update_params.append(user_params[i])
            
            # Добавляем user_id в параметры
            update_params.append(master_user_id)
            
            update_query = f"UPDATE users SET {', '.join(update_query_parts)} WHERE id = ?"
            logger.info(f"Executing query: {update_query}")
            logger.info(f"With params: {update_params}")
            
            cursor.execute(update_query, tuple(update_params))
        
        # Обновляем данные мастера
        master_updates = []
        master_params = []
        
        if qualification is not None:
            master_updates.append("qualification = ?")
            master_params.append(qualification)
        if description is not None:
            master_updates.append("description = ?")
            master_params.append(description)
        if is_active is not None:
            master_updates.append("is_active = ?")
            master_params.append(int(is_active))
        
        if master_updates:
            master_params.append(master_id)
            cursor.execute(f"UPDATE masters SET {', '.join(master_updates)} WHERE id = ?", tuple(master_params))
        
        conn.commit()
        
        # Получаем обновленные данные - ИСПРАВЛЕННЫЙ ЗАПРОС
        cursor.execute("""
            SELECT 
                m.id, m.user_id, m.photo, m.qualification, 
                m.description, m.is_active, m.created_at,
                u.first_name, u.last_name, u.phone, u.email, 
                u.telegram_id
            FROM masters m
            JOIN users u ON m.user_id = u.id
            WHERE m.id = ?
        """, (master_id,))
        
        updated_row = cursor.fetchone()
        
        # ОТЛАДКА: Проверяем что получили из БД
        if updated_row:
            logger.info(f"DEBUG - Raw DB result keys: {updated_row.keys()}")
            logger.info(f"DEBUG - Telegram ID from DB: {updated_row['telegram_id']}")
            logger.info(f"DEBUG - Type of telegram_id from DB: {type(updated_row['telegram_id'])}")
            
            # Создаем словарь из результата запроса
            updated_master_dict = {}
            for key in updated_row.keys():
                value = updated_row[key]
                logger.info(f"DEBUG - Key: {key}, Value: {value}, Type: {type(value)}")
                updated_master_dict[key] = value
            
            # ИСПРАВЛЕНО: Убеждаемся, что telegram_id корректно преобразуется в строку
            if 'telegram_id' in updated_master_dict and updated_master_dict['telegram_id'] is not None:
                # Преобразуем в строку для фронтенда
                updated_master_dict['telegram_id'] = str(updated_master_dict['telegram_id'])
                logger.info(f"DEBUG - Converted telegram_id to string: {updated_master_dict['telegram_id']}")
            else:
                updated_master_dict['telegram_id'] = None
                logger.info(f"DEBUG - telegram_id is None in DB")
        else:
            logger.error(f"DEBUG - No data returned for master {master_id}")
            raise HTTPException(status_code=500, detail="Не удалось получить обновленные данные мастера")
        
        current_photo = new_photo_filename if new_photo_filename else (None if remove_photo else old_photo)
        if current_photo:
            updated_master_dict["photo_url"] = f"{settings.BASE_URL}/uploads/masters/{current_photo}"
        else:
            updated_master_dict["photo_url"] = None
        
        logger.info(f"Master updated: {master_id}, Telegram ID in response: {updated_master_dict.get('telegram_id', 'NULL')}")
        
        # ИСПРАВЛЕНО: Убедимся, что все ключи присутствуют в ответе
        response_data = {
            "success": True,
            "message": "Данные мастера успешно обновлены",
            "master": {
                "id": updated_master_dict.get("id"),
                "user_id": updated_master_dict.get("user_id"),
                "photo": updated_master_dict.get("photo"),
                "photo_url": updated_master_dict.get("photo_url"),
                "qualification": updated_master_dict.get("qualification"),
                "description": updated_master_dict.get("description"),
                "is_active": bool(updated_master_dict.get("is_active", 0)),
                "created_at": updated_master_dict.get("created_at"),
                "first_name": updated_master_dict.get("first_name"),
                "last_name": updated_master_dict.get("last_name"),
                "phone": updated_master_dict.get("phone"),
                "email": updated_master_dict.get("email"),
                "telegram_id": updated_master_dict.get("telegram_id")  # Явно указываем telegram_id
            }
        }
        
        logger.info(f"Response data: {response_data['master'].get('telegram_id')}")
        
        return response_data
        
    except HTTPException as he:
        logger.error(f"HTTPException in update_master: {he}")
        if conn:
            conn.rollback()
        raise he
    except Exception as e:
        logger.error(f"Error updating master: {e}", exc_info=True)
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка при обновлении мастера: {str(e)}")
    finally:
        if conn:
            conn.close()
@app.get("/masters/{master_id}")
async def get_master(master_id: int):
    """Получение информации о мастере"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                m.id, m.user_id, m.photo, m.qualification, 
                m.description, m.is_active, m.created_at,
                u.first_name, u.last_name, u.phone, u.email, 
                u.telegram_id
            FROM masters m
            JOIN users u ON m.user_id = u.id
            WHERE m.id = ?
        """, (master_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            raise HTTPException(status_code=404, detail="Master not found")
        
        master_dict = {}
        for key in row.keys():
            value = row[key]
            # Преобразуем telegram_id в строку если он не None
            if key == 'telegram_id' and value is not None:
                master_dict[key] = str(value)
            else:
                master_dict[key] = value
        
        if master_dict.get("photo"):
            master_dict["photo_url"] = f"{settings.BASE_URL}/uploads/masters/{master_dict['photo']}"
        else:
            master_dict["photo_url"] = None
        
        return master_dict
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching master: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
@app.delete("/masters/{master_id}")
async def delete_master(master_id: int):
    """Удаление мастера (БЕЗ АВТОРИЗАЦИИ)"""
    
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Получаем данные мастера
        cursor.execute("SELECT * FROM masters WHERE id = ?", (master_id,))
        row = cursor.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Мастер не найден")
        
        master_dict = {}
        for key in row.keys():
            master_dict[key] = row[key]
        
        # Удаляем фото если есть
        if master_dict["photo"]:
            delete_master_photo(master_dict["photo"])
        
        # Удаляем мастера
        cursor.execute("DELETE FROM masters WHERE id = ?", (master_id,))
        
        # Удаляем пользователя
        cursor.execute("DELETE FROM users WHERE id = ?", (master_dict["user_id"],))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Master deleted: {master_id}")
        
        return {
            "success": True,
            "message": "Мастер успешно удален"
        }
        
    except Exception as e:
        logger.error(f"Error deleting master: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка при удалении мастера: {str(e)}")

# ==================== SCHEDULE API ====================

@app.get("/schedule/masters/{master_id}")
async def get_master_schedule(master_id: int):
    """Получение графика работы мастера (БЕЗ АВТОРИЗАЦИИ)"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM master_work_schedule 
            WHERE master_id = ?
            ORDER BY day_of_week
        """, (master_id,))
        
        schedule = []
        for row in cursor.fetchall():
            schedule_dict = {}
            for key in row.keys():
                schedule_dict[key] = row[key]
            schedule.append(schedule_dict)
        
        conn.close()
        
        return schedule
        
    except Exception as e:
        logger.error(f"Error fetching schedule: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/schedule/masters/{master_id}")
async def set_master_schedule(
    master_id: int,
    schedule_data: dict
):
    """Установка графика работы мастера (БЕЗ АВТОРИЗАЦИИ)"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Проверяем существование мастера
        cursor.execute("SELECT id FROM masters WHERE id = ?", (master_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Мастер не найден")
        
        day_of_week = schedule_data.get('day_of_week')
        start_time = schedule_data.get('start_time')
        end_time = schedule_data.get('end_time')
        
        if day_of_week is None or start_time is None or end_time is None:
            raise HTTPException(status_code=400, detail="Необходимо указать day_of_week, start_time и end_time")
        
        # Проверяем существующий график на этот день
        cursor.execute("""
            SELECT id FROM master_work_schedule 
            WHERE master_id = ? AND day_of_week = ?
        """, (master_id, day_of_week))
        
        existing = cursor.fetchone()
        
        if existing:
            # Обновляем существующий график
            cursor.execute("""
                UPDATE master_work_schedule 
                SET start_time = ?, end_time = ?
                WHERE id = ?
            """, (start_time, end_time, existing[0]))
        else:
            # Создаем новый график
            cursor.execute("""
                INSERT INTO master_work_schedule (master_id, day_of_week, start_time, end_time)
                VALUES (?, ?, ?, ?)
            """, (master_id, day_of_week, start_time, end_time))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Schedule updated for master {master_id}, day {day_of_week}: {start_time}-{end_time}")
        
        return {"success": True, "message": "График сохранен"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting schedule: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/schedule/masters/{master_id}/days/{day_of_week}")
async def remove_schedule_day(master_id: int, day_of_week: int):
    """Удаление графика на конкретный день (БЕЗ АВТОРИЗАЦИИ)"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            DELETE FROM master_work_schedule 
            WHERE master_id = ? AND day_of_week = ?
        """, (master_id, day_of_week))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Schedule removed for master {master_id}, day {day_of_week}")
        
        return {"success": True, "message": "Запись удалена"}
        
    except Exception as e:
        logger.error(f"Error removing schedule: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# ==================== ОСНОВНЫЕ ENDPOINTS ====================


@app.get("/health")
async def health_check():
    """Проверка здоровья приложения"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        conn.close()
        
        return {
            "status": "healthy",
            "service": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "database": "connected",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "service": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "database": "disconnected",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

# ==================== TEST ENDPOINTS ====================

@app.post("/test/upload")
async def test_upload(
    file: UploadFile = File(...),
    name: str = Form(...)
):
    """Тестовый эндпоинт для проверки загрузки файлов"""
    try:
        filename = save_master_photo(file)
        return {
            "success": True,
            "filename": filename,
            "original_name": file.filename,
            "content_type": file.content_type,
            "name": name,
            "url": f"{settings.BASE_URL}/uploads/masters/{filename}"
        }
    except Exception as e:
        logger.error(f"Test upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ДОБАВЛЕН ТЕСТОВЫЙ ENDPOINT ДЛЯ ОТЛАДКИ
@app.post("/debug/add-service")
async def debug_add_service(
    master_id: int = Form(...),
    service_id: int = Form(...),
    is_primary: bool = Form(False)
):
    """Тестовый endpoint для отладки добавления услуг"""
    logger.info(f"DEBUG: Add service {service_id} to master {master_id}, primary={is_primary}")
    logger.info(f"DEBUG: Received - master_id: {master_id} (type: {type(master_id)}), "
                f"service_id: {service_id} (type: {type(service_id)}), "
                f"is_primary: {is_primary} (type: {type(is_primary)})")
    
    return {
        "success": True,
        "message": "Тестовый endpoint работает",
        "data": {
            "master_id": master_id,
            "service_id": service_id,
            "is_primary": is_primary
        }
    }

# ==================== ФРОНТЕНД (статические файлы) ====================

_frontend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "static", "frontend")
if os.path.isdir(_frontend_dir):
    app.mount("/", StaticFiles(directory=_frontend_dir, html=True), name="frontend")

# ==================== ЗАПУСК СЕРВЕРА ====================

if __name__ == "__main__":
    import uvicorn
    
    logger.info(f"🚀 Starting server on {settings.HOST}:{settings.PORT}")
    logger.info(f"📚 Documentation: http://{settings.HOST}:{settings.PORT}/docs")
    logger.info(f"📁 Uploads directory: http://{settings.HOST}:{settings.PORT}/uploads/")
    logger.info("=" * 60)
    logger.info("🔗 НОВЫЕ ENDPOINTS ДЛЯ СВЯЗИ МАСТЕР-УСЛУГИ:")
    logger.info("  • GET    /masters/{id}/services        - Получить услуги мастера")
    logger.info("  • POST   /masters/{id}/services        - Добавить услугу мастеру")
    logger.info("  • POST   /masters/{id}/services/batch  - Массовое добавление услуг")
    logger.info("  • DELETE /masters/{id}/services/{sid}  - Удалить услугу у мастера")
    logger.info("  • GET    /services/{id}/masters        - Получить мастеров для услуги")
    logger.info("  • GET    /masters/{id}/available-services - Доступные услуги для мастера")
    logger.info("=" * 60)
    logger.info("📊 ANALYTICS API:")
    logger.info("  • GET    /analytics/dashboard          - Dashboard statistics")
    logger.info("  • GET    /analytics/masters-load       - Masters load")
    logger.info("  • GET    /analytics/services-popularity - Services popularity")
    logger.info("  • GET    /analytics/recent-appointments - Recent appointments")
    logger.info("  • GET    /analytics/test               - Test endpoint")
    logger.info("=" * 60)
    logger.info("📅 APPOINTMENTS API:")
    logger.info("  • GET    /appointments         - List appointments")
    logger.info("  • POST   /appointments         - Create appointment")
    logger.info("  • PUT    /appointments/{id}    - Update appointment")
    logger.info("  • PUT    /appointments/{id}/status - Update appointment status")
    logger.info("  • DELETE /appointments/{id}    - Delete appointment")
    logger.info("  • DELETE /appointments/{id}/services - Delete appointment services")
    logger.info("  • POST   /appointments/{id}/services - Add service to appointment")
    logger.info("=" * 60)
    logger.info("👥 CLIENTS API:")
    logger.info("  • GET    /clients              - List clients")
    logger.info("  • POST   /clients              - Create client (JSON)")
    logger.info("  • POST   /clients/form         - Create client (Form)")
    logger.info("  • PUT    /clients/{id}         - Update client")
    logger.info("  • DELETE /clients/{id}         - Delete client")
    logger.info("  • GET    /clients/{id}/stats   - Get client stats")
    logger.info("  • GET    /clients/{id}/recent-appointments - Get recent appointments")
    logger.info("=" * 60)
    logger.info("👨‍💼 MASTERS API (NO AUTH REQUIRED):")
    logger.info("  • GET    /masters           - List masters")
    logger.info("  • POST   /masters           - Create master (with photo)")
    logger.info("  • GET    /masters/{id}      - Get master details")
    logger.info("  • PUT    /masters/{id}      - Update master")
    logger.info("  • DELETE /masters/{id}      - Delete master")
    logger.info("=" * 60)
    logger.info("📁 SERVICES API:")
    logger.info("  • GET    /services          - List services")
    logger.info("  • POST   /services          - Create service")
    logger.info("  • GET    /services/{id}     - Get service details")
    logger.info("  • PUT    /services/{id}     - Update service")
    logger.info("  • DELETE /services/{id}     - Deactivate service")
    logger.info("  • DELETE /services/{id}/force - Force delete service")
    logger.info("=" * 60)
    logger.info("📂 CATEGORIES API:")
    logger.info("  • GET    /services/categories     - List categories")
    logger.info("  • POST   /services/categories     - Create category")
    logger.info("  • GET    /services/categories/{id} - Get category details")
    logger.info("  • PUT    /services/categories/{id} - Update category")
    logger.info("  • DELETE /services/categories/{id} - Delete category (use ?recursive=true for recursive delete)")
    logger.info("=" * 60)
    logger.info("📅 SCHEDULE API:")
    logger.info("  • GET    /schedule/masters/{id} - Get master schedule")
    logger.info("  • POST   /schedule/masters/{id} - Set master schedule")
    logger.info("  • DELETE /schedule/masters/{id}/days/{day} - Remove schedule day")
    logger.info("=" * 60)
    logger.info("✅ Ready to accept requests!")
    
    try:
        uvicorn.run(
            "main:app",
            host=settings.HOST,
            port=settings.PORT,
            reload=True,
            log_level="info"
        )
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Error starting server: {e}")