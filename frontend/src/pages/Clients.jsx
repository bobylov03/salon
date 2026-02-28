import React, { useState, useEffect } from 'react';
import {
  Table,
  Button,
  Modal,
  Form,
  Input,
  Select,
  Space,
  Tag,
  message,
  Card,
  Row,
  Col,
  Descriptions,
  Tabs,
  Statistic,
  Tooltip,
  Badge,
  Avatar,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  EyeOutlined,
  UserOutlined,
  PhoneOutlined,
  CalendarOutlined,
  StarOutlined,
  HistoryOutlined,
  MailOutlined,
  IdcardOutlined,
  ClockCircleOutlined,
  DollarOutlined,
} from '@ant-design/icons';
import axios from 'axios';
import dayjs from 'dayjs';

const { Option } = Select;
const { TabPane } = Tabs;

const Clients = () => {
  const [clients, setClients] = useState([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [detailsModalVisible, setDetailsModalVisible] = useState(false);
  const [editingClient, setEditingClient] = useState(null);
  const [selectedClient, setSelectedClient] = useState(null);
  const [clientAppointments, setClientAppointments] = useState([]);
  const [clientStats, setClientStats] = useState(null);
  const [form] = Form.useForm();
  const [searchText, setSearchText] = useState('');
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 10,
    total: 0,
  });

  useEffect(() => {
    fetchClients();
  }, [pagination.current, pagination.pageSize, searchText]);

  const fetchClients = async () => {
    setLoading(true);
    try {
      const response = await axios.get('/clients', {
        params: {
          page: pagination.current,
          per_page: pagination.pageSize,
          search: searchText,
        }
      });
      
      setClients(response.data.items || []);
      setPagination({
        ...pagination,
        total: response.data.total || 0,
      });
    } catch (error) {
      console.error('Error fetching clients:', error);
      message.error('Ошибка при загрузке клиентов');
    } finally {
      setLoading(false);
    }
  };

  const fetchClientAppointments = async (clientId) => {
    try {
      const response = await axios.get(`/clients/${clientId}/recent-appointments`, {
        params: { limit: 10 }
      });
      setClientAppointments(response.data.appointments || []);
    } catch (error) {
      console.error('Error fetching client appointments:', error);
      setClientAppointments([]);
    }
  };

  const fetchClientStats = async (clientId) => {
    try {
      const response = await axios.get(`/clients/${clientId}/stats`);
      setClientStats(response.data);
    } catch (error) {
      console.error('Error fetching client stats:', error);
      setClientStats(null);
    }
  };

  const handleSubmit = async (values) => {
  try {
    console.log('Submitting client data:', values);
    
    // Подготавливаем данные в формате, который ожидает Pydantic
    const clientData = {
      first_name: values.first_name?.trim() || '',
      last_name: values.last_name?.trim() || '',
      phone: values.phone?.trim() || '',
      email: values.email?.trim() || '',
    };

    // Валидация
    if (!clientData.first_name) {
      message.error('Имя обязательно для заполнения');
      return;
    }

    if (!clientData.phone) {
      message.error('Телефон обязателен для заполнения');
      return;
    }

    if (editingClient) {
      // Обновление клиента
      const updateData = {};
      if (clientData.first_name !== editingClient.first_name) updateData.first_name = clientData.first_name;
      if (clientData.last_name !== editingClient.last_name) updateData.last_name = clientData.last_name;
      if (clientData.phone !== editingClient.phone) updateData.phone = clientData.phone;
      if (clientData.email !== editingClient.email) updateData.email = clientData.email;
      
      await axios.put(`/clients/${editingClient.id}`, updateData, {
        headers: {
          'Content-Type': 'application/json',
        }
      });
      message.success('Клиент обновлен');
    } else {
      // Создание нового клиента - отправляем как простой объект
      // Попробуем отправить без заголовков Content-Type, чтобы FastAPI сам определил
      const response = await axios.post('/clients', clientData);
      
      if (response.data.success) {
        message.success('Клиент успешно создан');
        console.log('Client created:', response.data);
      } else {
        message.error(response.data.message || 'Ошибка при создании клиента');
      }
    }
    
    setModalVisible(false);
    form.resetFields();
    setEditingClient(null);
    fetchClients();
  } catch (error) {
    console.error('Error saving client:', error);
    console.error('Error response:', error.response?.data);
    
    // Если ошибка связана с Pydantic, попробуем другой формат
    if (error.response?.status === 422 && !editingClient) {
      console.log('Trying alternative format for Pydantic...');
      try {
        // Пробуем отправить как строку JSON
        const clientData = {
          first_name: values.first_name?.trim() || '',
          last_name: values.last_name?.trim() || '',
          phone: values.phone?.trim() || '',
          email: values.email?.trim() || '',
        };
        
        const response = await axios.post('/clients', 
          JSON.stringify(clientData),
          {
            headers: {
              'Content-Type': 'application/json',
            }
          }
        );
        
        if (response.data.success) {
          message.success('Клиент успешно создан');
          setModalVisible(false);
          form.resetFields();
          setEditingClient(null);
          fetchClients();
          return;
        }
      } catch (retryError) {
        console.error('Retry failed:', retryError);
      }
    }
    
    if (error.response?.status === 400) {
      message.error(error.response.data.detail || 'Ошибка валидации данных');
    } else if (error.response?.status === 409) {
      message.error('Клиент с таким телефоном или email уже существует');
    } else if (error.response?.status === 422) {
      const errors = error.response.data.detail;
      if (Array.isArray(errors)) {
        errors.forEach(err => {
          if (err.loc && err.msg) {
            message.error(`${err.loc[1]}: ${err.msg}`);
          }
        });
      } else {
        message.error('Некорректные данные');
      }
    } else {
      message.error(`Ошибка при сохранении: ${error.response?.data?.detail || error.message}`);
    }
  }
};

  const handleDelete = async (id) => {
    Modal.confirm({
      title: 'Удалить клиента?',
      content: 'Все данные клиента будут удалены. Продолжить?',
      onOk: async () => {
        try {
          await axios.delete(`/clients/${id}`);
          message.success('Клиент удален');
          fetchClients();
        } catch (error) {
          if (error.response?.status === 400) {
            message.error(error.response.data.detail || 'Невозможно удалить клиента');
          } else {
            message.error(error.response?.data?.detail || 'Ошибка при удалении');
          }
        }
      },
    });
  };

  const showClientDetails = async (client) => {
    setSelectedClient(client);
    await fetchClientAppointments(client.id);
    await fetchClientStats(client.id);
    setDetailsModalVisible(true);
  };

  const handleTableChange = (paginationConfig) => {
    setPagination(paginationConfig);
  };

  const handleSearch = (value) => {
    setSearchText(value);
    setPagination({ ...pagination, current: 1 });
  };

  const calculateOverallStats = () => {
    const totalClients = clients.length;
    
    // Активные клиенты - те, у кого были записи за последние 3 месяца
    const activeClients = clients.filter(client => {
      // Простая логика: считаем активными клиентов, созданных за последние 3 месяца
      const createdDate = dayjs(client.created_at);
      const threeMonthsAgo = dayjs().subtract(3, 'month');
      return createdDate.isAfter(threeMonthsAgo);
    }).length;
    
    // Новые клиенты - созданные за последний месяц
    const newClients = clients.filter(client => {
      const createdDate = dayjs(client.created_at);
      const oneMonthAgo = dayjs().subtract(1, 'month');
      return createdDate.isAfter(oneMonthAgo);
    }).length;

    return {
      total: totalClients,
      active: activeClients,
      new: newClients,
    };
  };

  const columns = [
    {
      title: 'Клиент',
      key: 'client',
      render: (record) => (
        <div style={{ display: 'flex', alignItems: 'center' }}>
          <Avatar 
            size="small" 
            style={{ backgroundColor: '#1890ff', marginRight: 8 }}
            icon={<UserOutlined />}
          />
          <div>
            <div style={{ fontWeight: 500 }}>
              {record.first_name} {record.last_name || ''}
            </div>
            <div style={{ fontSize: '12px', color: '#666' }}>
              ID: {record.id} {record.telegram_id && `| TG: ${record.telegram_id}`}
            </div>
          </div>
        </div>
      ),
    },
    {
      title: 'Контакты',
      key: 'contacts',
      render: (record) => (
        <div>
          {record.phone && (
            <div style={{ display: 'flex', alignItems: 'center', marginBottom: 4 }}>
              <PhoneOutlined style={{ marginRight: 4, color: '#666' }} />
              <span>{record.phone}</span>
            </div>
          )}
          {record.email && (
            <div style={{ display: 'flex', alignItems: 'center' }}>
              <MailOutlined style={{ marginRight: 4, color: '#666' }} />
              <span style={{ fontSize: '12px' }}>{record.email}</span>
            </div>
          )}
        </div>
      ),
    },
    {
      title: 'Статистика',
      key: 'stats',
      render: (record) => {
        const hasAppointments = record.appointment_count > 0;
        return (
          <div>
            {hasAppointments ? (
              <Tag color="green">
                {record.completed_count || 0}/{record.appointment_count || 0} зап.
              </Tag>
            ) : (
              <Tag color="default">Нет записей</Tag>
            )}
          </div>
        );
      },
    },
    {
      title: 'Регистрация',
      key: 'registration',
      render: (record) => (
        <div style={{ fontSize: '12px', color: '#666' }}>
          {dayjs(record.created_at).format('DD.MM.YYYY')}
          <br />
          {dayjs(record.created_at).format('HH:mm')}
        </div>
      ),
    },
    {
      title: 'Статус',
      key: 'status',
      render: (record) => {
        const isNew = dayjs().diff(dayjs(record.created_at), 'month') < 1;
        const hasAppointments = record.appointment_count > 0;
        
        if (isNew) {
          return <Badge status="processing" text="Новый" />;
        } else if (hasAppointments) {
          return <Badge status="success" text="Активен" />;
        } else {
          return <Badge status="default" text="Неактивен" />;
        }
      },
    },
    {
      title: 'Действия',
      key: 'actions',
      width: 120,
      render: (_, record) => (
        <Space>
          <Tooltip title="Просмотр">
            <Button
              type="text"
              icon={<EyeOutlined />}
              onClick={() => showClientDetails(record)}
            />
          </Tooltip>
          <Tooltip title="Редактировать">
            <Button
              type="text"
              icon={<EditOutlined />}
              onClick={() => {
                setEditingClient(record);
                form.setFieldsValue({
                  first_name: record.first_name,
                  last_name: record.last_name || '',
                  phone: record.phone || '',
                  email: record.email || '',
                });
                setModalVisible(true);
              }}
            />
          </Tooltip>
          <Tooltip title="Удалить">
            <Button
              type="text"
              danger
              icon={<DeleteOutlined />}
              onClick={() => handleDelete(record.id)}
            />
          </Tooltip>
        </Space>
      ),
    },
  ];

  const overallStats = calculateOverallStats();

  return (
    <div>
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="Всего клиентов"
              value={overallStats.total}
              prefix={<UserOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="Активных"
              value={overallStats.active}
              prefix={<UserOutlined />}
              valueStyle={{ color: '#3f8600' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="Новых (за месяц)"
              value={overallStats.new}
              prefix={<UserOutlined />}
              valueStyle={{ color: '#fa8c16' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="С свободными записями"
              value={clients.filter(c => c.appointment_count > 0).length}
              prefix={<CalendarOutlined />}
              valueStyle={{ color: '#722ed1' }}
            />
          </Card>
        </Col>
      </Row>

      <Card
        title={
          <Space>
            <UserOutlined />
            Клиенты
            <span style={{ fontSize: '14px', color: '#666', marginLeft: 8 }}>
              ({overallStats.total} записей)
            </span>
          </Space>
        }
        extra={
          <Space>
            <Input.Search
              placeholder="Поиск по имени, телефону..."
              style={{ width: 250 }}
              onSearch={handleSearch}
              allowClear
              onChange={(e) => {
                if (!e.target.value) {
                  handleSearch('');
                }
              }}
            />
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => {
                setEditingClient(null);
                form.resetFields();
                setModalVisible(true);
              }}
            >
              Добавить клиента
            </Button>
          </Space>
        }
      >
        <Table
          columns={columns}
          dataSource={clients}
          rowKey="id"
          loading={loading}
          pagination={{
            ...pagination,
            showSizeChanger: true,
            showTotal: (total) => `Всего ${total} клиентов`,
            pageSizeOptions: ['10', '20', '50', '100'],
          }}
          onChange={handleTableChange}
        />
      </Card>

      {/* Модальное окно создания/редактирования клиента */}
      <Modal
        title={editingClient ? 'Редактировать клиента' : 'Новый клиент'}
        open={modalVisible}
        onCancel={() => {
          setModalVisible(false);
          form.resetFields();
          setEditingClient(null);
        }}
        onOk={() => form.submit()}
        okText={editingClient ? 'Обновить' : 'Создать'}
        cancelText="Отмена"
        width={500}
        destroyOnClose
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
          autoComplete="off"
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
                  placeholder="Имя" 
                  prefix={<UserOutlined />}
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="last_name"
                label="Фамилия"
              >
                <Input placeholder="Фамилия (необязательно)" />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="phone"
            label="Телефон"
            rules={[
              { required: true, message: 'Введите телефон' },
              { pattern: /^[+\d\s\-()]+$/, message: 'Введите корректный номер телефона' }
            ]}
          >
            <Input 
              placeholder="+7 999 123-45-67" 
              prefix={<PhoneOutlined />}
            />
          </Form.Item>

          <Form.Item
            name="email"
            label="Email"
            rules={[
              { type: 'email', message: 'Некорректный email' },
            ]}
          >
            <Input 
              placeholder="email@example.com (необязательно)" 
              prefix={<MailOutlined />}
            />
          </Form.Item>
        </Form>
      </Modal>

      {/* Модальное окно деталей клиента */}
      <Modal
        title={
          <Space>
            <UserOutlined />
            Информация о клиенте
            {selectedClient && (
              <span style={{ fontWeight: 'normal', fontSize: '14px' }}>
                {selectedClient.first_name} {selectedClient.last_name || ''}
              </span>
            )}
          </Space>
        }
        open={detailsModalVisible}
        onCancel={() => setDetailsModalVisible(false)}
        footer={[
          <Button key="close" onClick={() => setDetailsModalVisible(false)}>
            Закрыть
          </Button>
        ]}
        width={800}
      >
        {selectedClient && (
          <Tabs defaultActiveKey="info">
            <TabPane tab="Основная информация" key="info">
              <Descriptions column={2} bordered size="small">
                <Descriptions.Item label="ID">{selectedClient.id}</Descriptions.Item>
                <Descriptions.Item label="Telegram ID">
                  {selectedClient.telegram_id || 'Не указан'}
                </Descriptions.Item>
                <Descriptions.Item label="Имя" span={2}>
                  {selectedClient.first_name} {selectedClient.last_name || ''}
                </Descriptions.Item>
                <Descriptions.Item label="Телефон">
                  {selectedClient.phone || 'Не указан'}
                </Descriptions.Item>
                <Descriptions.Item label="Email">
                  {selectedClient.email || 'Не указан'}
                </Descriptions.Item>
                <Descriptions.Item label="Дата регистрации">
                  {dayjs(selectedClient.created_at).format('DD.MM.YYYY HH:mm')}
                </Descriptions.Item>
                <Descriptions.Item label="Язык">
                  {selectedClient.language === 'ru' ? 'Русский' : selectedClient.language || 'Русский'}
                </Descriptions.Item>
                <Descriptions.Item label="Всего записей">
                  {selectedClient.appointment_count || 0}
                </Descriptions.Item>
                <Descriptions.Item label="Завершено">
                  {selectedClient.completed_count || 0}
                </Descriptions.Item>
              </Descriptions>
            </TabPane>
            
            <TabPane tab="Статистика" key="stats">
              {clientStats ? (
                <Row gutter={16}>
                  <Col span={12}>
                    <Card size="small" style={{ marginBottom: 16 }}>
                      <Statistic
                        title="Всего записей"
                        value={clientStats.appointments?.total || 0}
                        prefix={<CalendarOutlined />}
                      />
                    </Card>
                    <Card size="small">
                      <Statistic
                        title="Завершено"
                        value={clientStats.appointments?.completed || 0}
                        prefix={<CalendarOutlined />}
                        valueStyle={{ color: '#3f8600' }}
                      />
                    </Card>
                  </Col>
                  <Col span={12}>
                    <Card size="small" style={{ marginBottom: 16 }}>
                      <Statistic
                        title="Всего потрачено"
                        value={clientStats.spending?.total || 0}
                        prefix={<DollarOutlined />}
                        valueStyle={{ color: '#722ed1' }}
                        formatter={(value) => `${value.toLocaleString('ru-RU')} ₽`}
                      />
                    </Card>
                    <Card size="small">
                      <Statistic
                        title="Средний чек"
                        value={clientStats.spending?.average || 0}
                        prefix={<DollarOutlined />}
                        formatter={(value) => `${value.toLocaleString('ru-RU')} ₽`}
                      />
                    </Card>
                  </Col>
                  <Col span={24} style={{ marginTop: 16 }}>
                    <Card size="small">
                      <div style={{ textAlign: 'center', padding: '8px' }}>
                        <ClockCircleOutlined style={{ marginRight: 8 }} />
                        Последняя запись: {clientStats.last_appointment?.date 
                          ? dayjs(clientStats.last_appointment.date).format('DD.MM.YYYY')
                          : 'Нет записей'}
                        {clientStats.last_appointment?.status && (
                          <Tag color="blue" style={{ marginLeft: 8 }}>
                            {clientStats.last_appointment.status === 'completed' ? 'Завершена' : 
                             clientStats.last_appointment.status === 'pending' ? 'Ожидает' :
                             clientStats.last_appointment.status === 'cancelled' ? 'Отменена' :
                             clientStats.last_appointment.status === 'no_show' ? 'Неявка' : 
                             clientStats.last_appointment.status}
                          </Tag>
                        )}
                      </div>
                    </Card>
                  </Col>
                </Row>
              ) : (
                <div style={{ textAlign: 'center', padding: '40px' }}>
                  <p>Нет данных статистики</p>
                </div>
              )}
            </TabPane>
            
            <TabPane 
              tab={
                <span>
                  <HistoryOutlined />
                  История записей ({clientAppointments.length})
                </span>
              } 
              key="appointments"
            >
              {clientAppointments.length > 0 ? (
                <Table
                  columns={[
                    {
                      title: 'Дата и время',
                      key: 'datetime',
                      render: (record) => (
                        <div>
                          <div>{dayjs(record.appointment_date).format('DD.MM.YYYY')}</div>
                          <div style={{ fontSize: '12px', color: '#666' }}>
                            {record.start_time} - {record.end_time}
                          </div>
                        </div>
                      ),
                    },
                    {
                      title: 'Мастер',
                      key: 'master',
                      render: (record) => (
                        record.master_first_name 
                          ? `${record.master_first_name} ${record.master_last_name}`
                          : 'Не указан'
                      ),
                    },
                    {
                      title: 'Услуги',
                      key: 'services',
                      render: (record) => (
                        <div>
                          {record.services?.slice(0, 2).map(service => (
                            <div key={service.id} style={{ fontSize: '12px' }}>
                              {service.title}
                            </div>
                          ))}
                          {record.services?.length > 2 && (
                            <div style={{ fontSize: '11px', color: '#666' }}>
                              +{record.services.length - 2} еще
                            </div>
                          )}
                        </div>
                      ),
                    },
                    {
                      title: 'Сумма',
                      key: 'amount',
                      render: (record) => {
                        const total = record.services?.reduce((sum, service) => 
                          sum + (service.price || 0), 0) || 0;
                        return `${total.toLocaleString('ru-RU')} ₽`;
                      },
                    },
                    {
                      title: 'Статус',
                      key: 'status',
                      render: (record) => {
                        const statusColors = {
                          pending: 'blue',
                          confirmed: 'green',
                          cancelled: 'red',
                          completed: 'purple',
                          no_show: 'orange',
                        };
                        const statusLabels = {
                          pending: 'Ожидает',
                          confirmed: 'Подтверждена',
                          cancelled: 'Отменена',
                          completed: 'Завершена',
                          no_show: 'Неявка',
                        };
                        return (
                          <Tag color={statusColors[record.status] || 'default'}>
                            {statusLabels[record.status] || record.status}
                          </Tag>
                        );
                      },
                    },
                  ]}
                  dataSource={clientAppointments}
                  rowKey="id"
                  size="small"
                  pagination={{ pageSize: 5, simple: true }}
                />
              ) : (
                <div style={{ textAlign: 'center', padding: '40px' }}>
                  <p>Нет записей у клиента</p>
                </div>
              )}
            </TabPane>
          </Tabs>
        )}
      </Modal>
    </div>
  );
};

export default Clients;