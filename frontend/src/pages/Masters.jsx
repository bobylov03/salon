// Masters.jsx (исправленный - с правильной валидацией telegram_id)
import React, { useState, useEffect, useRef } from 'react';
import {
  Table,
  Button,
  Modal,
  Form,
  Input,
  Upload,
  Switch,
  Tag,
  Space,
  message,
  Popconfirm,
  Card,
  Row,
  Col,
  Select,
  Divider,
  Image,
  Spin,
  Avatar,
  Tooltip,
  Dropdown,
  Menu,
  Badge,
  Typography,
  InputNumber,
  Alert,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  EyeOutlined,
  SearchOutlined,
  UploadOutlined,
  UserOutlined,
  MoreOutlined,
  ScissorOutlined,
  StarOutlined,
  StarFilled,
  FilterOutlined,
  ReloadOutlined,
  InfoCircleOutlined,
  CheckCircleOutlined,
  WarningOutlined,
  SendOutlined,
  MessageOutlined,
  PhoneOutlined,
} from '@ant-design/icons';
import { mastersAPI } from '../services/api';
import MasterDetailsModal from '../components/MasterDetailsModal';

const { TextArea } = Input;
const { Option } = Select;
const { Text } = Typography;

const Masters = () => {
  const [masters, setMasters] = useState([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingMaster, setEditingMaster] = useState(null);
  const [detailsModalVisible, setDetailsModalVisible] = useState(false);
  const [selectedMasterId, setSelectedMasterId] = useState(null);
  const [photoPreview, setPhotoPreview] = useState(null);
  const [photoFile, setPhotoFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 10,
    total: 0,
  });
  const [filters, setFilters] = useState({
    search: '',
    is_active: null,
    services_count: null,
  });

  const [form] = Form.useForm();
  const fileInputRef = useRef(null);

  useEffect(() => {
    fetchMasters();
  }, [pagination.current, pagination.pageSize, filters]);

  // Очищаем object URLs при размонтировании
  useEffect(() => {
    return () => {
      if (photoPreview && photoPreview.startsWith('blob:')) {
        URL.revokeObjectURL(photoPreview);
      }
    };
  }, [photoPreview]);

  const fetchMasters = async () => {
    setLoading(true);
    try {
      const response = await mastersAPI.getMasters({
        page: pagination.current,
        per_page: pagination.pageSize,
        ...filters,
        with_services: true,
      });
      
      const transformedMasters = (response.data.items || response.data || []).map(master => ({
        ...master,
        telegram_id: master.telegram_id,
      }));
      
      setMasters(transformedMasters);
      setPagination({
        ...pagination,
        total: response.data.total || 0,
      });
    } catch (error) {
      console.error('Error fetching masters:', error);
      message.error('Ошибка при загрузке мастеров: ' + (error.message || 'Неизвестная ошибка'));
    } finally {
      setLoading(false);
    }
  };

  const handleTableChange = (pagination) => {
    setPagination(pagination);
  };

  const handleSubmit = async (values) => {
    try {
      console.log('Form values:', values);
      console.log('Telegram ID from form:', values.telegram_id);
      
      setUploading(true);
      const formData = new FormData();
      
      // Добавляем текстовые поля из формы
      formData.append('first_name', values.first_name || '');
      formData.append('last_name', values.last_name || '');
      
      // Сохраняем phone и telegram_id отдельно
      if (values.phone) {
        console.log('Сохраняем телефон:', values.phone);
        formData.append('phone', values.phone);
      }
      
      if (values.telegram_id) {
        console.log('Сохраняем Telegram ID:', values.telegram_id);
        formData.append('telegram_id', values.telegram_id.toString());
      }
      
      if (values.email) formData.append('email', values.email);
      if (values.qualification) formData.append('qualification', values.qualification);
      if (values.description) formData.append('description', values.description);
      
      // Добавляем статус
      formData.append('is_active', values.is_active ? 'true' : 'false');
      
      // Добавляем фото если есть
      if (photoFile) {
        formData.append('photo', photoFile);
      }
      
      // Добавляем флаг удаления фото для редактирования
      if (editingMaster && values.remove_photo) {
        formData.append('remove_photo', 'true');
      }
      
      let result;
      if (editingMaster) {
        result = await mastersAPI.updateMaster(editingMaster.id, formData);
        message.success('Мастер обновлен');
      } else {
        result = await mastersAPI.createMaster(formData);
        message.success('Мастер создан');
      }
      
      console.log('API Response:', result);
      
      setModalVisible(false);
      form.resetFields();
      setPhotoFile(null);
      
      // Очищаем preview URL
      if (photoPreview && photoPreview.startsWith('blob:')) {
        URL.revokeObjectURL(photoPreview);
      }
      setPhotoPreview(null);
      
      fetchMasters();
    } catch (error) {
      console.error('Error submitting form:', error);
      message.error(error.response?.data?.detail || error.message || 'Ошибка при сохранении');
    } finally {
      setUploading(false);
    }
  };

  const handleEdit = (record) => {
    setEditingMaster(record);
    form.setFieldsValue({
      first_name: record.first_name,
      last_name: record.last_name,
      phone: record.phone || '',
      telegram_id: record.telegram_id || '',
      email: record.email,
      qualification: record.qualification,
      description: record.description,
      is_active: record.is_active,
      remove_photo: false,
    });
    
    if (record.photo_url) {
      setPhotoPreview(record.photo_url);
    } else {
      setPhotoPreview(null);
    }
    
    setPhotoFile(null);
    setModalVisible(true);
  };

  const handleDeactivate = async (id) => {
    try {
      const master = masters.find(m => m.id === id);
      if (!master) return;
      
      const newStatus = !master.is_active;
      
      const formData = new FormData();
      formData.append('is_active', newStatus.toString());
      
      await mastersAPI.updateMaster(id, formData);
      message.success(`Мастер успешно ${newStatus ? 'активирован' : 'деактивирован'}`);
      fetchMasters();
    } catch (error) {
      console.error('Error toggling master status:', error);
      message.error('Ошибка при изменении статуса мастера');
    }
  };

  const handleDelete = async (id) => {
    try {
      const master = masters.find(m => m.id === id);
      if (master && master.services_count > 0) {
        Modal.confirm({
          title: 'У мастера есть услуги!',
          content: (
            <div>
              <Alert
                type="warning"
                message="Внимание!"
                description={
                  <div>
                    <p>У этого мастера есть {master.services_count} услуг.</p>
                    <p>При удалении мастера все связанные услуги будут удалены.</p>
                    <p>Вы уверены, что хотите продолжить?</p>
                  </div>
                }
                showIcon
                style={{ marginBottom: 16 }}
              />
            </div>
          ),
          okText: 'Да, удалить',
          okType: 'danger',
          cancelText: 'Отмена',
          onOk: async () => {
            try {
              await mastersAPI.deleteMaster(id);
              message.success('Мастер успешно удален');
              fetchMasters();
            } catch (error) {
              console.error('Error deleting master:', error);
              message.error('Ошибка при удалении мастера');
            }
          },
        });
      } else {
        await mastersAPI.deleteMaster(id);
        message.success('Мастер успешно удален');
        fetchMasters();
      }
    } catch (error) {
      console.error('Error deleting master:', error);
      message.error('Ошибка при удалении мастера');
    }
  };

  const showDetails = (id) => {
    setSelectedMasterId(id);
    setDetailsModalVisible(true);
  };

  const beforeUpload = (file) => {
    const isImage = file.type.startsWith('image/');
    if (!isImage) {
      message.error('Можно загружать только изображения!');
      return Upload.LIST_IGNORE;
    }
    
    const isLt5M = file.size / 1024 / 1024 < 5;
    if (!isLt5M) {
      message.error('Изображение должно быть меньше 5MB!');
      return Upload.LIST_IGNORE;
    }
    
    return false;
  };

  const handlePhotoChange = (info) => {
    const { file } = info;
    
    if (file.status === 'uploading') {
      setUploading(true);
      return;
    }
    
    if (file.status === 'removed') {
      removePhoto();
      return;
    }
    
    const rawFile = file.originFileObj || file;
    
    if (!rawFile) {
      console.error('No file object found:', file);
      message.error('Не удалось получить файл');
      return;
    }
    
    if (!(rawFile instanceof File)) {
      console.error('Invalid file object:', rawFile);
      message.error('Неверный формат файла');
      return;
    }
    
    if (!rawFile.type.startsWith('image/')) {
      message.error('Можно загружать только изображения!');
      return;
    }
    
    setPhotoFile(rawFile);
    
    try {
      const previewUrl = URL.createObjectURL(rawFile);
      
      if (photoPreview && photoPreview.startsWith('blob:')) {
        URL.revokeObjectURL(photoPreview);
      }
      
      setPhotoPreview(previewUrl);
      message.success(`Файл "${rawFile.name}" выбран для загрузки`);
    } catch (error) {
      console.error('Error creating object URL:', error);
      message.error('Ошибка при создании предпросмотра');
      
      const reader = new FileReader();
      reader.onload = (e) => {
        setPhotoPreview(e.target.result);
      };
      reader.readAsDataURL(rawFile);
    }
    
    setUploading(false);
  };

  const removePhoto = () => {
    if (photoPreview && photoPreview.startsWith('blob:')) {
      URL.revokeObjectURL(photoPreview);
    }
    
    setPhotoFile(null);
    setPhotoPreview(null);
    
    if (editingMaster) {
      form.setFieldsValue({ remove_photo: true });
    }
  };

  const handleCreate = () => {
    setEditingMaster(null);
    form.resetFields();
    setPhotoFile(null);
    setPhotoPreview(null);
    setModalVisible(true);
  };

  const handleFilterChange = (key, value) => {
    setFilters(prev => ({
      ...prev,
      [key]: value,
    }));
    setPagination(prev => ({
      ...prev,
      current: 1,
    }));
  };

  const handleManualUpload = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    const isImage = file.type.startsWith('image/');
    if (!isImage) {
      message.error('Можно загружать только изображения!');
      return;
    }
    
    const isLt5M = file.size / 1024 / 1024 < 5;
    if (!isLt5M) {
      message.error('Изображение должно быть меньше 5MB!');
      return;
    }
    
    const syntheticEvent = {
      file: {
        uid: '-1',
        name: file.name,
        size: file.size,
        type: file.type,
        originFileObj: file,
        status: 'done',
      }
    };
    
    handlePhotoChange(syntheticEvent);
  };

  const handleRefresh = () => {
    fetchMasters();
    message.success('Список мастеров обновлен');
  };

  const handleAddServiceToMaster = async (masterId) => {
    try {
      const response = await fetch(`/api/masters/${masterId}/available-services`);
      const data = await response.json();
      
      if (!data.success || data.available_services.length === 0) {
        message.warning('Нет доступных услуг для добавления');
        return;
      }
      
      let selectedServiceId = null;
      let selectedIsPrimary = false;
      
      Modal.confirm({
        title: 'Добавить услугу мастеру',
        content: (
          <div>
            <Select
              placeholder="Выберите услугу"
              style={{ width: '100%', marginBottom: '16px' }}
              showSearch
              optionFilterProp="children"
              filterOption={(input, option) =>
                option.children.toLowerCase().includes(input.toLowerCase())
              }
              onChange={(value) => selectedServiceId = value}
            >
              {data.available_services.map(service => (
                <Option key={service.id} value={service.id}>
                  {service.title} - {service.price}₽ ({service.duration_minutes} мин)
                </Option>
              ))}
            </Select>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Switch 
                size="small" 
                onChange={(checked) => selectedIsPrimary = checked}
              />
              <span>Сделать основной услугой</span>
            </div>
          </div>
        ),
        onOk: async () => {
          if (!selectedServiceId) {
            message.warning('Выберите услугу');
            return Promise.reject();
          }
          
          try {
            const formData = new FormData();
            formData.append('service_id', selectedServiceId.toString());
            formData.append('is_primary', selectedIsPrimary.toString());
            
            console.log('FormData:', {
              service_id: selectedServiceId,
              is_primary: selectedIsPrimary
            });
            
            const addResponse = await fetch(`/api/masters/${masterId}/services`, {
              method: 'POST',
              body: formData,
            });
            
            console.log('Response status:', addResponse.status);
            
            const addData = await addResponse.json();
            
            if (addResponse.ok && addData.success) {
              message.success('Услуга успешно добавлена мастеру');
              fetchMasters();
            } else {
              const errorMsg = addData.detail || addData.message || addData.error || 'Ошибка при добавлении';
              message.error(errorMsg);
            }
          } catch (error) {
            console.error('Error adding service:', error);
            message.error('Ошибка при добавлении услуги: ' + error.message);
          }
        },
      });
    } catch (error) {
      console.error('Error fetching available services:', error);
      message.error('Ошибка при получении доступных услуг');
    }
  };

  const actionsMenu = (record) => (
    <Menu>
      <Menu.Item key="view" onClick={() => showDetails(record.id)}>
        <EyeOutlined /> Просмотр
      </Menu.Item>
      <Menu.Item key="edit" onClick={() => handleEdit(record)}>
        <EditOutlined /> Редактировать
      </Menu.Item>
      <Menu.Item key="add_service" onClick={() => handleAddServiceToMaster(record.id)}>
        <PlusOutlined /> Добавить услугу
      </Menu.Item>
      <Menu.Item key="status" onClick={() => handleDeactivate(record.id)}>
        <DeleteOutlined style={{ 
          color: record.is_active ? '#ff4d4f' : '#52c41a',
          marginRight: 8 
        }} />
        {record.is_active ? 'Деактивировать' : 'Активировать'}
      </Menu.Item>
      <Menu.Divider />
      <Menu.Item 
        key="delete" 
        danger
        onClick={() => {
          Modal.confirm({
            title: 'Удалить мастера?',
            content: (
              <div>
                <p>Вы уверены, что хотите удалить мастера <strong>{record.first_name} {record.last_name}</strong>?</p>
                {record.services_count > 0 && (
                  <Alert
                    type="warning"
                    message={`У мастера есть ${record.services_count} услуг`}
                    description="Все связанные услуги будут удалены."
                    showIcon
                    style={{ marginTop: 8 }}
                  />
                )}
                <p style={{ color: '#ff4d4f', marginTop: 8 }}>Это действие нельзя отменить!</p>
              </div>
            ),
            okText: 'Да, удалить',
            okType: 'danger',
            cancelText: 'Отмена',
            onOk: () => handleDelete(record.id),
          });
        }}
      >
        <DeleteOutlined /> Удалить навсегда
      </Menu.Item>
    </Menu>
  );

  const columns = [
    {
      title: 'Фото',
      dataIndex: 'photo_url',
      key: 'photo',
      width: 80,
      render: (photo_url, record) => (
        <Tooltip title="Нажмите для просмотра деталей">
          <Avatar
            size={50}
            src={photo_url}
            icon={!photo_url && <UserOutlined />}
            style={{ 
              backgroundColor: photo_url ? 'transparent' : '#f0f0f0',
              cursor: 'pointer'
            }}
            onClick={() => showDetails(record.id)}
          />
        </Tooltip>
      ),
    },
    {
      title: 'Имя',
      key: 'name',
      render: (_, record) => (
        <div>
          <div style={{ fontWeight: 500, fontSize: 14 }}>
            {`${record.first_name} ${record.last_name}`}
            {record.qualification && (
              <Tag color="blue" style={{ marginLeft: 8, fontSize: 10 }}>
                {record.qualification}
              </Tag>
            )}
          </div>
          {record.email && (
            <div style={{ fontSize: '12px', color: '#666' }}>
              <MessageOutlined /> {record.email}
            </div>
          )}
          {record.phone && (
            <div style={{ fontSize: '12px', color: '#666', display: 'flex', alignItems: 'center', gap: 4 }}>
              <PhoneOutlined style={{ color: '#52c41a' }} />
              <span>Телефон: </span>
              <span style={{ 
                fontFamily: 'monospace',
                backgroundColor: '#f5f5f5',
                padding: '1px 4px',
                borderRadius: '2px'
              }}>
                {record.phone}
              </span>
            </div>
          )}
          {record.telegram_id && (
            <div style={{ fontSize: '12px', color: '#666', display: 'flex', alignItems: 'center', gap: 4 }}>
              <SendOutlined style={{ color: '#0088cc' }} />
              <span>Telegram: </span>
              <span style={{ 
                fontFamily: 'monospace',
                backgroundColor: '#f5f5f5',
                padding: '1px 4px',
                borderRadius: '2px'
              }}>
                {record.telegram_id}
              </span>
            </div>
          )}
        </div>
      ),
    },
    {
      title: 'Услуги',
      key: 'services',
      width: 140,
      render: (_, record) => {
        const servicesCount = record.services_count || 0;
        const services = record.services || [];
        const primaryCount = services.filter(s => s.is_primary).length;
        
        return (
          <Tooltip
            title={
              <div style={{ maxWidth: 300 }}>
                <div style={{ fontWeight: 500, marginBottom: 8 }}>Услуги мастера:</div>
                {servicesCount === 0 ? (
                  <div style={{ color: '#999' }}>Нет назначенных услуг</div>
                ) : (
                  <>
                    <div>Всего: {servicesCount}</div>
                    <div>Основных: {primaryCount}</div>
                    <div>Дополнительных: {servicesCount - primaryCount}</div>
                    <Divider style={{ margin: '8px 0' }} />
                    <div style={{ maxHeight: 200, overflowY: 'auto' }}>
                      {services.map(service => (
                        <div key={service.service_id} style={{ 
                          padding: '4px 8px', 
                          background: service.is_primary ? '#fffbe6' : '#f6ffed',
                          marginBottom: 4,
                          borderRadius: 4,
                          fontSize: 11
                        }}>
                          <div>
                            <StarOutlined style={{ 
                              color: service.is_primary ? '#faad14' : '#d9d9d9',
                              marginRight: 4,
                              fontSize: 10 
                            }} />
                            <strong>{service.service_title || `Услуга #${service.service_id}`}</strong>
                          </div>
                          <div style={{ color: '#666' }}>
                            {service.price}₽ • {service.duration_minutes} мин
                          </div>
                        </div>
                      ))}
                    </div>
                  </>
                )}
              </div>
            }
          >
            <Badge 
              count={servicesCount} 
              style={{ 
                backgroundColor: servicesCount > 0 ? '#52c41a' : '#d9d9d9',
                cursor: 'pointer',
                boxShadow: '0 0 0 1px #fff'
              }}
              overflowCount={99}
            >
              <Button 
                type="link" 
                size="small"
                icon={<ScissorOutlined />}
                onClick={() => showDetails(record.id)}
                style={{ 
                  color: servicesCount > 0 ? '#1890ff' : '#999',
                  padding: '0 8px',
                  fontWeight: servicesCount > 0 ? 500 : 400
                }}
              >
                {servicesCount > 0 ? `${servicesCount} услуг` : 'Нет услуг'}
              </Button>
            </Badge>
          </Tooltip>
        );
      },
    },
    {
      title: 'Статус',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 100,
      render: (active, record) => (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Tag 
            color={active ? 'green' : 'red'}
            icon={active ? <CheckCircleOutlined /> : <WarningOutlined />}
          >
            {active ? 'Активен' : 'Неактивен'}
          </Tag>
          {record.services_count === 0 && (
            <Tooltip title="У мастера нет назначенных услуг">
              <InfoCircleOutlined style={{ color: '#faad14' }} />
            </Tooltip>
          )}
        </div>
      ),
    },
    {
      title: 'Действия',
      key: 'actions',
      width: 60,
      render: (_, record) => (
        <Dropdown 
          overlay={actionsMenu(record)} 
          trigger={['click']}
          placement="bottomRight"
        >
          <Button 
            type="text" 
            icon={<MoreOutlined />}
            style={{ padding: '4px 8px' }}
          />
        </Dropdown>
      ),
    },
  ];

  const renderStats = () => {
    const activeMasters = masters.filter(m => m.is_active).length;
    const mastersWithServices = masters.filter(m => (m.services_count || 0) > 0).length;
    const totalServices = masters.reduce((sum, m) => sum + (m.services_count || 0), 0);
    
    return (
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card size="small" hoverable>
            <StatisticCard
              title="Всего мастеров"
              value={masters.length}
              color="#1890ff"
              icon={<UserOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small" hoverable>
            <StatisticCard
              title="Активных"
              value={activeMasters}
              color="#52c41a"
              icon={<CheckCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small" hoverable>
            <StatisticCard
              title="С услугами"
              value={mastersWithServices}
              color="#722ed1"
              icon={<ScissorOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small" hoverable>
            <StatisticCard
              title="Всего услуг"
              value={totalServices}
              color="#fa8c16"
              icon={<StarOutlined />}
            />
          </Card>
        </Col>
      </Row>
    );
  };

  const StatisticCard = ({ title, value, color, icon }) => (
    <div style={{ textAlign: 'center' }}>
      <div style={{ 
        fontSize: 24, 
        fontWeight: 'bold', 
        color,
        marginBottom: 4 
      }}>
        {value}
      </div>
      <div style={{ fontSize: 12, color: '#666', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 4 }}>
        {React.cloneElement(icon, { style: { fontSize: 14 } })}
        {title}
      </div>
    </div>
  );

  return (
    <div style={{ padding: '0 8px' }}>
      <Card
        title={
          <Space>
            <span style={{ fontSize: 18, fontWeight: 500 }}>Мастера</span>
            <Tag color="blue">{pagination.total}</Tag>
          </Space>
        }
        extra={
          <Space>
            <Button
              icon={<ReloadOutlined />}
              onClick={handleRefresh}
              loading={loading}
            >
              Обновить
            </Button>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={handleCreate}
            >
              Добавить мастера
            </Button>
          </Space>
        }
        style={{ marginBottom: 16 }}
      >
        {renderStats()}
        
        <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
          <Col span={8}>
            <Input
              placeholder="Поиск по имени, телефону или Telegram..."
              prefix={<SearchOutlined />}
              onChange={(e) => handleFilterChange('search', e.target.value)}
              allowClear
              size="middle"
            />
          </Col>
          <Col span={8}>
            <Select
              placeholder="Фильтр по статусу"
              style={{ width: '100%' }}
              allowClear
              onChange={(value) => handleFilterChange('is_active', value)}
              size="middle"
            >
              <Option value={true}>Активен</Option>
              <Option value={false}>Неактивен</Option>
            </Select>
          </Col>
          <Col span={8}>
            <Select
              placeholder="Фильтр по услугам"
              style={{ width: '100%' }}
              allowClear
              onChange={(value) => handleFilterChange('services_count', value)}
              size="middle"
            >
              <Option value="has_services">С услугами</Option>
              <Option value="no_services">Без услуг</Option>
            </Select>
          </Col>
        </Row>

        <Table
          columns={columns}
          dataSource={masters}
          rowKey="id"
          loading={loading}
          pagination={{
            ...pagination,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total, range) => `${range[0]}-${range[1]} из ${total} мастеров`,
            pageSizeOptions: ['10', '20', '50', '100'],
            size: 'middle',
          }}
          onChange={handleTableChange}
          scroll={{ x: 900 }}
          locale={{
            emptyText: (
              <div style={{ padding: '40px 0', textAlign: 'center' }}>
                <div style={{ fontSize: 16, marginBottom: 8, color: '#999' }}>
                  Мастеры не найдены
                </div>
                <div style={{ fontSize: 14, color: '#666', marginBottom: 16 }}>
                  {filters.search || filters.is_active !== null || filters.services_count ? 
                    'Попробуйте изменить условия поиска' : 
                    'Добавьте первого мастера'}
                </div>
                <Button
                  type="primary"
                  icon={<PlusOutlined />}
                  onClick={handleCreate}
                >
                  Добавить мастера
                </Button>
              </div>
            ),
          }}
        />
      </Card>

      {/* Модальное окно создания/редактирования */}
      <Modal
        title={
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            {editingMaster ? 
              <><EditOutlined /> Редактировать мастера</> : 
              <><PlusOutlined /> Добавить мастера</>
            }
          </div>
        }
        open={modalVisible}
        onCancel={() => {
          setModalVisible(false);
          
          if (photoPreview && photoPreview.startsWith('blob:')) {
            URL.revokeObjectURL(photoPreview);
          }
          
          setPhotoPreview(null);
          setPhotoFile(null);
        }}
        footer={null}
        width={700}
        destroyOnClose
        maskClosable={false}
      >
        <Spin spinning={uploading} tip="Сохранение...">
          <Form
            form={form}
            layout="vertical"
            onFinish={handleSubmit}
            initialValues={{
              is_active: true,
              remove_photo: false,
            }}
          >
            <Row gutter={16}>
              <Col span={12}>
                <Form.Item
                  name="first_name"
                  label="Имя"
                  rules={[
                    { required: true, message: 'Введите имя' },
                    { min: 2, message: 'Имя должно быть не менее 2 символов' }
                  ]}
                >
                  <Input 
                    placeholder="Введите имя" 
                    size="large"
                  />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item
                  name="last_name"
                  label="Фамилия"
                  rules={[
                    { required: true, message: 'Введите фамилию' },
                    { min: 2, message: 'Фамилия должна быть не менее 2 символов' }
                  ]}
                >
                  <Input 
                    placeholder="Введите фамилию" 
                    size="large"
                  />
                </Form.Item>
              </Col>
            </Row>

            <Row gutter={16}>
              <Col span={12}>
                <Form.Item
                  name="phone"
                  label="Телефон"
                  rules={[
                    { 
                      required: false,
                      message: 'Введите корректный номер телефона' 
                    },
                    {
                      pattern: /^[\d\s\-\+\(\)]+$/,
                      message: 'Номер телефона может содержать только цифры, пробелы, тире и скобки'
                    }
                  ]}
                >
                  <Input 
                    placeholder="+7 (999) 123-45-67" 
                    size="large"
                    prefix={<PhoneOutlined style={{ color: '#52c41a' }} />}
                  />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item
                  name="email"
                  label="Email"
                  rules={[
                    { 
                      type: 'email', 
                      message: 'Введите корректный email' 
                    }
                  ]}
                >
                  <Input 
                    placeholder="example@email.com" 
                    size="large"
                  />
                </Form.Item>
              </Col>
            </Row>

            <Row gutter={16}>
              <Col span={12}>
                <Form.Item
                  name="telegram_id"
                  label="Telegram ID"
                  help="Числовой ID или @username (например: 123456789 или @username)"
                  rules={[
                    { 
                      required: false,
                      message: 'Введите Telegram ID' 
                    },
                    { 
                      pattern: /^[@a-zA-Z0-9_]+$/, 
                      message: 'Telegram ID может содержать только латинские буквы, цифры, @ и подчеркивания' 
                    },
                    { 
                      max: 32, 
                      message: 'Telegram ID должен быть не более 32 символов' 
                    }
                  ]}
                >
                  <Input 
                    placeholder="123456789 или @username" 
                    size="large"
                    prefix={<SendOutlined style={{ color: '#0088cc' }} />}
                  />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item
                  name="qualification"
                  label="Квалификация"
                >
                  <Input 
                    placeholder="Например: Топ-мастер, Стажер, Ведущий специалист" 
                    size="large"
                  />
                </Form.Item>
              </Col>
            </Row>

            <Form.Item
              name="description"
              label="Описание"
            >
              <TextArea 
                rows={4} 
                placeholder="Опыт работы, специализация, достижения, образование..." 
                size="large"
                showCount
                maxLength={500}
              />
            </Form.Item>

            <Row gutter={16} align="middle">
              <Col span={12}>
                <div style={{ marginBottom: 8 }}>
                  <label style={{ fontWeight: 500 }}>Фото мастера</label>
                  <span style={{ color: '#666', marginLeft: 8, fontSize: 12 }}>
                    (опционально)
                  </span>
                </div>
                <Upload
                  name="photo"
                  listType="picture-card"
                  className="avatar-uploader"
                  showUploadList={false}
                  beforeUpload={beforeUpload}
                  onChange={handlePhotoChange}
                  accept="image/*"
                  maxCount={1}
                  disabled={uploading}
                >
                  {photoPreview ? (
                    <div style={{ position: 'relative', width: '100%', height: '100%' }}>
                      <img
                        src={photoPreview}
                        alt="preview"
                        style={{ 
                          width: '100%', 
                          height: '100%', 
                          objectFit: 'cover',
                          borderRadius: '8px'
                        }}
                      />
                      <Button
                        type="link"
                        danger
                        size="small"
                        style={{ 
                          position: 'absolute', 
                          top: -10, 
                          right: -10, 
                          padding: 0,
                          background: '#ff4d4f',
                          color: 'white',
                          borderRadius: '50%',
                          width: 24,
                          height: 24,
                          minWidth: 24,
                          border: '2px solid white',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          fontSize: '12px',
                          fontWeight: 'bold'
                        }}
                        onClick={(e) => {
                          e.stopPropagation();
                          e.preventDefault();
                          removePhoto();
                        }}
                      >
                        ×
                      </Button>
                    </div>
                  ) : (
                    <div style={{ padding: 8, textAlign: 'center' }}>
                      <UploadOutlined style={{ fontSize: 20, marginBottom: 8, color: '#999' }} />
                      <div style={{ color: '#999' }}>Загрузить фото</div>
                    </div>
                  )}
                </Upload>
                
                <input
                  type="file"
                  ref={fileInputRef}
                  style={{ display: 'none' }}
                  accept="image/*"
                  onChange={handleManualUpload}
                />
                
                <Button 
                  type="link" 
                  size="small"
                  onClick={() => fileInputRef.current?.click()}
                  style={{ marginTop: 8 }}
                >
                  Или выберите файл
                </Button>
                
                <div style={{ marginTop: 8, fontSize: 12, color: '#666' }}>
                  Макс. размер: 5MB. Форматы: JPG, PNG, WebP, GIF
                </div>
              </Col>
              <Col span={12}>
                <Form.Item
                  name="is_active"
                  label="Статус мастера"
                  valuePropName="checked"
                  style={{ marginTop: 8 }}
                >
                  <Switch
                    checkedChildren="Активен"
                    unCheckedChildren="Неактивен"
                    size="default"
                  />
                </Form.Item>
                
                {editingMaster && (
                  <Form.Item
                    name="remove_photo"
                    label="Удалить текущее фото"
                    valuePropName="checked"
                    style={{ marginTop: 16 }}
                  >
                    <Switch
                      checkedChildren="Удалить"
                      unCheckedChildren="Оставить"
                      size="default"
                      onChange={(checked) => {
                        if (checked && photoPreview) {
                          if (photoPreview && photoPreview.startsWith('blob:')) {
                            URL.revokeObjectURL(photoPreview);
                          }
                          setPhotoPreview(null);
                          setPhotoFile(null);
                        }
                      }}
                    />
                  </Form.Item>
                )}
              </Col>
            </Row>

            <Form.Item style={{ textAlign: 'right', marginTop: 24 }}>
              <Space>
                <Button
                  onClick={() => {
                    setModalVisible(false);
                    
                    if (photoPreview && photoPreview.startsWith('blob:')) {
                      URL.revokeObjectURL(photoPreview);
                    }
                    
                    setPhotoPreview(null);
                    setPhotoFile(null);
                  }}
                  size="large"
                >
                  Отмена
                </Button>
                <Button 
                  type="primary" 
                  htmlType="submit" 
                  loading={uploading}
                  disabled={uploading}
                  size="large"
                >
                  {editingMaster ? 'Сохранить изменения' : 'Создать мастера'}
                </Button>
              </Space>
            </Form.Item>
          </Form>
        </Spin>
      </Modal>

      {/* Модальное окно деталей */}
      <MasterDetailsModal
        visible={detailsModalVisible}
        masterId={selectedMasterId}
        onClose={() => setDetailsModalVisible(false)}
      />
    </div>
  );
};

export default Masters;