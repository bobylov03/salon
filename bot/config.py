import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Токен бота
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    
    # ID администраторов
    ADMIN_IDS = [int(id.strip()) for id in os.getenv('ADMIN_IDS', '').split(',') if id.strip()]
    
    # Путь к базе данных
    DATABASE_PATH = os.getenv('DATABASE_PATH', '../salon.db')  # путь от папки bot
    
    # Часовой пояс
    TIMEZONE = os.getenv('TIMEZONE', 'Europe/Moscow')
    
    # Настройки уведомлений
    NOTIFICATION_HOURS_BEFORE = [8, 2]  # За 8 и 2 часа
    
    # Настройки пагинации
    ITEMS_PER_PAGE = 5
    
    # Поддерживаемые языки
    SUPPORTED_LANGUAGES = ['ru', 'en', 'tr']
    DEFAULT_LANGUAGE = 'ru'
    
    # URL для фото мастеров (из FastAPI)
    BASE_URL = "http://localhost:8000"
    
    # Логирование
    LOG_LEVEL = "INFO"
    
    @classmethod
    def validate(cls):
        """Проверка конфигурации"""
        if not cls.BOT_TOKEN:
            raise ValueError("BOT_TOKEN не установлен в .env файле")
        # БД создаётся backend при старте — не проверяем её наличие здесь
        return True