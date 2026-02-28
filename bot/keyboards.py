# keyboards.py
from typing import List, Dict, Any, Optional
from telegram import InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton
from datetime import datetime, date
import calendar

class UnifiedKeyboards:
    @staticmethod
    def get_language_keyboard() -> ReplyKeyboardMarkup:
        """Клавиатура для выбора языка"""
        keyboard = [
            [KeyboardButton("🇷🇺 Русский"), KeyboardButton("🇬🇧 English")],
            [KeyboardButton("🇹🇷 Türkçe")]
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    
    @staticmethod
    def get_main_menu_keyboard(language: str = 'ru') -> ReplyKeyboardMarkup:
        """Главное меню для клиентов"""
        if language == 'ru':
            buttons = [
                ["💇 Записаться на услугу", "📋 Мои записи"],
                ["👤 Мой профиль", "ℹ️ О салоне"],
                ["🌐 Сменить язык"]
            ]
        elif language == 'en':
            buttons = [
                ["💇 Book a Service", "📋 My Appointments"],
                ["👤 My Profile", "ℹ️ About Salon"],
                ["🌐 Change Language"]
            ]
        else:  # tr
            buttons = [
                ["💇 Randevu Al", "📋 Randevularım"],
                ["👤 Profilim", "ℹ️ Salon Hakkında"],
                ["🌐 Dil Değiştir"]
            ]
        
        return ReplyKeyboardMarkup(buttons, resize_keyboard=True)
    
    @staticmethod
    def get_master_menu_keyboard(language: str = 'ru') -> ReplyKeyboardMarkup:
        """Меню для мастеров"""
        if language == 'ru':
            buttons = [
                ["📅 Мои записи на сегодня", "📋 Все записи"],
                ["⏰ Свободные слоты", "⚙️ Расписание"],
                ["📊 Статистика", "👤 Профиль"],
                ["🌐 Сменить язык"]
            ]
        elif language == 'en':
            buttons = [
                ["📅 Today's Appointments", "📋 All Appointments"],
                ["⏰ Available Slots", "⚙️ Schedule"],
                ["📊 Statistics", "👤 Profile"],
                ["🌐 Change Language"]
            ]
        else:  # tr
            buttons = [
                ["📅 Bugünkü Randevular", "📋 Tüm Randevular"],
                ["⏰ Uygun Zamanlar", "⚙️ Çalışma Saatleri"],
                ["📊 İstatistikler", "👤 Profil"],
                ["🌐 Dil Değiştir"]
            ]
        
        return ReplyKeyboardMarkup(buttons, resize_keyboard=True)
    
    @staticmethod
    def get_categories_keyboard(categories: List[Dict[str, Any]], language: str) -> InlineKeyboardMarkup:
        """Клавиатура с категориями услуг"""
        keyboard = []
        for category in categories:
            title = category.get('title', f"Категория {category['id']}")
            keyboard.append([InlineKeyboardButton(title, callback_data=f"category_{category['id']}")])
        
        # Исправлено: добавляем кнопку "назад" только если есть категории
        if categories:
            back_text = "⬅️ Назад" if language == 'ru' else "⬅️ Back" if language == 'en' else "⬅️ Geri"
            keyboard.append([InlineKeyboardButton(back_text, callback_data="back_to_categories")])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def get_services_keyboard(services: List[Dict[str, Any]], language: str, selected_services: List[int] = None) -> InlineKeyboardMarkup:
        """Клавиатура с услугами"""
        selected_services = selected_services or []
        keyboard = []
        
        for service in services:
            title = service.get('title', f"Услуга {service['id']}")
            price = service.get('price', 0)
            is_selected = service['id'] in selected_services
            emoji = "✅ " if is_selected else ""
            
            button_text = f"{emoji}{title} - {price}₺"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"toggle_service_{service['id']}")])
        
        if language == 'ru':
            keyboard.append([
                InlineKeyboardButton("⬅️ Назад", callback_data="back_to_categories"),
                InlineKeyboardButton("📅 Выбрать дату", callback_data="select_date"),
                InlineKeyboardButton("✅ Завершить выбор", callback_data="finish_selection")
            ])
        elif language == 'en':
            keyboard.append([
                InlineKeyboardButton("⬅️ Back", callback_data="back_to_categories"),
                InlineKeyboardButton("📅 Select Date", callback_data="select_date"),
                InlineKeyboardButton("✅ Finish Selection", callback_data="finish_selection")
            ])
        else:  # tr
            keyboard.append([
                InlineKeyboardButton("⬅️ Geri", callback_data="back_to_categories"),
                InlineKeyboardButton("📅 Tarih Seç", callback_data="select_date"),
                InlineKeyboardButton("✅ Seçimi Tamamla", callback_data="finish_selection")
            ])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def get_calendar_keyboard(year: int, month: int, language: str) -> InlineKeyboardMarkup:
        """Клавиатура календаря"""
        import calendar as cal_module
        
        keyboard = []
        month_names = {
            'ru': ['Янв', 'Фев', 'Мар', 'Апр', 'Май', 'Июн', 'Июл', 'Авг', 'Сен', 'Окт', 'Ноя', 'Дек'],
            'en': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
            'tr': ['Oca', 'Şub', 'Mar', 'Nis', 'May', 'Haz', 'Tem', 'Ağu', 'Eyl', 'Eki', 'Kas', 'Ara']
        }
        
        # Месяц и год
        month_name = month_names[language][month - 1]
        keyboard.append([InlineKeyboardButton(f"{month_name} {year}", callback_data="ignore")])
        
        # Дни недели
        weekdays = {
            'ru': ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'],
            'en': ['Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa', 'Su'],
            'tr': ['Pt', 'Sa', 'Ça', 'Pe', 'Cu', 'Ct', 'Pz']
        }
        
        row = []
        for day in weekdays[language]:
            row.append(InlineKeyboardButton(day, callback_data="ignore"))
        keyboard.append(row)
        
        # Дни месяца
        cal = cal_module.monthcalendar(year, month)
        today = datetime.now().date()
        
        for week in cal:
            row = []
            for day in week:
                if day == 0:
                    row.append(InlineKeyboardButton(" ", callback_data="ignore"))
                else:
                    date_str = f"{year}-{month:02d}-{day:02d}"
                    date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
                    
                    if date_obj < today:
                        row.append(InlineKeyboardButton(" ", callback_data="ignore"))
                    else:
                        row.append(InlineKeyboardButton(str(day), callback_data=f"select_date_{date_str}"))
            keyboard.append(row)
        
        # Навигация - ИСПРАВЛЕНО: используем целые числа для месяцев
        prev_month = month - 1 if month > 1 else 12
        prev_year = year if month > 1 else year - 1
        next_month = month + 1 if month < 12 else 1
        next_year = year if month < 12 else year + 1
        
        # Убеждаемся, что это числа
        prev_month = int(prev_month)
        next_month = int(next_month)
        
        if language == 'ru':
            keyboard.append([
                InlineKeyboardButton("◀️", callback_data=f"change_month_{prev_year}_{prev_month}"),
                InlineKeyboardButton("Сегодня", callback_data="select_today"),
                InlineKeyboardButton("▶️", callback_data=f"change_month_{next_year}_{next_month}")
            ])
        elif language == 'en':
            keyboard.append([
                InlineKeyboardButton("◀️", callback_data=f"change_month_{prev_year}_{prev_month}"),
                InlineKeyboardButton("Today", callback_data="select_today"),
                InlineKeyboardButton("▶️", callback_data=f"change_month_{next_year}_{next_month}")
            ])
        else:  # tr
            keyboard.append([
                InlineKeyboardButton("◀️", callback_data=f"change_month_{prev_year}_{prev_month}"),
                InlineKeyboardButton("Bugün", callback_data="select_today"),
                InlineKeyboardButton("▶️", callback_data=f"change_month_{next_year}_{next_month}")
            ])
        
        # Кнопка назад
        back_text = "⬅️ Назад" if language == 'ru' else "⬅️ Back" if language == 'en' else "⬅️ Geri"
        keyboard.append([InlineKeyboardButton(back_text, callback_data="back_to_services")])
        
        return InlineKeyboardMarkup(keyboard)
    @staticmethod
    def get_master_choice_keyboard(language: str) -> InlineKeyboardMarkup:
        """Клавиатура выбора мастера"""
        if language == 'ru':
            keyboard = [
                [InlineKeyboardButton("👨‍💻 Выбрать мастера", callback_data="choose_master")],
                [InlineKeyboardButton("🤝 Любой доступный", callback_data="any_master")],
                [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_date")]
            ]
        elif language == 'en':
            keyboard = [
                [InlineKeyboardButton("👨‍💻 Choose Master", callback_data="choose_master")],
                [InlineKeyboardButton("🤝 Any Available", callback_data="any_master")],
                [InlineKeyboardButton("⬅️ Back", callback_data="back_to_date")]
            ]
        else:  # tr
            keyboard = [
                [InlineKeyboardButton("👨‍💻 Usta Seç", callback_data="choose_master")],
                [InlineKeyboardButton("🤝 Uygun Herhangi", callback_data="any_master")],
                [InlineKeyboardButton("⬅️ Geri", callback_data="back_to_date")]
            ]
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def get_masters_keyboard(masters: List[Dict[str, Any]], language: str) -> InlineKeyboardMarkup:
        """Клавиатура с мастерами"""
        keyboard = []
        for master in masters:
            name = f"{master.get('first_name', '')} {master.get('last_name', '')}".strip()
            qualification = master.get('qualification', '')
            
            if qualification and len(qualification) > 15:
                qualification = qualification[:15] + "..."
            
            button_text = f"{name}"
            if qualification:
                button_text += f" ({qualification})"
            
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"select_master_{master['id']}")])
        
        back_text = "⬅️ Назад" if language == 'ru' else "⬅️ Back" if language == 'en' else "⬅️ Geri"
        keyboard.append([InlineKeyboardButton(back_text, callback_data="back_to_master_choice")])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def get_time_slots_keyboard(time_slots: List[str], language: str) -> InlineKeyboardMarkup:
        """Клавиатура со временем"""
        keyboard = []
        # Группируем временные слоты по 3 в ряд
        for i in range(0, len(time_slots), 3):
            row = time_slots[i:i+3]
            keyboard.append([InlineKeyboardButton(slot, callback_data=f"select_time_{slot}") for slot in row])
        
        back_text = "⬅️ Назад" if language == 'ru' else "⬅️ Back" if language == 'en' else "⬅️ Geri"
        keyboard.append([InlineKeyboardButton(back_text, callback_data="back_to_masters")])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def get_confirmation_keyboard(language: str) -> InlineKeyboardMarkup:
        """Клавиатура подтверждения записи"""
        if language == 'ru':
            keyboard = [
                [InlineKeyboardButton("✅ Подтвердить запись", callback_data="confirm_appointment")],
                [InlineKeyboardButton("❌ Отменить", callback_data="cancel_appointment")]
            ]
        elif language == 'en':
            keyboard = [
                [InlineKeyboardButton("✅ Confirm Booking", callback_data="confirm_appointment")],
                [InlineKeyboardButton("❌ Cancel", callback_data="cancel_appointment")]
            ]
        else:  # tr
            keyboard = [
                [InlineKeyboardButton("✅ Randevuyu Onayla", callback_data="confirm_appointment")],
                [InlineKeyboardButton("❌ İptal", callback_data="cancel_appointment")]
            ]
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def get_appointments_list_keyboard(appointments: List[Dict[str, Any]], language: str) -> InlineKeyboardMarkup:
        """Клавиатура со списком записей"""
        keyboard = []
        for appointment in appointments:
            date_str = appointment['appointment_date']
            time_str = appointment['start_time']
            services = appointment.get('services_titles', 'Не указаны')
            
            if len(services) > 30:
                services = services[:30] + "..."
            
            button_text = f"📅 {date_str} ⏰ {time_str} - {services}"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"appointment_detail_{appointment['id']}")])
        
        back_text = "⬅️ Назад" if language == 'ru' else "⬅️ Back" if language == 'en' else "⬅️ Geri"
        keyboard.append([InlineKeyboardButton(back_text, callback_data="back_to_main")])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def get_appointment_detail_keyboard(appointment_id: int, language: str) -> InlineKeyboardMarkup:
        """Клавиатура для управления записью"""
        if language == 'ru':
            keyboard = [
                [InlineKeyboardButton("✏️ Перенести", callback_data=f"reschedule_{appointment_id}")],
                [InlineKeyboardButton("❌ Отменить запись", callback_data=f"cancel_{appointment_id}")],
                [InlineKeyboardButton("⬅️ Назад к записям", callback_data="back_to_appointments")]
            ]
        elif language == 'en':
            keyboard = [
                [InlineKeyboardButton("✏️ Reschedule", callback_data=f"reschedule_{appointment_id}")],
                [InlineKeyboardButton("❌ Cancel Appointment", callback_data=f"cancel_{appointment_id}")],
                [InlineKeyboardButton("⬅️ Back to Appointments", callback_data="back_to_appointments")]
            ]
        else:  # tr
            keyboard = [
                [InlineKeyboardButton("✏️ Yeniden Planla", callback_data=f"reschedule_{appointment_id}")],
                [InlineKeyboardButton("❌ Randevuyu İptal Et", callback_data=f"cancel_{appointment_id}")],
                [InlineKeyboardButton("⬅️ Randevulara Geri Dön", callback_data="back_to_appointments")]
            ]
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def get_after_booking_keyboard(language: str) -> InlineKeyboardMarkup:
        """Клавиатура после успешного бронирования"""
        if language == 'ru':
            keyboard = [
                [InlineKeyboardButton("📋 Мои записи", callback_data="my_appointments")],
                [InlineKeyboardButton("💇 Новая запись", callback_data="new_appointment")]
            ]
        elif language == 'en':
            keyboard = [
                [InlineKeyboardButton("📋 My Appointments", callback_data="my_appointments")],
                [InlineKeyboardButton("💇 New Booking", callback_data="new_appointment")]
            ]
        else:  # tr
            keyboard = [
                [InlineKeyboardButton("📋 Randevularım", callback_data="my_appointments")],
                [InlineKeyboardButton("💇 Yeni Randevu", callback_data="new_appointment")]
            ]
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def get_back_to_main_keyboard(language: str) -> InlineKeyboardMarkup:
        """Клавиатура для возврата в главное меню"""
        if language == 'ru':
            text = "⬅️ Главное меню"
        elif language == 'en':
            text = "⬅️ Main Menu"
        else:  # tr
            text = "⬅️ Ana Menü"
        
        return InlineKeyboardMarkup([[InlineKeyboardButton(text, callback_data="back_to_main")]])
    
    @staticmethod
    def get_empty_keyboard() -> InlineKeyboardMarkup:
        """Пустая клавиатура (для удаления существующей)"""
        return InlineKeyboardMarkup([])

# Создаем синглтон для импорта
Keyboards = UnifiedKeyboards