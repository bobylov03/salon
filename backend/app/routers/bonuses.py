from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from app.auth import get_current_admin, log_admin_action
from app.database import db
from app.models import BonusUpdate, PaginatedResponse
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/bonuses", tags=["bonuses"])

@router.get("/{client_id}/balance")
async def get_client_bonus_balance(
    client_id: int,
    current_user: dict = Depends(get_current_admin)
):
    """
    Получение бонусного баланса клиента
    """
    # Проверяем существование клиента
    client = db.fetch_one("SELECT id FROM users WHERE id = ? AND role = 'client'", (client_id,))
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Получаем баланс
    bonus = db.fetch_one("SELECT * FROM bonuses WHERE client_id = ?", (client_id,))
    
    if not bonus:
        # Создаем запись с нулевым балансом
        db.execute_query("INSERT INTO bonuses (client_id, balance) VALUES (?, 0)", (client_id,))
        bonus = {"client_id": client_id, "balance": 0}
    
    # Получаем историю операций (последние 10)
    history = db.fetch_all("""
        SELECT * FROM bonus_history 
        WHERE client_id = ? 
        ORDER BY created_at DESC 
        LIMIT 10
    """, (client_id,))
    
    return {
        "balance": bonus["balance"],
        "history": history
    }

@router.post("/{client_id}/add")
async def add_bonuses(
    client_id: int,
    bonus_data: BonusUpdate,
    current_user: dict = Depends(get_current_admin)
):
    """
    Начисление бонусов клиенту
    """
    if bonus_data.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")
    
    # Проверяем существование клиента
    client = db.fetch_one("SELECT id FROM users WHERE id = ? AND role = 'client'", (client_id,))
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Получаем текущий баланс
    bonus = db.fetch_one("SELECT * FROM bonuses WHERE client_id = ?", (client_id,))
    
    if not bonus:
        # Создаем запись
        db.execute_query("INSERT INTO bonuses (client_id, balance) VALUES (?, ?)", 
                        (client_id, bonus_data.amount))
    else:
        # Обновляем баланс
        new_balance = bonus["balance"] + bonus_data.amount
        db.execute_query("UPDATE bonuses SET balance = ? WHERE client_id = ?", 
                        (new_balance, client_id))
    
    # Добавляем запись в историю
    db.execute_query("""
        INSERT INTO bonus_history (client_id, amount, reason)
        VALUES (?, ?, ?)
    """, (client_id, bonus_data.amount, bonus_data.reason or "Manual addition"))
    
    log_admin_action(
        current_user["id"], 
        "ADD_BONUSES", 
        f"Added {bonus_data.amount} bonuses to client {client_id}"
    )
    
    return {"message": f"Added {bonus_data.amount} bonuses"}

@router.post("/{client_id}/subtract")
async def subtract_bonuses(
    client_id: int,
    bonus_data: BonusUpdate,
    current_user: dict = Depends(get_current_admin)
):
    """
    Списание бонусов с клиента
    """
    if bonus_data.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")
    
    # Проверяем существование клиента
    client = db.fetch_one("SELECT id FROM users WHERE id = ? AND role = 'client'", (client_id,))
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Получаем текущий баланс
    bonus = db.fetch_one("SELECT * FROM bonuses WHERE client_id = ?", (client_id,))
    
    if not bonus or bonus["balance"] < bonus_data.amount:
        raise HTTPException(status_code=400, detail="Insufficient bonus balance")
    
    # Обновляем баланс
    new_balance = bonus["balance"] - bonus_data.amount
    db.execute_query("UPDATE bonuses SET balance = ? WHERE client_id = ?", 
                    (new_balance, client_id))
    
    # Добавляем запись в историю с отрицательным значением
    db.execute_query("""
        INSERT INTO bonus_history (client_id, amount, reason)
        VALUES (?, ?, ?)
    """, (client_id, -bonus_data.amount, bonus_data.reason or "Manual subtraction"))
    
    log_admin_action(
        current_user["id"], 
        "SUBTRACT_BONUSES", 
        f"Subtracted {bonus_data.amount} bonuses from client {client_id}"
    )
    
    return {"message": f"Subtracted {bonus_data.amount} bonuses"}

@router.get("/{client_id}/history")
async def get_bonus_history(
    client_id: int,
    current_user: dict = Depends(get_current_admin),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100)
):
    """
    Получение истории операций с бонусами
    """
    offset = (page - 1) * per_page
    
    history = db.fetch_all("""
        SELECT * FROM bonus_history 
        WHERE client_id = ? 
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
    """, (client_id, per_page, offset))
    
    # Общее количество
    count_result = db.fetch_one(
        "SELECT COUNT(*) as count FROM bonus_history WHERE client_id = ?",
        (client_id,)
    )
    total = count_result["count"] if count_result else 0
    
    return {
        "items": history,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page
    }