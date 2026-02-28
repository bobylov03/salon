// components/MasterDetailsModal.jsx (исправленная версия)
import React, { useState, useEffect } from 'react';
import {
  Modal,
  Descriptions,
  Avatar,
  Rate,
  Tabs,
  Table,
  Tag,
  Space,
  Spin,
  Empty,
  Card,
  Row,
  Col,
  Statistic,
  Timeline,
  Badge,
  Tooltip,
  Button,
  message,
  Alert,
} from 'antd';
import {
  UserOutlined,
  CalendarOutlined,
  StarOutlined,
  StarFilled,
  PhoneOutlined,
  MailOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ScissorOutlined,
  DollarOutlined,
  PlusOutlined,
  InfoCircleOutlined,
  SendOutlined,
  MessageOutlined,
  WarningOutlined,
} from '@ant-design/icons';
import { mastersAPI } from '../services/api';
import dayjs from 'dayjs';

// Импортируем новый компонент
import MasterServicesTab from './MasterServicesTab';

const { TabPane } = Tabs;

const MasterDetailsModal = ({ visible, masterId, onClose }) => {
  const [master, setMaster] = useState(null);
  const [services, setServices] = useState([]);
  const [reviews, setReviews] = useState([]);
  const [appointments, setAppointments] = useState([]);
  const [loading, setLoading] = useState(false);
  const [reviewsLoading, setReviewsLoading] = useState(false);
  const [appointmentsLoading, setAppointmentsLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('info');

  useEffect(() => {
    if (visible && masterId) {
      fetchMasterDetails();
    } else {
      setMaster(null);
      setServices([]);
      setReviews([]);
      setAppointments([]);
    }
  }, [visible, masterId]);

  const fetchMasterDetails = async () => {
    if (!masterId) return;
    
    setLoading(true);
    try {
      // Получаем информацию о мастере
      const masterResponse = await mastersAPI.getMasterById(masterId);
      const masterData = masterResponse.data;
      
      // Получаем услуги мастера
      await fetchMasterServices(masterData);
      
      // Получаем отзывы (если endpoint существует)
      try {
        fetchReviews();
      } catch (error) {
        console.log('Reviews endpoint not available:', error);
      }
      
      // Получаем записи (если endpoint существует)
      try {
        fetchAppointments();
      } catch (error) {
        console.log('Appointments endpoint not available:', error);
      }
    } catch (error) {
      console.error('Error fetching master details:', error);
      message.error('Ошибка при загрузке данных мастера');
    } finally {
      setLoading(false);
    }
  };

  const fetchMasterServices = async (masterData = null) => {
    try {
      const response = await fetch(`/api/masters/${masterId}/services`);
      const servicesData = await response.json();
      
      if (servicesData.success) {
        setServices(servicesData.services || []);
        
        // Обновляем данные мастера если они были переданы
        if (masterData) {
          masterData.services = servicesData.services || [];
          masterData.services_count = servicesData.count || 0;
          setMaster(masterData);
        }
      } else {
        console.warn('Failed to fetch master services:', servicesData.message);
      }
    } catch (error) {
      console.error('Error fetching master services:', error);
    }
  };

  const fetchReviews = async () => {
    setReviewsLoading(true);
    try {
      // Проверяем наличие endpoint для отзывов
      const response = await fetch(`/api/masters/${masterId}/reviews`);
      if (response.ok) {
        const data = await response.json();
        if (data.success) {
          setReviews(data.items || data.reviews || []);
        }
      }
    } catch (error) {
      console.log('Reviews endpoint not available or error:', error);
    } finally {
      setReviewsLoading(false);
    }
  };

  const fetchAppointments = async () => {
    setAppointmentsLoading(true);
    try {
      // Пробуем получить записи мастера
      const response = await fetch(`/api/masters/${masterId}/appointments?per_page=10`);
      
      if (response.ok) {
        const data = await response.json();
        if (data.success) {
          setAppointments(data.items || []);
        } else if (data.items) {
          // Для совместимости со старым форматом
          setAppointments(data.items);
        }
      } else if (response.status === 404) {
        // Если endpoint не существует, пытаемся получить общие записи
        const generalResponse = await fetch(`/api/appointments?master_id=${masterId}&per_page=10`);
        if (generalResponse.ok) {
          const generalData = await generalResponse.json();
          setAppointments(generalData.items || []);
        }
      }
    } catch (error) {
      console.log('Appointments endpoint not available or error:', error);
    } finally {
      setAppointmentsLoading(false);
    }
  };

  // Функция для быстрого добавления услуги
  const handleQuickAddService = async () => {
    try {
      // Получаем список доступных услуг
      const response = await fetch(`/api/masters/${masterId}/available-services`);
      const data = await response.json();
      
      if (!data.success || data.available_services.length === 0) {
        message.warning('Нет доступных услуг для добавления');
        return;
      }
      
      let selectedServiceId = null;
      
      // Показываем простое модальное окно для выбора услуги
      Modal.confirm({
        title: 'Добавить услугу мастеру',
        content: (
          <div style={{ maxHeight: 300, overflowY: 'auto' }}>
            {data.available_services.map(service => (
              <Card
                key={service.id}
                size="small"
                hoverable
                style={{ marginBottom: 8, cursor: 'pointer' }}
                onClick={() => {
                  selectedServiceId = service.id;
                  // Автоматически подтверждаем выбор
                  setTimeout(() => {
                    document.querySelector('.ant-modal-confirm-btns .ant-btn-primary')?.click();
                  }, 100);
                }}
              >
                <div style={{ fontWeight: 500 }}>{service.title || `Услуга #${service.id}`}</div>
                <div style={{ fontSize: 12, color: '#666' }}>
                  Цена: {service.price}₽ • Длительность: {service.duration_minutes} мин
                </div>
                {service.category_title && (
                  <div style={{ fontSize: 11, color: '#999' }}>
                    Категория: {service.category_title}
                  </div>
                )}
              </Card>
            ))}
          </div>
        ),
        onOk: async () => {
          if (!selectedServiceId) {
            message.warning('Выберите услугу');
            return Promise.reject();
          }
          
          try {
            // Используем FormData для добавления
            const formData = new FormData();
            formData.append('service_id', selectedServiceId.toString());
            formData.append('is_primary', 'false');
            
            const addResponse = await fetch(`/api/masters/${masterId}/services`, {
              method: 'POST',
              body: formData,
            });
            
            const addData = await addResponse.json();
            
            if (addResponse.ok && addData.success) {
              message.success('Услуга успешно добавлена мастеру');
              // Обновляем список услуг
              fetchMasterServices();
              // Переключаемся на вкладку услуг
              setActiveTab('services');
            } else {
              const errorMsg = addData.detail || addData.message || addData.error || 'Ошибка при добавлении';
              message.error(errorMsg);
            }
          } catch (error) {
            console.error('Error adding service:', error);
            message.error('Ошибка при добавлении услуги');
          }
        },
        okText: 'Добавить выбранную',
        cancelText: 'Отмена',
        width: 500,
      });
    } catch (error) {
      console.error('Error fetching available services:', error);
      message.error('Ошибка при получении доступных услуг');
    }
  };

  // Функция для копирования Telegram ID в буфер обмена
  const copyTelegramId = () => {
    if (master?.telegram_id) {
      navigator.clipboard.writeText(master.telegram_id)
        .then(() => {
          message.success('Telegram ID скопирован в буфер обмена');
        })
        .catch(() => {
          message.error('Не удалось скопировать Telegram ID');
        });
    }
  };

  // Функция для открытия Telegram
  const openTelegram = () => {
    if (master?.telegram_id) {
      window.open(`https://t.me/${master.telegram_id}`, '_blank');
    }
  };

  // Функция для копирования номера телефона
  const copyPhoneNumber = () => {
    if (master?.phone) {
      navigator.clipboard.writeText(master.phone)
        .then(() => {
          message.success('Номер телефона скопирован в буфер обмена');
        })
        .catch(() => {
          message.error('Не удалось скопировать номер телефона');
        });
    }
  };

  // Функция для звонка по номеру телефона
  const callPhoneNumber = () => {
    if (master?.phone) {
      const phoneNumber = master.phone.replace(/[^\d+]/g, '');
      window.open(`tel:${phoneNumber}`);
    }
  };

  // Проверка наличия контактной информации
  const hasContactInfo = master?.phone || master?.telegram_id || master?.email;
  const hasRequiredContactInfo = master?.telegram_id; // Только Telegram ID обязателен

  const reviewColumns = [
    {
      title: 'Клиент',
      dataIndex: 'client_name',
      key: 'client',
      render: (text, record) => (
        <Space>
          <Avatar size="small" icon={<UserOutlined />} />
          {text || `${record.client_first_name || ''} ${record.client_last_name || ''}`}
        </Space>
      ),
    },
    {
      title: 'Рейтинг',
      dataIndex: 'rating',
      key: 'rating',
      render: (rating) => (
        <Tooltip title={`${rating}/5`}>
          <Rate disabled defaultValue={rating || 0} style={{ fontSize: 14 }} />
        </Tooltip>
      ),
    },
    {
      title: 'Отзыв',
      dataIndex: 'text',
      key: 'text',
      ellipsis: true,
      width: 300,
    },
    {
      title: 'Дата',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date) => date ? dayjs(date).format('DD.MM.YYYY HH:mm') : '-',
    },
  ];

  const appointmentColumns = [
    {
      title: 'Дата и время',
      key: 'datetime',
      width: 150,
      render: (record) => (
        <div>
          <div>{record.appointment_date ? dayjs(record.appointment_date).format('DD.MM.YYYY') : '-'}</div>
          <div style={{ fontSize: 12, color: '#666' }}>
            {record.start_time || '-'} {record.end_time ? `- ${record.end_time}` : ''}
          </div>
        </div>
      ),
    },
    {
      title: 'Клиент',
      key: 'client',
      render: (record) => 
        `${record.client_first_name || ''} ${record.client_last_name || ''}`.trim() || '-',
    },
    {
      title: 'Услуги',
      key: 'services',
      render: (record) => {
        if (record.services && record.services.length > 0) {
          return (
            <Tooltip
              title={
                <div>
                  {record.services.map(service => (
                    <div key={service.id} style={{ marginBottom: 4 }}>
                      {service.title} - {service.price}₽
                    </div>
                  ))}
                </div>
              }
            >
              <span>{record.services.length} услуг</span>
            </Tooltip>
          );
        }
        return '-';
      },
    },
    {
      title: 'Статус',
      dataIndex: 'status',
      key: 'status',
      render: (status) => {
        const statusConfig = {
          pending: { color: 'orange', text: 'Ожидание', icon: <ClockCircleOutlined /> },
          confirmed: { color: 'blue', text: 'Подтверждено', icon: <ClockCircleOutlined /> },
          completed: { color: 'green', text: 'Завершено', icon: <CheckCircleOutlined /> },
          cancelled: { color: 'red', text: 'Отменено', icon: <CloseCircleOutlined /> },
          no_show: { color: 'gray', text: 'Не пришел', icon: <CloseCircleOutlined /> },
          default: { color: 'default', text: status || 'Неизвестно' },
        };
        
        const config = statusConfig[status] || statusConfig.default;
        return (
          <Tag color={config.color} icon={config.icon}>
            {config.text}
          </Tag>
        );
      },
    },
  ];

  const getStatusTag = (isActive) => (
    <Tag color={isActive ? 'green' : 'red'}>
      {isActive ? 'Активен' : 'Неактивен'}
    </Tag>
  );

  // Функция для отображения услуг в карточке
  const renderServicesPreview = () => {
    if (!services || services.length === 0) {
      return (
        <div style={{ textAlign: 'center', padding: '20px 0' }}>
          <Empty 
            description="Нет услуг" 
            image={Empty.PRESENTED_IMAGE_SIMPLE} 
            imageStyle={{ height: 40 }}
          />
          <Button 
            type="primary" 
            size="small" 
            icon={<PlusOutlined />}
            onClick={handleQuickAddService}
            style={{ marginTop: 8 }}
          >
            Добавить услугу
          </Button>
        </div>
      );
    }

    const primaryServices = services.filter(s => s.is_primary);
    const additionalServices = services.filter(s => !s.is_primary);

    return (
      <div>
        {primaryServices.length > 0 && (
          <div style={{ marginBottom: 16 }}>
            <div style={{ fontWeight: 500, marginBottom: 8, color: '#faad14' }}>
              <StarFilled style={{ marginRight: 4 }} /> Основные услуги ({primaryServices.length})
            </div>
            {primaryServices.slice(0, 3).map(service => (
              <div key={service.service_id} style={{ 
                padding: '8px 12px', 
                background: '#fffbe6',
                marginBottom: 4,
                borderRadius: 4,
                border: '1px solid #ffe58f'
              }}>
                <div style={{ fontWeight: 500 }}>{service.service_title || `Услуга #${service.service_id}`}</div>
                <div style={{ fontSize: 12, color: '#666' }}>
                  {service.price}₽ • {service.duration_minutes} мин
                </div>
              </div>
            ))}
          </div>
        )}

        {additionalServices.length > 0 && (
          <div>
            <div style={{ fontWeight: 500, marginBottom: 8, color: '#1890ff' }}>
              Дополнительные услуги ({additionalServices.length})
            </div>
            {additionalServices.slice(0, 3).map(service => (
              <div key={service.service_id} style={{ 
                padding: '8px 12px', 
                background: '#e6f7ff',
                marginBottom: 4,
                borderRadius: 4,
                border: '1px solid #91d5ff'
              }}>
                <div style={{ fontWeight: 500 }}>{service.service_title || `Услуга #${service.service_id}`}</div>
                <div style={{ fontSize: 12, color: '#666' }}>
                  {service.price}₽ • {service.duration_minutes} мин
                </div>
              </div>
            ))}
          </div>
        )}
        
        {(primaryServices.length > 3 || additionalServices.length > 3) && (
          <div style={{ textAlign: 'center', marginTop: 8 }}>
            <Button 
              type="link" 
              size="small" 
              onClick={() => setActiveTab('services')}
            >
              Показать все услуги ({services.length})
            </Button>
          </div>
        )}
      </div>
    );
  };

  const renderMasterStats = () => {
    const primaryCount = services.filter(s => s.is_primary).length;
    const additionalCount = services.filter(s => !s.is_primary).length;
    const totalPrice = services.reduce((sum, s) => sum + (s.price || 0), 0);
    const totalDuration = services.reduce((sum, s) => sum + (s.duration_minutes || 0), 0);

    return (
      <Row gutter={16}>
        <Col span={12}>
          <Card size="small">
            <Statistic
              title="Всего услуг"
              value={services.length}
              prefix={<ScissorOutlined />}
            />
          </Card>
        </Col>
        <Col span={12}>
          <Card size="small">
            <Statistic
              title="Основные"
              value={primaryCount}
              prefix={<StarFilled />}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
        <Col span={12}>
          <Card size="small" style={{ marginTop: 8 }}>
            <Statistic
              title="Стоимость"
              value={totalPrice}
              prefix={<DollarOutlined />}
              suffix="₽"
            />
          </Card>
        </Col>
        <Col span={12}>
          <Card size="small" style={{ marginTop: 8 }}>
            <Statistic
              title="Общая длительность"
              value={totalDuration}
              suffix="мин"
              prefix={<ClockCircleOutlined />}
            />
          </Card>
        </Col>
      </Row>
    );
  };

  // Оповещение о наличии контактной информации
  const renderContactInfoAlert = () => {
    if (!hasContactInfo) {
      return (
        <Alert
          message="Контактная информация отсутствует"
          description="Добавьте хотя бы Telegram ID для связи с мастером"
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
        />
      );
    }

    if (!hasRequiredContactInfo) {
      return (
        <Alert
          message="Telegram ID отсутствует"
          description="Telegram ID является обязательным полем для связи с мастером"
          type="error"
          showIcon
          style={{ marginBottom: 16 }}
        />
      );
    }

    return null;
  };

  if (!visible) return null;

  if (loading && !master) {
    return (
      <Modal
        title="Информация о мастере"
        open={visible}
        onCancel={onClose}
        footer={null}
        width={800}
      >
        <div style={{ textAlign: 'center', padding: '40px 0' }}>
          <Spin size="large" tip="Загрузка данных мастера..." />
        </div>
      </Modal>
    );
  }

  if (!master) {
    return (
      <Modal
        title="Информация о мастере"
        open={visible}
        onCancel={onClose}
        footer={null}
        width={800}
      >
        <Empty description="Мастер не найден" />
      </Modal>
    );
  }

  const masterName = `${master.first_name || ''} ${master.last_name || ''}`.trim();

  return (
    <Modal
      title={
        <Space>
          <Avatar src={master.photo_url} size={40} icon={<UserOutlined />} />
          <span style={{ fontWeight: 500 }}>{masterName}</span>
          {getStatusTag(master.is_active)}
          {!hasRequiredContactInfo && (
            <Tag icon={<WarningOutlined />} color="error">
              Нет Telegram ID
            </Tag>
          )}
        </Space>
      }
      open={visible}
      onCancel={onClose}
      footer={null}
      width={1000}
      style={{ top: 20 }}
      destroyOnClose
    >
      {renderContactInfoAlert()}
      
      <Tabs 
        activeKey={activeTab} 
        onChange={setActiveTab}
        type="card"
        size="large"
      >
        <TabPane tab="Основная информация" key="info">
          <Row gutter={24}>
            <Col span={8}>
              <Card style={{ textAlign: 'center', marginBottom: 16 }}>
                <Avatar
                  src={master.photo_url}
                  size={150}
                  icon={<UserOutlined />}
                  style={{ marginBottom: 16, border: '2px solid #f0f0f0' }}
                />
                <h3 style={{ marginBottom: 4 }}>{masterName}</h3>
                <p style={{ color: '#666', marginBottom: 16 }}>
                  {master.qualification || 'Квалификация не указана'}
                </p>
                
                {/* Бейдж с количеством услуг */}
                <Badge 
                  count={services.length || 0} 
                  style={{ backgroundColor: '#52c41a' }}
                  overflowCount={99}
                >
                  <Button 
                    type="primary" 
                    icon={<ScissorOutlined />}
                    onClick={() => setActiveTab('services')}
                  >
                    Услуги
                  </Button>
                </Badge>
              </Card>
              
              {/* Статистика услуг */}
              <Card title="Статистика услуг" style={{ marginBottom: 16 }}>
                {renderMasterStats()}
              </Card>
              
              {/* Предпросмотр услуг */}
              <Card 
                title="Услуги мастера" 
                size="small"
                extra={
                  <Button 
                    type="link" 
                    size="small" 
                    icon={<PlusOutlined />}
                    onClick={handleQuickAddService}
                  >
                    Добавить
                  </Button>
                }
              >
                {renderServicesPreview()}
              </Card>
            </Col>
            
            <Col span={16}>
              <Descriptions bordered column={1} size="middle" style={{ marginBottom: 16 }}>
                <Descriptions.Item label="Контактная информация">
                  <Space direction="vertical" style={{ width: '100%' }}>
                    {/* Telegram ID - обязательное поле */}
                    <Card 
                      size="small" 
                      style={{ 
                        backgroundColor: master.telegram_id ? '#f9f9f9' : '#fff2f0',
                        border: master.telegram_id ? '1px solid #d9d9d9' : '1px solid #ffccc7'
                      }}
                      bodyStyle={{ padding: '12px' }}
                    >
                      <Space>
                        <MessageOutlined style={{ 
                          color: master.telegram_id ? '#0088cc' : '#ff4d4f', 
                          fontSize: '18px' 
                        }} />
                        <div>
                          <div style={{ fontWeight: 500, marginBottom: 4 }}>
                            Telegram ID {!master.telegram_id && <Tag color="error">обязательно</Tag>}
                          </div>
                          {master.telegram_id ? (
                            <div style={{ 
                              fontFamily: 'monospace', 
                              fontSize: '14px',
                              backgroundColor: '#fff',
                              padding: '4px 8px',
                              borderRadius: '4px',
                              border: '1px solid #e8e8e8',
                              display: 'inline-block'
                            }}>
                              {master.telegram_id}
                            </div>
                          ) : (
                            <div style={{ color: '#ff4d4f', fontStyle: 'italic' }}>
                              Не указан
                            </div>
                          )}
                        </div>
                      </Space>
                      {master.telegram_id && (
                        <Space style={{ marginTop: 8 }}>
                          <Button 
                            size="small" 
                            icon={<SendOutlined />}
                            onClick={openTelegram}
                          >
                            Открыть Telegram
                          </Button>
                          <Button 
                            size="small" 
                            onClick={copyTelegramId}
                          >
                            Копировать ID
                          </Button>
                        </Space>
                      )}
                    </Card>
                    
                    {/* Телефон - необязательное поле */}
                    {master.phone && (
                      <Card 
                        size="small" 
                        style={{ 
                          backgroundColor: '#f6ffed',
                          border: '1px solid #b7eb8f',
                          marginTop: 8
                        }}
                        bodyStyle={{ padding: '12px' }}
                      >
                        <Space>
                          <PhoneOutlined style={{ color: '#52c41a', fontSize: '18px' }} />
                          <div>
                            <div style={{ fontWeight: 500, marginBottom: 4 }}>Телефон</div>
                            <div style={{ 
                              fontFamily: 'monospace', 
                              fontSize: '14px',
                              backgroundColor: '#fff',
                              padding: '4px 8px',
                              borderRadius: '4px',
                              border: '1px solid #b7eb8f',
                              display: 'inline-block'
                            }}>
                              {master.phone}
                            </div>
                          </div>
                        </Space>
                        <Space style={{ marginTop: 8 }}>
                          <Button 
                            size="small" 
                            icon={<PhoneOutlined />}
                            onClick={callPhoneNumber}
                          >
                            Позвонить
                          </Button>
                          <Button 
                            size="small" 
                            onClick={copyPhoneNumber}
                          >
                            Копировать
                          </Button>
                        </Space>
                      </Card>
                    )}
                    
                    {/* Email */}
                    {master.email && (
                      <Card 
                        size="small" 
                        style={{ 
                          backgroundColor: '#e6f7ff',
                          border: '1px solid #91d5ff',
                          marginTop: 8
                        }}
                        bodyStyle={{ padding: '12px' }}
                      >
                        <Space>
                          <MailOutlined style={{ color: '#1890ff', fontSize: '18px' }} />
                          <div>
                            <div style={{ fontWeight: 500, marginBottom: 4 }}>Email</div>
                            <div style={{ 
                              fontSize: '14px',
                              backgroundColor: '#fff',
                              padding: '4px 8px',
                              borderRadius: '4px',
                              border: '1px solid #91d5ff',
                              display: 'inline-block'
                            }}>
                              {master.email}
                            </div>
                          </div>
                        </Space>
                      </Card>
                    )}
                    
                    {/* Сообщение если нет контактной информации */}
                    {!hasContactInfo && (
                      <Alert
                        message="Контактная информация отсутствует"
                        description="Для связи с мастером необходимо добавить хотя бы Telegram ID в разделе редактирования"
                        type="warning"
                        showIcon
                        style={{ marginTop: 8 }}
                      />
                    )}
                  </Space>
                </Descriptions.Item>
                
                <Descriptions.Item label="Квалификация">
                  {master.qualification || 'Не указана'}
                </Descriptions.Item>
                
                <Descriptions.Item label="Описание">
                  {master.description ? (
                    <div style={{ whiteSpace: 'pre-wrap', maxHeight: 200, overflowY: 'auto' }}>
                      {master.description}
                    </div>
                  ) : 'Описание отсутствует'}
                </Descriptions.Item>
                
                <Descriptions.Item label="Дата добавления">
                  {master.created_at ? dayjs(master.created_at).format('DD.MM.YYYY HH:mm') : '-'}
                </Descriptions.Item>
              </Descriptions>
              
              {/* Кнопки действий */}
              <Card size="small">
                <Space wrap>
                  <Button 
                    type="primary"
                    icon={<ScissorOutlined />}
                    onClick={() => setActiveTab('services')}
                  >
                    Управление услугами
                  </Button>
                  <Button 
                    icon={<PlusOutlined />}
                    onClick={handleQuickAddService}
                  >
                    Быстро добавить услугу
                  </Button>
                  <Button 
                    icon={<CalendarOutlined />}
                    onClick={() => setActiveTab('appointments')}
                  >
                    Записи
                  </Button>
                  {master.telegram_id && (
                    <Button 
                      icon={<SendOutlined />}
                      onClick={openTelegram}
                      type="dashed"
                    >
                      Написать в Telegram
                    </Button>
                  )}
                  {master.phone && (
                    <Button 
                      icon={<PhoneOutlined />}
                      onClick={callPhoneNumber}
                      type="dashed"
                    >
                      Позвонить
                    </Button>
                  )}
                </Space>
              </Card>
            </Col>
          </Row>
        </TabPane>
        
        <TabPane tab="Услуги" key="services">
          <MasterServicesTab 
            masterId={masterId} 
            masterName={masterName}
            onServicesUpdated={fetchMasterServices}
          />
        </TabPane>
        
        <TabPane tab="Последние записи" key="appointments">
          <Spin spinning={appointmentsLoading}>
            <Table
              columns={appointmentColumns}
              dataSource={appointments}
              rowKey="id"
              pagination={{
                pageSize: 10,
                showSizeChanger: true,
                showTotal: (total) => `Всего ${total} записей`,
              }}
              locale={{
                emptyText: (
                  <Empty 
                    description="Записи отсутствуют" 
                    image={Empty.PRESENTED_IMAGE_SIMPLE}
                  />
                ),
              }}
            />
          </Spin>
        </TabPane>
        
        <TabPane tab="Отзывы клиентов" key="reviews">
  <Spin spinning={reviewsLoading}>
    <Table
      columns={reviewColumns}
      dataSource={reviews}
      rowKey="id"
      pagination={{
        pageSize: 5,
        showSizeChanger: true,
        showTotal: (total) => `Всего ${total} отзывов`,
      }}
      locale={{
        emptyText: (
          <Empty 
            description="Отзывы отсутствуют" 
            image={Empty.PRESENTED_IMAGE_SIMPLE}
          />
        ),
      }}
    />
  </Spin>
</TabPane>
        
        <TabPane tab="Активность" key="activity">
          <Timeline>
            <Timeline.Item color="green" dot={<InfoCircleOutlined />}>
              <p style={{ fontWeight: 500 }}>Мастер добавлен в систему</p>
              <p style={{ fontSize: 12, color: '#666' }}>
                {master.created_at ? dayjs(master.created_at).format('DD.MM.YYYY HH:mm') : '-'}
              </p>
            </Timeline.Item>
            
            {services.length > 0 && (
              <Timeline.Item color="blue" dot={<ScissorOutlined />}>
                <p style={{ fontWeight: 500 }}>Назначены услуги</p>
                <p style={{ fontSize: 12, color: '#666' }}>
                  {services.length} услуг назначено
                </p>
                <p style={{ fontSize: 12, color: '#666' }}>
                  Основных: {services.filter(s => s.is_primary).length} | 
                  Дополнительных: {services.filter(s => !s.is_primary).length}
                </p>
              </Timeline.Item>
            )}
            
            {appointments.length > 0 ? (
              appointments.slice(0, 5).map(appointment => (
                <Timeline.Item
                  key={appointment.id}
                  color={
                    appointment.status === 'completed' ? 'green' :
                    appointment.status === 'cancelled' ? 'red' :
                    'blue'
                  }
                >
                  <p style={{ fontWeight: 500 }}>
                    {appointment.status === 'completed' ? '✅ Завершена запись' :
                     appointment.status === 'cancelled' ? '❌ Отменена запись' :
                     '⏳ Создана запись'}
                  </p>
                  <p style={{ fontSize: 12, color: '#666' }}>
                    {appointment.appointment_date ? dayjs(appointment.appointment_date).format('DD.MM.YYYY') : '-'} 
                    {appointment.start_time ? ` в ${appointment.start_time}` : ''}
                  </p>
                  {appointment.client_first_name && (
                    <p style={{ fontSize: 12 }}>
                      Клиент: {appointment.client_first_name} {appointment.client_last_name || ''}
                    </p>
                  )}
                </Timeline.Item>
              ))
            ) : (
              <Timeline.Item color="gray">
                <p style={{ color: '#999' }}>Еще нет записей</p>
              </Timeline.Item>
            )}
          </Timeline>
        </TabPane>
      </Tabs>
    </Modal>
  );
};

export default MasterDetailsModal;