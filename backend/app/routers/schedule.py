from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List
from app.auth import get_current_admin, log_admin_action
from app.database import db
from app.models import WorkScheduleCreate, WorkScheduleResponse
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/schedule", tags=["work schedule"])

@router.get("/masters/{master_id}", response_model=List[WorkScheduleResponse])
async def get_master_schedule(
    master_id: int,
    current_user: dict = Depends(get_current_admin)
):
    """
    Получение графика работы мастера
    """
    schedule = db.fetch_all("""
        SELECT * FROM master_work_schedule 
        WHERE master_id = ?
        ORDER BY day_of_week
    """, (master_id,))
    
    return schedule

@router.post("/masters/{master_id}", response_model=WorkScheduleResponse)
async def set_master_schedule(
    master_id: int,
    schedule_data: WorkScheduleCreate,
    current_user: dict = Depends(get_current_admin)
):
    """
    Установка графика работы мастера
    """
    # Проверяем существование мастера
    master = db.fetch_one("SELECT id FROM masters WHERE id = ?", (master_id,))
    if not master:
        raise HTTPException(status_code=404, detail="Master not found")
    
    # Проверяем существующий график на этот день
    existing = db.fetch_one("""
        SELECT id FROM master_work_schedule 
        WHERE master_id = ? AND day_of_week = ?
    """, (master_id, schedule_data.day_of_week))
    
    if existing:
        # Обновляем существующий график
        db.execute_query("""
            UPDATE master_work_schedule 
            SET start_time = ?, end_time = ?
            WHERE id = ?
        """, (schedule_data.start_time, schedule_data.end_time, existing["id"]))
        
        schedule_id = existing["id"]
    else:
        # Создаем новый график
        schedule_id = db.insert_and_get_id("""
            INSERT INTO master_work_schedule (master_id, day_of_week, start_time, end_time)
            VALUES (?, ?, ?, ?)
        """, (master_id, schedule_data.day_of_week, 
              schedule_data.start_time, schedule_data.end_time))
    
    # Получаем созданный/обновленный график
    schedule = db.fetch_one("""
        SELECT * FROM master_work_schedule WHERE id = ?
    """, (schedule_id,))
    
    log_admin_action(
        current_user["id"], 
        "UPDATE_SCHEDULE", 
        f"Updated schedule for master {master_id}, day {schedule_data.day_of_week}"
    )
    
    return schedule

@router.delete("/masters/{master_id}/days/{day_of_week}")
async def remove_schedule_day(
    master_id: int,
    day_of_week: int,
    current_user: dict = Depends(get_current_admin)
):
    """
    Удаление графика на конкретный день
    """
    db.execute_query("""
        DELETE FROM master_work_schedule 
        WHERE master_id = ? AND day_of_week = ?
    """, (master_id, day_of_week))
    
    log_admin_action(
        current_user["id"], 
        "REMOVE_SCHEDULE_DAY", 
        f"Removed schedule for master {master_id}, day {day_of_week}"
    )
    
    return {"message": "Schedule day removed"}

@router.post("/masters/{master_id}/breaks")
async def add_break_slot(
    master_id: int,
    break_date: str,  # "2024-01-15"
    start_time: str,
    end_time: str,
    reason: str = "",
    current_user: dict = Depends(get_current_admin)
):
    """
    Добавление временного перерыва/закрытия
    (Для реализации потребуется дополнительная таблица master_breaks)
    """
    # В реальной реализации нужно создать таблицу master_breaks
    # Для демо: просто логируем действие
    log_admin_action(
        current_user["id"], 
        "ADD_BREAK", 
        f"Added break for master {master_id} on {break_date} {start_time}-{end_time}: {reason}"
    )
    
    return {"message": "Break added (not implemented in demo)"}