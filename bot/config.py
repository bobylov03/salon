import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Токен бота
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    
    # ID администраторов
    ADMIN_IDS = [int(id.strip()) for id in os.getenv('ADMIN_IDS', '').split(',') if id.strip()]
    
    # Путь к базе данных (в Docker переопределяется через DATABASE_PATH env var)
    DATABASE_PATH = os.getenv('DATABASE_PATH', '')
    
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
    BASE_URL = os.getenv('BASE_URL', 'http://localhost:8000')
    
    # Логирование
    LOG_LEVEL = "INFO"
    
    @classmethod
    def validate(cls):
        """Проверка конфигурации"""
        if not cls.BOT_TOKEN:
            raise ValueError("BOT_TOKEN не установлен в .env файле")
        
        # Получаем абсолютный путь к БД
        import os
        current_dir = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(current_dir, cls.DATABASE_PATH)
        
        if not os.path.exists(db_path):
            # Пробуем найти на уровень выше
            db_path = os.path.join(os.path.dirname(current_dir), 'salon.db')
            if not os.path.exists(db_path):
                raise FileNotFoundError(f"База данных не найдена по пути: {db_path}")
        
        return True