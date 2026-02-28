#models.py
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import date, time, datetime

# Аутентификация
class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

# Мастера
class MasterCreate(BaseModel):
    first_name: str
    last_name: str
    phone: Optional[str] = None
    photo: Optional[str] = None
    qualification: Optional[str] = None
    description: Optional[str] = None
    is_active: bool = True

class MasterUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    photo: Optional[str] = None
    qualification: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None

class MasterResponse(BaseModel):
    id: int
    user_id: int
    first_name: str
    last_name: str
    phone: Optional[str]
    photo: Optional[str]
    qualification: Optional[str]
    description: Optional[str]
    is_active: bool

# График работы
class WorkScheduleCreate(BaseModel):
    master_id: int
    day_of_week: int  # 0-6
    start_time: str  # "09:00"
    end_time: str    # "18:00"

class WorkScheduleResponse(BaseModel):
    id: int
    master_id: int
    day_of_week: int
    start_time: str
    end_time: str

# Услуги и категории
class CategoryCreate(BaseModel):
    parent_id: Optional[int] = None
    is_active: bool = True
    translations: List[dict]  # [{"language": "ru", "title": "Маникюр"}]

class ServiceCreate(BaseModel):
    category_id: int
    duration_minutes: int
    price: float
    is_active: bool = True
    translations: List[dict]
# Связь мастера с услугами
class MasterServiceLink(BaseModel):
    service_id: int
    category_id: int
    is_primary: bool = True

class MasterWithServices(BaseModel):
    id: int
    first_name: str
    last_name: str
    phone: Optional[str]
    photo_url: Optional[str]
    qualification: Optional[str]
    services: List[MasterServiceLink]
    
class ServiceWithMasters(BaseModel):
    id: int
    title: str
    description: Optional[str]
    price: float
    duration_minutes: int
    category_id: int
    masters: List[dict]  # список мастеров с их данными
# Записи
class AppointmentCreate(BaseModel):
    client_id: int
    master_id: Optional[int] = None
    appointment_date: date
    start_time: str
    services: List[int]  # список ID услуг
    status: str = "pending"

class AppointmentUpdate(BaseModel):
    master_id: Optional[int] = None
    appointment_date: Optional[date] = None
    start_time: Optional[str] = None
    status: Optional[str] = None

# Клиенты
class ClientResponse(BaseModel):
    id: int
    telegram_id: Optional[int]
    first_name: str
    last_name: Optional[str]
    phone: Optional[str]
    created_at: datetime

# Бонусы
class BonusUpdate(BaseModel):
    client_id: int
    amount: int
    reason: Optional[str] = None

# Аналитика
class AnalyticsPeriod(BaseModel):
    start_date: date
    end_date: date

# Ответы API
class PaginatedResponse(BaseModel):
    items: List
    total: int
    page: int
    per_page: int
    total_pages: int