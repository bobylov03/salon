// services/api.js
import axios from 'axios';

// Базовый URL API - пустая строка = относительные пути (тот же хост)
const API_URL = import.meta.env.VITE_API_URL ?? '';

console.log('🔧 API Configuration:');
console.log('   • API_URL:', API_URL);
console.log('   • Mode:', import.meta.env.MODE);

// Создаем экземпляр axios
const api = axios.create({
  baseURL: API_URL,
  timeout: 30000, // 30 секунд для загрузки файлов
  headers: {
    'Content-Type': 'application/json',
  },
});

// Логирование запросов (для отладки)
api.interceptors.request.use(
  (config) => {
    console.log(`📤 ${config.method?.toUpperCase()} ${config.url}`);
    
    // Логируем параметры запроса
    if (config.params) {
      console.log('   Params:', config.params);
    }
    
    // Логируем данные FormData
    if (config.data instanceof FormData) {
      console.log('   📄 FormData contents:');
      for (let pair of config.data.entries()) {
        console.log(`     ${pair[0]}:`, pair[0] === 'photo' ? '[FILE]' : pair[1]);
      }
    } else if (config.data) {
      console.log('   Data:', config.data);
    }
    
    return config;
  },
  (error) => {
    console.error('❌ Request error:', error);
    return Promise.reject(error);
  }
);

// Логирование ответов
api.interceptors.response.use(
  (response) => {
    console.log(`📥 ${response.status} ${response.config.url}`);
    if (response.config.method?.toUpperCase() === 'GET') {
      console.log('   Response data sample:', 
        Array.isArray(response.data) 
          ? `[${response.data.length} items]` 
          : typeof response.data === 'object' 
            ? JSON.stringify(response.data).substring(0, 200) + '...'
            : response.data
      );
    }
    return response;
  },
  (error) => {
    console.error('❌ API Error:', {
      url: error.config?.url,
      method: error.config?.method,
      status: error.response?.status,
      data: error.response?.data,
      message: error.response?.data?.detail || error.response?.data?.message || error.message,
    });
    return Promise.reject(error);
  }
);

// ==================== AUTH API ====================
export const authAPI = {
  login: async (username, password) => {
    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);
    return api.post('/auth/login', formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    });
  },

  // Выход
  logout: () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    localStorage.removeItem('isLoggedIn');
    console.log('👋 User logged out');
  },
  
  // Получение текущего пользователя
  getCurrentUser: () => {
    const userStr = localStorage.getItem('user');
    return userStr ? JSON.parse(userStr) : null;
  },
  
  // Проверка аутентификации
  isAuthenticated: () => {
    return localStorage.getItem('isLoggedIn') === 'true';
  }
};

// ==================== MASTERS API ====================
export const mastersAPI = {
  // Получение списка мастеров
  getMasters: (params = {}) => {
    const defaultParams = {
      page: params.page || 1,
      per_page: params.per_page || 10,
      ...params
    };
    console.log('👨‍💼 Fetching masters with params:', defaultParams);
    return api.get('/masters', { params: defaultParams });
  },
  
  // Получение мастера по ID
  getMasterById: (id) => {
    console.log('🔍 Fetching master by ID:', id);
    return api.get(`/masters/${id}`);
  },
  
  // Создание мастера
  createMaster: (formData) => {
    console.log('➕ Creating master');
    return api.post('/masters', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      timeout: 60000, // 60 секунд для загрузки фото
    });
  },
  
  // Обновление мастера
  updateMaster: (id, formData) => {
    console.log('✏️ Updating master:', id);
    return api.put(`/masters/${id}`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      timeout: 60000,
    });
  },
  
  // Удаление мастера
  deleteMaster: (id) => {
    console.log('🗑️ Deleting master:', id);
    return api.delete(`/masters/${id}`);
  },
  
  // Переключение статуса мастера
  toggleMasterStatus: async (id, isActive) => {
    console.log('🔄 Toggling master status:', { id, isActive });
    try {
      // Сначала получаем текущего мастера
      const masterResponse = await mastersAPI.getMasterById(id);
      const master = masterResponse.data;
      
      // Создаем formData для обновления
      const formData = new FormData();
      formData.append('first_name', master.first_name || '');
      formData.append('last_name', master.last_name || '');
      if (master.phone) formData.append('phone', master.phone);
      if (master.email) formData.append('email', master.email);
      if (master.telegram_id) formData.append('telegram_id', master.telegram_id);
      if (master.qualification) formData.append('qualification', master.qualification);
      if (master.description) formData.append('description', master.description);
      formData.append('is_active', isActive ? 'true' : 'false');
      
      return await mastersAPI.updateMaster(id, formData);
    } catch (error) {
      console.error('Error toggling master status:', error);
      throw error;
    }
  },
  
  // Получение записей мастера
  getMasterAppointments: (id, params = {}) => {
    console.log('📅 Fetching master appointments:', id);
    return api.get(`/masters/${id}/appointments`, { params });
  },
  
  // Получение отзывов мастера
  getMasterReviews: (id, params = {}) => {
    console.log('⭐ Fetching master reviews:', id);
    return api.get(`/masters/${id}/reviews`, { params });
  },
  
  // Получение услуг мастера
  getMasterServices: (id, params = {}) => {
    console.log('🔧 Fetching master services:', id);
    return api.get(`/masters/${id}/services`, { params });
  },
  
  // Добавление услуги мастеру
  addServiceToMaster: (masterId, serviceId, isPrimary = false) => {
    console.log('➕ Adding service to master:', { masterId, serviceId, isPrimary });
    return api.post(`/masters/${masterId}/services`, null, {
      params: {
        service_id: serviceId,
        is_primary: isPrimary
      }
    });
  },
  
  // Удаление услуги у мастера
  removeServiceFromMaster: (masterId, serviceId) => {
    console.log('➖ Removing service from master:', { masterId, serviceId });
    return api.delete(`/masters/${masterId}/services/${serviceId}`);
  },
  
  // Получение доступных услуг для мастера
  getAvailableServicesForMaster: (masterId, params = {}) => {
    console.log('📋 Getting available services for master:', masterId);
    return api.get(`/masters/${masterId}/available-services`, { params });
  },
};

// ==================== SERVICES API (ОБНОВЛЕННЫЙ С ИЕРАРХИЧЕСКИМИ КАТЕГОРИЯМИ) ====================
export const servicesAPI = {
  // ==================== КАТЕГОРИИ ====================
  
  // Получение категорий с древовидной структурой
  getCategories: (params = {}) => {
    console.log('📁 Fetching categories with params:', params);
    return api.get('/services/categories', { params });
  },
  
  // Получение категорий в формате дерева для TreeSelect
  getCategoriesTree: (params = {}) => {
    console.log('🌳 Fetching categories tree');
    return api.get('/services/categories/tree', { params });
  },
  
  // Получение информации о конкретной категории
  getCategory: (categoryId, params = {}) => {
    console.log('🔍 Fetching category:', categoryId);
    return api.get(`/services/categories/${categoryId}`, { params });
  },
  
  // Создание новой категории
  createCategory: (data) => {
    console.log('➕ Creating category:', data);
    return api.post('/services/categories', data);
  },
  
  // Обновление категории
  updateCategory: (categoryId, data) => {
    console.log('✏️ Updating category:', categoryId, data);
    return api.put(`/services/categories/${categoryId}`, data);
  },
  
  // Удаление категории
  deleteCategory: (categoryId) => {
    console.log('🗑️ Deleting category:', categoryId);
    return api.delete(`/services/categories/${categoryId}`);
  },
  
  // Получение статистики по категории
  getCategoryStats: (categoryId, params = {}) => {
    console.log('📊 Fetching category stats:', categoryId);
    return api.get(`/services/categories/${categoryId}/stats`, { params });
  },
  
  // ==================== УСЛУГИ ====================
  
  // Получение услуг с пагинацией и фильтрацией
  getServices: (params = {}) => {
    const defaultParams = {
      page: params.page || 1,
      per_page: params.per_page || 20,
      language: 'ru',
      ...params
    };
    console.log('🔧 Fetching services with params:', defaultParams);
    return api.get('/services', { params: defaultParams });
  },
  
  // Получение услуги по ID
  getService: (serviceId, params = {}) => {
    console.log('🔍 Fetching service:', serviceId);
    return api.get(`/services/${serviceId}`, { params });
  },
  
  // Создание услуги
  createService: (data) => {
    console.log('➕ Creating service:', data);
    return api.post('/services', data);
  },
  
  // Обновление услуги
  updateService: (serviceId, data) => {
    console.log('✏️ Updating service:', serviceId, data);
    return api.put(`/services/${serviceId}`, data);
  },
  
  // Удаление (деактивация) услуги
  deleteService: (serviceId) => {
    console.log('🗑️ Deleting service:', serviceId);
    return api.delete(`/services/${serviceId}`);
  },
  
  // Получение переводов услуги
  getServiceTranslations: (serviceId) => {
    console.log('🌐 Fetching service translations:', serviceId);
    return api.get(`/services/${serviceId}/translations`);
  },
  
  // Поиск услуг (автодополнение)
  searchServices: (query, params = {}) => {
    console.log('🔎 Searching services:', query);
    return api.get('/services/search/suggestions', { 
      params: { q: query, ...params } 
    });
  },
  
  // Получение услуг по категории (с подкатегориями)
  getServicesByCategory: (categoryId, params = {}) => {
    console.log('📦 Fetching services by category:', categoryId);
    return api.get(`/services/categories/${categoryId}/services`, { params });
  },
  
  // Получение мастеров, предоставляющих услугу
  getServiceMasters: (serviceId, params = {}) => {
    console.log('👨‍💼 Fetching masters for service:', serviceId);
    return api.get(`/services/${serviceId}/masters`, { params });
  },
  
  // ==================== УТИЛИТЫ ====================
  
  // Построение иерархических данных для TreeSelect
  buildCategoryTreeData: async (language = 'ru') => {
    try {
      const response = await api.get('/services/categories/tree', {
        params: { language, include_inactive: false }
      });
      
      const categories = response.data || [];
      
      // Добавляем опцию для корневой категории
      const treeData = [
        { 
          id: null, 
          value: null, 
          title: 'Корневая категория (без родителя)', 
          label: 'Корневая категория (без родителя)', 
          isLeaf: true 
        },
        ...categories.map(category => ({
          id: category.id,
          value: category.id,
          title: category.label || category.title,
          label: category.label || category.title,
          isLeaf: category.is_leaf || false,
          children: category.children || [],
        }))
      ];
      
      console.log('🌳 Built tree data with', treeData.length, 'items');
      return treeData;
    } catch (error) {
      console.error('❌ Error building category tree:', error);
      // Возвращаем хотя бы корневую категорию
      return [
        { 
          id: null, 
          value: null, 
          title: 'Корневая категория (без родителя)', 
          label: 'Корневая категория (без родителя)', 
          isLeaf: true 
        }
      ];
    }
  },
  
  // Получение плоского списка конечных категорий (для выбора услуг)
  getLeafCategories: async (language = 'ru') => {
    try {
      const response = await api.get('/services/categories/tree', {
        params: { language, include_inactive: false }
      });
      
      const categories = response.data || [];
      
      // Рекурсивно собираем только конечные категории
      const collectLeafCategories = (items, result = []) => {
        items.forEach(item => {
          if (item.is_leaf || (!item.children || item.children.length === 0)) {
            result.push({
              id: item.id,
              value: item.id,
              title: item.label || item.title,
              label: item.label || item.title,
            });
          }
          if (item.children && item.children.length > 0) {
            collectLeafCategories(item.children, result);
          }
        });
        return result;
      };
      
      const leafCategories = collectLeafCategories(categories);
      console.log('🍃 Found', leafCategories.length, 'leaf categories');
      return leafCategories;
    } catch (error) {
      console.error('❌ Error fetching leaf categories:', error);
      return [];
    }
  },
  
  // Проверка, можно ли добавить услугу в категорию
  canAddServiceToCategory: async (categoryId) => {
    try {
      const response = await api.get(`/services/categories/${categoryId}/stats`);
      const stats = response.data;
      
      // Нельзя добавить услугу в категорию, у которой есть подкатегории
      const canAdd = stats.subcategory_count === 0;
      console.log(`📋 Can add service to category ${categoryId}:`, canAdd);
      return canAdd;
    } catch (error) {
      console.error('❌ Error checking category:', error);
      return false;
    }
  },
};

// ==================== APPOINTMENTS API ====================
export const appointmentsAPI = {
  // Получение записей
  getAppointments: (params = {}) => {
    console.log('📅 Fetching appointments with params:', params);
    return api.get('/appointments', { params });
  },
  
  // Создание записи
  createAppointment: (data) => {
    console.log('➕ Creating appointment:', data);
    return api.post('/appointments', data);
  },
  
  // Обновление записи
  updateAppointment: (id, data) => {
    console.log('✏️ Updating appointment:', id);
    return api.put(`/appointments/${id}`, data);
  },
  
  // Обновление статуса записи
  updateAppointmentStatus: (id, status) => {
    console.log('🔄 Updating appointment status:', { id, status });
    return api.put(`/appointments/${id}/status`, null, { params: { status } });
  },
  
  // Сегодняшние записи
  getTodayAppointments: () => {
    console.log('📅 Fetching today appointments');
    return api.get('/appointments/today');
  },
  
  // Предстоящие записи
  getUpcomingAppointments: (days = 7) => {
    console.log('📅 Fetching upcoming appointments for', days, 'days');
    return api.get('/appointments/upcoming', { params: { days } });
  },
  
  // Удаление записи
  deleteAppointment: (id) => {
    console.log('🗑️ Deleting appointment:', id);
    return api.delete(`/appointments/${id}`);
  },
};

// ==================== CLIENTS API ====================
export const clientsAPI = {
  // Получение клиентов
  getClients: (params = {}) => {
    console.log('👥 Fetching clients with params:', params);
    return api.get('/clients', { params });
  },
  
  // Создание клиента (JSON версия)
  createClient: (data) => {
    console.log('➕ Creating client:', data);
    return api.post('/clients', data);
  },
  
  // Создание клиента (Form версия)
  createClientForm: (formData) => {
    console.log('➕ Creating client via form');
    return api.post('/clients/form', formData);
  },
  
  // Получение клиента по ID
  getClient: (id) => {
    console.log('🔍 Fetching client:', id);
    return api.get(`/clients/${id}`);
  },
  
  // Обновление клиента
  updateClient: (id, data) => {
    console.log('✏️ Updating client:', id);
    return api.put(`/clients/${id}`, data);
  },
  
  // Удаление клиента
  deleteClient: (id) => {
    console.log('🗑️ Deleting client:', id);
    return api.delete(`/clients/${id}`);
  },
  
  // Получение статистики клиента
  getClientStats: (id) => {
    console.log('📊 Fetching client stats:', id);
    return api.get(`/clients/${id}/stats`);
  },
  
  // Получение последних записей клиента
  getClientRecentAppointments: (id, limit = 5) => {
    console.log('📅 Fetching client recent appointments:', { id, limit });
    return api.get(`/clients/${id}/recent-appointments`, { params: { limit } });
  },
  
  // Поиск клиентов
  searchClients: (query) => {
    console.log('🔎 Searching clients:', query);
    return api.get('/clients/search', { params: { q: query } });
  },
};

// ==================== ANALYTICS API ====================
export const analyticsAPI = {
  // Получение статистики для дашборда
  getDashboardStats: (periodDays = 30) => {
    console.log('📊 Fetching dashboard stats for', periodDays, 'days');
    return api.get('/analytics/dashboard', { params: { period_days: periodDays } });
  },
  
  // Получение загрузки мастеров
  getMastersLoad: (days = 7) => {
    console.log('📈 Fetching masters load for', days, 'days');
    return api.get('/analytics/masters-load', { params: { days } });
  },
  
  // Получение популярности услуг
  getServicesPopularity: (periodDays = 30) => {
    console.log('🔥 Fetching services popularity for', periodDays, 'days');
    return api.get('/analytics/services-popularity', { params: { period_days: periodDays } });
  },
  
  // Получение последних записей
  getRecentAppointments: (limit = 10) => {
    console.log('🔄 Fetching recent appointments:', limit);
    return api.get('/analytics/recent-appointments', { params: { limit } });
  },
  
  // Тестовый endpoint
  testAnalytics: () => {
    console.log('🧪 Testing analytics endpoint');
    return api.get('/analytics/test');
  },
};

// ==================== BONUSES API ====================
export const bonusesAPI = {
  // Получение баланса клиента
  getClientBalance: (clientId) => {
    console.log('💰 Fetching client balance:', clientId);
    return api.get(`/bonuses/clients/${clientId}/balance`);
  },
  
  // Получение истории бонусов
  getBonusHistory: (clientId, params = {}) => {
    console.log('📜 Fetching bonus history for client:', clientId);
    return api.get(`/bonuses/clients/${clientId}/history`, { params });
  },
};

// ==================== УТИЛИТЫ ====================

// Создание FormData для мастера
export const createMasterFormData = (masterData, file) => {
  const formData = new FormData();
  
  // Обязательные поля
  formData.append('first_name', masterData.first_name || '');
  formData.append('last_name', masterData.last_name || '');
  formData.append('is_active', masterData.is_active !== false ? 'true' : 'false');
  
  // Опциональные поля
  if (masterData.qualification) {
    formData.append('qualification', masterData.qualification);
  }
  
  if (masterData.description) {
    formData.append('description', masterData.description);
  }
  
  if (masterData.phone) {
    formData.append('phone', masterData.phone);
  }
  
  if (masterData.email) {
    formData.append('email', masterData.email);
  }
  
  // ВАЖНО: Добавляем telegram_id
  if (masterData.telegram_id) {
    formData.append('telegram_id', masterData.telegram_id);
  }
  
  // Файл фото
  if (file) {
    formData.append('photo', file);
  }
  
  // Флаг удаления фото (для редактирования)
  if (masterData.remove_photo) {
    formData.append('remove_photo', 'true');
  }
  
  // Логирование
  console.log('📄 Created FormData for master:', {
    first_name: masterData.first_name,
    last_name: masterData.last_name,
    phone: masterData.phone || 'not set',
    telegram_id: masterData.telegram_id || 'not set',
    email: masterData.email || 'not set',
    hasPhoto: !!file,
    remove_photo: !!masterData.remove_photo
  });
  
  return formData;
};

// Создание данных для категории
export const createCategoryData = (formValues) => {
  const translations = [
    { language: 'ru', title: formValues.title_ru },
    { language: 'en', title: formValues.title_en || formValues.title_ru },
    { language: 'tr', title: formValues.title_tr || formValues.title_ru },
  ];
  
  return {
    parent_id: formValues.parent_id || null,
    is_active: formValues.is_active !== false,
    translations: translations
  };
};

// Создание данных для услуги
export const createServiceData = (formValues) => {
  const translations = [
    { 
      language: 'ru', 
      title: formValues.title_ru,
      description: formValues.description_ru || ''
    },
    { 
      language: 'en', 
      title: formValues.title_en || formValues.title_ru,
      description: formValues.description_en || formValues.description_ru || ''
    },
    { 
      language: 'tr', 
      title: formValues.title_tr || formValues.title_ru,
      description: formValues.description_tr || formValues.description_ru || ''
    },
  ];
  
  return {
    category_id: formValues.category_id,
    duration_minutes: Number(formValues.duration_minutes),
    price: Number(formValues.price),
    is_active: formValues.is_active !== false,
    translations: translations
  };
};

// Обработка ошибок API
export const handleApiError = (error, customMessage = null) => {
  let message = customMessage || 'Произошла ошибка';
  
  if (error.response) {
    const { status, data } = error.response;
    
    console.error('API Error Details:', {
      status,
      data,
      url: error.config?.url,
      method: error.config?.method
    });
    
    switch (status) {
      case 400:
        message = data.detail || data.message || 'Неверный запрос';
        break;
      case 401:
        message = 'Требуется авторизация';
        break;
      case 403:
        message = 'Доступ запрещен';
        break;
      case 404:
        message = 'Ресурс не найден';
        break;
      case 409:
        message = data.detail || 'Конфликт данных';
        break;
      case 422:
        message = 'Ошибка валидации данных: ' + (data.detail || '');
        break;
      case 500:
        message = 'Внутренняя ошибка сервера';
        break;
      default:
        message = data.detail || data.message || `Ошибка ${status}`;
    }
  } else if (error.code === 'ECONNABORTED') {
    message = 'Превышено время ожидания';
  } else if (error.message === 'Network Error') {
    message = `Не удается подключиться к серверу: ${API_URL}`;
  } else {
    message = error.message;
  }
  
  console.error('⚠️ API Error handled:', message);
  return message;
};

// Проверка состояния API
export const checkApiHealth = async () => {
  try {
    console.log('🏥 Checking API health...');
    
    const results = {
      apiUrl: API_URL,
      isOnline: false,
      endpoints: {},
      error: null,
      timestamp: new Date().toISOString()
    };
    
    // Проверяем корневой endpoint
    try {
      const response = await api.get('/', { timeout: 5000 });
      results.endpoints.root = { success: true, data: response.data };
      console.log('✅ Root endpoint is OK');
    } catch (error) {
      results.endpoints.root = { success: false, error: error.message };
      console.log('❌ Root endpoint error:', error.message);
    }
    
    // Проверяем health endpoint
    try {
      const response = await api.get('/health', { timeout: 5000 });
      results.endpoints.health = { success: true, data: response.data };
      console.log('✅ Health endpoint is OK');
    } catch (error) {
      results.endpoints.health = { success: false, error: error.message };
      console.log('❌ Health endpoint error:', error.message);
    }
    
    // Проверяем masters endpoint
    try {
      const response = await api.get('/masters?page=1&per_page=1', { timeout: 5000 });
      results.endpoints.masters = { 
        success: true, 
        count: response.data?.total || 0,
        sample: response.data?.items?.[0] 
      };
      console.log('✅ Masters endpoint is OK');
    } catch (error) {
      results.endpoints.masters = { success: false, error: error.message };
      console.log('❌ Masters endpoint error:', error.message);
    }
    
    // Проверяем services endpoint
    try {
      const response = await api.get('/services?page=1&per_page=1', { timeout: 5000 });
      results.endpoints.services = { 
        success: true, 
        count: response.data?.total || 0 
      };
      console.log('✅ Services endpoint is OK');
    } catch (error) {
      results.endpoints.services = { success: false, error: error.message };
      console.log('❌ Services endpoint error:', error.message);
    }
    
    // Определяем общий статус
    results.isOnline = Object.values(results.endpoints).some(endpoint => endpoint.success);
    
    if (results.isOnline) {
      console.log('🎉 API is online and working!');
    } else {
      results.error = `API недоступен по адресу: ${API_URL}`;
      console.log('❌ API is not responding');
    }
    
    return results;
    
  } catch (error) {
    console.error('💥 API health check failed:', error);
    return {
      apiUrl: API_URL,
      isOnline: false,
      error: `Ошибка проверки: ${error.message}`,
      timestamp: new Date().toISOString()
    };
  }
};

// Тестовые функции
export const testAPI = {
  // Тест подключения
  testConnection: async () => {
    try {
      const response = await api.get('/');
      console.log('✅ API connection test passed:', response.data);
      return { success: true, data: response.data };
    } catch (error) {
      console.error('❌ API connection test failed:', error);
      return { success: false, error: handleApiError(error) };
    }
  },
  
  // Тест создания мастера
  testCreateMaster: async () => {
    try {
      const formData = createMasterFormData({
        first_name: 'Тест',
        last_name: 'Мастер',
        qualification: 'Тестовая квалификация',
        phone: '+79990000000',
        telegram_id: '@testmaster',
        is_active: true
      }, null);
      
      const response = await mastersAPI.createMaster(formData);
      console.log('✅ Master creation test passed:', response.data);
      return { success: true, data: response.data };
    } catch (error) {
      console.error('❌ Master creation test failed:', error);
      return { success: false, error: handleApiError(error) };
    }
  },
  
  // Тест создания категории
  testCreateCategory: async () => {
    try {
      const categoryData = createCategoryData({
        title_ru: 'Тестовая категория',
        is_active: true,
        parent_id: null
      });
      
      const response = await servicesAPI.createCategory(categoryData);
      console.log('✅ Category creation test passed:', response.data);
      return { success: true, data: response.data };
    } catch (error) {
      console.error('❌ Category creation test failed:', error);
      return { success: false, error: handleApiError(error) };
    }
  },
  
  // Тест загрузки файла
  testUpload: async (formData) => {
    try {
      const response = await api.post('/test/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      console.log('✅ Upload test passed:', response.data);
      return { success: true, data: response.data };
    } catch (error) {
      console.error('❌ Upload test failed:', error);
      return { success: false, error: handleApiError(error) };
    }
  }
};

// Функция для инициализации демо-данных
export const initializeDemoData = async () => {
  console.log('🎬 Initializing demo data...');
  
  try {
    // Проверяем наличие категорий
    const categoriesResponse = await servicesAPI.getCategories();
    const categories = categoriesResponse.data || [];
    
    if (categories.length === 0) {
      console.log('📁 No categories found, creating demo categories...');
      
      // Создаем демо-категории
      const demoCategories = [
        {
          title_ru: 'Парикмахерские услуги',
          title_en: 'Hair Services',
          title_tr: 'Kuaför Hizmetleri',
          is_active: true,
          parent_id: null
        },
        {
          title_ru: 'Маникюр и педикюр',
          title_en: 'Manicure & Pedicure',
          title_tr: 'Manikür & Pedikür',
          is_active: true,
          parent_id: null
        },
        {
          title_ru: 'Женская стрижка',
          title_en: 'Women\'s Haircut',
          title_tr: 'Kadın Saç Kesimi',
          is_active: true,
          parent_id: 1 // Подкатегория парикмахерских услуг
        },
        {
          title_ru: 'Мужская стрижка',
          title_en: 'Men\'s Haircut',
          title_tr: 'Erkek Saç Kesimi',
          is_active: true,
          parent_id: 1
        }
      ];
      
      for (const category of demoCategories) {
        const categoryData = createCategoryData(category);
        await servicesAPI.createCategory(categoryData);
      }
      
      console.log('✅ Demo categories created');
    }
    
    // Проверяем наличие услуг
    const servicesResponse = await servicesAPI.getServices();
    const services = servicesResponse.data?.items || [];
    
    if (services.length === 0) {
      console.log('🔧 No services found, creating demo services...');
      
      // Создаем демо-услуги
      const demoServices = [
        {
          title_ru: 'Женская стрижка с укладкой',
          description_ru: 'Стрижка и укладка для женщин любой длины',
          duration_minutes: 60,
          price: 1500,
          is_active: true,
          category_id: 3 // Женская стрижка
        },
        {
          title_ru: 'Мужская стрижка машинкой',
          description_ru: 'Классическая мужская стрижка машинкой',
          duration_minutes: 30,
          price: 800,
          is_active: true,
          category_id: 4 // Мужская стрижка
        }
      ];
      
      for (const service of demoServices) {
        const serviceData = createServiceData(service);
        await servicesAPI.createService(serviceData);
      }
      
      console.log('✅ Demo services created');
    }
    
    console.log('🎉 Demo data initialization complete');
    return { success: true };
    
  } catch (error) {
    console.error('❌ Demo data initialization failed:', error);
    return { success: false, error: error.message };
  }
};

// Экспорт основного экземпляра axios
export { api, API_URL };

// Экспорт по умолчанию
export default api;