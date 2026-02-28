# run_bot.py
import sys
import os
import logging
from telegram.error import NetworkError

# Добавляем папку bot в путь Python
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'bot'))

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main():
    try:
        from bot.main import main as bot_main
        
        # Запускаем бота
        logger.info("Запускаем бота...")
        bot_main()
        
    except NetworkError as e:
        logger.error(f"Ошибка сети при запуске бота: {e}")
        logger.info("Проверьте:")
        logger.info("1. Интернет-соединение")
        logger.info("2. Токен бота в .env файле")
        logger.info("3. Прокси, если вы в России")
        return 1
    except ImportError as e:
        logger.error(f"Ошибка импорта: {e}")
        logger.info("Проверьте структуру проекта:")
        logger.info("Папка 'bot' должна содержать main.py, config.py и другие файлы")
        return 1
    except Exception as e:
        logger.error(f"Неожиданная ошибка: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())