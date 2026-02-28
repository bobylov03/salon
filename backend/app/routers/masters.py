# routers/masters.py
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form, status
from typing import List, Optional
from app.auth import get_current_admin, log_admin_action
from app.database import db
from app.models import MasterCreate, MasterUpdate, MasterResponse, PaginatedResponse
from app.config import settings
import os
import shutil
import uuid
import logging
from pathlib import Path
from datetime import datetime
import imghdr  # Для проверки типа изображения
from sqlalchemy.exc import IntegrityError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/masters", tags=["masters"])

# Папка для хранения фото мастеров
PHOTOS_DIR = Path("uploads/masters")
PHOTOS_DIR.mkdir(parents=True, exist_ok=True)

# Разрешенные типы файлов
ALLOWED_IMAGE_TYPES = ["image/jpeg", "image/jpg", "image/png", "image/webp", "image/gif"]
ALLOWED_EXTENSIONS = [".jpg", ".jpeg", ".png", ".webp", ".gif"]
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

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

def save_uploaded_file(file: UploadFile) -> str:
    """Сохраняет загруженный файл и возвращает путь относительно uploads"""
    
    # Временный файл для проверки
    temp_filename = f"temp_{uuid.uuid4()}"
    temp_path = PHOTOS_DIR / temp_filename
    
    try:
        # Сохраняем временно для проверки
        with open(temp_path, "wb") as buffer:
            content = file.file.read()
            buffer.write(content)
            file.file.seek(0)  # Возвращаем курсор в начало
        
        # Проверяем размер файла
        file_size = os.path.getsize(temp_path)
        if file_size > MAX_FILE_SIZE:
            os.remove(temp_path)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Файл слишком большой (максимум 5MB)"
            )
        
        # Проверяем расширение файла
        original_filename = file.filename or ""
        file_ext = Path(original_filename).suffix.lower()
        
        if file_ext not in ALLOWED_EXTENSIONS:
            os.remove(temp_path)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Недопустимое расширение файла. Разрешены: {', '.join(ALLOWED_EXTENSIONS)}"
            )
        
        # Проверяем содержимое файла
        if not validate_image_file(temp_path):
            os.remove(temp_path)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Файл не является валидным изображением"
            )
        
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
        final_path = PHOTOS_DIR / final_filename
        
        # Переименовываем временный файл в окончательный
        os.rename(temp_path, final_path)
        
        logger.info(f"Фото сохранено: {original_filename} -> {final_filename} ({file_size} bytes)")
        return f"masters/{final_filename}"
        
    except HTTPException:
        raise
    except Exception as e:
        # Удаляем временный файл если что-то пошло не так
        if temp_path.exists():
            try:
                os.remove(temp_path)
            except:
                pass
        logger.error(f"Ошибка сохранения фото: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при сохранении файла: {str(e)}"
        )

def delete_photo(photo_path: str):
    """Удаляет файл фото"""
    if not photo_path:
        return
        
    try:
        full_path = Path("uploads") / photo_path
        if full_path.exists() and full_path.is_file():
            full_path.unlink()
            logger.info(f"Фото удалено: {photo_path}")
    except Exception as e:
        logger.error(f"Ошибка удаления фото {photo_path}: {e}")

def get_photo_url(photo_path: Optional[str]) -> Optional[str]:
    """Формирует полный URL для фото"""
    if not photo_path:
        return None
    return f"{settings.BASE_URL}/uploads/{photo_path}"

def check_master_exists(master_id: int) -> bool:
    """Проверяет существование мастера"""
    master = db.fetch_one("SELECT id FROM masters WHERE id = ?", (master_id,))
    return bool(master)

def check_phone_unique(phone: str, exclude_user_id: Optional[int] = None) -> bool:
    """Проверяет уникальность телефона"""
    if not phone:
        return True
        
    if exclude_user_id:
        query = "SELECT id FROM users WHERE phone = ? AND id != ?"
        params = (phone, exclude_user_id)
    else:
        query = "SELECT id FROM users WHERE phone = ?"
        params = (phone,)
    
    existing = db.fetch_one(query, params)
    return existing is None

def check_email_unique(email: str, exclude_user_id: Optional[int] = None) -> bool:
    """Проверяет уникальность email"""
    if not email:
        return True
        
    if exclude_user_id:
        query = "SELECT id FROM users WHERE email = ? AND id != ?"
        params = (email, exclude_user_id)
    else:
        query = "SELECT id FROM users WHERE email = ?"
        params = (email,)
    
    existing = db.fetch_one(query, params)
    return existing is None

def get_next_telegram_id() -> int:
    """Генерирует следующий telegram_id для мастера"""
    try:
        result = db.fetch_one("SELECT MAX(telegram_id) as max_id FROM users WHERE role = 'master'")
        max_id = result["max_id"] if result and result["max_id"] else 1000
        return max_id + 1
    except Exception as e:
        logger.error(f"Ошибка получения telegram_id: {e}")
        return 1001

@router.get("", response_model=PaginatedResponse)
async def get_masters(
    current_user: dict = Depends(get_current_admin),
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    is_active: Optional[bool] = None,
    search: Optional[str] = None
):
    """
    Получение списка мастеров с пагинацией
    """
    logger.info(f"Запрос списка мастеров от пользователя {current_user.get('id')}")
    
    try:
        offset = (page - 1) * per_page
        
        # Базовый запрос
        query = """
            SELECT m.id, m.user_id, m.photo, m.qualification, 
                   m.description, m.is_active, m.created_at,
                   u.first_name, u.last_name, u.phone, u.email
            FROM masters m
            JOIN users u ON m.user_id = u.id
            WHERE u.role = 'master'
        """
        count_query = """
            SELECT COUNT(*) as count 
            FROM masters m
            JOIN users u ON m.user_id = u.id
            WHERE u.role = 'master'
        """
        params = []
        where_conditions = []
        
        # Фильтры
        if is_active is not None:
            where_conditions.append("m.is_active = ?")
            params.append(int(is_active))
        
        if search and search.strip():
            where_conditions.append(
                "(u.first_name LIKE ? OR u.last_name LIKE ? OR u.phone LIKE ? OR m.qualification LIKE ? OR u.email LIKE ?)"
            )
            search_term = f"%{search.strip()}%"
            params.extend([search_term, search_term, search_term, search_term, search_term])
        
        # Добавляем условия WHERE
        if where_conditions:
            query += " AND " + " AND ".join(where_conditions)
            count_query += " AND " + " AND ".join(where_conditions)
        
        # Пагинация
        query += " ORDER BY m.created_at DESC LIMIT ? OFFSET ?"
        params.extend([per_page, offset])
        
        # Получаем данные
        masters = db.fetch_all(query, tuple(params))
        
        # Формируем полные URL для фото
        for master in masters:
            master["photo_url"] = get_photo_url(master.get("photo"))
        
        # Общее количество
        count_params = params[:-2] if len(params) > 2 else tuple()
        count_result = db.fetch_one(count_query, count_params)
        total = count_result["count"] if count_result else 0
        
        logger.info(f"Найдено {len(masters)} мастеров, всего: {total}")
        
        return {
            "items": masters,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page if per_page > 0 else 0
        }
    
    except Exception as e:
        logger.error(f"Ошибка получения мастеров: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при получении мастеров: {str(e)}"
        )

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_master(
    first_name: str = Form(...),
    last_name: str = Form(...),
    phone: Optional[str] = Form(None),
    telegram_id: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    qualification: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    is_active: bool = Form(True),
    photo: Optional[UploadFile] = File(None),
    current_user: dict = Depends(get_current_admin)
):
    """
    Создание нового мастера с возможностью загрузки фото
    """
    logger.info(f"Создание мастера от пользователя {current_user.get('id')}")
    
    photo_path = None
    connection = None
    
    try:
        # Проверяем уникальность телефона если указан
        if phone and not check_phone_unique(phone):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Телефон уже используется"
            )
        
        # Проверяем уникальность email если указан
        if email and not check_email_unique(email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email уже используется"
            )
        
        # Сохраняем фото если есть
        if photo and photo.filename:
            logger.info(f"Загрузка фото: {photo.filename}")
            photo_path = save_uploaded_file(photo)
            logger.info(f"Фото сохранено как: {photo_path}")
        
        # Генерируем уникальный telegram_id
        telegram_id = get_next_telegram_id()
        
        # Начинаем транзакцию
        connection = db.get_connection()
        cursor = connection.cursor()
        
        # Создаем пользователя
        cursor.execute("""
            INSERT INTO users (telegram_id, role, first_name, last_name, phone, email, language, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (telegram_id, 'master', first_name, last_name, phone or '', email or '', 'ru', datetime.now()))
        
        user_id = cursor.lastrowid
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Не удалось создать пользователя"
            )
        
        # Создаем мастера
        cursor.execute("""
            INSERT INTO masters (user_id, photo, qualification, description, is_active, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, photo_path, qualification or '', description or '', int(is_active), datetime.now()))
        
        master_id = cursor.lastrowid
        if not master_id:
            cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
            connection.commit()
            if photo_path:
                delete_photo(photo_path)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Не удалось создать мастера"
            )
        
        # Получаем созданного мастера
        cursor.execute("""
            SELECT m.id, m.user_id, m.photo, m.qualification, 
                   m.description, m.is_active, m.created_at,
                   u.first_name, u.last_name, u.phone, u.email, u.telegram_id
            FROM masters m
            JOIN users u ON m.user_id = u.id
            WHERE m.id = ?
        """, (master_id,))
        
        master_row = cursor.fetchone()
        if not master_row:
            cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
            cursor.execute("DELETE FROM masters WHERE id = ?", (master_id,))
            connection.commit()
            if photo_path:
                delete_photo(photo_path)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Не удалось получить данные созданного мастера"
            )
        
        # Конвертируем строку в словарь
        master = dict(zip([col[0] for col in cursor.description], master_row))
        
        # Коммитим транзакцию
        connection.commit()
        
        # Формируем полный URL фото
        master["photo_url"] = get_photo_url(master.get("photo"))
        
        log_admin_action(
            current_user["id"], 
            "CREATE_MASTER", 
            f"Создан мастер {master_id}: {first_name} {last_name}"
        )
        
        return {
            "success": True,
            "message": "Мастер успешно создан",
            "master": master
        }
    
    except HTTPException:
        if connection:
            connection.rollback()
        if photo_path:
            delete_photo(photo_path)
        raise
    
    except Exception as e:
        logger.error(f"Ошибка создания мастера: {e}", exc_info=True)
        if connection:
            connection.rollback()
        if photo_path:
            delete_photo(photo_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при создании мастера: {str(e)}"
        )
    
    finally:
        if connection:
            connection.close()

@router.get("/{master_id}")
async def get_master(
    master_id: int,
    current_user: dict = Depends(get_current_admin)
):
    """
    Получение информации о мастере
    """
    logger.info(f"Запрос мастера {master_id} от пользователя {current_user.get('id')}")
    
    try:
        master = db.fetch_one("""
            SELECT m.id, m.user_id, m.photo, m.qualification, 
                   m.description, m.is_active, m.created_at,
                   u.first_name, u.last_name, u.phone, u.email, u.telegram_id
            FROM masters m
            JOIN users u ON m.user_id = u.id
            WHERE m.id = ?
        """, (master_id,))
        
        if not master:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Мастер не найден"
            )
        
        # Формируем полный URL фото
        master["photo_url"] = get_photo_url(master.get("photo"))
        
        return master
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"Ошибка получения мастера {master_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при получении данных мастера: {str(e)}"
        )

@router.put("/{master_id}")
async def update_master(
    master_id: int,
    first_name: Optional[str] = Form(None),
    last_name: Optional[str] = Form(None),
    phone: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    qualification: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    is_active: Optional[bool] = Form(None),
    photo: Optional[UploadFile] = File(None),
    remove_photo: Optional[bool] = Form(False),
    current_user: dict = Depends(get_current_admin)
):
    """
    Обновление данных мастера с возможностью загрузки нового фото
    """
    logger.info(f"Обновление мастера {master_id} от пользователя {current_user.get('id')}")
    
    # Проверяем существование мастера
    if not check_master_exists(master_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Мастер не найден"
        )
    
    connection = None
    old_photo_path = None
    new_photo_path = None
    
    try:
        # Получаем текущие данные мастера
        master = db.fetch_one("""
            SELECT m.*, u.id as user_id, u.phone as current_phone, u.email as current_email
            FROM masters m
            JOIN users u ON m.user_id = u.id
            WHERE m.id = ?
        """, (master_id,))
        
        if not master:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Мастер не найден"
            )
        
        user_id = master["user_id"]
        old_photo_path = master.get("photo")
        
        # Проверяем уникальность телефона если изменяется
        if phone is not None and phone != master.get("current_phone"):
            if not check_phone_unique(phone, user_id):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Телефон уже используется другим пользователем"
                )
        
        # Проверяем уникальность email если изменяется
        if email is not None and email != master.get("current_email"):
            if not check_email_unique(email, user_id):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email уже используется другим пользователем"
                )
        
        # Обработка фото
        if remove_photo:
            # Помечаем фото для удаления
            if old_photo_path:
                delete_photo(old_photo_path)
            new_photo_path = None
            photo_update_query = "photo = NULL"
            photo_params = ()
        
        elif photo and photo.filename:
            # Сохраняем новое фото
            new_photo_path = save_uploaded_file(photo)
            photo_update_query = "photo = ?"
            photo_params = (new_photo_path,)
            
            # Удаляем старое фото после успешного сохранения нового
            if old_photo_path:
                delete_photo(old_photo_path)
        
        else:
            # Фото не изменяется
            photo_update_query = ""
            photo_params = ()
        
        # Начинаем транзакцию
        connection = db.get_connection()
        cursor = connection.cursor()
        
        # Обновляем пользователя
        user_updates = []
        user_params = []
        
        if first_name is not None:
            user_updates.append("first_name = ?")
            user_params.append(first_name)
        if last_name is not None:
            user_updates.append("last_name = ?")
            user_params.append(last_name)
        if phone is not None:
            user_updates.append("phone = ?")
            user_params.append(phone)
        if email is not None:
            user_updates.append("email = ?")
            user_params.append(email)
        
        if user_updates:
            user_params.append(user_id)
            cursor.execute(
                f"UPDATE users SET {', '.join(user_updates)} WHERE id = ?",
                tuple(user_params)
            )
        
        # Обновляем мастера
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
        
        # Добавляем обновление фото если нужно
        if photo_update_query:
            master_updates.append(photo_update_query)
            master_params.extend(photo_params)
        
        if master_updates:
            master_params.append(master_id)
            cursor.execute(
                f"UPDATE masters SET {', '.join(master_updates)} WHERE id = ?",
                tuple(master_params)
            )
        
        # Получаем обновленного мастера
        cursor.execute("""
            SELECT m.id, m.user_id, m.photo, m.qualification, 
                   m.description, m.is_active, m.created_at,
                   u.first_name, u.last_name, u.phone, u.email, u.telegram_id
            FROM masters m
            JOIN users u ON m.user_id = u.id
            WHERE m.id = ?
        """, (master_id,))
        
        updated_master_row = cursor.fetchone()
        if not updated_master_row:
            connection.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Не удалось получить обновленные данные мастера"
            )
        
        # Конвертируем строку в словарь
        updated_master = dict(zip([col[0] for col in cursor.description], updated_master_row))
        
        # Коммитим транзакцию
        connection.commit()
        
        # Формируем полный URL фото
        current_photo = new_photo_path if new_photo_path else (None if remove_photo else old_photo_path)
        updated_master["photo_url"] = get_photo_url(current_photo)
        
        log_admin_action(current_user["id"], "UPDATE_MASTER", f"Обновлен мастер {master_id}")
        
        return {
            "success": True,
            "message": "Данные мастера успешно обновлены",
            "master": updated_master
        }
    
    except HTTPException:
        if connection:
            connection.rollback()
        # Удаляем новое фото если была ошибка
        if new_photo_path:
            delete_photo(new_photo_path)
        raise
    
    except Exception as e:
        logger.error(f"Ошибка обновления мастера {master_id}: {e}", exc_info=True)
        if connection:
            connection.rollback()
        # Удаляем новое фото если была ошибка
        if new_photo_path:
            delete_photo(new_photo_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при обновлении мастера: {str(e)}"
        )
    
    finally:
        if connection:
            connection.close()

@router.delete("/{master_id}")
async def delete_master(
    master_id: int,
    current_user: dict = Depends(get_current_admin)
):
    """
    Удаление мастера
    """
    logger.info(f"Удаление мастера {master_id} от пользователя {current_user.get('id')}")
    
    connection = None
    
    try:
        # Получаем информацию о мастере для удаления фото
        master = db.fetch_one("""
            SELECT m.*, u.first_name, u.last_name
            FROM masters m
            JOIN users u ON m.user_id = u.id
            WHERE m.id = ?
        """, (master_id,))
        
        if not master:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Мастер не найден"
            )
        
        master_name = f"{master['first_name']} {master['last_name']}"
        
        # Проверяем, есть ли связанные записи (например, записи на прием)
        # Это опциональная проверка, можно удалить или адаптировать под вашу логику
        appointments_count = db.fetch_one(
            "SELECT COUNT(*) as count FROM appointments WHERE master_id = ?",
            (master_id,)
        )
        
        if appointments_count and appointments_count["count"] > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Нельзя удалить мастера, так как у него есть записи на прием ({appointments_count['count']} записей)"
            )
        
        # Начинаем транзакцию
        connection = db.get_connection()
        cursor = connection.cursor()
        
        # Удаляем фото если есть
        if master.get("photo"):
            delete_photo(master["photo"])
        
        # Получаем user_id для удаления пользователя
        user_id = master["user_id"]
        
        # Удаляем мастера
        cursor.execute("DELETE FROM masters WHERE id = ?", (master_id,))
        master_deleted = cursor.rowcount > 0
        
        if not master_deleted:
            connection.rollback()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Мастер не найден"
            )
        
        # Удаляем пользователя
        cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
        
        # Коммитим транзакцию
        connection.commit()
        
        log_admin_action(
            current_user["id"], 
            "DELETE_MASTER", 
            f"Удален мастер {master_id}: {master_name}"
        )
        
        return {
            "success": True,
            "message": "Мастер успешно удален",
            "deleted_master": {
                "id": master_id,
                "name": master_name
            }
        }
    
    except HTTPException:
        if connection:
            connection.rollback()
        raise
    
    except Exception as e:
        logger.error(f"Ошибка удаления мастера {master_id}: {e}", exc_info=True)
        if connection:
            connection.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при удалении мастера: {str(e)}"
        )
    
    finally:
        if connection:
            connection.close()

@router.patch("/{master_id}/status")
async def toggle_master_status(
    master_id: int,
    is_active: bool = Form(...),
    current_user: dict = Depends(get_current_admin)
):
    """
    Включение/выключение мастера (активация/деактивация)
    """
    logger.info(f"Изменение статуса мастера {master_id} на {is_active} от пользователя {current_user.get('id')}")
    
    try:
        # Проверяем существование мастера
        if not check_master_exists(master_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Мастер не найден"
            )
        
        # Обновляем статус
        rows_affected = db.execute_query(
            "UPDATE masters SET is_active = ? WHERE id = ?",
            (int(is_active), master_id)
        )
        
        if rows_affected == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Мастер не найден"
            )
        
        status_text = "активирован" if is_active else "деактивирован"
        log_admin_action(
            current_user["id"], 
            "TOGGLE_MASTER_STATUS", 
            f"Мастер {master_id} {status_text}"
        )
        
        return {
            "success": True,
            "message": f"Мастер успешно {status_text}",
            "master_id": master_id,
            "is_active": is_active
        }
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"Ошибка изменения статуса мастера {master_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при изменении статуса мастера: {str(e)}"
        )