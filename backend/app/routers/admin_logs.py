from fastapi import APIRouter, Depends, Query
from typing import Optional  # Добавьте этот импорт!
from app.auth import get_current_admin
from app.database import db
from app.models import PaginatedResponse
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin-logs", tags=["admin logs"])

@router.get("/", response_model=PaginatedResponse)
async def get_admin_logs(
    current_user: dict = Depends(get_current_admin),
    admin_id: Optional[int] = None,
    action: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100)
):
    """
    Получение логов действий администраторов
    """
    offset = (page - 1) * per_page
    
    query = """
        SELECT al.*, u.first_name, u.last_name
        FROM admin_logs al
        JOIN users u ON al.admin_id = u.id
        WHERE 1=1
    """
    count_query = "SELECT COUNT(*) as count FROM admin_logs al JOIN users u ON al.admin_id = u.id WHERE 1=1"
    params = []
    
    if admin_id:
        query += " AND al.admin_id = ?"
        count_query += " AND al.admin_id = ?"
        params.append(admin_id)
    
    if action:
        query += " AND al.action LIKE ?"
        count_query += " AND al.action LIKE ?"
        params.append(f"%{action}%")
    
    if start_date:
        query += " AND DATE(al.created_at) >= ?"
        count_query += " AND DATE(al.created_at) >= ?"
        params.append(start_date)
    
    if end_date:
        query += " AND DATE(al.created_at) <= ?"
        count_query += " AND DATE(al.created_at) <= ?"
        params.append(end_date)
    
    query += " ORDER BY al.created_at DESC LIMIT ? OFFSET ?"
    params.extend([per_page, offset])
    
    logs = db.fetch_all(query, tuple(params))
    
    # Общее количество
    count_result = db.fetch_one(count_query, tuple(params[:len(params)-2] if len(params) > 2 else ()))
    total = count_result["count"] if count_result else 0
    
    return {
        "items": logs,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page
    }