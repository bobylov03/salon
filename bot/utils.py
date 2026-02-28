#utils.py
import logging
from datetime import datetime, date, time, timedelta
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

class Utils:
    @staticmethod
    def calculate_total_duration(service_ids: List[int], db) -> int:
        """Рассчет общей длительности выбранных услуг"""
        total_duration = 0
        
        for service_id in service_ids:
            service = db.get_service_by_id(service_id, 'ru')  # Язык не важен для длительности
            if service:
                total_duration += service.get('duration_minutes', 0)
        
        return total_duration
    
    @staticmethod
    def calculate_total_price(service_ids: List[int], db) -> float:
        """Рассчет общей стоимости выбранных услуг"""
        total_price = 0.0
        
        for service_id in service_ids:
            service = db.get_service_by_id(service_id, 'ru')  # Язык не важен для цены
            if service:
                total_price += service.get('price', 0)
        
        return total_price
    
    @staticmethod
    def get_available_time_slots_for_services(
        service_ids: List[int], 
        appointment_date: date,
        master_id: Optional[int],
        db
    ) -> List[Dict[str, Any]]:
        """Получение доступных временных слотов для услуг"""
        
        # Если выбран конкретный мастер
        if master_id:
            # Проверяем, предоставляет ли мастер все выбранные услуги
            for service_id in service_ids:
                masters_for_service = db.get_masters_for_service(service_id)
                master_ids = [m['id'] for m in masters_for_service]
                if master_id not in master_ids:
                    return []  # Мастер не предоставляет одну из услуг
            
            # Получаем доступные слоты для этого мастера
            total_duration = Utils.calculate_total_duration(service_ids, db)
            time_slots = db.get_available_time_slots(master_id, appointment_date, total_duration)
            
            return [{'master_id': master_id, 'time_slots': time_slots}]
        
        # Если выбран "любой доступный мастер"
        else:
            # Находим мастеров, которые предоставляют все выбранные услуги
            all_masters = {}
            
            for service_id in service_ids:
                masters_for_service = db.get_masters_for_service(service_id)
                
                for master in masters_for_service:
                    master_id = master['id']
                    if master_id not in all_masters:
                        all_masters[master_id] = {
                            'master': master,
                            'services_count': 1
                        }
                    else:
                        all_masters[master_id]['services_count'] += 1
            
            # Фильтруем мастеров, которые предоставляют все услуги
            suitable_masters = []
            for master_id, data in all_masters.items():
                if data['services_count'] == len(service_ids):
                    suitable_masters.append(master_id)
            
            if not suitable_masters:
                return []
            
            # Получаем общие свободные слоты для всех подходящих мастеров
            total_duration = Utils.calculate_total_duration(service_ids, db)
            all_time_slots = {}
            
            for master_id in suitable_masters:
                time_slots = db.get_available_time_slots(master_id, appointment_date, total_duration)
                for slot in time_slots:
                    if slot not in all_time_slots:
                        all_time_slots[slot] = [master_id]
                    else:
                        all_time_slots[slot].append(master_id)
            
            # Преобразуем в нужный формат
            result = []
            for time_slot, master_ids_list in all_time_slots.items():
                result.append({
                    'time': time_slot,
                    'master_ids': master_ids_list,
                    'is_common': len(master_ids_list) > 1
                })
            
            # Сортируем по времени
            result.sort(key=lambda x: x['time'])
            
            return result
    
    @staticmethod
    def find_master_for_time_slot(
        service_ids: List[int],
        appointment_date: date,
        time_slot: str,
        db
    ) -> Optional[int]:
        """Поиск мастера для временного слота"""
        
        # Получаем всех мастеров, которые предоставляют все услуги
        suitable_masters = []
        
        for service_id in service_ids:
            masters_for_service = db.get_masters_for_service(service_id)
            
            if not suitable_masters:
                # Первая услуга - добавляем всех мастеров
                suitable_masters = [m['id'] for m in masters_for_service]
            else:
                # Пересечение с мастерами для предыдущих услуг
                current_masters = [m['id'] for m in masters_for_service]
                suitable_masters = [m for m in suitable_masters if m in current_masters]
            
            if not suitable_masters:
                return None
        
        # Проверяем, у кого из подходящих мастеров свободен этот слот
        total_duration = Utils.calculate_total_duration(service_ids, db)
        
        for master_id in suitable_masters:
            available_slots = db.get_available_time_slots(master_id, appointment_date, total_duration)
            if time_slot in available_slots:
                return master_id
        
        return None
    
    @staticmethod
    def validate_time_slot(
        master_id: int,
        appointment_date: date,
        time_slot: str,
        service_ids: List[int],
        db
    ) -> bool:
        """Проверка, доступен ли временной слот"""
        total_duration = Utils.calculate_total_duration(service_ids, db)
        available_slots = db.get_available_time_slots(master_id, appointment_date, total_duration)
        return time_slot in available_slots
    
    @staticmethod
    def generate_appointment_summary(
        service_ids: List[int],
        appointment_date: date,
        time_slot: str,
        master_id: Optional[int],
        language: str,
        db
    ) -> Dict[str, Any]:
        """Генерация сводки по записи"""
        services = []
        total_price = 0
        
        for service_id in service_ids:
            service = db.get_service_by_id(service_id, language)
            if service:
                services.append({
                    'id': service_id,
                    'title': service.get('title', f'Услуга {service_id}'),
                    'price': service.get('price', 0),
                    'duration': service.get('duration_minutes', 0)
                })
                total_price += service.get('price', 0)
        
        master_info = None
        if master_id:
            master = db.get_master_by_id(master_id)
            if master:
                master_info = {
                    'id': master_id,
                    'name': f"{master.get('first_name', '')} {master.get('last_name', '')}".strip(),
                    'photo_url': master.get('photo_url')
                }
        
        return {
            'services': services,
            'total_price': total_price,
            'date': appointment_date.isoformat(),
            'time': time_slot,
            'master': master_info,
            'total_duration': Utils.calculate_total_duration(service_ids, db)
        }