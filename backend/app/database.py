import sqlite3
from contextlib import contextmanager
from typing import Generator, Optional, Dict, Any
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, db_path: str = "salon.db"):
        self.db_path = db_path
        
    @contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Получение соединения с БД"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            yield conn
            conn.commit()
        except sqlite3.Error as e:
            if conn:
                conn.rollback()
            logger.error(f"Database error: {e}")
            raise HTTPException(status_code=500, detail="Database error")
        finally:
            if conn:
                conn.close()
    
    def execute_query(self, query: str, params: tuple = None) -> Optional[sqlite3.Cursor]:
        """Выполнение SQL запроса"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                return cursor
        except Exception as e:
            logger.error(f"Query error: {e}, query: {query}")
            return None
    
    def fetch_one(self, query: str, params: tuple = None) -> Optional[Dict[str, Any]]:
        """Получение одной записи"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Fetch one error: {e}, query: {query}")
            return None
    
    def fetch_all(self, query: str, params: tuple = None) -> list:
        """Получение всех записей"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Fetch all error: {e}, query: {query}")
            return []
    
    def insert_and_get_id(self, query: str, params: tuple = None) -> int:
        """Вставка записи и получение ID"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                return cursor.lastrowid
        except Exception as e:
            logger.error(f"Insert error: {e}, query: {query}")
            return -1

# Инициализация менеджера БД
db = DatabaseManager()

# Функция инициализации админа
def init_admin():
    """Создание администратора по умолчанию если его нет"""
    from app.config import settings
    
    # Проверяем существование админа
    admin = db.fetch_one(
        "SELECT id, role FROM users WHERE role = 'admin' LIMIT 1"
    )
    
    if not admin:
        # Создаем админа
        db.insert_and_get_id("""
            INSERT INTO users (telegram_id, role, first_name, last_name, phone, language)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (0, 'admin', 'Admin', 'Admin', '', 'ru'))
        
        logger.info("Default admin user created")