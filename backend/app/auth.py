# backend/app/auth.py
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, status, Form, Depends
from fastapi.security import HTTPBearer
import logging
import secrets

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["authentication"])
security = HTTPBearer()

# Единое хранилище токенов для всего приложения
# Формат: {"token_string": {"user_id": int, "expires": datetime}}
active_tokens = {}

def authenticate_user(username: str, password: str):
    """Аутентификация пользователя"""
    # Фиксированные креды для демо
    if username == "admin@salon.com" and password == "admin123":
        return {"id": 1, "role": "admin", "email": "admin@salon.com", "first_name": "Admin", "last_name": "User"}
    return None

def create_access_token(data: dict):
    """Создание токена"""
    # Генерируем токен
    token = secrets.token_hex(32)
    
    # Получаем user_id из данных
    user_id = int(data.get("sub", "1"))
    
    # Время истечения токена
    expires = datetime.utcnow() + timedelta(hours=24)
    
    # Сохраняем токен
    active_tokens[token] = {
        "user_id": user_id,
        "expires": expires
    }
    
    logger.info(f"Token created for user {user_id}")
    return token

def validate_token(token: str):
    """Валидация токена"""
    if token not in active_tokens:
        logger.warning(f"Token not found: {token[:20]}...")
        return None
    
    token_data = active_tokens[token]
    
    # Проверяем срок действия
    if datetime.utcnow() > token_data["expires"]:
        # Удаляем просроченный токен
        del active_tokens[token]
        logger.info(f"Token expired: {token[:20]}...")
        return None
    
    # Возвращаем ID пользователя
    return token_data["user_id"]

async def get_current_user(credentials = Depends(security)):
    """Получение текущего пользователя"""
    token = credentials.credentials
    
    # Для отладки
    logger.debug(f"Validating token: {token[:20]}...")
    logger.debug(f"Active tokens count: {len(active_tokens)}")
    
    user_id = validate_token(token)
    
    if not user_id:
        logger.warning(f"Token validation failed for: {token[:20]}...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    logger.debug(f"Token valid for user_id: {user_id}")
    
    # Возвращаем информацию о пользователе
    return {
        "id": user_id,
        "role": "admin",
        "email": "admin@salon.com",
        "first_name": "Admin",
        "last_name": "User"
    }

async def get_current_admin(current_user: dict = Depends(get_current_user)):
    """Проверка что пользователь админ"""
    # В нашей системе все пользователи - админы
    return current_user

@router.post("/login")
async def login(
    username: str = Form(...),
    password: str = Form(...)
):
    """
    Аутентификация администратора
    """
    # Проверяем учетные данные
    user = authenticate_user(username, password)
    
    if not user:
        logger.warning(f"Failed login attempt for: {username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    
    # Создаем токен
    access_token = create_access_token(data={"sub": str(user["id"])})
    
    logger.info(f"User logged in: {username}, user_id: {user['id']}")
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me")
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """
    Получение информации о текущем пользователе
    """
    return {
        "id": current_user["id"],
        "email": current_user["email"],
        "role": current_user["role"],
        "first_name": current_user["first_name"],
        "last_name": current_user["last_name"]
    }

@router.post("/logout")
async def logout(token: str = Form(...)):
    """
    Выход из системы (инвалидация токена)
    """
    if token in active_tokens:
        user_id = active_tokens[token]["user_id"]
        del active_tokens[token]
        logger.info(f"User logged out: user_id={user_id}")
        return {"message": "Successfully logged out"}
    
    return {"message": "Token not found or already invalidated"}

@router.get("/validate")
async def validate_token_endpoint(token: str):
    """
    Проверка валидности токена (для отладки)
    """
    user_id = validate_token(token)
    if user_id:
        return {
            "valid": True,
            "user_id": user_id,
            "expires": active_tokens[token]["expires"].isoformat() if token in active_tokens else None
        }
    return {"valid": False}

@router.get("/active-tokens")
async def get_active_tokens():
    """
    Получение списка активных токенов (только для отладки!)
    """
    result = {}
    for token, data in active_tokens.items():
        result[token[:10] + "..."] = {
            "user_id": data["user_id"],
            "expires": data["expires"].isoformat(),
            "ttl": (data["expires"] - datetime.utcnow()).total_seconds()
        }
    return {
        "total_tokens": len(active_tokens),
        "tokens": result
    }

def log_admin_action(admin_id: int, action: str, details: str = ""):
    """
    Логирование действий администратора
    """
    logger.info(f"Admin action: {action} by admin_id: {admin_id}")

@router.get("/test-protected")
async def test_protected(current_user: dict = Depends(get_current_user)):
    """
    Тестовый защищенный endpoint
    """
    return {
        "message": "Access granted",
        "user_id": current_user["id"],
        "role": current_user["role"]
    }