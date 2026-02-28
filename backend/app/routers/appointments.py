#routers/apointments.py
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from datetime import date, datetime
from app.auth import get_current_admin, log_admin_action
from app.database import db
from app.models import AppointmentCreate, AppointmentUpdate, PaginatedResponse
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/appointments", tags=["appointments"])

@router.get("/", response_model=PaginatedResponse)
async def get_appointments(
    current_user: dict = Depends(get_current_admin),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    master_id: Optional[int] = None,
    client_id: Optional[int] = None,
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100)
):
    """
    Получение списка записей с фильтрацией
    """
    offset = (page - 1) * per_page
    
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
    
    appointments = db.fetch_all(query, tuple(params))
    
    # Добавляем услуги для каждой записи
    for appointment in appointments:
        services = db.fetch_all("""
            SELECT s.id, st.title, s.duration_minutes, s.price
            FROM appointment_services aps
            JOIN services s ON aps.service_id = s.id
            LEFT JOIN service_translations st ON s.id = st.service_id AND st.language = 'ru'
            WHERE aps.appointment_id = ?
        """, (appointment["id"],))
        appointment["services"] = services
    
    # Общее количество
    count_result = db.fetch_one(count_query, tuple(count_params))
    total = count_result["count"] if count_result else 0
    
    return {
        "items": appointments,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page
    }

@router.post("/")
async def create_appointment(
    appointment_data: AppointmentCreate,
    current_user: dict = Depends(get_current_admin)
):
    """
    Создание новой записи
    """
    # Рассчитываем время окончания на основе услуг
    total_duration = 0
    for service_id in appointment_data.services:
        service = db.fetch_one("SELECT duration_minutes FROM services WHERE id = ?", (service_id,))
        if service:
            total_duration += service["duration_minutes"]
    
    # Преобразуем время окончания
    start_datetime = datetime.strptime(appointment_data.start_time, "%H:%M")
    end_datetime = start_datetime.replace(minute=start_datetime.minute + total_duration)
    end_time = end_datetime.strftime("%H:%M")
    
    # Создаем запись
    appointment_id = db.insert_and_get_id("""
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
    
    # Добавляем услуги
    for service_id in appointment_data.services:
        db.execute_query("""
            INSERT INTO appointment_services (appointment_id, service_id)
            VALUES (?, ?)
        """, (appointment_id, service_id))
    
    log_admin_action(
        current_user["id"], 
        "CREATE_APPOINTMENT", 
        f"Created appointment {appointment_id} for client {appointment_data.client_id}"
    )
    
    return {"id": appointment_id, "message": "Appointment created"}

@router.put("/{appointment_id}")
async def update_appointment(
    appointment_id: int,
    appointment_data: AppointmentUpdate,
    current_user: dict = Depends(get_current_admin)
):
    """
    Обновление записи
    """
    # Проверяем существование записи
    appointment = db.fetch_one("SELECT * FROM appointments WHERE id = ?", (appointment_id,))
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    update_fields = []
    params = []
    
    for field, value in appointment_data.dict(exclude_unset=True).items():
        if value is not None:
            update_fields.append(f"{field} = ?")
            params.append(value)
    
    if update_fields:
        params.append(appointment_id)
        db.execute_query(
            f"UPDATE appointments SET {', '.join(update_fields)} WHERE id = ?",
            tuple(params)
        )
    
    log_admin_action(current_user["id"], "UPDATE_APPOINTMENT", f"Updated appointment {appointment_id}")
    
    return {"message": "Appointment updated"}

@router.put("/{appointment_id}/status")
async def update_appointment_status(
    appointment_id: int,
    status: str,
    current_user: dict = Depends(get_current_admin)
):
    """
    Обновление статуса записи
    """
    valid_statuses = ["pending", "confirmed", "cancelled", "completed", "no_show"]
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")
    
    db.execute_query(
        "UPDATE appointments SET status = ? WHERE id = ?",
        (status, appointment_id)
    )
    
    log_admin_action(
        current_user["id"], 
        "UPDATE_APPOINTMENT_STATUS", 
        f"Updated appointment {appointment_id} status to {status}"
    )
    
    return {"message": "Status updated"}