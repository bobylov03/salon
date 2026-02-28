// Services.jsx
import React, { useState, useEffect, useMemo } from 'react';
import {
  Table,
  Button,
  Modal,
  Form,
  Input,
  Select,
  InputNumber,
  Switch,
  Tree,
  Tabs,
  Space,
  message,
  Card,
  Row,
  Col,
  Tag,
  TreeSelect,
  Breadcrumb,
  Typography,
  Popconfirm,
  Spin,
  Empty,
  Alert,
  Dropdown,
  Menu,
  Tooltip,
  Badge,
  Divider,
  Statistic,
  Progress,
  Collapse,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  FolderOutlined,
  FolderOpenOutlined,
  CaretRightOutlined,
  CaretDownOutlined,
  ExclamationCircleOutlined,
  MoreOutlined,
  SearchOutlined,
  FilterOutlined,
  ReloadOutlined,
  EyeOutlined,
  EyeInvisibleOutlined,
  ApartmentOutlined,
  ShoppingOutlined,
  SettingOutlined,
  ExportOutlined,
  ImportOutlined,
  DragOutlined,
  SortAscendingOutlined,
  SortDescendingOutlined,
  InfoCircleOutlined,
  WarningOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  GlobalOutlined,
  TeamOutlined,
} from '@ant-design/icons';

const { TextArea, Search } = Input;
const { Option } = Select;
const { TabPane } = Tabs;
const { Title, Text } = Typography;
const { confirm } = Modal;
const { Panel } = Collapse;

const Services = () => {
  const [categories, setCategories] = useState([]);
  const [services, setServices] = useState([]);
  const [loading, setLoading] = useState(false);
  const [categoriesLoading, setCategoriesLoading] = useState(false);
  const [categoryModalVisible, setCategoryModalVisible] = useState(false);
  const [serviceModalVisible, setServiceModalVisible] = useState(false);
  const [editingCategory, setEditingCategory] = useState(null);
  const [editingService, setEditingService] = useState(null);
  const [selectedCategoryId, setSelectedCategoryId] = useState('all');
  const [selectedCategoryPath, setSelectedCategoryPath] = useState([]);
  const [expandedKeys, setExpandedKeys] = useState([]);
  const [categoryTreeData, setCategoryTreeData] = useState([]);
  const [treeSelectData, setTreeSelectData] = useState([]);
  const [error, setError] = useState(null);
  const [form] = Form.useForm();
  const [serviceForm] = Form.useForm();

  const [isParentCategory, setIsParentCategory] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [searchText, setSearchText] = useState('');
  const [activeTab, setActiveTab] = useState('services');
  const [filterStatus, setFilterStatus] = useState('all');
  const [sortOrder, setSortOrder] = useState('desc');
  const [categoryFilter, setCategoryFilter] = useState(null);
  const [stats, setStats] = useState({
    totalCategories: 0,
    totalServices: 0,
    activeServices: 0,
    inactiveServices: 0,
  });

  // Базовый URL API
  const API_BASE_URL = 'http://localhost:8000';

  // Утилитная функция для fetch с обработкой ошибок
  const fetchWithAuth = async (url, options = {}) => {
    const token = localStorage.getItem('token');
    
    const headers = {
      'Content-Type': 'application/json',
      ...options.headers,
    };
    
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    
    try {
      const cleanBaseUrl = API_BASE_URL.endsWith('/') 
        ? API_BASE_URL.slice(0, -1) 
        : API_BASE_URL;
      
      const cleanUrl = url.startsWith('/') ? url.slice(1) : url;
      const fullUrl = `${cleanBaseUrl}/${cleanUrl}`;
      
      const response = await fetch(fullUrl, {
        ...options,
        headers,
      });
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error(`HTTP error ${response.status}:`, errorText);
        throw new Error(`HTTP ${response.status}: ${response.statusText} - ${errorText}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('Fetch error:', error);
      throw error;
    }
  };

  // Загрузка категорий
  const fetchCategories = async () => {
    setCategoriesLoading(true);
    setError(null);
    
    try {
      console.log('🔄 Загрузка категорий...');
      
      const data = await fetchWithAuth('services/categories?include_children=true&language=ru');
      console.log('📦 Данные категорий:', data);
      
      let categoriesData = [];
      
      if (Array.isArray(data)) {
        categoriesData = data;
      } else if (data && Array.isArray(data.items)) {
        categoriesData = data.items;
      } else if (data && data.data && Array.isArray(data.data)) {
        categoriesData = data.data;
      }
      
      console.log('📊 Обработанные категории:', categoriesData.length);
      
      // Собираем статистику
      const calculateStats = (categories) => {
        let serviceCount = 0;
        const traverse = (items) => {
          items.forEach(item => {
            serviceCount += item.service_count || 0;
            if (item.children && item.children.length > 0) {
              traverse(item.children);
            }
          });
        };
        traverse(categories);
        return serviceCount;
      };
      
      const totalServices = calculateStats(categoriesData);
      
      setCategories(categoriesData);
      
      // Создаем treeData для Tree компонента
      const treeData = [
        {
          title: (
            <div style={{ display: 'flex', alignItems: 'center' }}>
              <FolderOpenOutlined style={{ marginRight: 8 }} />
              <span>Все категории</span>
              <Badge 
                count={totalServices} 
                style={{ marginLeft: 8, backgroundColor: '#52c41a' }} 
              />
            </div>
          ),
          key: 'all',
          icon: <FolderOpenOutlined />,
          selectable: true,
          isLeaf: false,
        },
        ...buildTreeData(categoriesData),
      ];
      
      setCategoryTreeData(treeData);
      
      // Автоматически разворачиваем все узлы
      const allKeys = getAllCategoryKeys(categoriesData);
      setExpandedKeys(['all', ...allKeys]);
      
      // Строим данные для TreeSelect
      const tsData = buildTreeSelectData(categoriesData);
      setTreeSelectData([
        { 
          id: null, 
          value: null, 
          title: 'Корневая категория', 
          label: 'Корневая категория (без родителя)', 
          isLeaf: true 
        },
        ...tsData
      ]);
      
      // Обновляем статистику
      setStats(prev => ({
        ...prev,
        totalCategories: categoriesData.length,
        totalServices: totalServices,
      }));
      
      // Обновляем путь для текущей выбранной категории
      if (selectedCategoryId && selectedCategoryId !== 'all') {
        updateCategoryPath(selectedCategoryId, categoriesData);
      }
      
    } catch (error) {
      console.error('❌ Ошибка загрузки категорий:', error);
      setError(`Ошибка загрузки данных: ${error.message}`);
    } finally {
      setCategoriesLoading(false);
    }
  };

  // Загрузка услуг
  const fetchServices = async () => {
    setLoading(true);
    try {
      console.log('🔄 Загрузка услуг для категории:', selectedCategoryId);
      
      const params = new URLSearchParams();
      params.append('page', '1');
      params.append('per_page', '100');
      params.append('language', 'ru');
      
      if (selectedCategoryId && selectedCategoryId !== 'all') {
        params.append('category_id', selectedCategoryId);
      }
      
      if (filterStatus !== 'all') {
        params.append('is_active', filterStatus === 'active' ? 'true' : 'false');
      }
      
      if (searchText) {
        params.append('search', searchText);
      }
      
      const data = await fetchWithAuth(`services?${params.toString()}`);
      console.log('📦 Данные услуг:', data);
      
      let servicesData = [];
      
      if (data && Array.isArray(data.items)) {
        servicesData = data.items;
      } else if (Array.isArray(data)) {
        servicesData = data;
      } else if (data && data.data && Array.isArray(data.data)) {
        servicesData = data.data;
      }
      
      // Применяем сортировку
      const sortedServices = [...servicesData].sort((a, b) => {
        if (sortOrder === 'asc') {
          return a.title?.localeCompare(b.title);
        } else {
          return b.title?.localeCompare(a.title);
        }
      });
      
      // Обновляем статистику
      const activeServices = sortedServices.filter(s => s.is_active).length;
      const inactiveServices = sortedServices.filter(s => !s.is_active).length;
      
      setStats(prev => ({
        ...prev,
        activeServices,
        inactiveServices,
      }));
      
      setServices(sortedServices);
      
    } catch (error) {
      console.error('❌ Ошибка загрузки услуг:', error);
      setServices([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCategories();
  }, []);

  useEffect(() => {
    fetchServices();
  }, [selectedCategoryId, filterStatus, sortOrder, searchText]);

  // Функция для построения древовидных данных
  const buildTreeData = (categoriesData, parentId = null) => {
    if (!Array.isArray(categoriesData)) return [];
    
    return categoriesData
      .filter(cat => {
        const catParentId = cat.parent_id === undefined || cat.parent_id === null ? null : cat.parent_id;
        return catParentId === parentId;
      })
      .map(cat => {
        const hasChildren = cat.has_children || 
                          (cat.children && cat.children.length > 0) ||
                          categoriesData.some(child => child.parent_id === cat.id);
        
        const node = {
          key: cat.id.toString(),
          title: (
            <div style={{ 
              display: 'flex', 
              alignItems: 'center', 
              justifyContent: 'space-between',
              width: '100%',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', flex: 1 }}>
                {cat.is_active ? (
                  <CheckCircleOutlined style={{ color: '#52c41a', marginRight: 8 }} />
                ) : (
                  <CloseCircleOutlined style={{ color: '#ff4d4f', marginRight: 8 }} />
                )}
                <span style={{ flex: 1 }}>
                  {cat.title || `Категория #${cat.id}`}
                </span>
                <Badge 
                  count={cat.service_count || 0} 
                  style={{ 
                    backgroundColor: cat.service_count > 0 ? '#1890ff' : '#d9d9d9',
                    marginLeft: 8 
                  }} 
                />
              </div>
              <Space size="small" onClick={e => e.stopPropagation()}>
                <Tooltip title="Добавить подкатегорию">
                  <Button
                    type="text"
                    size="small"
                    icon={<PlusOutlined />}
                    onClick={() => handleAddSubcategory(cat)}
                  />
                </Tooltip>
                <Tooltip title="Добавить услугу">
                  <Button
                    type="text"
                    size="small"
                    icon={<ShoppingOutlined />}
                    onClick={() => handleAddServiceToCategory(cat)}
                    disabled={hasChildren}
                  />
                </Tooltip>
                <Tooltip title="Редактировать">
                  <Button
                    type="text"
                    size="small"
                    icon={<EditOutlined />}
                    onClick={() => handleEditCategory(cat)}
                  />
                </Tooltip>
                <Dropdown
                  menu={{
                    items: [
                      {
                        key: 'view',
                        label: 'Просмотреть',
                        icon: <EyeOutlined />,
                        onClick: () => handleViewCategory(cat),
                      },
                      {
                        key: 'toggle',
                        label: cat.is_active ? 'Деактивировать' : 'Активировать',
                        icon: cat.is_active ? <EyeInvisibleOutlined /> : <EyeOutlined />,
                        onClick: () => handleToggleCategory(cat),
                      },
                      {
                        type: 'divider',
                      },
                      {
                        key: 'delete',
                        label: 'Удалить только эту категорию',
                        icon: <DeleteOutlined />,
                        danger: true,
                        onClick: () => handleDeleteCategory(cat.id, cat.title || `Категория #${cat.id}`),
                      },
                      {
                        key: 'delete_recursive',
                        label: 'Удалить с подкатегориями',
                        icon: <DeleteOutlined />,
                        danger: true,
                        onClick: () => handleDeleteCategoryRecursive(cat.id, cat.title || `Категория #${cat.id}`),
                      },
                    ],
                  }}
                  trigger={['click']}
                  placement="bottomRight"
                >
                  <Button
                    type="text"
                    size="small"
                    icon={<MoreOutlined />}
                  />
                </Dropdown>
              </Space>
            </div>
          ),
          icon: hasChildren ? <FolderOpenOutlined /> : <FolderOutlined />,
          selectable: !hasChildren,
          isLeaf: !hasChildren,
          disabled: !cat.is_active,
        };
        
        // Рекурсивно добавляем детей
        let children = [];
        if (cat.children && cat.children.length > 0) {
          children = buildTreeData(cat.children, cat.id);
        } else if (hasChildren) {
          children = buildTreeData(categoriesData, cat.id);
        }
        
        if (children.length > 0) {
          node.children = children;
        }
        
        return node;
      });
  };

  // Получение всех ключей категорий
  const getAllCategoryKeys = (categoriesData) => {
    const keys = [];
    
    if (!Array.isArray(categoriesData)) return keys;
    
    const traverse = (items) => {
      items.forEach(item => {
        keys.push(item.id.toString());
        if (item.children && item.children.length > 0) {
          traverse(item.children);
        }
      });
    };
    
    traverse(categoriesData);
    return keys;
  };

  // Построение данных для TreeSelect
  const buildTreeSelectData = (categoriesData, parentId = null, level = 0, prefix = '') => {
    if (!Array.isArray(categoriesData)) return [];
    
    return categoriesData
      .filter(cat => {
        const catParentId = cat.parent_id === undefined || cat.parent_id === null ? null : cat.parent_id;
        return catParentId === parentId;
      })
      .flatMap(cat => {
        const title = cat.title || `Категория #${cat.id}`;
        const fullTitle = prefix ? `${prefix} › ${title}` : title;
        
        const hasChildren = cat.has_children || 
                          (cat.children && cat.children.length > 0) ||
                          categoriesData.some(child => child.parent_id === cat.id);
        
        const node = {
          id: cat.id,
          value: cat.id,
          title: fullTitle,
          label: (
            <div style={{ display: 'flex', alignItems: 'center' }}>
              <span>{fullTitle}</span>
              {!cat.is_active && (
                <Tag color="red" style={{ marginLeft: 8, fontSize: '10px' }}>
                  неактивна
                </Tag>
              )}
              {(cat.service_count > 0 && !hasChildren) && (
                <Tag color="blue" style={{ marginLeft: 8, fontSize: '10px' }}>
                  {cat.service_count}
                </Tag>
              )}
            </div>
          ),
          isLeaf: !hasChildren,
          disabled: !cat.is_active,
        };
        
        // Рекурсивно добавляем детей
        let childNodes = [];
        if (cat.children && cat.children.length > 0) {
          childNodes = buildTreeSelectData(cat.children, cat.id, level + 1, fullTitle);
        } else if (hasChildren) {
          childNodes = buildTreeSelectData(categoriesData, cat.id, level + 1, fullTitle);
        }
        
        return [node, ...childNodes];
      });
  };

  // Обновление пути категории
  const updateCategoryPath = (categoryId, categoriesData = categories) => {
    if (categoryId === 'all') {
      setSelectedCategoryPath([{ id: 'all', title: 'Все категории' }]);
      setIsParentCategory(false);
      return;
    }

    const findPath = (items, targetId, path = []) => {
      if (!Array.isArray(items)) return null;
      
      for (const item of items) {
        const newPath = [...path, { 
          id: item.id, 
          title: item.title || `Категория #${item.id}` 
        }];
        
        if (item.id == targetId) {
          const hasChildren = item.has_children || 
                            (item.children && item.children.length > 0) ||
                            categoriesData.some(child => child.parent_id == item.id);
          setIsParentCategory(hasChildren);
          return newPath;
        }
        
        if (item.children && item.children.length > 0) {
          const found = findPath(item.children, targetId, newPath);
          if (found) return found;
        }
      }
      return null;
    };

    const path = findPath(categoriesData, categoryId);
    setSelectedCategoryPath(path || [{ id: categoryId, title: `Категория #${categoryId}` }]);
  };

  // Добавление подкатегории
  const handleAddSubcategory = (parentCategory) => {
    setEditingCategory(null);
    form.resetFields();
    form.setFieldsValue({
      parent_id: parentCategory.id,
      is_active: true,
      title_ru: '',
      title_en: '',
      title_tr: '',
    });
    setCategoryModalVisible(true);
  };

  // Добавление услуги в категорию
  const handleAddServiceToCategory = (category) => {
    if (category.has_children) {
      message.warning('Вы не можете добавить услугу в родительскую категорию. Выберите конкретную подкатегорию.');
      return;
    }
    
    setEditingService(null);
    serviceForm.resetFields();
    serviceForm.setFieldsValue({
      category_id: category.id,
      duration_minutes: 60,
      price: 1000,
      is_active: true,
    });
    setServiceModalVisible(true);
  };

  // Просмотр категории
  const handleViewCategory = (category) => {
    Modal.info({
      title: category.title || `Категория #${category.id}`,
      width: 600,
      content: (
        <div>
          <Row gutter={16} style={{ marginBottom: 16 }}>
            <Col span={12}>
              <Statistic 
                title="Статус" 
                value={category.is_active ? 'Активна' : 'Неактивна'} 
                prefix={category.is_active ? 
                  <CheckCircleOutlined style={{ color: '#52c41a' }} /> : 
                  <CloseCircleOutlined style={{ color: '#ff4d4f' }} />
                }
              />
            </Col>
            <Col span={12}>
              <Statistic 
                title="Услуг в категории" 
                value={category.service_count || 0} 
                prefix={<ShoppingOutlined />}
              />
            </Col>
          </Row>
          {category.has_children && (
            <Alert
              message="Родительская категория"
              description="Эта категория содержит подкатегории. Услуги можно добавлять только в конечные подкатегории."
              type="info"
              showIcon
              style={{ marginBottom: 16 }}
            />
          )}
        </div>
      ),
    });
  };

  // Переключение статуса категории
  const handleToggleCategory = async (category) => {
    try {
      await fetchWithAuth(`services/categories/${category.id}`, {
        method: 'PUT',
        body: JSON.stringify({
          is_active: !category.is_active,
        }),
      });
      
      message.success(`Категория ${!category.is_active ? 'активирована' : 'деактивирована'}`);
      fetchCategories();
    } catch (error) {
      console.error('Error toggling category:', error);
      message.error('Ошибка при изменении статуса категории');
    }
  };

  // Редактирование категории
  const handleEditCategory = async (category) => {
    setEditingCategory(category);
    form.resetFields();
    
    try {
      // Загружаем все переводы категории
      const data = await fetchWithAuth(`services/categories/${category.id}`);
      const categoryData = data.data || data;
      
      // Также загружаем существующие переводы
      const translations = await fetchWithAuth(`services/categories/${category.id}/translations`);
      
      const ruTranslation = translations?.find(t => t.language === 'ru');
      const enTranslation = translations?.find(t => t.language === 'en');
      const trTranslation = translations?.find(t => t.language === 'tr');
      
      form.setFieldsValue({
        parent_id: categoryData.parent_id || null,
        is_active: categoryData.is_active !== false,
        title_ru: ruTranslation?.title || categoryData.title || '',
        title_en: enTranslation?.title || '',
        title_tr: trTranslation?.title || '',
      });
    } catch (error) {
      console.error('Error loading category details:', error);
      form.setFieldsValue({
        parent_id: category.parent_id || null,
        is_active: category.is_active !== false,
        title_ru: category.title || '',
      });
    }
    
    setCategoryModalVisible(true);
  };

  // Удаление категории (только текущей)
  const handleDeleteCategory = async (categoryId, categoryName) => {
    confirm({
      title: 'Удалить категорию?',
      icon: <ExclamationCircleOutlined />,
      content: (
        <div>
          <p>Вы действительно хотите удалить категорию "{categoryName}"?</p>
          <Alert
            message="Внимание!"
            description="Это действие удалит только эту категорию. Если в категории есть подкатегории или услуги, удаление не будет выполнено."
            type="warning"
            showIcon
            style={{ margin: '16px 0' }}
          />
        </div>
      ),
      okText: 'Да, удалить',
      okType: 'danger',
      cancelText: 'Отмена',
      async onOk() {
        setIsDeleting(true);
        try {
          await fetchWithAuth(`services/categories/${categoryId}`, {
            method: 'DELETE',
          });
          
          message.success('Категория удалена');
          await fetchCategories();
          
          if (selectedCategoryId == categoryId) {
            setSelectedCategoryId('all');
          }
          
        } catch (error) {
          console.error('❌ Ошибка удаления категории:', error);
          
          let errorMessage = 'Ошибка при удалении категории';
          
          if (error.message.includes('подкатегории')) {
            errorMessage = 'Невозможно удалить категорию, так как у неё есть подкатегории. Используйте опцию "Удалить с подкатегориями".';
          } else if (error.message.includes('активные услуги')) {
            errorMessage = 'Невозможно удалить категорию, так как в ней есть активные услуги. Сначала удалите или переместите услуги.';
          }
          
          Modal.error({
            title: 'Ошибка удаления',
            content: errorMessage,
          });
        } finally {
          setIsDeleting(false);
        }
      },
    });
  };

  // Рекурсивное удаление категории с подкатегориями
  const handleDeleteCategoryRecursive = async (categoryId, categoryName) => {
    confirm({
      title: 'Удалить категорию со всем содержимым?',
      icon: <ExclamationCircleOutlined />,
      content: (
        <div>
          <p>Вы действительно хотите удалить категорию "{categoryName}" и ВСЁ её содержимое?</p>
          <Alert
            message="Критическое действие!"
            description={
              <div>
                <p>Будет удалено:</p>
                <ul>
                  <li>Все подкатегории (включая вложенные)</li>
                  <li>Все услуги в этих категориях</li>
                  <li>Все переводы</li>
                </ul>
                <p><strong>Это действие нельзя отменить!</strong></p>
              </div>
            }
            type="error"
            showIcon
            style={{ margin: '16px 0' }}
          />
        </div>
      ),
      okText: 'Да, удалить всё',
      okType: 'danger',
      cancelText: 'Отмена',
      async onOk() {
        setIsDeleting(true);
        try {
          await fetchWithAuth(`services/categories/${categoryId}?recursive=true`, {
            method: 'DELETE',
          });
          
          message.success('Категория и всё её содержимое удалено');
          await fetchCategories();
          
          if (selectedCategoryId == categoryId) {
            setSelectedCategoryId('all');
          }
          
        } catch (error) {
          console.error('❌ Ошибка удаления категории:', error);
          message.error(`Ошибка при удалении: ${error.message}`);
        } finally {
          setIsDeleting(false);
        }
      },
    });
  };

  // Обработчик создания/обновления категории
  const handleCategorySubmit = async (values) => {
    try {
      // Подготавливаем переводы
      const translations = [
        { language: 'ru', title: values.title_ru?.trim() || '' },
        { language: 'en', title: values.title_en?.trim() || values.title_ru?.trim() || '' },
        { language: 'tr', title: values.title_tr?.trim() || values.title_ru?.trim() || '' },
      ].filter(t => t.title);

      const categoryData = {
        parent_id: values.parent_id || null,
        is_active: values.is_active !== false,
        translations: translations,
      };

      const url = editingCategory 
        ? `services/categories/${editingCategory.id}`
        : 'services/categories';
      
      const method = editingCategory ? 'PUT' : 'POST';
      
      await fetchWithAuth(url, {
        method: method,
        body: JSON.stringify(categoryData)
      });
      
      message.success(editingCategory ? 'Категория обновлена' : 'Категория создана');
      setCategoryModalVisible(false);
      form.resetFields();
      fetchCategories();
      
    } catch (error) {
      console.error('❌ Ошибка сохранения категории:', error);
      message.error(`Ошибка сохранения: ${error.message}`);
    }
  };

  // Обработчик создания/обновления услуги
  const handleServiceSubmit = async (values) => {
    try {
      const translations = [
        { 
          language: 'ru', 
          title: values.title_ru?.trim() || '',
          description: values.description_ru?.trim() || '',
        },
        { 
          language: 'en', 
          title: values.title_en?.trim() || values.title_ru?.trim() || '',
          description: values.description_en?.trim() || values.description_ru?.trim() || '',
        },
        { 
          language: 'tr', 
          title: values.title_tr?.trim() || values.title_ru?.trim() || '',
          description: values.description_tr?.trim() || values.description_ru?.trim() || '',
        },
      ].filter(t => t.title);

      const serviceData = {
        category_id: values.category_id,
        duration_minutes: Number(values.duration_minutes) || 60,
        price: Number(values.price) || 1000,
        is_active: values.is_active !== false,
        translations: translations,
      };

      const url = editingService 
        ? `services/${editingService.id}`
        : 'services';
      
      const method = editingService ? 'PUT' : 'POST';
      
      await fetchWithAuth(url, {
        method: method,
        body: JSON.stringify(serviceData)
      });
      
      message.success(editingService ? 'Услуга обновлена' : 'Услуга создана');
      setServiceModalVisible(false);
      serviceForm.resetFields();
      fetchServices();
      
    } catch (error) {
      console.error('❌ Ошибка сохранения услуги:', error);
      message.error(`Ошибка сохранения: ${error.message}`);
    }
  };

  // Обработчик выбора категории в дереве
  const handleCategorySelect = (selectedKeys, info) => {
    if (selectedKeys.length > 0) {
      const categoryId = selectedKeys[0];
      setSelectedCategoryId(categoryId);
      
      // Находим категорию в дереве
      const findCategory = (nodes, targetKey) => {
        for (const node of nodes) {
          if (node.key === targetKey) {
            return node;
          }
          if (node.children) {
            const found = findCategory(node.children, targetKey);
            if (found) return found;
          }
        }
        return null;
      };
      
      const category = findCategory(categoryTreeData, categoryId);
      const hasChildren = category?.isLeaf === false || category?.children?.length > 0;
      setIsParentCategory(hasChildren);
      
      // Обновляем путь
      if (categoryId === 'all') {
        setSelectedCategoryPath([{ id: 'all', title: 'Все категории' }]);
      } else {
        updateCategoryPath(categoryId);
      }
    }
  };

  // Деактивация услуги
  const handleDeactivateService = async (serviceId) => {
    try {
      await fetchWithAuth(`services/${serviceId}`, {
        method: 'DELETE',
      });
      
      message.success('Услуга деактивирована');
      fetchServices();
    } catch (error) {
      console.error('Error deactivating service:', error);
      message.error(error.message || 'Ошибка при деактивации услуги');
    }
  };

  // Активация услуги
  const handleActivateService = async (serviceId) => {
    try {
      await fetchWithAuth(`services/${serviceId}`, {
        method: 'PUT',
        body: JSON.stringify({ is_active: true }),
      });
      
      message.success('Услуга активирована');
      fetchServices();
    } catch (error) {
      console.error('Error activating service:', error);
      message.error(error.message || 'Ошибка при активации услуги');
    }
  };

  // Полное удаление услуги
  const handleForceDeleteService = async (serviceId, serviceTitle) => {
    confirm({
      title: 'Полностью удалить услугу?',
      icon: <ExclamationCircleOutlined />,
      content: (
        <div>
          <p>Вы уверены, что хотите полностью удалить услугу "{serviceTitle || `#${serviceId}`}"?</p>
          <Alert
            message="Внимание!"
            description="Это действие нельзя отменить. Услуга будет полностью удалена из базы данных."
            type="error"
            showIcon
            style={{ margin: '16px 0' }}
          />
        </div>
      ),
      okText: 'Да, удалить',
      okType: 'danger',
      cancelText: 'Отмена',
      async onOk() {
        try {
          await fetchWithAuth(`services/${serviceId}/force`, {
            method: 'DELETE',
          });
          
          message.success('Услуга полностью удалена');
          fetchServices();
        } catch (error) {
          console.error('Error force deleting service:', error);
          
          if (error.message.includes('используется в записях')) {
            Modal.error({
              title: 'Невозможно удалить услугу',
              content: (
                <div>
                  <p>Услуга используется в существующих записях.</p>
                  <p>Сначала удалите эти записи или измените услуги в них.</p>
                </div>
              ),
            });
          } else {
            message.error('Ошибка при удалении услуги: ' + error.message);
          }
        }
      },
    });
  };

  // Добавление новой корневой категории
  const handleAddRootCategory = () => {
    setEditingCategory(null);
    form.resetFields();
    form.setFieldsValue({
      parent_id: null,
      is_active: true,
      title_ru: '',
      title_en: '',
      title_tr: '',
    });
    setCategoryModalVisible(true);
  };

  // Обновить все
  const handleRefresh = () => {
    fetchCategories();
    fetchServices();
    message.success('Данные обновлены');
  };

  // Колонки таблицы услуг
  const serviceColumns = [
    {
      title: 'Название услуги',
      dataIndex: 'title',
      key: 'title',
      width: 250,
      render: (text, record) => (
        <div>
          <div style={{ fontWeight: 500, marginBottom: 4 }}>
            {text || `Услуга #${record.id}`}
          </div>
          {record.description && (
            <Text type="secondary" style={{ fontSize: '12px', display: 'block' }}>
              {record.description.length > 120 
                ? `${record.description.substring(0, 120)}...` 
                : record.description}
            </Text>
          )}
        </div>
      ),
    },
    {
      title: 'Категория',
      dataIndex: 'category_title',
      key: 'category_title',
      width: 150,
      render: (text) => (
        <Tag color="blue" icon={<FolderOutlined />}>
          {text || 'Без категории'}
        </Tag>
      ),
    },
    {
      title: 'Длительность',
      dataIndex: 'duration_minutes',
      key: 'duration_minutes',
      width: 100,
      render: (minutes) => (
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '16px', fontWeight: 500 }}>{minutes || 0}</div>
          <Text type="secondary" style={{ fontSize: '11px' }}>минут</Text>
        </div>
      ),
    },
    {
      title: 'Цена',
      dataIndex: 'price',
      key: 'price',
      width: 120,
      render: (price) => (
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '16px', fontWeight: 500, color: '#1890ff' }}>
            {price ? Number(price).toLocaleString('ru-RU') : '0'}
          </div>
          <Text type="secondary" style={{ fontSize: '11px' }}>₺</Text>
        </div>
      ),
    },
    {
      title: 'Статус',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 100,
      render: (active) => (
        <Tag 
          color={active ? 'green' : 'red'} 
          icon={active ? <CheckCircleOutlined /> : <CloseCircleOutlined />}
        >
          {active ? 'Активна' : 'Неактивна'}
        </Tag>
      ),
    },
    {
      title: 'Действия',
      key: 'actions',
      width: 150,
      render: (_, record) => (
        <Space>
          <Tooltip title="Редактировать">
            <Button
              type="text"
              icon={<EditOutlined />}
              onClick={() => {
                setEditingService(record);
                serviceForm.setFieldsValue({
                  category_id: record.category_id,
                  duration_minutes: record.duration_minutes,
                  price: record.price,
                  is_active: record.is_active,
                  title_ru: record.title,
                  description_ru: record.description,
                });
                setServiceModalVisible(true);
              }}
            />
          </Tooltip>
          {record.is_active ? (
            <Tooltip title="Деактивировать">
              <Button
                type="text"
                danger
                icon={<EyeInvisibleOutlined />}
                onClick={() => handleDeactivateService(record.id)}
              />
            </Tooltip>
          ) : (
            <Tooltip title="Активировать">
              <Button
                type="text"
                icon={<EyeOutlined />}
                onClick={() => handleActivateService(record.id)}
              />
            </Tooltip>
          )}
          <Dropdown
            menu={{
              items: [
                {
                  key: 'forceDelete',
                  label: 'Полностью удалить',
                  icon: <DeleteOutlined />,
                  danger: true,
                  onClick: () => handleForceDeleteService(record.id, record.title),
                },
              ],
            }}
            trigger={['click']}
            placement="bottomRight"
          >
            <Button
              type="text"
              icon={<MoreOutlined />}
            />
          </Dropdown>
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: '0 24px' }}>
      {/* Заголовок и статистика */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col span={24}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <Title level={2} style={{ margin: 0, display: 'flex', alignItems: 'center' }}>
                <ShoppingOutlined style={{ marginRight: 12, color: '#1890ff' }} />
                Управление услугами
              </Title>
              <Text type="secondary">Управление категориями и услугами салона</Text>
            </div>
            <Space>
              <Button
                icon={<ReloadOutlined />}
                onClick={handleRefresh}
                loading={loading || categoriesLoading}
              >
                Обновить
              </Button>
            </Space>
          </div>
        </Col>
        <Col span={24}>
          <Row gutter={16}>
            <Col span={6}>
              <Card size="small">
                <Statistic
                  title="Всего категорий"
                  value={stats.totalCategories}
                  prefix={<ApartmentOutlined />}
                  valueStyle={{ color: '#1890ff' }}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card size="small">
                <Statistic
                  title="Всего услуг"
                  value={stats.totalServices}
                  prefix={<ShoppingOutlined />}
                  valueStyle={{ color: '#52c41a' }}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card size="small">
                <Statistic
                  title="Активные услуги"
                  value={stats.activeServices}
                  prefix={<CheckCircleOutlined />}
                  valueStyle={{ color: '#52c41a' }}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card size="small">
                <Statistic
                  title="Неактивные услуги"
                  value={stats.inactiveServices}
                  prefix={<CloseCircleOutlined />}
                  valueStyle={{ color: '#ff4d4f' }}
                />
              </Card>
            </Col>
          </Row>
        </Col>
      </Row>

      {error && (
        <Alert
          message="Ошибка загрузки данных"
          description={error}
          type="error"
          showIcon
          closable
          style={{ marginBottom: 16 }}
          onClose={() => setError(null)}
        />
      )}

      {/* Основной контент */}
      <Tabs 
        activeKey={activeTab} 
        onChange={setActiveTab}
        items={[
          {
            key: 'services',
            label: (
              <span>
                <ShoppingOutlined />
                Услуги
              </span>
            ),
            children: (
              <Row gutter={16}>
                <Col span={6}>
                  <Card 
                    title={
                      <div style={{ display: 'flex', alignItems: 'center' }}>
                        <ApartmentOutlined style={{ marginRight: 8 }} />
                        Категории услуг
                      </div>
                    }
                    extra={
                      <Tooltip title="Добавить корневую категорию">
                        <Button
                          type="text"
                          icon={<PlusOutlined />}
                          onClick={handleAddRootCategory}
                        />
                      </Tooltip>
                    }
                    bodyStyle={{ padding: 0 }}
                    loading={categoriesLoading}
                  >
                    <div style={{ padding: '16px' }}>
                      <Search
                        placeholder="Поиск категорий..."
                        onSearch={(value) => setCategoryFilter(value)}
                        allowClear
                        style={{ marginBottom: 16 }}
                      />
                      <Button
                        type={selectedCategoryId === 'all' ? 'primary' : 'default'}
                        block
                        style={{ 
                          textAlign: 'left', 
                          marginBottom: '8px',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between'
                        }}
                        onClick={() => {
                          setSelectedCategoryId('all');
                          setIsParentCategory(false);
                          setSelectedCategoryPath([{ id: 'all', title: 'Все категории' }]);
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center' }}>
                          <FolderOpenOutlined style={{ marginRight: 8 }} />
                          Все категории
                        </div>
                        <Badge 
                          count={stats.totalServices} 
                          style={{ backgroundColor: '#52c41a' }} 
                        />
                      </Button>
                    </div>
                    
                    {categoriesLoading ? (
                      <div style={{ textAlign: 'center', padding: '40px' }}>
                        <Spin />
                        <div style={{ marginTop: 8 }}>Загрузка категорий...</div>
                      </div>
                    ) : categoryTreeData.length <= 1 ? (
                      <Empty
                        description="Нет категорий"
                        image={Empty.PRESENTED_IMAGE_SIMPLE}
                        style={{ padding: '40px 20px' }}
                      >
                        <Button 
                          type="primary" 
                          icon={<PlusOutlined />}
                          onClick={handleAddRootCategory}
                        >
                          Создать первую категорию
                        </Button>
                      </Empty>
                    ) : (
                      <div style={{ padding: '0 16px 16px', maxHeight: '500px', overflow: 'auto' }}>
                        <Tree
                          showIcon
                          expandedKeys={expandedKeys}
                          onExpand={setExpandedKeys}
                          treeData={categoryTreeData}
                          onSelect={handleCategorySelect}
                          selectedKeys={[selectedCategoryId]}
                          switcherIcon={({ expanded }) => 
                            expanded ? <CaretDownOutlined /> : <CaretRightOutlined />
                          }
                          blockNode
                        />
                      </div>
                    )}
                  </Card>
                </Col>
                
                <Col span={18}>
                  <Card 
                    title={
                      <div>
                        <div style={{ display: 'flex', alignItems: 'center' }}>
                          <ShoppingOutlined style={{ marginRight: 8 }} />
                          Услуги
                          {selectedCategoryPath.length > 0 && (
                            <Breadcrumb style={{ marginLeft: 16, display: 'inline-flex' }}>
                              {selectedCategoryPath.map((cat, index) => (
                                <Breadcrumb.Item key={cat.id}>
                                  {index === selectedCategoryPath.length - 1 ? (
                                    <strong>{cat.title}</strong>
                                  ) : cat.title}
                                </Breadcrumb.Item>
                              ))}
                            </Breadcrumb>
                          )}
                        </div>
                        {selectedCategoryPath.length > 0 && selectedCategoryId !== 'all' && (
                          <div style={{ marginTop: 8 }}>
                            <Text type="secondary">
                              {isParentCategory 
                                ? 'Эта категория содержит подкатегории. Выберите конкретную подкатегорию для добавления услуг.'
                                : 'Добавляйте услуги в эту категорию.'}
                            </Text>
                          </div>
                        )}
                      </div>
                    }
                    extra={
                      <Space>
                        <Search
                          placeholder="Поиск услуг..."
                          value={searchText}
                          onChange={e => setSearchText(e.target.value)}
                          style={{ width: 200 }}
                          allowClear
                        />
                        <Select
                          value={filterStatus}
                          onChange={setFilterStatus}
                          style={{ width: 120 }}
                        >
                          <Option value="all">Все статусы</Option>
                          <Option value="active">Активные</Option>
                          <Option value="inactive">Неактивные</Option>
                        </Select>
                        <Tooltip title={sortOrder === 'desc' ? 'Сортировка по убыванию' : 'Сортировка по возрастанию'}>
                          <Button
                            icon={sortOrder === 'desc' ? <SortDescendingOutlined /> : <SortAscendingOutlined />}
                            onClick={() => setSortOrder(sortOrder === 'desc' ? 'asc' : 'desc')}
                          />
                        </Tooltip>
                        <Button
                          type="primary"
                          icon={<PlusOutlined />}
                          onClick={() => {
                            setEditingService(null);
                            serviceForm.resetFields();
                            if (selectedCategoryId && selectedCategoryId !== 'all') {
                              serviceForm.setFieldValue('category_id', selectedCategoryId);
                            }
                            setServiceModalVisible(true);
                          }}
                          disabled={isParentCategory && selectedCategoryId !== 'all'}
                          loading={isDeleting}
                        >
                          Добавить услугу
                        </Button>
                      </Space>
                    }
                  >
                    {isParentCategory && selectedCategoryId !== 'all' && (
                      <Alert
                        message="Внимание: выбрана родительская категория"
                        description="Для добавления услуг выберите конкретную подкатегорию (без иконки папки)."
                        type="warning"
                        showIcon
                        style={{ marginBottom: 16 }}
                      />
                    )}
                    
                    <Table
                      columns={serviceColumns}
                      dataSource={services}
                      rowKey="id"
                      loading={loading || isDeleting}
                      pagination={{ 
                        pageSize: 10,
                        showSizeChanger: true,
                        showQuickJumper: true,
                        showTotal: (total, range) => 
                          `${range[0]}-${range[1]} из ${total} услуг`
                      }}
                      scroll={{ x: 'max-content' }}
                      locale={{
                        emptyText: services.length === 0 && !loading ? (
                          <Empty
                            image={Empty.PRESENTED_IMAGE_SIMPLE}
                            description={
                              selectedCategoryId === 'all' 
                                ? 'Нет услуг' 
                                : `Нет услуг в категории "${selectedCategoryPath[selectedCategoryPath.length - 1]?.title || 'выбранной'}"`
                            }
                          >
                            <Button 
                              type="primary" 
                              icon={<PlusOutlined />}
                              onClick={() => {
                                setEditingService(null);
                                serviceForm.resetFields();
                                if (selectedCategoryId && selectedCategoryId !== 'all') {
                                  serviceForm.setFieldValue('category_id', selectedCategoryId);
                                }
                                setServiceModalVisible(true);
                              }}
                              disabled={isParentCategory && selectedCategoryId !== 'all'}
                            >
                              Добавить первую услугу
                            </Button>
                          </Empty>
                        ) : null,
                      }}
                    />
                  </Card>
                </Col>
              </Row>
            ),
          },
          {
            key: 'categories',
            label: (
              <span>
                <ApartmentOutlined />
                Управление категориями
              </span>
            ),
            children: (
              <Card
                title={
                  <div style={{ display: 'flex', alignItems: 'center' }}>
                    <SettingOutlined style={{ marginRight: 8 }} />
                    Управление категориями
                  </div>
                }
                extra={
                  <Space>
                    <Button
                      icon={<PlusOutlined />}
                      onClick={handleAddRootCategory}
                      loading={isDeleting}
                    >
                      Новая категория
                    </Button>
                    <Button
                      icon={<ApartmentOutlined />}
                      onClick={() => setExpandedKeys(getAllCategoryKeys(categories))}
                    >
                      Развернуть всё
                    </Button>
                  </Space>
                }
                loading={categoriesLoading || isDeleting}
              >
                {categoriesLoading ? (
                  <div style={{ textAlign: 'center', padding: '80px 0' }}>
                    <Spin size="large" />
                    <div style={{ marginTop: 16 }}>Загрузка структуры категорий...</div>
                  </div>
                ) : categories.length === 0 ? (
                  <Empty
                    description="Структура категорий пуста"
                    image={Empty.PRESENTED_IMAGE_SIMPLE}
                    style={{ padding: '80px 0' }}
                  >
                    <Button 
                      type="primary" 
                      icon={<PlusOutlined />}
                      onClick={handleAddRootCategory}
                    >
                      Создать первую категорию
                    </Button>
                  </Empty>
                ) : (
                  <div style={{ padding: '16px', background: '#fafafa', borderRadius: '8px' }}>
                    <Tree
                      showIcon
                      expandedKeys={expandedKeys}
                      onExpand={setExpandedKeys}
                      treeData={buildTreeData(categories)}
                      onSelect={handleCategorySelect}
                      switcherIcon={({ expanded }) => 
                        expanded ? <CaretDownOutlined /> : <CaretRightOutlined />
                      }
                      blockNode
                    />
                  </div>
                )}
                
                <Divider />
                
                <Alert
                  message="Информация об управлении категориями"
                  description={
                    <div>
                      <p><strong>Правила удаления категорий:</strong></p>
                      <ul>
                        <li>Чтобы удалить только категорию (без содержимого) - она должна быть пустой</li>
                        <li>Для удаления категории с подкатегориями используйте опцию "Удалить с подкатегориями"</li>
                        <li>Услуги можно добавлять только в конечные (бездетные) категории</li>
                      </ul>
                    </div>
                  }
                  type="info"
                  showIcon
                />
              </Card>
            ),
          },
        ]}
      />

      {/* Модальное окно категории */}
      <Modal
        title={
          <div style={{ display: 'flex', alignItems: 'center' }}>
            {editingCategory ? <EditOutlined /> : <PlusOutlined />}
            <span style={{ marginLeft: 8 }}>
              {editingCategory ? 'Редактирование категории' : 'Создание новой категории'}
            </span>
          </div>
        }
        open={categoryModalVisible}
        onCancel={() => {
          setCategoryModalVisible(false);
          form.resetFields();
        }}
        onOk={() => form.submit()}
        okText={editingCategory ? 'Обновить' : 'Создать'}
        cancelText="Отмена"
        width={600}
        destroyOnClose
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleCategorySubmit}
        >
          <Form.Item
            name="parent_id"
            label="Родительская категория"
            tooltip="Оставьте пустым для создания корневой категории"
          >
            <TreeSelect
              showSearch
              style={{ width: '100%' }}
              dropdownStyle={{ maxHeight: 400, overflow: 'auto' }}
              placeholder="Выберите родительскую категорию"
              allowClear
              treeDefaultExpandAll
              treeData={treeSelectData}
              treeNodeFilterProp="title"
            />
          </Form.Item>

          <Tabs defaultActiveKey="ru">
            <TabPane tab="Русский" key="ru">
              <Form.Item
                name="title_ru"
                label="Название *"
                rules={[{ 
                  required: true, 
                  message: 'Введите название на русском',
                  whitespace: true 
                }]}
              >
                <Input placeholder="Введите название на русском" />
              </Form.Item>
            </TabPane>
            <TabPane tab="English" key="en">
              <Form.Item
                name="title_en"
                label="Title"
              >
                <Input placeholder="Enter title in English" />
              </Form.Item>
            </TabPane>
            <TabPane tab="Türkçe" key="tr">
              <Form.Item
                name="title_tr"
                label="Başlık"
              >
                <Input placeholder="Türkçe başlık girin" />
              </Form.Item>
            </TabPane>
          </Tabs>

          <Form.Item
            name="is_active"
            label="Статус категории"
            valuePropName="checked"
            initialValue={true}
          >
            <Switch 
              checkedChildren="Активна" 
              unCheckedChildren="Неактивна" 
            />
          </Form.Item>
        </Form>
      </Modal>

      {/* Модальное окно услуги */}
      <Modal
        title={
          <div style={{ display: 'flex', alignItems: 'center' }}>
            {editingService ? <EditOutlined /> : <PlusOutlined />}
            <span style={{ marginLeft: 8 }}>
              {editingService ? 'Редактирование услуги' : 'Создание новой услуги'}
            </span>
          </div>
        }
        open={serviceModalVisible}
        onCancel={() => {
          setServiceModalVisible(false);
          serviceForm.resetFields();
        }}
        onOk={() => serviceForm.submit()}
        okText={editingService ? 'Обновить' : 'Создать'}
        cancelText="Отмена"
        width={700}
        destroyOnClose
      >
        <Form
          form={serviceForm}
          layout="vertical"
          onFinish={handleServiceSubmit}
        >
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="category_id"
                label="Категория *"
                rules={[{ required: true, message: 'Выберите категорию' }]}
                tooltip="Выберите конечную категорию (без подкатегорий)"
              >
                <TreeSelect
                  showSearch
                  style={{ width: '100%' }}
                  dropdownStyle={{ maxHeight: 400, overflow: 'auto' }}
                  placeholder="Выберите категорию"
                  treeData={treeSelectData.filter(item => 
                    item.id !== null && item.isLeaf
                  )}
                  treeDefaultExpandAll
                  treeNodeFilterProp="title"
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="duration_minutes"
                label="Длительность (минуты) *"
                rules={[{ 
                  required: true, 
                  message: 'Введите длительность' 
                }]}
                initialValue={60}
              >
                <InputNumber 
                  min={1}
                  max={1440}
                  style={{ width: '100%' }} 
                  placeholder="Например, 60"
                  addonAfter="мин"
                />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="price"
                label="Цена (₺) *"
                rules={[{ 
                  required: true, 
                  message: 'Введите цену' 
                }]}
                initialValue={1000}
              >
                <InputNumber 
                  min={0}
                  style={{ width: '100%' }} 
                  placeholder="Например, 1500"
                  formatter={value => `${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ' ')}
                  parser={value => value.replace(/\s/g, '')}
                  addonAfter="₺"
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="is_active"
                label="Статус услуги"
                valuePropName="checked"
                initialValue={true}
                style={{ marginTop: 29 }}
              >
                <Switch checkedChildren="Активна" unCheckedChildren="Неактивна" />
              </Form.Item>
            </Col>
          </Row>

          <Tabs defaultActiveKey="ru">
            <TabPane tab="Русский" key="ru">
              <Form.Item
                name="title_ru"
                label="Название *"
                rules={[{ 
                  required: true, 
                  message: 'Введите название',
                  whitespace: true 
                }]}
              >
                <Input placeholder="Введите название услуги на русском" />
              </Form.Item>
              <Form.Item
                name="description_ru"
                label="Описание"
              >
                <TextArea 
                  rows={4} 
                  placeholder="Введите подробное описание услуги на русском"
                  maxLength={1000}
                  showCount
                />
              </Form.Item>
            </TabPane>
            <TabPane tab="English" key="en">
              <Form.Item
                name="title_en"
                label="Title"
              >
                <Input placeholder="Enter service title in English" />
              </Form.Item>
              <Form.Item
                name="description_en"
                label="Description"
              >
                <TextArea 
                  rows={4} 
                  placeholder="Enter service description in English"
                  maxLength={1000}
                  showCount
                />
              </Form.Item>
            </TabPane>
            <TabPane tab="Türkçe" key="tr">
              <Form.Item
                name="title_tr"
                label="Başlık"
              >
                <Input placeholder="Hizmet başlığını Türkçe olarak girin" />
              </Form.Item>
              <Form.Item
                name="description_tr"
                label="Açıklama"
              >
                <TextArea 
                  rows={4} 
                  placeholder="Hizmet açıklamasını Türkçe olarak girin"
                  maxLength={1000}
                  showCount
                />
              </Form.Item>
            </TabPane>
          </Tabs>
        </Form>
      </Modal>
    </div>
  );
};

export default Services;