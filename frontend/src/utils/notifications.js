// frontend/src/utils/notifications.js
export const showNotification = (type, title, message) => {
  // Можно использовать Ant Design notification, Toast, или другой UI компонент
  if (typeof window !== 'undefined') {
    // Пример для Ant Design
    if (window.message && window.message[type]) {
      window.message[type]({
        content: message,
        duration: 3,
      });
    }
    
    // Или выводим в консоль для отладки
    console.log(`📢 ${type.toUpperCase()}: ${title} - ${message}`);
  }
};

// Экспортируем в глобальную область видимости для использования в интерцепторах
if (typeof window !== 'undefined') {
  window.showNotification = showNotification;
}