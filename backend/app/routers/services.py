# backend/app/routers/services.py
from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import List, Optional
from app.auth import get_current_admin, log_admin_action
from app.database import db
from pydantic import BaseModel, validator, Field
from typing import Optional as Opt
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/services", tags=["services"])

# Модели Pydantic
class TranslationBase(BaseModel):
    language: str = Field(..., min_length=2, max_length=2)
    title: str = Field(..., min_length=1, max_length=255)
    description: Opt[str] = Field(None, max_length=1000)

class CategoryCreate(BaseModel):
    parent_id: Opt[int] = Field(None, description="ID родительской категории. None для корневой категории.")
    is_active: bool = Field(True, description="Активна ли категория")
    translations: List[TranslationBase] = Field(..., min_items=1, description="Переводы названия категории")
    
    @validator('translations')
    def validate_languages(cls, v):
        languages = [t.language for t in v]
        if len(set(languages)) != len(languages):
            raise ValueError('Duplicate languages in translations')
        return v

class CategoryUpdate(BaseModel):
    parent_id: Opt[int] = Field(None, description="ID родительской категории")
    is_active: Opt[bool] = Field(None, description="Активна ли категория")
    translations: Opt[List[TranslationBase]] = Field(None, description="Обновленные переводы")

class CategoryResponse(BaseModel):
    id: int
    parent_id: Opt[int] = None
    is_active: bool
    title: Opt[str] = None
    children: Opt[List['CategoryResponse']] = None
    has_children: bool = False
    service_count: int = 0

CategoryResponse.update_forward_refs()

class CategoryTreeResponse(BaseModel):
    id: int
    parent_id: Opt[int] = None
    is_active: bool
    title: Opt[str] = None
    value: int
    label: str
    is_leaf: bool = False
    children: Opt[List['CategoryTreeResponse']] = None

CategoryTreeResponse.update_forward_refs()

class ServiceCreate(BaseModel):
    category_id: int = Field(..., gt=0, description="ID категории услуги")
    duration_minutes: int = Field(..., gt=0, le=1440, description="Длительность в минутах")
    price: float = Field(..., ge=0, description="Цена услуги")
    is_active: bool = Field(True, description="Активна ли услуга")
    translations: List[TranslationBase] = Field(..., min_items=1, description="Переводы услуги")
    
    @validator('translations')
    def validate_service_languages(cls, v):
        languages = [t.language for t in v]
        if len(set(languages)) != len(languages):
            raise ValueError('Duplicate languages in translations')
        # Проверяем обязательность title для каждой локали
        for translation in v:
            if not translation.title.strip():
                raise ValueError(f'Title is required for language {translation.language}')
        return v

class ServiceUpdate(BaseModel):
    category_id: Opt[int] = Field(None, gt=0)
    duration_minutes: Opt[int] = Field(None, gt=0, le=1440)
    price: Opt[float] = Field(None, ge=0)
    is_active: Opt[bool] = None
    translations: Opt[List[TranslationBase]] = None
    
    @validator('translations')
    def validate_update_languages(cls, v):
        if v is not None:
            languages = [t.language for t in v]
            if len(set(languages)) != len(languages):
                raise ValueError('Duplicate languages in translations')
        return v

class ServiceResponse(BaseModel):
    id: int
    category_id: int
    duration_minutes: int
    price: float
    is_active: bool
    title: Opt[str] = None
    description: Opt[str] = None
    category_title: Opt[str] = None
    category_path: Opt[str] = None

class ServiceWithDetailsResponse(BaseModel):
    id: int
    category_id: int
    duration_minutes: int
    price: float
    is_active: bool
    translations: List[TranslationBase]
    category_title: Opt[str] = None
    category_path: Opt[str] = None

class PaginatedResponse(BaseModel):
    items: List
    total: int
    page: int
    per_page: int
    total_pages: int

class CategoryStatsResponse(BaseModel):
    category_id: int
    title: str
    service_count: int
    subcategory_count: int

# Категории услуг
@router.get("/categories", response_model=List[CategoryResponse])
async def get_categories(
    current_user: dict = Depends(get_current_admin),
    is_active: Optional[bool] = None,
    language: str = "ru",
    include_children: bool = Query(True, description="Включать ли подкатегории")
):
    """
    Получение категорий услуг с переводами в древовидной структуре
    """
    logger.info(f"Get categories request from user {current_user['id']}")
    
    try:
        query = """
            SELECT sc.*, sct.title,
                   (SELECT COUNT(*) FROM service_categories sc2 WHERE sc2.parent_id = sc.id) as child_count,
                   (SELECT COUNT(*) FROM services s WHERE s.category_id = sc.id AND s.is_active = 1) as service_count
            FROM service_categories sc
            LEFT JOIN service_category_translations sct 
                ON sc.id = sct.category_id AND sct.language = ?
            WHERE 1=1
        """
        params = [language]
        
        if is_active is not None:
            query += " AND sc.is_active = ?"
            params.append(int(is_active))
        
        query += " ORDER BY sc.parent_id NULLS FIRST, sc.id"
        
        categories = db.fetch_all(query, tuple(params))
        
        # Формируем древовидную структуру
        def build_tree(parent_id=None):
            tree = []
            for cat in categories:
                if cat.get("parent_id") == parent_id:
                    children = []
                    if include_children and cat.get("child_count", 0) > 0:
                        children = build_tree(cat["id"])
                    
                    category_response = {
                        "id": cat["id"],
                        "parent_id": cat.get("parent_id"),
                        "is_active": bool(cat.get("is_active", 1)),
                        "title": cat.get("title"),
                        "has_children": cat.get("child_count", 0) > 0,
                        "service_count": cat.get("service_count", 0)
                    }
                    
                    if children:
                        category_response["children"] = children
                    
                    tree.append(category_response)
            return tree
        
        result = build_tree()
        logger.info(f"Found {len(result)} root categories with tree structure")
        return result
    
    except Exception as e:
        logger.error(f"Error fetching categories: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при загрузке категорий: {str(e)}"
        )

@router.get("/categories/tree", response_model=List[CategoryTreeResponse])
async def get_categories_tree(
    current_user: dict = Depends(get_current_admin),
    language: str = "ru",
    include_inactive: bool = Query(False, description="Включать неактивные категории")
):
    """
    Получение категорий в формате дерева для TreeSelect компонентов
    """
    logger.info(f"Get categories tree request from user {current_user['id']}")
    
    try:
        query = """
            SELECT sc.*, sct.title,
                   (SELECT COUNT(*) FROM service_categories sc2 WHERE sc2.parent_id = sc.id) as child_count
            FROM service_categories sc
            LEFT JOIN service_category_translations sct 
                ON sc.id = sct.category_id AND sct.language = ?
            WHERE 1=1
        """
        params = [language]
        
        if not include_inactive:
            query += " AND sc.is_active = 1"
        
        query += " ORDER BY sc.parent_id NULLS FIRST, sc.id"
        
        categories = db.fetch_all(query, tuple(params))
        
        # Формируем плоский список для древовидного выбора
        def build_tree_select_data(items, parent_id=None, level=0, prefix=""):
            tree_data = []
            for item in items:
                if item.get("parent_id") == parent_id:
                    title = item.get("title", f"Категория #{item['id']}")
                    full_title = f"{prefix}{title}" if prefix else title
                    
                    node = {
                        "id": item["id"],
                        "parent_id": item.get("parent_id"),
                        "is_active": bool(item.get("is_active", 1)),
                        "title": title,
                        "value": item["id"],
                        "label": full_title,
                        "is_leaf": item.get("child_count", 0) == 0,
                    }
                    
                    # Рекурсивно добавляем детей
                    children = build_tree_select_data(
                        items, 
                        item["id"], 
                        level + 1, 
                        f"{full_title} / "
                    )
                    if children:
                        node["children"] = children
                        node["is_leaf"] = False
                    
                    tree_data.append(node)
            return tree_data
        
        result = build_tree_select_data(categories)
        logger.info(f"Generated tree with {len(result)} root nodes")
        return result
    
    except Exception as e:
        logger.error(f"Error fetching categories tree: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при построении дерева категорий: {str(e)}"
        )

@router.get("/categories/{category_id}", response_model=CategoryResponse)
async def get_category(
    category_id: int,
    current_user: dict = Depends(get_current_admin),
    language: str = "ru"
):
    """
    Получение информации о конкретной категории
    """
    logger.info(f"Get category {category_id} request from user {current_user['id']}")
    
    try:
        category = db.fetch_one("""
            SELECT sc.*, sct.title,
                   (SELECT COUNT(*) FROM service_categories sc2 WHERE sc2.parent_id = sc.id) as child_count,
                   (SELECT COUNT(*) FROM services s WHERE s.category_id = sc.id AND s.is_active = 1) as service_count
            FROM service_categories sc
            LEFT JOIN service_category_translations sct 
                ON sc.id = sct.category_id AND sct.language = ?
            WHERE sc.id = ?
        """, (language, category_id))
        
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Категория не найдена"
            )
        
        return {
            "id": category["id"],
            "parent_id": category.get("parent_id"),
            "is_active": bool(category.get("is_active", 1)),
            "title": category.get("title"),
            "has_children": category.get("child_count", 0) > 0,
            "service_count": category.get("service_count", 0)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching category: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при загрузке категории: {str(e)}"
        )

@router.post("/categories", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_category(
    category_data: CategoryCreate,
    current_user: dict = Depends(get_current_admin)
):
    """
    Создание новой категории услуг
    """
    logger.info(f"Create category request from user {current_user['id']}")
    
    try:
        # Проверяем parent_id если указан
        if category_data.parent_id is not None:
            parent_category = db.fetch_one(
                "SELECT id, is_active FROM service_categories WHERE id = ?",
                (category_data.parent_id,)
            )
            if not parent_category:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Родительская категория не найдена"
                )
            if not bool(parent_category.get("is_active", 1)):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Родительская категория неактивна"
                )
        
        # Проверяем наличие переводов для всех обязательных языков
        required_languages = ["ru", "en", "tr"]
        translation_languages = {t.language for t in category_data.translations}
        
        # Создаем категорию
        category_id = db.insert_and_get_id("""
            INSERT INTO service_categories (parent_id, is_active)
            VALUES (?, ?)
        """, (category_data.parent_id, int(category_data.is_active)))
        
        if not category_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Не удалось создать категорию"
            )
        
        # Добавляем переводы
        for translation in category_data.translations:
            db.execute_query("""
                INSERT INTO service_category_translations (category_id, language, title)
                VALUES (?, ?, ?)
            """, (category_id, translation.language, translation.title))
        
        log_admin_action(
            current_user["id"], 
            "CREATE_CATEGORY", 
            f"Created category {category_id} with parent {category_data.parent_id}"
        )
        
        logger.info(f"Category {category_id} created successfully")
        return {
            "id": category_id, 
            "message": "Категория успешно создана",
            "has_children": False,
            "service_count": 0
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating category: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при создании категории: {str(e)}"
        )

@router.put("/categories/{category_id}", response_model=dict)
async def update_category(
    category_id: int,
    category_data: CategoryUpdate,
    current_user: dict = Depends(get_current_admin)
):
    """
    Обновление категории услуг
    """
    logger.info(f"Update category {category_id} request from user {current_user['id']}")
    
    try:
        # Проверяем существование категории
        existing_category = db.fetch_one(
            "SELECT * FROM service_categories WHERE id = ?", 
            (category_id,)
        )
        if not existing_category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Категория не найдена"
            )
        
        # Проверяем parent_id если указан
        if category_data.parent_id is not None:
            if category_data.parent_id == category_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Категория не может быть родителем самой себя"
                )
            
            # Проверяем существование родительской категории
            parent_category = db.fetch_one(
                "SELECT id, is_active FROM service_categories WHERE id = ?",
                (category_data.parent_id,)
            )
            if not parent_category:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Родительская категория не найдена"
                )
            
            # Проверяем циклические зависимости
            def check_circular_dependency(parent_id, child_id):
                current_parent = parent_id
                visited = set()
                while current_parent is not None:
                    if current_parent == child_id:
                        return True
                    if current_parent in visited:
                        break
                    visited.add(current_parent)
                    parent = db.fetch_one(
                        "SELECT parent_id FROM service_categories WHERE id = ?",
                        (current_parent,)
                    )
                    current_parent = parent["parent_id"] if parent else None
                return False
            
            if check_circular_dependency(category_data.parent_id, category_id):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Обнаружена циклическая зависимость в иерархии категорий"
                )
        
        # Обновляем основную информацию
        update_fields = []
        params = []
        
        if category_data.parent_id is not None:
            update_fields.append("parent_id = ?")
            params.append(category_data.parent_id)
        
        if category_data.is_active is not None:
            update_fields.append("is_active = ?")
            params.append(int(category_data.is_active))
        
        if update_fields:
            params.append(category_id)
            db.execute_query(
                f"UPDATE service_categories SET {', '.join(update_fields)} WHERE id = ?",
                tuple(params)
            )
        
        # Обновляем переводы
        if category_data.translations:
            for translation in category_data.translations:
                existing_translation = db.fetch_one("""
                    SELECT id FROM service_category_translations 
                    WHERE category_id = ? AND language = ?
                """, (category_id, translation.language))
                
                if existing_translation:
                    db.execute_query("""
                        UPDATE service_category_translations 
                        SET title = ?
                        WHERE id = ?
                    """, (translation.title, existing_translation["id"]))
                else:
                    db.execute_query("""
                        INSERT INTO service_category_translations (category_id, language, title)
                        VALUES (?, ?, ?)
                    """, (category_id, translation.language, translation.title))
        
        log_admin_action(
            current_user["id"], 
            "UPDATE_CATEGORY", 
            f"Updated category {category_id}"
        )
        
        logger.info(f"Category {category_id} updated successfully")
        return {"message": "Категория успешно обновлена"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating category: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при обновлении категории: {str(e)}"
        )

@router.delete("/categories/{category_id}", response_model=dict)
async def delete_category(
    category_id: int,
    current_user: dict = Depends(get_current_admin)
):
    """
    Удаление категории услуг (только если нет подкатегорий и услуг)
    """
    logger.info(f"Delete category {category_id} request from user {current_user['id']}")
    
    try:
        # Проверяем существование категории
        existing_category = db.fetch_one(
            "SELECT * FROM service_categories WHERE id = ?", 
            (category_id,)
        )
        if not existing_category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Категория не найдена"
            )
        
        # Проверяем наличие подкатегорий
        child_categories = db.fetch_all(
            "SELECT id, title FROM service_categories WHERE parent_id = ?", 
            (category_id,)
        )
        
        if child_categories:
            child_titles = [c["title"] or f"Категория #{c['id']}" for c in child_categories]
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Невозможно удалить категорию, так как у неё есть подкатегории: {', '.join(child_titles[:3])}"
                + ("..." if len(child_titles) > 3 else "")
            )
        
        # Проверяем наличие услуг в категории
        services_in_category = db.fetch_all(
            "SELECT id FROM services WHERE category_id = ? AND is_active = 1", 
            (category_id,)
        )
        
        if services_in_category:
            service_ids = [s["id"] for s in services_in_category]
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Невозможно удалить категорию, так как в ней есть активные услуги (ID: {', '.join(map(str, service_ids[:5]))})"
                + ("..." if len(service_ids) > 5 else "")
            )
        
        # Удаляем переводы
        db.execute_query(
            "DELETE FROM service_category_translations WHERE category_id = ?", 
            (category_id,)
        )
        
        # Удаляем категорию
        rows_affected = db.execute_query(
            "DELETE FROM service_categories WHERE id = ?", 
            (category_id,)
        )
        
        if rows_affected == 0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Не удалось удалить категорию"
            )
        
        log_admin_action(
            current_user["id"], 
            "DELETE_CATEGORY", 
            f"Deleted category {category_id}"
        )
        
        logger.info(f"Category {category_id} deleted successfully")
        return {"message": "Категория успешно удалена"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting category: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при удалении категории: {str(e)}"
        )

@router.get("/categories/{category_id}/stats", response_model=CategoryStatsResponse)
async def get_category_stats(
    category_id: int,
    current_user: dict = Depends(get_current_admin),
    language: str = "ru"
):
    """
    Получение статистики по категории
    """
    logger.info(f"Get category stats for {category_id} from user {current_user['id']}")
    
    try:
        category = db.fetch_one("""
            SELECT sc.id, sct.title,
                   (SELECT COUNT(*) FROM service_categories sc2 WHERE sc2.parent_id = sc.id) as subcategory_count,
                   (SELECT COUNT(*) FROM services s WHERE s.category_id = sc.id AND s.is_active = 1) as service_count
            FROM service_categories sc
            LEFT JOIN service_category_translations sct 
                ON sc.id = sct.category_id AND sct.language = ?
            WHERE sc.id = ?
        """, (language, category_id))
        
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Категория не найдена"
            )
        
        return {
            "category_id": category["id"],
            "title": category.get("title", f"Категория #{category['id']}"),
            "service_count": category.get("service_count", 0),
            "subcategory_count": category.get("subcategory_count", 0)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching category stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при получении статистики категории: {str(e)}"
        )

# Услуги
@router.get("", response_model=PaginatedResponse)
async def get_services(
    current_user: dict = Depends(get_current_admin),
    category_id: Optional[int] = Query(None, description="ID категории для фильтрации"),
    is_active: Optional[bool] = Query(None, description="Фильтр по активности"),
    language: str = Query("ru", description="Язык переводов"),
    page: int = Query(1, ge=1, description="Номер страницы"),
    per_page: int = Query(20, ge=1, le=100, description="Количество на странице"),
    search: Optional[str] = Query(None, description="Поиск по названию и описанию")
):
    """
    Получение услуг с фильтрацией и пагинацией
    """
    logger.info(f"Get services request from user {current_user['id']}")
    
    offset = (page - 1) * per_page
    
    try:
        # Основной запрос для получения услуг
        query = """
            SELECT s.*, st.title, st.description, 
                   sct.title as category_title,
                   (SELECT GROUP_CONCAT(pct.title, ' / ') 
                    FROM service_categories sc2
                    LEFT JOIN service_category_translations pct 
                        ON sc2.id = pct.category_id AND pct.language = ?
                    WHERE sc2.id = sc.id 
                    START WITH sc2.id = s.category_id
                    CONNECT BY PRIOR sc2.parent_id = sc2.id
                    ORDER BY LEVEL DESC) as category_path
            FROM services s
            LEFT JOIN service_translations st 
                ON s.id = st.service_id AND st.language = ?
            LEFT JOIN service_categories sc ON s.category_id = sc.id
            LEFT JOIN service_category_translations sct 
                ON sc.id = sct.category_id AND sct.language = ?
            WHERE 1=1
        """
        
        # Запрос для подсчета общего количества
        count_query = """
            SELECT COUNT(*) as count 
            FROM services s
            LEFT JOIN service_translations st ON s.id = st.service_id AND st.language = ?
            WHERE 1=1
        """
        
        params = [language, language, language]
        count_params = [language]
        
        # Добавляем фильтр по категории
        if category_id is not None:
            # Если category_id = -1, показываем услуги без категории
            if category_id == -1:
                query += " AND s.category_id IS NULL"
                count_query += " AND s.category_id IS NULL"
            else:
                # Получаем все подкатегории выбранной категории
                all_category_ids = [category_id]
                subcategories = db.fetch_all("""
                    WITH RECURSIVE category_tree AS (
                        SELECT id FROM service_categories WHERE id = ?
                        UNION ALL
                        SELECT sc.id FROM service_categories sc
                        INNER JOIN category_tree ct ON sc.parent_id = ct.id
                    )
                    SELECT id FROM category_tree
                """, (category_id,))
                
                all_category_ids.extend([c["id"] for c in subcategories])
                
                query += " AND s.category_id IN (" + ",".join(["?"] * len(all_category_ids)) + ")"
                count_query += " AND s.category_id IN (" + ",".join(["?"] * len(all_category_ids)) + ")"
                params.extend(all_category_ids)
                count_params.extend(all_category_ids)
        
        # Фильтр по активности
        if is_active is not None:
            query += " AND s.is_active = ?"
            count_query += " AND s.is_active = ?"
            params.append(int(is_active))
            count_params.append(int(is_active))
        
        # Поиск
        if search and search.strip():
            search_term = f"%{search.strip()}%"
            query += " AND (st.title LIKE ? OR st.description LIKE ?)"
            count_query += " AND (st.title LIKE ? OR st.description LIKE ?)"
            params.extend([search_term, search_term])
            count_params.extend([search_term, search_term])
        
        # Сортировка и пагинация
        query += " ORDER BY s.id DESC LIMIT ? OFFSET ?"
        params.extend([per_page, offset])
        
        # Выполняем запросы
        services = db.fetch_all(query, tuple(params))
        
        # Общее количество
        count_result = db.fetch_one(count_query, tuple(count_params))
        total = count_result["count"] if count_result else 0
        
        logger.info(f"Found {len(services)} services, total: {total}")
        
        return {
            "items": services,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page if per_page > 0 else 0
        }
    
    except Exception as e:
        logger.error(f"Error fetching services: {e}", exc_info=True)
        return {
            "items": [],
            "total": 0,
            "page": page,
            "per_page": per_page,
            "total_pages": 0
        }

@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_service(
    service_data: ServiceCreate,
    current_user: dict = Depends(get_current_admin)
):
    """
    Создание новой услуги
    """
    logger.info(f"Create service request from user {current_user['id']}")
    
    try:
        # Проверяем существование категории
        if service_data.category_id:
            category = db.fetch_one(
                "SELECT id, is_active FROM service_categories WHERE id = ?",
                (service_data.category_id,)
            )
            if not category:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Категория не найдена"
                )
            
            # Проверяем, что категория не является родительской
            child_categories = db.fetch_all(
                "SELECT id FROM service_categories WHERE parent_id = ?",
                (service_data.category_id,)
            )
            if child_categories:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Нельзя добавить услугу в родительскую категорию. Выберите конкретную подкатегорию."
                )
        
        # Создаем услугу
        service_id = db.insert_and_get_id("""
            INSERT INTO services (category_id, duration_minutes, price, is_active)
            VALUES (?, ?, ?, ?)
        """, (
            service_data.category_id,
            service_data.duration_minutes,
            service_data.price,
            int(service_data.is_active)
        ))
        
        if not service_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Не удалось создать услугу"
            )
        
        # Добавляем переводы
        for translation in service_data.translations:
            db.execute_query("""
                INSERT INTO service_translations (service_id, language, title, description)
                VALUES (?, ?, ?, ?)
            """, (
                service_id,
                translation.language,
                translation.title,
                translation.description or ""
            ))
        
        log_admin_action(
            current_user["id"], 
            "CREATE_SERVICE", 
            f"Created service {service_id} in category {service_data.category_id}"
        )
        
        logger.info(f"Service {service_id} created successfully")
        return {
            "id": service_id, 
            "message": "Услуга успешно создана",
            "category_id": service_data.category_id
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating service: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при создании услуги: {str(e)}"
        )

@router.get("/{service_id}", response_model=ServiceWithDetailsResponse)
async def get_service(
    service_id: int,
    current_user: dict = Depends(get_current_admin),
    language: str = "ru"
):
    """
    Получение полной информации об услуге с переводами
    """
    logger.info(f"Get service {service_id} request from user {current_user['id']}")
    
    try:
        # Основная информация об услуге
        service = db.fetch_one("""
            SELECT s.*, sct.title as category_title
            FROM services s
            LEFT JOIN service_categories sc ON s.category_id = sc.id
            LEFT JOIN service_category_translations sct 
                ON sc.id = sct.category_id AND sct.language = ?
            WHERE s.id = ?
        """, (language, service_id))
        
        if not service:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Услуга не найдена"
            )
        
        # Все переводы услуги
        translations = db.fetch_all("""
            SELECT language, title, description 
            FROM service_translations 
            WHERE service_id = ?
            ORDER BY language
        """, (service_id,))
        
        # Получаем путь категории
        category_path = None
        if service.get("category_id"):
            path_result = db.fetch_one("""
                WITH RECURSIVE category_path AS (
                    SELECT id, parent_id, 1 as level
                    FROM service_categories 
                    WHERE id = ?
                    UNION ALL
                    SELECT sc.id, sc.parent_id, cp.level + 1
                    FROM service_categories sc
                    JOIN category_path cp ON sc.id = cp.parent_id
                )
                SELECT GROUP_CONCAT(cp.id ORDER BY cp.level DESC) as path_ids
                FROM category_path cp
            """, (service["category_id"],))
            
            if path_result and path_result.get("path_ids"):
                path_ids = path_result["path_ids"].split(",")
                path_titles = []
                for pid in path_ids:
                    title = db.fetch_one("""
                        SELECT title FROM service_category_translations 
                        WHERE category_id = ? AND language = ?
                    """, (int(pid), language))
                    path_titles.append(title["title"] if title else f"#{pid}")
                category_path = " / ".join(path_titles)
        
        return {
            "id": service["id"],
            "category_id": service["category_id"],
            "duration_minutes": service["duration_minutes"],
            "price": service["price"],
            "is_active": bool(service.get("is_active", 1)),
            "translations": translations,
            "category_title": service.get("category_title"),
            "category_path": category_path
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching service: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при загрузке услуги: {str(e)}"
        )

@router.put("/{service_id}", response_model=dict)
async def update_service(
    service_id: int,
    service_data: ServiceUpdate,
    current_user: dict = Depends(get_current_admin)
):
    """
    Обновление услуги
    """
    logger.info(f"Update service {service_id} request from user {current_user['id']}")
    
    try:
        # Проверяем существование услуги
        existing_service = db.fetch_one(
            "SELECT * FROM services WHERE id = ?", 
            (service_id,)
        )
        if not existing_service:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Услуга не найдена"
            )
        
        # Проверяем категорию если указана
        if service_data.category_id is not None:
            category = db.fetch_one(
                "SELECT id FROM service_categories WHERE id = ?",
                (service_data.category_id,)
            )
            if not category:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Категория не найдена"
                )
            
            # Проверяем, что категория не является родительской
            child_categories = db.fetch_all(
                "SELECT id FROM service_categories WHERE parent_id = ?",
                (service_data.category_id,)
            )
            if child_categories:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Нельзя переместить услугу в родительскую категорию"
                )
        
        # Обновляем основную информацию
        update_fields = []
        params = []
        
        if service_data.category_id is not None:
            update_fields.append("category_id = ?")
            params.append(service_data.category_id)
        
        if service_data.duration_minutes is not None:
            update_fields.append("duration_minutes = ?")
            params.append(service_data.duration_minutes)
        
        if service_data.price is not None:
            update_fields.append("price = ?")
            params.append(service_data.price)
        
        if service_data.is_active is not None:
            update_fields.append("is_active = ?")
            params.append(int(service_data.is_active))
        
        if update_fields:
            params.append(service_id)
            db.execute_query(
                f"UPDATE services SET {', '.join(update_fields)} WHERE id = ?",
                tuple(params)
            )
        
        # Обновляем переводы
        if service_data.translations:
            for translation in service_data.translations:
                existing_translation = db.fetch_one("""
                    SELECT id FROM service_translations 
                    WHERE service_id = ? AND language = ?
                """, (service_id, translation.language))
                
                if existing_translation:
                    db.execute_query("""
                        UPDATE service_translations 
                        SET title = ?, description = ?
                        WHERE id = ?
                    """, (
                        translation.title,
                        translation.description or "",
                        existing_translation["id"]
                    ))
                else:
                    db.execute_query("""
                        INSERT INTO service_translations (service_id, language, title, description)
                        VALUES (?, ?, ?, ?)
                    """, (
                        service_id,
                        translation.language,
                        translation.title,
                        translation.description or ""
                    ))
        
        log_admin_action(
            current_user["id"], 
            "UPDATE_SERVICE", 
            f"Updated service {service_id}"
        )
        
        logger.info(f"Service {service_id} updated successfully")
        return {"message": "Услуга успешно обновлена"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating service: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при обновлении услуги: {str(e)}"
        )
# В разделе услуг добавим новый endpoint после существующего delete_service:

@router.delete("/{service_id}/force", response_model=dict)
async def force_delete_service(
    service_id: int,
    current_user: dict = Depends(get_current_admin)
):
    """
    Полное удаление услуги (только если нет связанных записей)
    """
    logger.info(f"Force delete service {service_id} request from user {current_user['id']}")
    
    try:
        # Проверяем существование услуги
        existing_service = db.fetch_one(
            "SELECT * FROM services WHERE id = ?", 
            (service_id,)
        )
        if not existing_service:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Услуга не найдена"
            )
        
        # Проверяем, есть ли связанные записи в appointment_services
        appointments_with_service = db.fetch_all(
            "SELECT id FROM appointment_services WHERE service_id = ?", 
            (service_id,)
        )
        
        if appointments_with_service:
            appointment_ids = [a["id"] for a in appointments_with_service]
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Невозможно удалить услугу, так как она используется в записях (ID записей: {', '.join(map(str, appointment_ids[:5]))})"
                + ("..." if len(appointment_ids) > 5 else "")
            )
        
        # Удаляем переводы
        db.execute_query(
            "DELETE FROM service_translations WHERE service_id = ?", 
            (service_id,)
        )
        
        # Удаляем услугу
        rows_affected = db.execute_query(
            "DELETE FROM services WHERE id = ?", 
            (service_id,)
        )
        
        if rows_affected == 0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Не удалось удалить услугу"
            )
        
        log_admin_action(
            current_user["id"], 
            "FORCE_DELETE_SERVICE", 
            f"Permanently deleted service {service_id}"
        )
        
        logger.info(f"Service {service_id} permanently deleted")
        return {"message": "Услуга полностью удалена"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error force deleting service: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при удалении услуги: {str(e)}"
        )
@router.delete("/{service_id}", response_model=dict)
async def delete_service(
    service_id: int,
    current_user: dict = Depends(get_current_admin)
):
    """
    Удаление/деактивация услуги
    """
    logger.info(f"Delete service {service_id} request from user {current_user['id']}")
    
    try:
        # Проверяем существование услуги
        existing_service = db.fetch_one(
            "SELECT * FROM services WHERE id = ?", 
            (service_id,)
        )
        if not existing_service:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Услуга не найдена"
            )
        
        # Вместо удаления деактивируем
        rows_affected = db.execute_query(
            "UPDATE services SET is_active = 0 WHERE id = ?", 
            (service_id,)
        )
        
        if rows_affected == 0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Не удалось деактивировать услугу"
            )
        
        log_admin_action(
            current_user["id"], 
            "DELETE_SERVICE", 
            f"Deactivated service {service_id}"
        )
        
        logger.info(f"Service {service_id} deactivated")
        return {"message": "Услуга успешно деактивирована"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting service: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при деактивации услуги: {str(e)}"
        )

@router.get("/{service_id}/translations", response_model=List[TranslationBase])
async def get_service_translations(
    service_id: int,
    current_user: dict = Depends(get_current_admin)
):
    """
    Получение всех переводов услуги
    """
    logger.info(f"Get service {service_id} translations from user {current_user['id']}")
    
    try:
        translations = db.fetch_all("""
            SELECT language, title, description 
            FROM service_translations 
            WHERE service_id = ?
            ORDER BY language
        """, (service_id,))
        
        return translations
    
    except Exception as e:
        logger.error(f"Error fetching service translations: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при загрузке переводов услуги: {str(e)}"
        )

@router.get("/search/suggestions", response_model=List[ServiceResponse])
async def search_service_suggestions(
    current_user: dict = Depends(get_current_admin),
    q: str = Query(..., min_length=2, description="Поисковый запрос"),
    language: str = "ru",
    limit: int = Query(10, ge=1, le=50, description="Лимит результатов")
):
    """
    Поиск услуг по названию для автодополнения
    """
    try:
        search_term = f"%{q}%"
        services = db.fetch_all("""
            SELECT s.*, st.title, st.description, sct.title as category_title
            FROM services s
            LEFT JOIN service_translations st 
                ON s.id = st.service_id AND st.language = ?
            LEFT JOIN service_categories sc ON s.category_id = sc.id
            LEFT JOIN service_category_translations sct 
                ON sc.id = sct.category_id AND sct.language = ?
            WHERE st.title LIKE ? AND s.is_active = 1
            ORDER BY st.title
            LIMIT ?
        """, (language, language, search_term, limit))
        
        return services
    
    except Exception as e:
        logger.error(f"Error searching services: {e}", exc_info=True)
        return []

@router.get("/categories/{category_id}/services", response_model=List[ServiceResponse])
async def get_services_by_category(
    category_id: int,
    current_user: dict = Depends(get_current_admin),
    language: str = "ru",
    include_subcategories: bool = Query(True, description="Включать услуги из подкатегорий")
):
    """
    Получение всех услуг в категории и её подкатегориях
    """
    try:
        if include_subcategories:
            # Получаем все подкатегории
            category_ids = [category_id]
            subcategories = db.fetch_all("""
                WITH RECURSIVE category_tree AS (
                    SELECT id FROM service_categories WHERE id = ?
                    UNION ALL
                    SELECT sc.id FROM service_categories sc
                    INNER JOIN category_tree ct ON sc.parent_id = ct.id
                )
                SELECT id FROM category_tree
            """, (category_id,))
            
            category_ids.extend([c["id"] for c in subcategories])
            
            placeholders = ",".join(["?"] * len(category_ids))
            services = db.fetch_all(f"""
                SELECT s.*, st.title, st.description, sct.title as category_title
                FROM services s
                LEFT JOIN service_translations st 
                    ON s.id = st.service_id AND st.language = ?
                LEFT JOIN service_categories sc ON s.category_id = sc.id
                LEFT JOIN service_category_translations sct 
                    ON sc.id = sct.category_id AND sct.language = ?
                WHERE s.category_id IN ({placeholders}) AND s.is_active = 1
                ORDER BY s.id
            """, [language, language] + category_ids)
        else:
            services = db.fetch_all("""
                SELECT s.*, st.title, st.description, sct.title as category_title
                FROM services s
                LEFT JOIN service_translations st 
                    ON s.id = st.service_id AND st.language = ?
                LEFT JOIN service_categories sc ON s.category_id = sc.id
                LEFT JOIN service_category_translations sct 
                    ON sc.id = sct.category_id AND sct.language = ?
                WHERE s.category_id = ? AND s.is_active = 1
                ORDER BY s.id
            """, (language, language, category_id))
        
        return services
    
    except Exception as e:
        logger.error(f"Error fetching services by category: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при загрузке услуг категории: {str(e)}"
        )