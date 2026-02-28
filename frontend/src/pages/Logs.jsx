import React, { useState, useEffect } from 'react';
import {
  Table,
  Card,
  Tag,
  Select,
  DatePicker,
  Input,
  Space,
  Button,
  Row,
  Col,
  Descriptions,
  Badge,
} from 'antd';
import {
  SearchOutlined,
  FilterOutlined,
  UserOutlined,
  CalendarOutlined,
  ClockCircleOutlined,
  SafetyCertificateOutlined,
  EditOutlined,
  DeleteOutlined,
  PlusOutlined,
} from '@ant-design/icons';

const { Option } = Select;
const { RangePicker } = DatePicker;
const { Search } = Input;

const Logs = () => {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [filters, setFilters] = useState({
    admin: null,
    action: null,
    dateRange: null,
    search: '',
  });

  // Тестовые данные логов
  const testLogs = [
    {
      id: 1,
      admin_name: 'Администратор Системы',
      action: 'CREATE_MASTER',
      details: 'Создал мастера: Анна Петрова',
      ip_address: '192.168.1.100',
      created_at: '2024-01-15 14:30:25',
      level: 'info',
    },
    {
      id: 2,
      admin_name: 'Менеджер Мария',
      action: 'UPDATE_APPOINTMENT',
      details: 'Изменил статус записи #123 на "подтверждена"',
      ip_address: '192.168.1.101',
      created_at: '2024-01-15 12:15:42',
      level: 'info',
    },
    {
      id: 3,
      admin_name: 'Администратор Системы',
      action: 'DELETE_SERVICE',
      details: 'Удалил услугу "Мужская стрижка"',
      ip_address: '192.168.1.100',
      created_at: '2024-01-14 16:45:18',
      level: 'warning',
    },
    {
      id: 4,
      admin_name: 'Админ Иван',
      action: 'ADD_BONUSES',
      details: 'Начислил 500 бонусов клиенту Иван Иванов',
      ip_address: '192.168.1.102',
      created_at: '2024-01-14 11:20:33',
      level: 'info',
    },
    {
      id: 5,
      admin_name: 'Менеджер Мария',
      action: 'LOGIN',
      details: 'Успешный вход в систему',
      ip_address: '192.168.1.101',
      created_at: '2024-01-14 09:05:12',
      level: 'success',
    },
    {
      id: 6,
      admin_name: 'Администратор Системы',
      action: 'FAILED_LOGIN',
      details: 'Неудачная попытка входа с IP: 192.168.1.200',
      ip_address: '192.168.1.200',
      created_at: '2024-01-13 22:15:47',
      level: 'error',
    },
  ];

  useEffect(() => {
    fetchLogs();
  }, [filters]);

  const fetchLogs = async () => {
    setLoading(true);
    try {
      // В реальном приложении: const response = await axios.get('/api/admin-logs', { params: filters });
      setTimeout(() => {
        setLogs(testLogs);
        setLoading(false);
      }, 500);
    } catch (error) {
      console.error('Error fetching logs:', error);
      setLoading(false);
    }
  };

  const getActionLabel = (action) => {
    const labels = {
      'CREATE_MASTER': 'Создание мастера',
      'UPDATE_MASTER': 'Обновление мастера',
      'DELETE_MASTER': 'Удаление мастера',
      'CREATE_SERVICE': 'Создание услуги',
      'UPDATE_SERVICE': 'Обновление услуги',
      'DELETE_SERVICE': 'Удаление услуги',
      'CREATE_APPOINTMENT': 'Создание записи',
      'UPDATE_APPOINTMENT': 'Обновление записи',
      'DELETE_APPOINTMENT': 'Удаление записи',
      'ADD_BONUSES': 'Начисление бонусов',
      'SUBTRACT_BONUSES': 'Списание бонусов',
      'LOGIN': 'Вход в систему',
      'FAILED_LOGIN': 'Неудачный вход',
      'LOGOUT': 'Выход из системы',
    };
    return labels[action] || action;
  };

  const getLevelColor = (level) => {
    const colors = {
      'info': 'blue',
      'success': 'green',
      'warning': 'orange',
      'error': 'red',
    };
    return colors[level] || 'default';
  };

  const getLevelIcon = (level) => {
    const icons = {
      'info': <SafetyCertificateOutlined />,
      'success': <SafetyCertificateOutlined style={{ color: '#52c41a' }} />,
      'warning': <SafetyCertificateOutlined style={{ color: '#faad14' }} />,
      'error': <SafetyCertificateOutlined style={{ color: '#ff4d4f' }} />,
    };
    return icons[level];
  };

  const columns = [
    {
      title: 'Время',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (time) => (
        <div>
          <div>
            <CalendarOutlined style={{ marginRight: 4 }} />
            {time.split(' ')[0]}
          </div>
          <div style={{ fontSize: '12px', color: '#999' }}>
            <ClockCircleOutlined style={{ marginRight: 4 }} />
            {time.split(' ')[1]}
          </div>
        </div>
      ),
    },
    {
      title: 'Администратор',
      dataIndex: 'admin_name',
      key: 'admin_name',
      render: (name) => (
        <span>
          <UserOutlined style={{ marginRight: 8 }} />
          {name}
        </span>
      ),
    },
    {
      title: 'Действие',
      dataIndex: 'action',
      key: 'action',
      render: (action) => (
        <Tag color="blue">
          {getActionLabel(action)}
        </Tag>
      ),
    },
    {
      title: 'Описание',
      dataIndex: 'details',
      key: 'details',
      ellipsis: true,
    },
    {
      title: 'Уровень',
      dataIndex: 'level',
      key: 'level',
      render: (level) => (
        <Badge
          status={level}
          text={
            <Tag color={getLevelColor(level)} icon={getLevelIcon(level)}>
              {level === 'info' && 'Инфо'}
              {level === 'success' && 'Успех'}
              {level === 'warning' && 'Предупреждение'}
              {level === 'error' && 'Ошибка'}
            </Tag>
          }
        />
      ),
    },
    {
      title: 'IP адрес',
      dataIndex: 'ip_address',
      key: 'ip_address',
      render: (ip) => <Tag>{ip}</Tag>,
    },
  ];

  const stats = {
    total: logs.length,
    today: logs.filter(log => log.created_at.startsWith('2024-01-15')).length,
    errors: logs.filter(log => log.level === 'error').length,
    warnings: logs.filter(log => log.level === 'warning').length,
  };

  return (
    <div>
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card size="small">
            <Descriptions title="Статистика логов" column={1} size="small">
              <Descriptions.Item label="Всего записей">
                <Tag color="blue">{stats.total}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="Сегодня">
                <Tag color="green">{stats.today}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="Ошибки">
                <Tag color="red">{stats.errors}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="Предупреждения">
                <Tag color="orange">{stats.warnings}</Tag>
              </Descriptions.Item>
            </Descriptions>
          </Card>
        </Col>
        <Col span={18}>
          <Card title="Фильтры логов">
            <Row gutter={16}>
              <Col span={6}>
                <Select
                  placeholder="Администратор"
                  style={{ width: '100%' }}
                  allowClear
                  onChange={(value) => setFilters({ ...filters, admin: value })}
                >
                  <Option value="admin1">Администратор Системы</Option>
                  <Option value="admin2">Менеджер Мария</Option>
                  <Option value="admin3">Админ Иван</Option>
                </Select>
              </Col>
              <Col span={6}>
                <Select
                  placeholder="Действие"
                  style={{ width: '100%' }}
                  allowClear
                  onChange={(value) => setFilters({ ...filters, action: value })}
                >
                  <Option value="CREATE">Создание</Option>
                  <Option value="UPDATE">Обновление</Option>
                  <Option value="DELETE">Удаление</Option>
                  <Option value="LOGIN">Вход</Option>
                </Select>
              </Col>
              <Col span={8}>
                <RangePicker
                  style={{ width: '100%' }}
                  onChange={(dates) => setFilters({ ...filters, dateRange: dates })}
                />
              </Col>
              <Col span={4}>
                <Button
                  icon={<FilterOutlined />}
                  onClick={() => {
                    setFilters({
                      admin: null,
                      action: null,
                      dateRange: null,
                      search: '',
                    });
                  }}
                  style={{ width: '100%' }}
                >
                  Сбросить
                </Button>
              </Col>
            </Row>
            <Row style={{ marginTop: 16 }}>
              <Col span={24}>
                <Search
                  placeholder="Поиск по описанию..."
                  onSearch={(value) => setFilters({ ...filters, search: value })}
                  style={{ width: '100%' }}
                />
              </Col>
            </Row>
          </Card>
        </Col>
      </Row>

      <Card title="Журнал действий администраторов">
        <Table
          columns={columns}
          dataSource={logs}
          rowKey="id"
          loading={loading}
          pagination={{
            pageSize: 20,
            showSizeChanger: true,
            showTotal: (total) => `Всего ${total} записей`,
          }}
          expandable={{
            expandedRowRender: (record) => (
              <div style={{ margin: 0 }}>
                <p><strong>Подробности:</strong> {record.details}</p>
                <p><strong>Полное время:</strong> {record.created_at}</p>
                <p><strong>Тип действия:</strong> {record.action}</p>
              </div>
            ),
            rowExpandable: (record) => record.details.length > 50,
          }}
        />
      </Card>
    </div>
  );
};

export default Logs;