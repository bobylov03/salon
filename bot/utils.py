#utils.py
import logging
from datetime import datetime, date, time, timedelta
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

# Модульный инстанс базы данных — импортируем здесь, чтобы не передавать db в каждый метод
from .database import Database
_db = Database()


class Utils:
    @staticmethod
    def get_user_language(user_id: Optional[int]) -> str:
        """Получение языка пользователя"""
        if not user_id:
            return 'ru'
        return _db.get_user_language(user_id)

    @staticmethod
    def calculate_total_duration(service_ids: List[int]) -> int:
        """Рассчет общей длительности выбранных услуг"""
        total_duration = 0
        for service_id in service_ids:
            service = _db.get_service_by_id(service_id, 'ru')
            if service:
                total_duration += service.get('duration_minutes', 0)
        return total_duration

    @staticmethod
    def calculate_total_price(service_ids: List[int]) -> float:
        """Рассчет общей стоимости выбранных услуг"""
        total_price = 0.0
        for service_id in service_ids:
            service = _db.get_service_by_id(service_id, 'ru')
            if service:
                total_price += service.get('price', 0)
        return total_price

    @staticmethod
    def get_available_time_slots_for_services(
        service_ids: List[int],
        appointment_date: date,
        master_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Получение доступных временных слотов для услуг"""

        total_duration = Utils.calculate_total_duration(service_ids)

        if master_id:
            # Для конкретного мастера
            time_slots = _db.get_available_time_slots(master_id, appointment_date, total_duration)
            return [{'master_id': master_id, 'time_slots': time_slots}]

        # Для любого доступного мастера
        conn = _db.get_connection()
        cursor = conn.cursor()

        placeholders = ', '.join('?' for _ in service_ids)
        cursor.execute(f"""
            SELECT m.id as master_id, u.telegram_id
            FROM master_services ms
            JOIN masters m ON ms.master_id = m.id
            JOIN users u ON m.user_id = u.id
            WHERE ms.service_id IN ({placeholders}) AND m.is_active = 1
            GROUP BY m.id, u.telegram_id
            HAVING COUNT(DISTINCT ms.service_id) = ?
        """, tuple(service_ids) + (len(service_ids),))
        masters = cursor.fetchall()
        conn.close()

        all_time_slots: Dict[str, List[int]] = {}
        for master in masters:
            mid = master['master_id']
            slots = _db.get_available_time_slots(mid, appointment_date, total_duration)
            for slot in slots:
                all_time_slots.setdefault(slot, []).append(mid)

        result = [
            {'time': slot, 'master_ids': mids, 'is_common': len(mids) > 1}
            for slot, mids in all_time_slots.items()
        ]
        result.sort(key=lambda x: x['time'])
        return result

    @staticmethod
    def find_master_for_time_slot(
        service_ids: List[int],
        appointment_date: date,
        time_slot: str,
    ) -> Optional[int]:
        """Поиск master_id для временного слота"""
        total_duration = Utils.calculate_total_duration(service_ids)

        conn = _db.get_connection()
        cursor = conn.cursor()
        placeholders = ', '.join('?' for _ in service_ids)
        cursor.execute(f"""
            SELECT m.id as master_id
            FROM master_services ms
            JOIN masters m ON ms.master_id = m.id
            WHERE ms.service_id IN ({placeholders}) AND m.is_active = 1
            GROUP BY m.id
            HAVING COUNT(DISTINCT ms.service_id) = ?
        """, tuple(service_ids) + (len(service_ids),))
        masters = cursor.fetchall()
        conn.close()

        for master in masters:
            mid = master['master_id']
            slots = _db.get_available_time_slots(mid, appointment_date, total_duration)
            if time_slot in slots:
                return mid

        return None

    @staticmethod
    def validate_time_slot(
        master_id: int,
        appointment_date: date,
        time_slot: str,
        service_ids: List[int],
    ) -> bool:
        """Проверка, доступен ли временной слот"""
        total_duration = Utils.calculate_total_duration(service_ids)
        available_slots = _db.get_available_time_slots(master_id, appointment_date, total_duration)
        return time_slot in available_slots

    @staticmethod
    def check_user_is_master(telegram_id: int) -> Optional[Dict[str, Any]]:
        """Проверяет, является ли пользователь мастером"""
        return _db.check_user_is_master(telegram_id)

    @staticmethod
    def format_date(d: date, language: str = 'ru') -> str:
        """Форматирует дату в читаемый вид"""
        if isinstance(d, str):
            try:
                d = date.fromisoformat(d)
            except ValueError:
                return d
        months_ru = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
                     'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря']
        months_en = ['January', 'February', 'March', 'April', 'May', 'June',
                     'July', 'August', 'September', 'October', 'November', 'December']
        months_tr = ['Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran',
                     'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık']
        if language == 'en':
            return f"{months_en[d.month - 1]} {d.day}, {d.year}"
        elif language == 'tr':
            return f"{d.day} {months_tr[d.month - 1]} {d.year}"
        else:
            return f"{d.day} {months_ru[d.month - 1]} {d.year}"

    @staticmethod
    def generate_appointment_summary(
        service_ids: List[int],
        appointment_date: date,
        time_slot: str,
        master_id: Optional[int],
        language: str,
    ) -> Dict[str, Any]:
        """Генерация сводки по записи"""
        services = []
        total_price = 0.0

        for service_id in service_ids:
            service = _db.get_service_by_id(service_id, language)
            if service:
                services.append({
                    'id': service_id,
                    'title': service.get('title', f'Услуга {service_id}'),
                    'price': service.get('price', 0),
                    'duration': service.get('duration_minutes', 0),
                })
                total_price += service.get('price', 0)

        master_info = None
        if master_id:
            master = _db.get_master_by_id(master_id)
            if master:
                master_info = {
                    'id': master_id,
                    'name': f"{master.get('first_name', '')} {master.get('last_name', '')}".strip(),
                    'photo_url': master.get('photo_url'),
                }

        return {
            'services': services,
            'total_price': total_price,
            'date': appointment_date.isoformat() if isinstance(appointment_date, date) else appointment_date,
            'time': time_slot,
            'master': master_info,
            'total_duration': Utils.calculate_total_duration(service_ids),
        }
