# routes/clients.py
from fastapi import APIRouter, Depends, HTTPException, Query, Form
from typing import Optional, List
from datetime import datetime
import sqlite3
import logging

logger = logging.getLogger(__name__)
router = APIRouter(tags=["clients"])

# Эндпоинты уже реализованы в main.py, поэтому этот файл может быть пустым
# или содержать дополнительные эндпоинты, которых нет в main.py

@router.get("/search")
async def search_clients(
    query: str = Query(..., min_length=2, description="Поисковый запрос"),
    limit: int = Query(10, ge=1, le=50, description="Лимит результатов")
):
    """Быстрый поиск клиентов по имени, фамилии или телефону"""
    logger.info(f"Search clients: {query}")
    
    try:
        conn = sqlite3.connect("salon.db")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        search_term = f"%{query}%"
        
        cursor.execute("""
            SELECT id, first_name, last_name, phone, email, created_at
            FROM users
            WHERE role = 'client' 
                AND (first_name LIKE ? OR last_name LIKE ? OR phone LIKE ? OR email LIKE ?)
            ORDER BY last_name, first_name
            LIMIT ?
        """, (search_term, search_term, search_term, search_term, limit))
        
        clients = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return {
            "success": True,
            "count": len(clients),
            "results": clients
        }
    
    except Exception as e:
        logger.error(f"Error searching clients: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка при поиске клиентов: {str(e)}")

@router.get("/{client_id}/stats")
async def get_client_stats(client_id: int):
    """Получение статистики клиента"""
    logger.info(f"Get client {client_id} stats")
    
    try:
        conn = sqlite3.connect("salon.db")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Проверяем существование клиента
        cursor.execute("""
            SELECT id, first_name, last_name 
            FROM users 
            WHERE id = ? AND role = 'client'
        """, (client_id,))
        
        client = cursor.fetchone()
        if not client:
            raise HTTPException(status_code=404, detail="Клиент не найден")
        
        # Получаем статистику по записям
        cursor.execute("""
            SELECT 
                COUNT(*) as total_appointments,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_appointments,
                SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END) as cancelled_appointments,
                SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending_appointments,
                SUM(CASE WHEN status = 'no_show' THEN 1 ELSE 0 END) as no_show_appointments
            FROM appointments
            WHERE client_id = ?
        """, (client_id,))
        
        appointment_stats = cursor.fetchone()
        
        # Получаем общую сумму потраченных средств
        cursor.execute("""
            SELECT COALESCE(SUM(s.price), 0) as total_spent
            FROM appointments a
            JOIN appointment_services aps ON a.id = aps.appointment_id
            JOIN services s ON aps.service_id = s.id
            WHERE a.client_id = ? AND a.status = 'completed'
        """, (client_id,))
        
        spending_stats = cursor.fetchone()
        
        # Получаем последнюю запись
        cursor.execute("""
            SELECT appointment_date, start_time, status
            FROM appointments
            WHERE client_id = ?
            ORDER BY appointment_date DESC, start_time DESC
            LIMIT 1
        """, (client_id,))
        
        last_appointment = cursor.fetchone()
        
        # Получаем статистику по отзывам
        cursor.execute("""
            SELECT 
                COUNT(*) as total_reviews,
                AVG(rating) as avg_rating
            FROM reviews
            WHERE client_id = ?
        """, (client_id,))
        
        review_stats = cursor.fetchone()
        
        conn.close()
        
        stats = {
            "client_id": client_id,
            "client_name": f"{client['first_name']} {client['last_name']}",
            "appointments": {
                "total": appointment_stats["total_appointments"] or 0,
                "completed": appointment_stats["completed_appointments"] or 0,
                "cancelled": appointment_stats["cancelled_appointments"] or 0,
                "pending": appointment_stats["pending_appointments"] or 0,
                "no_show": appointment_stats["no_show_appointments"] or 0
            },
            "spending": {
                "total": spending_stats["total_spent"] or 0,
                "average": round((spending_stats["total_spent"] or 0) / 
                               (appointment_stats["completed_appointments"] or 1))
                if (appointment_stats["completed_appointments"] or 0) > 0 else 0
            },
            "last_appointment": {
                "date": last_appointment["appointment_date"] if last_appointment else None,
                "time": last_appointment["start_time"] if last_appointment else None,
                "status": last_appointment["status"] if last_appointment else None
            },
            "reviews": {
                "total": review_stats["total_reviews"] or 0,
                "average_rating": round(review_stats["avg_rating"] or 0, 1)
            }
        }
        
        return stats
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting client stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка при получении статистики клиента: {str(e)}")

@router.get("/{client_id}/recent-appointments")
async def get_client_recent_appointments(
    client_id: int,
    limit: int = Query(5, ge=1, le=20, description="Количество последних записей")
):
    """Получение последних записей клиента"""
    logger.info(f"Get client {client_id} recent appointments")
    
    try:
        conn = sqlite3.connect("salon.db")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Проверяем существование клиента
        cursor.execute("SELECT id FROM users WHERE id = ? AND role = 'client'", (client_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Клиент не найден")
        
        cursor.execute("""
            SELECT a.*, 
                   u.first_name as master_first_name, u.last_name as master_last_name
            FROM appointments a
            LEFT JOIN masters m ON a.master_id = m.id
            LEFT JOIN users u ON m.user_id = u.id
            WHERE a.client_id = ?
            ORDER BY a.appointment_date DESC, a.start_time DESC
            LIMIT ?
        """, (client_id, limit))
        
        appointments = [dict(row) for row in cursor.fetchall()]
        
        # Добавляем услуги для каждой записи
        for appointment in appointments:
            cursor.execute("""
                SELECT s.id, st.title, s.duration_minutes, s.price
                FROM appointment_services aps
                JOIN services s ON aps.service_id = s.id
                LEFT JOIN service_translations st ON s.id = st.service_id AND st.language = 'ru'
                WHERE aps.appointment_id = ?
            """, (appointment["id"],))
            services = [dict(row) for row in cursor.fetchall()]
            appointment["services"] = services
        
        conn.close()
        
        return {
            "success": True,
            "count": len(appointments),
            "appointments": appointments
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting client appointments: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка при получении записей клиента: {str(e)}")

@router.put("/{client_id}")
async def update_client(
    client_id: int,
    first_name: Optional[str] = Form(None),
    last_name: Optional[str] = Form(None),
    phone: Optional[str] = Form(None),
    email: Optional[str] = Form(None)
):
    """Обновление информации о клиенте"""
    logger.info(f"Update client {client_id}")
    
    try:
        conn = sqlite3.connect("salon.db")
        cursor = conn.cursor()
        
        # Проверяем существование клиента
        cursor.execute("SELECT id FROM users WHERE id = ? AND role = 'client'", (client_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Клиент не найден")
        
        # Проверяем уникальность телефона если указан
        if phone:
            cursor.execute("SELECT id FROM users WHERE phone = ? AND id != ?", (phone, client_id))
            if cursor.fetchone():
                raise HTTPException(status_code=400, detail="Телефон уже используется другим пользователем")
        
        # Проверяем уникальность email если указан
        if email:
            cursor.execute("SELECT id FROM users WHERE email = ? AND id != ?", (email, client_id))
            if cursor.fetchone():
                raise HTTPException(status_code=400, detail="Email уже используется другим пользователем")
        
        # Формируем запрос на обновление
        update_fields = []
        params = []
        
        if first_name is not None:
            update_fields.append("first_name = ?")
            params.append(first_name)
        
        if last_name is not None:
            update_fields.append("last_name = ?")
            params.append(last_name)
        
        if phone is not None:
            update_fields.append("phone = ?")
            params.append(phone)
        
        if email is not None:
            update_fields.append("email = ?")
            params.append(email)
        
        if update_fields:
            params.append(client_id)
            cursor.execute(
                f"UPDATE users SET {', '.join(update_fields)} WHERE id = ?",
                tuple(params)
            )
        
        conn.commit()
        conn.close()
        
        logger.info(f"Client {client_id} updated successfully")
        
        return {
            "success": True,
            "message": "Информация о клиенте успешно обновлена"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating client: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка при обновлении клиента: {str(e)}")

@router.delete("/{client_id}")
async def delete_client(client_id: int):
    """Удаление клиента"""
    logger.info(f"Delete client {client_id} request")
    
    try:
        conn = sqlite3.connect("salon.db")
        cursor = conn.cursor()
        
        # Проверяем существование клиента
        cursor.execute("SELECT id FROM users WHERE id = ? AND role = 'client'", (client_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Клиент не найден")
        
        # Проверяем, есть ли у клиента записи
        cursor.execute("SELECT id FROM appointments WHERE client_id = ? LIMIT 1", (client_id,))
        if cursor.fetchone():
            raise HTTPException(
                status_code=400, 
                detail="Невозможно удалить клиента, у которого есть записи. "
                       "Сначала удалите или отмените все записи клиента."
            )
        
        # Проверяем, есть ли у клиента отзывы
        cursor.execute("SELECT id FROM reviews WHERE client_id = ? LIMIT 1", (client_id,))
        if cursor.fetchone():
            raise HTTPException(
                status_code=400, 
                detail="Невозможно удалить клиента, у которого есть отзывы. "
                       "Сначала удалите все отзывы клиента."
            )
        
        # Проверяем, есть ли у клиента бонусы
        cursor.execute("SELECT id FROM bonuses WHERE client_id = ? LIMIT 1", (client_id,))
        if cursor.fetchone():
            raise HTTPException(
                status_code=400, 
                detail="Невозможно удалить клиента, у которого есть бонусы. "
                       "Сначала обнулите бонусный счет клиента."
            )
        
        # Удаляем клиента
        cursor.execute("DELETE FROM users WHERE id = ?", (client_id,))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Client {client_id} deleted successfully")
        
        return {
            "success": True,
            "message": "Клиент успешно удален"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting client: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка при удалении клиента: {str(e)}")

@router.get("/{client_id}/appointments/{appointment_id}/services")
async def get_client_appointment_services(
    client_id: int,
    appointment_id: int
):
    """Получение услуг конкретной записи клиента"""
    logger.info(f"Get appointment {appointment_id} services for client {client_id}")
    
    try:
        conn = sqlite3.connect("salon.db")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Проверяем, принадлежит ли запись клиенту
        cursor.execute("""
            SELECT id FROM appointments 
            WHERE id = ? AND client_id = ?
        """, (appointment_id, client_id))
        
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Запись не найдена или не принадлежит клиенту")
        
        # Получаем услуги записи
        cursor.execute("""
            SELECT s.id, st.title, s.duration_minutes, s.price, s.is_active
            FROM appointment_services aps
            JOIN services s ON aps.service_id = s.id
            LEFT JOIN service_translations st ON s.id = st.service_id AND st.language = 'ru'
            WHERE aps.appointment_id = ?
            ORDER BY st.title
        """, (appointment_id,))
        
        services = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return {
            "success": True,
            "appointment_id": appointment_id,
            "client_id": client_id,
            "services": services,
            "total": len(services),
            "total_price": sum(service["price"] for service in services)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting appointment services: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка при получении услуг записи: {str(e)}")