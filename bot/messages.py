from typing import Dict, Any, List
from datetime import date, datetime, time, timedelta

class Messages:
    # Словари с переводами
    LANGUAGES = {
        'ru': 'Русский',
        'en': 'English',
        'tr': 'Türkçe'
    }
    
    # Приветственные сообщения
    @staticmethod
    def get_welcome_message(language: str) -> str:
        messages = {
            'ru': "👋 Добро пожаловать в салон красоты!\n\nПожалуйста, выберите язык:",
            'en': "👋 WelcomЁ=ЁФ\.............."
            "e to the beauty salon!\n\nPlease select your language:",
            'tr': "👋 Güzellik salonuna hoş geldiniz!\n\nLütfen dilinizi seçin:"
        }
        return messages.get(language, messages['ru'])
    
    @staticmethod
    def get_language_set_message(language: str) -> str:
        messages = {
            'ru': f"✅ Язык установлен: {Messages.LANGUAGES[language]}\n\nВыберите действие:",
            'en': f"✅ Language set to: {Messages.LANGUAGES[language]}\n\nSelect an action:",
            'tr': f"✅ Dil ayarlandı: {Messages.LANGUAGES[language]}\n\nBir işlem seçin:"
        }
        return messages.get(language, messages['ru'])
    
    # Категории
    @staticmethod
    def get_categories_message(language: str) -> str:
        messages = {
            'ru': "📂 Выберите категорию услуг:",
            'en': "📂 Select service category:",
            'tr': "📂 Hizmet kategorisi seçin:"
        }
        return messages.get(language, messages['ru'])
    
    @staticmethod
    def get_no_categories_message(language: str) -> str:
        messages = {
            'ru': "😔 В этой категории пока нет подкатегорий.",
            'en': "😔 No subcategories in this category yet.",
            'tr': "😔 Bu kategoride henüz alt kategori yok."
        }
        return messages.get(language, messages['ru'])
    
    # Услуги
    @staticmethod
    def get_services_message(language: str, category_title: str) -> str:
        messages = {
            'ru': f"💅 Услуги в категории: {category_title}\n\nВыберите услуги (можно несколько):",
            'en': f"💅 Services in category: {category_title}\n\nSelect services (multiple allowed):",
            'tr': f"💅 Kategorideki hizmetler: {category_title}\n\nHizmetleri seçin (birden fazla seçebilirsiniz):"
        }
        return messages.get(language, messages['ru'])
    
    @staticmethod
    def get_no_services_message(language: str) -> str:
        messages = {
            'ru': "😔 В этой категории пока нет услуг.",
            'en': "😔 No services in this category yet.",
            'tr': "😔 Bu kategoride henüz hizmet yok."
        }
        return messages.get(language, messages['ru'])
    
    @staticmethod
    def get_selected_services_message(language: str, services: List[Dict[str, Any]], total_price: float) -> str:
        if language == 'ru':
            message = "✅ Выбранные услуги:\n\n"
        elif language == 'en':
            message = "✅ Selected services:\n\n"
        else:  # tr
            message = "✅ Seçilen hizmetler:\n\n"
        
        for service in services:
            if language == 'ru':
                message += f"• {service['title']} - {service['duration_minutes']} мин. - {service['price']}₺\n"
            elif language == 'en':
                message += f"• {service['title']} - {service['duration_minutes']} min. - {service['price']}₺\n"
            else:  # tr
                message += f"• {service['title']} - {service['duration_minutes']} dk. - {service['price']}₺\n"
        
        if language == 'ru':
            message += f"\n💰 Общая стоимость: {total_price}₺"
        elif language == 'en':
            message += f"\n💰 Total cost: {total_price}₺"
        else:  # tr
            message += f"\n💰 Toplam tutar: {total_price}₺"
        
        return message
    
    # Дата
    @staticmethod
    def get_date_selection_message(language: str) -> str:
        messages = {
            'ru': "📅 Выберите дату для записи:",
            'en': "📅 Select date for booking:",
            'tr': "📅 Randevu için tarih seçin:"
        }
        return messages.get(language, messages['ru'])
    
    # Мастера
    @staticmethod
    def get_master_choice_message(language: str) -> str:
        messages = {
            'ru': "👨‍💻 Как вы хотите записаться?",
            'en': "👨‍💻 How would you like to book?",
            'tr': "👨‍💻 Nasıl randevu almak istiyorsunuz?"
        }
        return messages.get(language, messages['ru'])
    
    @staticmethod
    def get_masters_list_message(language: str) -> str:
        messages = {
            'ru': "👨‍💻 Выберите мастера:",
            'en': "👨‍💻 Select a master:",
            'tr': "👨‍💻 Bir usta seçin:"
        }
        return messages.get(language, messages['ru'])
    
    @staticmethod
    def get_no_masters_message(language: str) -> str:
        messages = {
            'ru': "😔 На выбранные услуги нет доступных мастеров.",
            'en': "😔 No available masters for selected services.",
            'tr': "😔 Seçilen hizmetler için uygun usta yok."
        }
        return messages.get(language, messages['ru'])
    
    @staticmethod
    def get_master_info_message(language: str, master: Dict[str, Any]) -> str:
        name = f"{master.get('first_name', '')} {master.get('last_name', '')}".strip()
        qualification = master.get('qualification', '')
        description = master.get('description', '')
        
        if language == 'ru':
            message = f"👨‍💻 {name}\n"
            if qualification:
                message += f"🎓 Квалификация: {qualification}\n"
            if description:
                message += f"📝 О мастере: {description}\n"
        elif language == 'en':
            message = f"👨‍💻 {name}\n"
            if qualification:
                message += f"🎓 Qualification: {qualification}\n"
            if description:
                message += f"📝 About: {description}\n"
        else:  # tr
            message = f"👨‍💻 {name}\n"
            if qualification:
                message += f"🎓 Nitelik: {qualification}\n"
            if description:
                message += f"📝 Hakkında: {description}\n"
        
        return message
    
    # Время
    @staticmethod
    def get_time_selection_message(language: str, date_str: str, master_name: str = None) -> str:
        date_obj = date.fromisoformat(date_str)
        
        if language == 'ru':
            if master_name:
                message = f"⏰ Выберите время на {date_obj.strftime('%d.%m.%Y')} для мастера {master_name}:"
            else:
                message = f"⏰ Выберите время на {date_obj.strftime('%d.%m.%Y')} (любой доступный мастер):"
        elif language == 'en':
            if master_name:
                message = f"⏰ Select time for {date_obj.strftime('%Y-%m-%d')} with master {master_name}:"
            else:
                message = f"⏰ Select time for {date_obj.strftime('%Y-%m-%d')} (any available master):"
        else:  # tr
            if master_name:
                message = f"⏰ {date_obj.strftime('%d.%m.%Y')} tarihi için {master_name} usta ile saat seçin:"
            else:
                message = f"⏰ {date_obj.strftime('%d.%m.%Y')} tarihi için saat seçin (uygun herhangi bir usta):"
        
        return message
    
    @staticmethod
    def get_no_time_slots_message(language: str) -> str:
        messages = {
            'ru': "😔 На выбранную дату нет свободного времени. Попробуйте другую дату.",
            'en': "😔 No available time slots for selected date. Try another date.",
            'tr': "😔 Seçilen tarih için uygun saat yok. Başka bir tarih deneyin."
        }
        return messages.get(language, messages['ru'])
    
    # Подтверждение записи
    @staticmethod
    def get_appointment_confirmation_message(language: str, appointment_details: Dict[str, Any]) -> str:
        date_str = appointment_details['date']
        time_str = appointment_details['time']
        master_name = appointment_details.get('master_name', 'Любой мастер' if language == 'ru' else 'Any master' if language == 'en' else 'Uygun herhangi usta')
        services = appointment_details['services']
        total_price = appointment_details['total_price']
        
        date_obj = date.fromisoformat(date_str)
        
        if language == 'ru':
            message = f"📋 Подтвердите запись:\n\n"
            message += f"📅 Дата: {date_obj.strftime('%d.%m.%Y')}\n"
            message += f"⏰ Время: {time_str}\n"
            message += f"👨‍💻 Мастер: {master_name}\n\n"
            message += "💅 Услуги:\n"
            for service in services:
                message += f"• {service['title']} - {service['price']}₺\n"
            message += f"\n💰 Итого: {total_price}₺"
        elif language == 'en':
            message = f"📋 Confirm booking:\n\n"
            message += f"📅 Date: {date_obj.strftime('%Y-%m-%d')}\n"
            message += f"⏰ Time: {time_str}\n"
            message += f"👨‍💻 Master: {master_name}\n\n"
            message += "💅 Services:\n"
            for service in services:
                message += f"• {service['title']} - {service['price']}₺\n"
            message += f"\n💰 Total: {total_price}₺"
        else:  # tr
            message = f"📋 Randevuyu onaylayın:\n\n"
            message += f"📅 Tarih: {date_obj.strftime('%d.%m.%Y')}\n"
            message += f"⏰ Saat: {time_str}\n"
            message += f"👨‍💻 Usta: {master_name}\n\n"
            message += "💅 Hizmetler:\n"
            for service in services:
                message += f"• {service['title']} - {service['price']}₺\n"
            message += f"\n💰 Toplam: {total_price}₺"
        
        return message
    
    @staticmethod
    def get_appointment_success_message(language: str, appointment_id: int) -> str:
        messages = {
            'ru': f"✅ Запись #{appointment_id} успешно создана!\n\n"
                  f"📅 Вы получите уведомление за 8 часов и за 2 часа до записи.",
            'en': f"✅ Booking #{appointment_id} created successfully!\n\n"
                  f"📅 You will receive notifications 8 hours and 2 hours before the appointment.",
            'tr': f"✅ Randevu #{appointment_id} başarıyla oluşturuldu!\n\n"
                  f"📅 Randevudan 8 saat ve 2 saat önce bildirim alacaksınız."
        }
        return messages.get(language, messages['ru'])
    
    # Мои записи
    @staticmethod
    def get_my_appointments_message(language: str) -> str:
        messages = {
            'ru': "📋 Ваши записи:",
            'en': "📋 Your appointments:",
            'tr': "📋 Randevularınız:"
        }
        return messages.get(language, messages['ru'])
    
    @staticmethod
    def get_no_appointments_message(language: str) -> str:
        messages = {
            'ru': "😔 У вас пока нет записей.",
            'en': "😔 You don't have any appointments yet.",
            'tr': "😔 Henüz randevunuz yok."
        }
        return messages.get(language, messages['ru'])
    
    @staticmethod
    def get_appointment_detail_message(language: str, appointment: Dict[str, Any]) -> str:
        date_str = appointment['appointment_date']
        time_str = appointment['start_time']
        status = appointment['status']
        services = appointment.get('services_titles', '')
        master_name = f"{appointment.get('master_first_name', '')} {appointment.get('master_last_name', '')}".strip()
        
        date_obj = date.fromisoformat(date_str)
        
        # Перевод статуса
        status_translations = {
            'ru': {
                'pending': '⏳ Ожидание',
                'confirmed': '✅ Подтверждено',
                'cancelled': '❌ Отменено',
                'completed': '✅ Выполнено',
                'in_progress': '⚡ В процессе'
            },
            'en': {
                'pending': '⏳ Pending',
                'confirmed': '✅ Confirmed',
                'cancelled': '❌ Cancelled',
                'completed': '✅ Completed',
                'in_progress': '⚡ In Progress'
            },
            'tr': {
                'pending': '⏳ Beklemede',
                'confirmed': '✅ Onaylandı',
                'cancelled': '❌ İptal Edildi',
                'completed': '✅ Tamamlandı',
                'in_progress': '⚡ Devam Ediyor'
            }
        }
        
        status_text = status_translations[language].get(status, status)
        
        if language == 'ru':
            message = f"📋 Запись #{appointment['id']}\n\n"
            message += f"📅 Дата: {date_obj.strftime('%d.%m.%Y')}\n"
            message += f"⏰ Время: {time_str}\n"
            message += f"👨‍💻 Мастер: {master_name if master_name else 'Любой доступный'}\n"
            message += f"📝 Услуги: {services}\n"
            message += f"📊 Статус: {status_text}"
        elif language == 'en':
            message = f"📋 Appointment #{appointment['id']}\n\n"
            message += f"📅 Date: {date_obj.strftime('%Y-%m-%d')}\n"
            message += f"⏰ Time: {time_str}\n"
            message += f"👨‍💻 Master: {master_name if master_name else 'Any available'}\n"
            message += f"📝 Services: {services}\n"
            message += f"📊 Status: {status_text}"
        else:  # tr
            message = f"📋 Randevu #{appointment['id']}\n\n"
            message += f"📅 Tarih: {date_obj.strftime('%d.%m.%Y')}\n"
            message += f"⏰ Saat: {time_str}\n"
            message += f"👨‍💻 Usta: {master_name if master_name else 'Uygun herhangi'}\n"
            message += f"📝 Hizmetler: {services}\n"
            message += f"📊 Durum: {status_text}"
        
        return message
    
    @staticmethod
    def get_cancel_success_message(language: str) -> str:
        messages = {
            'ru': "✅ Запись успешно отменена.",
            'en': "✅ Appointment successfully cancelled.",
            'tr': "✅ Randevu başarıyla iptal edildi."
        }
        return messages.get(language, messages['ru'])
    
    # Уведомления
    @staticmethod
    def get_notification_8h_message(language: str, appointment: Dict[str, Any]) -> str:
        date_str = appointment['appointment_date']
        time_str = appointment['start_time']
        
        if language == 'ru':
            return f"🔔 Напоминание!\n\nЗапись через 8 часов:\n📅 {date_str} в {time_str}"
        elif language == 'en':
            return f"🔔 Reminder!\n\nAppointment in 8 hours:\n📅 {date_str} at {time_str}"
        else:  # tr
            return f"🔔 Hatırlatma!\n\n8 saat sonra randevu:\n📅 {date_str} saat {time_str}"
    
    @staticmethod
    def get_notification_2h_message(language: str, appointment: Dict[str, Any]) -> str:
        date_str = appointment['appointment_date']
        time_str = appointment['start_time']
        
        if language == 'ru':
            return f"🔔 Напоминание!\n\nЗапись через 2 часа:\n📅 {date_str} в {time_str}"
        elif language == 'en':
            return f"🔔 Reminder!\n\nAppointment in 2 hours:\n📅 {date_str} at {time_str}"
        else:  # tr
            return f"🔔 Hatırlatma!\n\n2 saat sonra randevu:\n📅 {date_str} saat {time_str}"
    
    @staticmethod
    def get_master_notification_message(language: str, appointment: Dict[str, Any]) -> str:
        client_name = f"{appointment.get('client_first_name', '')} {appointment.get('client_last_name', '')}".strip()
        date_str = appointment['appointment_date']
        time_str = appointment['start_time']
        services = appointment.get('services_titles', '')
        
        if language == 'ru':
            return f"📥 Новая запись!\n\n👤 Клиент: {client_name}\n📅 Дата: {date_str}\n⏰ Время: {time_str}\n💅 Услуги: {services}"
        elif language == 'en':
            return f"📥 New booking!\n\n👤 Client: {client_name}\n📅 Date: {date_str}\n⏰ Time: {time_str}\n💅 Services: {services}"
        else:  # tr
            return f"📥 Yeni randevu!\n\n👤 Müşteri: {client_name}\n📅 Tarih: {date_str}\n⏰ Saat: {time_str}\n💅 Hizmetler: {services}"
    
    # Ошибки
    @staticmethod
    def get_error_message(language: str) -> str:
        messages = {
            'ru': "😔 Произошла ошибка. Пожалуйста, попробуйте позже.",
            'en': "😔 An error occurred. Please try again later.",
            'tr': "😔 Bir hata oluştu. Lütfen daha sonra tekrar deneyin."
        }
        return messages.get(language, messages['ru'])
    
    @staticmethod
    def get_unknown_command_message(language: str) -> str:
        messages = {
            'ru': "🤔 Неизвестная команда. Используйте кнопки меню.",
            'en': "🤔 Unknown command. Please use menu buttons.",
            'tr': "🤔 Bilinmeyen komut. Lütfen menü düğmelerini kullanın."
        }
        return messages.get(language, messages['ru'])