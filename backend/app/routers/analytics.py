# backend/app/routers/analytics.py
from fastapi import APIRouter, Depends, Query
from app.auth import get_current_admin
import logging
from datetime import date, timedelta
import sqlite3
from typing import Dict, Any

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analytics", tags=["analytics"])

def get_db_connection():
    """Создание соединения с БД"""
    conn = sqlite3.connect("salon.db")
    conn.row_factory = sqlite3.Row
    return conn

@router.get("/dashboard")
async def get_dashboard_stats(
    current_user: dict = Depends(get_current_admin),
    period_days: int = Query(30, ge=1, le=365)
):
    """
    Получение статистики для дашборда (реальные данные из БД)
    """
    logger.info(f"✅ Dashboard request from user {current_user['id']}")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Рассчитываем дату начала периода
        start_date = date.today() - timedelta(days=period_days)
        
        # 1. Статистика по записям
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
                SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END) as cancelled
            FROM appointments
            WHERE appointment_date >= ?
        """, (start_date.isoformat(),))
        
        appointment_stats = cursor.fetchone()
        
        # 2. Статистика по клиентам
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT client_id) as total_clients
            FROM appointments
            WHERE appointment_date >= ?
        """, (start_date.isoformat(),))
        
        total_clients_result = cursor.fetchone()
        total_clients = total_clients_result[0] if total_clients_result else 0
        
        # Новые клиенты (которые записались впервые в этот период)
        cursor.execute("""
            SELECT COUNT(DISTINCT client_id) as new_clients
            FROM appointments a
            WHERE appointment_date >= ?
            AND NOT EXISTS (
                SELECT 1 FROM appointments a2 
                WHERE a2.client_id = a.client_id 
                AND a2.appointment_date < ?
            )
        """, (start_date.isoformat(), start_date.isoformat()))
        
        new_clients_result = cursor.fetchone()
        new_clients = new_clients_result[0] if new_clients_result else 0
        
        # 3. Активные мастера
        cursor.execute("""
            SELECT COUNT(DISTINCT m.id) as active_masters
            FROM masters m
            JOIN appointments a ON m.id = a.master_id
            WHERE a.appointment_date >= ?
            AND m.is_active = 1
        """, (start_date.isoformat(),))
        
        active_masters_result = cursor.fetchone()
        active_masters = active_masters_result[0] if active_masters_result else 0
        
        # 4. Общая выручка
        cursor.execute("""
            SELECT COALESCE(SUM(s.price), 0) as total_revenue
            FROM appointments a
            JOIN appointment_services aps ON a.id = aps.appointment_id
            JOIN services s ON aps.service_id = s.id
            WHERE a.appointment_date >= ? 
            AND a.status = 'completed'
        """, (start_date.isoformat(),))
        
        revenue_result = cursor.fetchone()
        total_revenue = revenue_result[0] if revenue_result else 0
        
        # 5. Выручка за сегодня
        today = date.today()
        cursor.execute("""
            SELECT COALESCE(SUM(s.price), 0) as today_revenue
            FROM appointments a
            JOIN appointment_services aps ON a.id = aps.appointment_id
            JOIN services s ON aps.service_id = s.id
            WHERE a.appointment_date = ? 
            AND a.status = 'completed'
        """, (today.isoformat(),))
        
        today_revenue_result = cursor.fetchone()
        today_revenue = today_revenue_result[0] if today_revenue_result else 0
        
        conn.close()
        
        return {
            "success": True,
            "user_id": current_user["id"],
            "period_days": period_days,
            "appointments": {
                "total": appointment_stats[0] if appointment_stats else 0,
                "completed": appointment_stats[1] if appointment_stats else 0,
                "pending": appointment_stats[2] if appointment_stats else 0,
                "cancelled": appointment_stats[3] if appointment_stats else 0
            },
            "clients": {
                "total": total_clients,
                "new": new_clients
            },
            "masters": {
                "active": active_masters
            },
            "revenue": {
                "total": total_revenue,
                "today": today_revenue,
                "change": 12.5  # TODO: Рассчитать реальный процент изменения
            }
        }
        
    except Exception as e:
        logger.error(f"Error fetching dashboard stats: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "appointments": {"total": 0, "completed": 0, "pending": 0, "cancelled": 0},
            "clients": {"total": 0, "new": 0},
            "masters": {"active": 0},
            "revenue": {"total": 0, "today": 0, "change": 0}
        }

@router.get("/masters-load")
async def get_masters_load(
    current_user: dict = Depends(get_current_admin),
    days: int = Query(7, ge=1, le=30)
):
    """
    Получение загрузки мастеров (реальные данные из БД)
    """
    logger.info(f"✅ Masters load request from user {current_user['id']}")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Рассчитываем дату начала периода
        start_date = date.today() - timedelta(days=days)
        
        # Получаем загрузку мастеров по количеству записей
        cursor.execute("""
            SELECT 
                u.first_name || ' ' || u.last_name as master_name,
                COUNT(a.id) as appointment_count,
                SUM(CASE WHEN a.status = 'completed' THEN 1 ELSE 0 END) as completed_count
            FROM masters m
            JOIN users u ON m.user_id = u.id
            LEFT JOIN appointments a ON m.id = a.master_id AND a.appointment_date >= ?
            WHERE m.is_active = 1
            GROUP BY m.id, u.first_name, u.last_name
            ORDER BY appointment_count DESC
        """, (start_date.isoformat(),))
        
        masters_data = cursor.fetchall()
        
        # Рассчитываем процент загрузки (условный, на основе количества записей)
        masters = []
        if masters_data:
            # Находим максимальное количество записей для расчета процентов
            max_appointments = max(row[1] for row in masters_data) if masters_data else 1
            
            for row in masters_data:
                master_name = row[0] or "Без имени"
                appointment_count = row[1] or 0
                completed_count = row[2] or 0
                
                # Расчет загрузки в процентах (0-100)
                if max_appointments > 0:
                    load_percent = min(100, int((appointment_count / max_appointments) * 100))
                else:
                    load_percent = 0
                
                masters.append({
                    "name": master_name,
                    "load": load_percent,
                    "appointment_count": appointment_count,
                    "completed_count": completed_count
                })
        
        conn.close()
        
        return {
            "success": True,
            "days": days,
            "masters": masters
        }
        
    except Exception as e:
        logger.error(f"Error fetching masters load: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "days": days,
            "masters": []
        }

@router.get("/services-popularity")
async def get_services_popularity(
    current_user: dict = Depends(get_current_admin),
    period_days: int = Query(30, ge=1, le=365)
):
    """
    Получение популярности услуг (реальные данные из БД)
    """
    logger.info(f"✅ Services popularity request from user {current_user['id']}")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        start_date = date.today() - timedelta(days=period_days)
        
        cursor.execute("""
            SELECT 
                st.title as service_title,
                COUNT(aps.service_id) as service_count,
                COALESCE(SUM(s.price), 0) as revenue
            FROM appointment_services aps
            JOIN appointments a ON aps.appointment_id = a.id
            JOIN services s ON aps.service_id = s.id
            LEFT JOIN service_translations st ON s.id = st.service_id AND st.language = 'ru'
            WHERE a.appointment_date >= ? AND a.status = 'completed'
            GROUP BY aps.service_id, st.title
            ORDER BY service_count DESC
            LIMIT 10
        """, (start_date.isoformat(),))
        
        services = []
        for row in cursor.fetchall():
            services.append({
                "title": row[0] or f"Услуга #{row[0]}",
                "service_count": row[1],
                "revenue": row[2]
            })
        
        conn.close()
        
        return {
            "success": True,
            "period_days": period_days,
            "services": services
        }
        
    except Exception as e:
        logger.error(f"Error fetching services popularity: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "period_days": period_days,
            "services": []
        }

@router.get("/recent-appointments")
async def get_recent_appointments(
    current_user: dict = Depends(get_current_admin),
    limit: int = Query(10, ge=1, le=50)
):
    """
    Получение последних записей
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                a.id,
                a.appointment_date,
                a.start_time,
                a.status,
                u1.first_name as client_first_name,
                u1.last_name as client_last_name,
                u2.first_name as master_first_name,
                u2.last_name as master_last_name,
                (SELECT GROUP_CONCAT(st.title, ', ')
                 FROM appointment_services aps2
                 JOIN services s2 ON aps2.service_id = s2.id
                 LEFT JOIN service_translations st ON s2.id = st.service_id AND st.language = 'ru'
                 WHERE aps2.appointment_id = a.id) as services
            FROM appointments a
            JOIN users u1 ON a.client_id = u1.id
            LEFT JOIN masters m ON a.master_id = m.id
            LEFT JOIN users u2 ON m.user_id = u2.id
            ORDER BY a.appointment_date DESC, a.start_time DESC
            LIMIT ?
        """, (limit,))
        
        appointments = []
        for row in cursor.fetchall():
            appointments.append({
                "id": row[0],
                "date": row[1],
                "time": row[2],
                "status": row[3],
                "client_name": f"{row[4]} {row[5]}" if row[5] else row[4],
                "master_name": f"{row[6]} {row[7]}" if row[6] else "Не назначен",
                "services": row[8] or "Не указаны"
            })
        
        conn.close()
        
        return {
            "success": True,
            "appointments": appointments
        }
        
    except Exception as e:
        logger.error(f"Error fetching recent appointments: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "appointments": []
        }

@router.get("/test")
async def test_endpoint(current_user: dict = Depends(get_current_admin)):
    """
    Простой тестовый endpoint для проверки авторизации
    """
    return {
        "success": True,
        "message": "Аналитика работает!",
        "user_id": current_user["id"],
        "timestamp": date.today().isoformat()
    }