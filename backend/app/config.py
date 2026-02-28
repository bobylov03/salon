import os
from pathlib import Path

class Settings:
    """
    Упрощенная конфигурация приложения
    """
    # Приложение
    APP_NAME = "Beauty Salon Admin API"
    APP_VERSION = "1.0.0"
    
    # Получаем настройки из переменных окружения или используем значения по умолчанию
    DEBUG = os.getenv("DEBUG", "true").lower() == "true"
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", "8000"))
    BASE_URL = os.getenv("BASE_URL", "")
    
    # Безопасность
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 30
    
    # CORS - разбиваем строку на список
    CORS_ORIGINS_STR = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000")
    CORS_ORIGINS = [origin.strip() for origin in CORS_ORIGINS_STR.split(",") if origin.strip()]
    
    # База данных
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///salon.db")
    
    # Загрузка файлов
    UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
    MAX_UPLOAD_SIZE = int(os.getenv("MAX_UPLOAD_SIZE", str(5 * 1024 * 1024)))  # 5MB по умолчанию
    
    # Разрешенные типы изображений
    ALLOWED_IMAGE_TYPES_STR = os.getenv("ALLOWED_IMAGE_TYPES", "image/jpeg,image/png,image/webp,image/gif")
    ALLOWED_IMAGE_TYPES = [img_type.strip() for img_type in ALLOWED_IMAGE_TYPES_STR.split(",")]
    
    # Директории для загрузок
    MASTERS_UPLOAD_DIR = "masters"
    REVIEWS_UPLOAD_DIR = "reviews"
    TEMP_UPLOAD_DIR = "temp"
    
    # Администратор
    ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@salon.com")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
    ADMIN_FIRST_NAME = "Admin"
    ADMIN_LAST_NAME = "Administrator"
    ADMIN_PHONE = os.getenv("ADMIN_PHONE", "")
    
    # Логирование
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    @property
    def upload_base_dir(self) -> Path:
        return Path(self.UPLOAD_DIR)
    
    @property
    def masters_upload_dir(self) -> Path:
        return self.upload_base_dir / self.MASTERS_UPLOAD_DIR
    
    @property
    def reviews_upload_dir(self) -> Path:
        return self.upload_base_dir / self.REVIEWS_UPLOAD_DIR
    
    @property
    def temp_upload_dir(self) -> Path:
        return self.upload_base_dir / self.TEMP_UPLOAD_DIR
    
    def create_upload_dirs(self) -> None:
        """Создать все необходимые директории для загрузок"""
        dirs_to_create = [
            self.upload_base_dir,
            self.masters_upload_dir,
            self.reviews_upload_dir,
            self.temp_upload_dir,
        ]
        
        for directory in dirs_to_create:
            directory.mkdir(parents=True, exist_ok=True)
            print(f"📁 Created directory: {directory.absolute()}")
    
    def get_max_upload_size_mb(self) -> float:
        """Получить максимальный размер в мегабайтах"""
        return self.MAX_UPLOAD_SIZE / (1024 * 1024)
    
    def get_allowed_image_extensions(self) -> list:
        """Получить список разрешенных расширений файлов"""
        type_to_extension = {
            "image/jpeg": [".jpg", ".jpeg", ".jpe"],
            "image/png": [".png"],
            "image/webp": [".webp"],
            "image/gif": [".gif"],
        }
        
        extensions = []
        for mime_type in self.ALLOWED_IMAGE_TYPES:
            if mime_type in type_to_extension:
                extensions.extend(type_to_extension[mime_type])
        
        return list(set(extensions))

# Создаем экземпляр настроек
settings = Settings()

# Автоматически создаем директории при импорте
if __name__ == "__main__":
    print("=" * 50)
    print(f"🔧 {settings.APP_NAME} Configuration")
    print("=" * 50)
    print(f"DEBUG: {settings.DEBUG}")
    print(f"HOST: {settings.HOST}")
    print(f"PORT: {settings.PORT}")
    print(f"BASE_URL: {settings.BASE_URL}")
    print(f"CORS Origins: {settings.CORS_ORIGINS}")
    print(f"Database: {settings.DATABASE_URL}")
    print(f"Upload Dir: {settings.UPLOAD_DIR}")
    print(f"Max Upload: {settings.get_max_upload_size_mb()} MB")
    print(f"Allowed Image Types: {settings.ALLOWED_IMAGE_TYPES}")
    print(f"Admin Email: {settings.ADMIN_EMAIL}")
    print("=" * 50)
    print("✅ Configuration loaded successfully!")
    print("=" * 50)