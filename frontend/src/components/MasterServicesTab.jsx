// components/MasterServicesTab.jsx
import React, { useState, useEffect } from 'react';
import {
  Table,
  Button,
  Tag,
  Select,
  Space,
  message,
  Popconfirm,
  Modal,
  Form,
  Switch,
  Card,
  Row,
  Col,
  TreeSelect,
  Tooltip,
  Divider,
  Badge,
  Typography,
  Input,
  Alert,
  Spin,
  Checkbox,
  List,
  Avatar,
  InputNumber,
  Radio,
  Collapse,
} from 'antd';
import {
  PlusOutlined,
  DeleteOutlined,
  StarOutlined,
  StarFilled,
  SearchOutlined,
  FilterOutlined,
  ReloadOutlined,
  LoadingOutlined,
  InfoCircleOutlined,
  ShoppingCartOutlined,
  ClearOutlined,
  AppstoreOutlined,
  UnorderedListOutlined,
  CheckOutlined,
} from '@ant-design/icons';

const { Option } = Select;
const { Text } = Typography;
const { Search } = Input;
const { Panel } = Collapse;

const MasterServicesTab = ({ masterId, masterName, onServicesUpdated }) => {
  const [services, setServices] = useState([]);
  const [availableServices, setAvailableServices] = useState([]);
  const [loading, setLoading] = useState(false);
  const [availableLoading, setAvailableLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [batchModalVisible, setBatchModalVisible] = useState(false);
  const [selectedServices, setSelectedServices] = useState([]);
  const [categories, setCategories] = useState([]);
  const [form] = Form.useForm();
  const [batchForm] = Form.useForm();
  
  // Фильтры
  const [serviceType, setServiceType] = useState('all'); // all, primary, additional
  const [searchText, setSearchText] = useState('');
  const [viewMode, setViewMode] = useState('list'); // 'list' или 'grid'
  
  // Состояние для массового выбора
  const [selectedAvailableServices, setSelectedAvailableServices] = useState(new Set());
  const [bulkActionType, setBulkActionType] = useState('additional'); // 'primary' или 'additional'

  useEffect(() => {
    if (masterId) {
      fetchMasterServices();
      fetchAvailableServices();
      fetchCategories();
    }
  }, [masterId, serviceType]);

  const fetchMasterServices = async () => {
    if (!masterId) return;
    
    setLoading(true);
    try {
      const response = await fetch(`/api/masters/${masterId}/services`);
      const data = await response.json();
      
      if (data.success) {
        // Фильтруем по типу если нужно
        let filteredServices = data.services || [];
        
        if (serviceType === 'primary') {
          filteredServices = filteredServices.filter(s => s.is_primary);
        } else if (serviceType === 'additional') {
          filteredServices = filteredServices.filter(s => !s.is_primary);
        }
        
        // Фильтруем по поиску если есть
        if (searchText) {
          filteredServices = filteredServices.filter(s => 
            s.service_title?.toLowerCase().includes(searchText.toLowerCase()) ||
            s.category_title?.toLowerCase().includes(searchText.toLowerCase())
          );
        }
        
        setServices(filteredServices);
      } else {
        message.error(data.message || 'Ошибка загрузки услуг');
      }
    } catch (error) {
      console.error('Error fetching master services:', error);
      message.error('Ошибка при загрузке услуг мастера');
    } finally {
      setLoading(false);
    }
  };

  const fetchAvailableServices = async () => {
    if (!masterId) return;
    
    setAvailableLoading(true);
    try {
      const response = await fetch(`/api/masters/${masterId}/available-services`);
      const data = await response.json();
      
      if (data.success) {
        setAvailableServices(data.available_services || []);
      } else {
        message.error(data.message || 'Ошибка загрузки доступных услуг');
      }
    } catch (error) {
      console.error('Error fetching available services:', error);
      message.error('Ошибка при загрузке доступных услуг');
    } finally {
      setAvailableLoading(false);
    }
  };

  const fetchCategories = async () => {
    try {
      const response = await fetch('/api/services/categories/tree');
      const data = await response.json();
      setCategories(data);
    } catch (error) {
      console.error('Error fetching categories:', error);
    }
  };

  // Функция добавления одной услуги
  const handleAddService = async (serviceId, isPrimary = false) => {
    try {
      console.log('Adding service:', { masterId, serviceId, isPrimary });

      const formData = new FormData();
      formData.append('service_id', serviceId.toString());
      formData.append('is_primary', isPrimary.toString());

      const response = await fetch(`/api/masters/${masterId}/services`, {
        method: 'POST',
        body: formData,
      });
      
      console.log('Response status:', response.status);
      
      const result = await response.json().catch(err => {
        console.error('JSON parse error:', err);
        return { error: 'Invalid JSON response' };
      });
      
      console.log('Response data:', result);
      
      if (response.ok && result.success) {
        message.success('Услуга успешно добавлена мастеру');
        fetchMasterServices();
        fetchAvailableServices();
        if (onServicesUpdated) onServicesUpdated();
      } else {
        const errorMsg = result.detail || result.message || result.error || 'Ошибка при добавлении';
        console.error('Server error:', errorMsg);
        message.error(errorMsg);
      }
    } catch (error) {
      console.error('Network error:', error);
      message.error('Сетевая ошибка при добавлении услуги: ' + error.message);
    }
  };

  // Функция удаления услуги
  const handleRemoveService = async (serviceId) => {
    try {
      const response = await fetch(`/api/masters/${masterId}/services/${serviceId}`, {
        method: 'DELETE',
      });
      
      if (response.ok) {
        const result = await response.json();
        if (result.success) {
          message.success('Услуга удалена у мастера');
          fetchMasterServices();
          fetchAvailableServices();
          if (onServicesUpdated) onServicesUpdated();
        } else {
          message.error(result.message || 'Ошибка при удалении');
        }
      } else {
        const error = await response.json();
        message.error(error.detail || 'Ошибка при удалении');
      }
    } catch (error) {
      console.error('Error removing service:', error);
      message.error('Ошибка при удалении услуги');
    }
  };

  // Функция изменения типа услуги
  const handleTogglePrimary = async (service) => {
    try {
      const newStatus = !service.is_primary;
      
      // Сначала удаляем старую связь
      await fetch(`/api/masters/${masterId}/services/${service.service_id}`, {
        method: 'DELETE',
      });
      
      // Затем создаем новую с обновленным статусом
      const fd = new FormData();
      fd.append('service_id', service.service_id.toString());
      fd.append('is_primary', newStatus.toString());
      const response = await fetch(`/api/masters/${masterId}/services`, {
        method: 'POST',
        body: fd,
      });
      
      if (response.ok) {
        message.success(`Услуга теперь ${newStatus ? 'основная' : 'дополнительная'}`);
        fetchMasterServices();
        if (onServicesUpdated) onServicesUpdated();
      }
    } catch (error) {
      console.error('Error toggling service type:', error);
      message.error('Ошибка при изменении типа услуги');
    }
  };

  // Функция массового добавления услуг
  const handleBatchAddServices = async () => {
    if (selectedAvailableServices.size === 0) {
      message.warning('Выберите хотя бы одну услугу для добавления');
      return;
    }
    
    const serviceIds = Array.from(selectedAvailableServices);
    const isPrimary = bulkActionType === 'primary';
    
    try {
      setLoading(true);
      const promises = serviceIds.map(serviceId => {
        const fd = new FormData();
        fd.append('service_id', serviceId.toString());
        fd.append('is_primary', isPrimary.toString());
        return fetch(`/api/masters/${masterId}/services`, {
          method: 'POST',
          body: fd,
        });
      });

      const responses = await Promise.allSettled(promises);

      let successCount = 0;
      let errorCount = 0;

      responses.forEach((result, index) => {
        if (result.status === 'fulfilled' && result.value.ok) {
          successCount++;
        } else {
          errorCount++;
          console.error(`Ошибка добавления услуги ${serviceIds[index]}:`, result.reason || result.value);
        }
      });

      if (successCount > 0) {
        message.success(`Успешно добавлено ${successCount} услуг`);
      }

      if (errorCount > 0) {
        message.warning(`Не удалось добавить ${errorCount} услуг`);
      }

      // Сбрасываем выбранные услуги
      setSelectedAvailableServices(new Set());
      fetchMasterServices();
      fetchAvailableServices();
      if (onServicesUpdated) onServicesUpdated();
      
    } catch (error) {
      console.error('Error in batch add:', error);
      message.error('Ошибка при массовом добавлении услуг');
    } finally {
      setLoading(false);
    }
  };

  // Функция добавления через TreeSelect (старый метод)
  const handleBatchAdd = async (values) => {
    try {
      const serviceIds = values.service_ids || [];
      const isPrimary = values.is_primary || false;
      
      if (serviceIds.length === 0) {
        message.warning('Выберите хотя бы одну услугу');
        return;
      }
      
      setLoading(true);
      const promises = serviceIds.map(serviceId => {
        const fd = new FormData();
        fd.append('service_id', serviceId.toString());
        fd.append('is_primary', isPrimary.toString());
        return fetch(`/api/masters/${masterId}/services`, {
          method: 'POST',
          body: fd,
        });
      });

      const responses = await Promise.allSettled(promises);

      let successCount = 0;
      let errorCount = 0;

      responses.forEach((result, index) => {
        if (result.status === 'fulfilled' && result.value.ok) {
          successCount++;
        } else {
          errorCount++;
        }
      });

      if (successCount > 0) {
        message.success(`Добавлено ${successCount} услуг`);
      }

      if (errorCount > 0) {
        message.warning(`Не удалось добавить ${errorCount} услуг`);
      }

      setModalVisible(false);
      form.resetFields();
      setSelectedServices([]);
      fetchMasterServices();
      fetchAvailableServices();
      if (onServicesUpdated) onServicesUpdated();
      
    } catch (error) {
      message.error('Ошибка при массовом добавлении');
    } finally {
      setLoading(false);
    }
  };

  // Функция для выбора/снятия выбора услуги
  const toggleServiceSelection = (serviceId) => {
    const newSelection = new Set(selectedAvailableServices);
    if (newSelection.has(serviceId)) {
      newSelection.delete(serviceId);
    } else {
      newSelection.add(serviceId);
    }
    setSelectedAvailableServices(newSelection);
  };

  // Выбор всех услуг в текущем списке
  const selectAllServices = () => {
    const allIds = availableServices.map(service => service.id);
    setSelectedAvailableServices(new Set(allIds));
  };

  // Сброс выбора всех услуг
  const clearSelection = () => {
    setSelectedAvailableServices(new Set());
  };

  // Групповые действия
  const handleBulkAction = (action) => {
    const selectedIds = Array.from(selectedAvailableServices);
    if (selectedIds.length === 0) {
      message.warning('Выберите хотя бы одну услугу');
      return;
    }
    
    if (action === 'add-as-primary') {
      setBulkActionType('primary');
      handleBatchAddServices();
    } else if (action === 'add-as-additional') {
      setBulkActionType('additional');
      handleBatchAddServices();
    }
  };

  // Обработчик удаления выбранных услуг
  const handleRemoveSelectedServices = async () => {
    if (selectedAvailableServices.size === 0) {
      message.warning('Выберите хотя бы одну услугу для удаления');
      return;
    }
    
    Modal.confirm({
      title: 'Удаление выбранных услуг',
      content: (
        <div>
          <p>Вы уверены, что хотите удалить {selectedAvailableServices.size} выбранных услуг у мастера?</p>
          <Alert
            type="warning"
            message="Это действие нельзя отменить!"
            showIcon
            style={{ marginTop: 8 }}
          />
        </div>
      ),
      okText: 'Да, удалить',
      okType: 'danger',
      cancelText: 'Отмена',
      onOk: async () => {
        try {
          setLoading(true);
          const promises = Array.from(selectedAvailableServices).map(serviceId => 
            fetch(`/api/masters/${masterId}/services/${serviceId}`, {
              method: 'DELETE',
            })
          );
          
          const responses = await Promise.allSettled(promises);
          
          let successCount = 0;
          let errorCount = 0;
          
          responses.forEach((result, index) => {
            if (result.status === 'fulfilled' && result.value.ok) {
              successCount++;
            } else {
              errorCount++;
            }
          });
          
          if (successCount > 0) {
            message.success(`Удалено ${successCount} услуг`);
          }
          
          if (errorCount > 0) {
            message.warning(`Не удалось удалить ${errorCount} услуг`);
          }
          
          clearSelection();
          fetchMasterServices();
          fetchAvailableServices();
          if (onServicesUpdated) onServicesUpdated();
          
        } catch (error) {
          console.error('Error removing services:', error);
          message.error('Ошибка при удалении услуг');
        } finally {
          setLoading(false);
        }
      },
    });
  };

  const columns = [
    {
      title: 'Услуга',
      key: 'service',
      width: 300,
      render: (record) => (
        <div>
          <div style={{ fontWeight: 500, fontSize: 14 }}>
            {record.service_title || `Услуга #${record.service_id}`}
          </div>
          <div style={{ fontSize: 12, color: '#666' }}>
            Категория: {record.category_title || 'Не указана'}
          </div>
          {record.service_description && (
            <div style={{ fontSize: 12, color: '#888', marginTop: 4 }}>
              {record.service_description.length > 100 
                ? `${record.service_description.substring(0, 100)}...` 
                : record.service_description}
            </div>
          )}
        </div>
      ),
    },
    {
      title: 'Цена',
      dataIndex: 'price',
      key: 'price',
      width: 100,
      render: (price) => (
        <div style={{ fontWeight: 500, fontSize: 14 }}>
          {price ? `${price.toLocaleString()} ₽` : '—'}
        </div>
      ),
    },
    {
      title: 'Длительность',
      dataIndex: 'duration_minutes',
      key: 'duration',
      width: 120,
      render: (minutes) => (
        <div style={{ fontSize: 13 }}>
          {minutes} мин
        </div>
      ),
    },
    {
      title: 'Тип',
      dataIndex: 'is_primary',
      key: 'type',
      width: 120,
      render: (isPrimary, record) => (
        <Tooltip title={isPrimary ? 'Основная услуга' : 'Дополнительная услуга'}>
          <Button
            type="text"
            icon={isPrimary ? <StarFilled style={{ color: '#faad14' }} /> : <StarOutlined />}
            onClick={() => handleTogglePrimary(record)}
            style={{ padding: '4px 8px' }}
          >
            {isPrimary ? 'Основная' : 'Дополнительная'}
          </Button>
        </Tooltip>
      ),
    },
    {
      title: 'Статус',
      key: 'status',
      width: 100,
      render: (record) => (
        <Tag color={record.service_active ? 'green' : 'red'}>
          {record.service_active ? 'Активна' : 'Неактивна'}
        </Tag>
      ),
    },
    {
      title: 'Действия',
      key: 'actions',
      width: 100,
      render: (record) => (
        <Popconfirm
          title="Удалить услугу у мастера?"
          description="Вы уверены, что хотите удалить эту услугу?"
          onConfirm={() => handleRemoveService(record.service_id)}
          okText="Да, удалить"
          cancelText="Отмена"
          okType="danger"
        >
          <Button 
            type="link" 
            danger 
            icon={<DeleteOutlined />}
            style={{ padding: '4px 8px' }}
          >
            Удалить
          </Button>
        </Popconfirm>
      ),
    },
  ];

  // Статистика
  const primaryCount = services.filter(s => s.is_primary).length;
  const additionalCount = services.filter(s => !s.is_primary).length;
  const totalPrice = services.reduce((sum, s) => sum + (s.price || 0), 0);
  const totalDuration = services.reduce((sum, s) => sum + (s.duration_minutes || 0), 0);

  return (
    <div style={{ padding: '0 8px' }}>
      {/* Статистика */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card size="small">
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 24, fontWeight: 'bold', color: '#1890ff' }}>
                {services.length}
              </div>
              <div style={{ fontSize: 12, color: '#666' }}>Всего услуг</div>
            </div>
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 24, fontWeight: 'bold', color: '#faad14' }}>
                {primaryCount}
              </div>
              <div style={{ fontSize: 12, color: '#666' }}>Основные</div>
            </div>
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 24, fontWeight: 'bold', color: '#52c41a' }}>
                {totalPrice.toLocaleString()} ₽
              </div>
              <div style={{ fontSize: 12, color: '#666' }}>Общая стоимость</div>
            </div>
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 24, fontWeight: 'bold', color: '#722ed1' }}>
                {totalDuration} мин
              </div>
              <div style={{ fontSize: 12, color: '#666' }}>Общая длительность</div>
            </div>
          </Card>
        </Col>
      </Row>

      {/* Панель управления */}
      <Card
        title="Услуги мастера"
        extra={
          <Space>
            <Button
              icon={<PlusOutlined />}
              onClick={() => setBatchModalVisible(true)}
            >
              Добавить несколько услуг
            </Button>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => setModalVisible(true)}
            >
              Расширенный выбор
            </Button>
          </Space>
        }
        style={{ marginBottom: 16 }}
      >
        <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
          <Col span={8}>
            <Search
              placeholder="Поиск по услугам..."
              allowClear
              enterButton={<SearchOutlined />}
              onSearch={(value) => {
                setSearchText(value);
                fetchMasterServices();
              }}
              onChange={(e) => {
                if (!e.target.value) {
                  setSearchText('');
                  fetchMasterServices();
                }
              }}
            />
          </Col>
          <Col span={8}>
            <Select
              placeholder="Фильтр по типу"
              style={{ width: '100%' }}
              value={serviceType}
              onChange={setServiceType}
            >
              <Option value="all">Все услуги</Option>
              <Option value="primary">Только основные</Option>
              <Option value="additional">Только дополнительные</Option>
            </Select>
          </Col>
          <Col span={8} style={{ textAlign: 'right' }}>
            <Button
              icon={<ReloadOutlined />}
              onClick={fetchMasterServices}
              loading={loading}
            >
              Обновить
            </Button>
          </Col>
        </Row>

        <Table
          columns={columns}
          dataSource={services}
          rowKey="service_id"
          loading={loading}
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showTotal: (total) => `Всего ${total} услуг`,
          }}
          scroll={{ x: 800 }}
          locale={{
            emptyText: (
              <div style={{ padding: '40px 0', textAlign: 'center' }}>
                <div style={{ fontSize: 16, marginBottom: 8, color: '#999' }}>
                  У мастера пока нет услуг
                </div>
                <div style={{ fontSize: 14, color: '#666', marginBottom: 16 }}>
                  Добавьте услуги, чтобы мастер мог их предоставлять
                </div>
                <Button
                  type="primary"
                  icon={<PlusOutlined />}
                  onClick={() => setBatchModalVisible(true)}
                >
                  Добавить услуги
                </Button>
              </div>
            ),
          }}
        />
      </Card>

      {/* Модальное окно массового добавления (новое с чекбоксами) */}
      <Modal
        title={
          <Space>
            <ShoppingCartOutlined />
            <span>Массовое добавление услуг</span>
            <Badge count={selectedAvailableServices.size} />
          </Space>
        }
        open={batchModalVisible}
        onCancel={() => {
          setBatchModalVisible(false);
          clearSelection();
        }}
        footer={null}
        width={800}
        style={{ top: 20 }}
      >
        <Spin spinning={availableLoading}>
          <div style={{ marginBottom: 16 }}>
            <Space style={{ marginBottom: 8 }}>
              <Text strong>Выбрано: {selectedAvailableServices.size} услуг</Text>
              <Button size="small" onClick={selectAllServices}>
                Выбрать все
              </Button>
              <Button size="small" onClick={clearSelection}>
                Сбросить
              </Button>
            </Space>
            
            <Space style={{ marginBottom: 16 }}>
              <Radio.Group 
                value={bulkActionType} 
                onChange={(e) => setBulkActionType(e.target.value)}
                buttonStyle="solid"
              >
                <Radio.Button value="additional">
                  Добавить как дополнительные
                </Radio.Button>
                <Radio.Button value="primary">
                  Добавить как основные
                </Radio.Button>
              </Radio.Group>
            </Space>
            
            <Space style={{ marginBottom: 16 }}>
              <Button 
                type="primary" 
                icon={<PlusOutlined />}
                onClick={handleBatchAddServices}
                disabled={selectedAvailableServices.size === 0}
                loading={loading}
              >
                Добавить выбранные ({selectedAvailableServices.size})
              </Button>
              
              <Button 
                danger 
                icon={<DeleteOutlined />}
                onClick={handleRemoveSelectedServices}
                disabled={selectedAvailableServices.size === 0}
              >
                Удалить выбранные
              </Button>
            </Space>
          </div>
          
          <Divider />
          
          <div style={{ maxHeight: 400, overflowY: 'auto', paddingRight: 8 }}>
            {availableServices.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '40px 0', color: '#999' }}>
                Нет доступных услуг для добавления
              </div>
            ) : (
              <List
                dataSource={availableServices}
                renderItem={(service) => (
                  <List.Item
                    style={{
                      padding: '12px 16px',
                      borderBottom: '1px solid #f0f0f0',
                      backgroundColor: selectedAvailableServices.has(service.id) ? '#f6ffed' : 'transparent',
                      cursor: 'pointer',
                      borderRadius: 4,
                    }}
                    onClick={() => toggleServiceSelection(service.id)}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', width: '100%' }}>
                      <Checkbox
                        checked={selectedAvailableServices.has(service.id)}
                        onChange={(e) => {
                          e.stopPropagation();
                          toggleServiceSelection(service.id);
                        }}
                        style={{ marginRight: 12 }}
                      />
                      
                      <Avatar
                        size="small"
                        style={{ 
                          backgroundColor: selectedAvailableServices.has(service.id) ? '#52c41a' : '#f0f0f0',
                          color: selectedAvailableServices.has(service.id) ? '#fff' : '#666',
                          marginRight: 12
                        }}
                      >
                        {service.category_title ? service.category_title.charAt(0) : 'У'}
                      </Avatar>
                      
                      <div style={{ flex: 1 }}>
                        <div style={{ fontWeight: 500, marginBottom: 4 }}>
                          {service.title}
                        </div>
                        <div style={{ fontSize: 12, color: '#666' }}>
                          Категория: {service.category_title || 'Не указана'} | 
                          Цена: {service.price.toLocaleString()} ₽ | 
                          Длительность: {service.duration_minutes} мин
                        </div>
                        {service.description && (
                          <div style={{ fontSize: 12, color: '#888', marginTop: 4 }}>
                            {service.description.length > 100 
                              ? `${service.description.substring(0, 100)}...` 
                              : service.description}
                          </div>
                        )}
                      </div>
                      
                      <Space>
                        <Button
                          size="small"
                          icon={<StarFilled style={{ color: '#faad14' }} />}
                          onClick={(e) => {
                            e.stopPropagation();
                            handleAddService(service.id, true);
                          }}
                        >
                          Основная
                        </Button>
                        <Button
                          size="small"
                          icon={<PlusOutlined />}
                          onClick={(e) => {
                            e.stopPropagation();
                            handleAddService(service.id, false);
                          }}
                        >
                          Дополнительная
                        </Button>
                      </Space>
                    </div>
                  </List.Item>
                )}
              />
            )}
          </div>
        </Spin>
      </Modal>

      {/* Модальное окно расширенного выбора (TreeSelect) */}
      <Modal
        title="Расширенный выбор услуг"
        open={modalVisible}
        onCancel={() => {
          setModalVisible(false);
          form.resetFields();
          setSelectedServices([]);
        }}
        onOk={() => form.submit()}
        width={600}
        okText="Добавить выбранные"
        cancelText="Отмена"
      >
        <Form form={form} layout="vertical" onFinish={handleBatchAdd}>
          <Form.Item
            name="service_ids"
            label="Выберите услуги для добавления"
            rules={[{ required: true, message: 'Выберите хотя бы одну услугу' }]}
          >
            <TreeSelect
              treeData={categories}
              placeholder="Начните вводить название услуги или категории"
              treeDefaultExpandAll
              showSearch
              treeCheckable
              multiple
              treeNodeFilterProp="title"
              onChange={(value) => setSelectedServices(value)}
              style={{ width: '100%' }}
              dropdownStyle={{ maxHeight: 400, overflow: 'auto' }}
            />
          </Form.Item>
          
          <Form.Item
            name="is_primary"
            label="Тип добавляемых услуг"
            valuePropName="checked"
          >
            <Switch
              checkedChildren="Основные"
              unCheckedChildren="Дополнительные"
            />
          </Form.Item>
          
          <div style={{ background: '#f6ffed', padding: 12, borderRadius: 6, marginBottom: 16 }}>
            <div style={{ fontSize: 12, color: '#666' }}>
              <div>📊 Статистика:</div>
              <div>• Уже добавлено: {services.length} услуг</div>
              <div>• Будет добавлено: {selectedServices.length} услуг</div>
              <div>• Всего станет: {services.length + selectedServices.length} услуг</div>
            </div>
          </div>
        </Form>
      </Modal>
    </div>
  );
};

export default MasterServicesTab;