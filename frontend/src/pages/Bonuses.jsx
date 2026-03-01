import React, { useState, useEffect } from 'react';
import {
  Table,
  Button,
  Modal,
  Form,
  Input,
  InputNumber,
  Select,
  Space,
  Tag,
  message,
  Card,
  Row,
  Col,
  Statistic,
  Descriptions,
} from 'antd';
import {
  PlusOutlined,
  MinusOutlined,
  GiftOutlined,
  ArrowUpOutlined,
  ArrowDownOutlined,
  HistoryOutlined,
  UserOutlined,
  DollarOutlined,
} from '@ant-design/icons';

const { Option } = Select;

const Bonuses = () => {
  const [clients, setClients] = useState([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [historyModalVisible, setHistoryModalVisible] = useState(false);
  const [selectedClientId, setSelectedClientId] = useState(null);
  const [operationType, setOperationType] = useState('add'); // 'add' или 'subtract'
  const [form] = Form.useForm();

  // Тестовые данные
  const testClients = [
    {
      id: 1,
      name: 'Иван Иванов',
      phone: '+7 999 123-45-67',
      balance: 1500,
      last_operation: '2024-01-10',
      status: 'active',
    },
    {
      id: 2,
      name: 'Мария Петрова',
      phone: '+7 999 987-65-43',
      balance: 500,
      last_operation: '2024-01-09',
      status: 'active',
    },
    {
      id: 3,
      name: 'Алексей Сидоров',
      phone: '+7 999 555-44-33',
      balance: 0,
      last_operation: '2023-12-20',
      status: 'inactive',
    },
  ];

  const testHistory = [
    {
      id: 1,
      date: '2024-01-10 14:30',
      amount: 500,
      type: 'add',
      reason: 'Начисление за покупку',
      balance_after: 1500,
    },
    {
      id: 2,
      date: '2024-01-05 11:15',
      amount: 1000,
      type: 'add',
      reason: 'Бонус за повторное посещение',
      balance_after: 1000,
    },
    {
      id: 3,
      date: '2023-12-25 16:45',
      amount: 300,
      type: 'subtract',
      reason: 'Оплата услуг',
      balance_after: 0,
    },
  ];

  useEffect(() => {
    fetchClients();
  }, []);

  const fetchClients = async () => {
    setLoading(true);
    try {
      // В реальном приложении: const response = await axios.get('/api/clients');
      setTimeout(() => {
        setClients(testClients);
        setLoading(false);
      }, 500);
    } catch (error) {
      message.error('Ошибка при загрузке данных');
      setLoading(false);
    }
  };

  const handleOperation = async (values) => {
    try {
      const amount = operationType === 'add' ? values.amount : -values.amount;
      
      // В реальном приложении:
      // if (operationType === 'add') {
      //   await axios.post(`/api/bonuses/${selectedClientId}/add`, values);
      // } else {
      //   await axios.post(`/api/bonuses/${selectedClientId}/subtract`, values);
      // }
      
      message.success(
        operationType === 'add' 
          ? `Начислено ${values.amount} бонусов` 
          : `Списано ${values.amount} бонусов`
      );
      
      setModalVisible(false);
      form.resetFields();
      fetchClients();
    } catch (error) {
      message.error('Ошибка при выполнении операции');
    }
  };

  const showOperationModal = (clientId, type) => {
    setSelectedClientId(clientId);
    setOperationType(type);
    setModalVisible(true);
  };

  const showHistory = (clientId) => {
    setSelectedClientId(clientId);
    setHistoryModalVisible(true);
  };

  const columns = [
    {
      title: 'Клиент',
      dataIndex: 'name',
      key: 'name',
      render: (text) => (
        <span>
          <UserOutlined style={{ marginRight: 8 }} />
          {text}
        </span>
      ),
    },
    {
      title: 'Телефон',
      dataIndex: 'phone',
      key: 'phone',
    },
    {
      title: 'Баланс',
      dataIndex: 'balance',
      key: 'balance',
      render: (balance) => (
        <Tag color={balance > 0 ? 'green' : 'default'} style={{ fontSize: '16px' }}>
          <GiftOutlined /> {balance.toLocaleString()} бонусов
        </Tag>
      ),
    },
    {
      title: 'Последняя операция',
      dataIndex: 'last_operation',
      key: 'last_operation',
    },
    {
      title: 'Действия',
      key: 'actions',
      render: (_, record) => (
        <Space>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => showOperationModal(record.id, 'add')}
          >
            Начислить
          </Button>
          <Button
            type="default"
            icon={<MinusOutlined />}
            onClick={() => showOperationModal(record.id, 'subtract')}
            disabled={record.balance <= 0}
          >
            Списать
          </Button>
          <Button
            type="link"
            icon={<HistoryOutlined />}
            onClick={() => showHistory(record.id)}
          >
            История
          </Button>
        </Space>
      ),
    },
  ];

  const stats = {
    totalClients: clients.length,
    activeClients: clients.filter(c => c.balance > 0).length,
    totalBalance: clients.reduce((sum, client) => sum + client.balance, 0),
    averageBalance: clients.length > 0 
      ? Math.round(clients.reduce((sum, client) => sum + client.balance, 0) / clients.length)
      : 0,
  };

  return (
    <div>
      <Row gutter={[12, 12]} style={{ marginBottom: 16 }}>
        <Col xs={12} sm={12} md={6}>
          <Card size="small">
            <Statistic
              title="Всего клиентов"
              value={stats.totalClients}
              prefix={<UserOutlined />}
            />
          </Card>
        </Col>
        <Col xs={12} sm={12} md={6}>
          <Card size="small">
            <Statistic
              title="С бонусами"
              value={stats.activeClients}
              prefix={<GiftOutlined />}
            />
          </Card>
        </Col>
        <Col xs={12} sm={12} md={6}>
          <Card size="small">
            <Statistic
              title="Общий баланс"
              value={stats.totalBalance}
              prefix={<DollarOutlined />}
              suffix="бон."
            />
          </Card>
        </Col>
        <Col xs={12} sm={12} md={6}>
          <Card size="small">
            <Statistic
              title="Средний баланс"
              value={stats.averageBalance}
              prefix={<DollarOutlined />}
              suffix="бон."
            />
          </Card>
        </Col>
      </Row>

      <Card title="Бонусная система">
        <Table
          columns={columns}
          dataSource={clients}
          rowKey="id"
          loading={loading}
          scroll={{ x: 600 }}
          pagination={{ pageSize: 10 }}
        />
      </Card>

      {/* Модальное окно операции с бонусами */}
      <Modal
        title={operationType === 'add' ? 'Начисление бонусов' : 'Списание бонусов'}
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        footer={null}
        width={500}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleOperation}
        >
          <Form.Item
            name="amount"
            label="Количество бонусов"
            rules={[
              { required: true, message: 'Введите количество' },
              { type: 'number', min: 1, message: 'Минимум 1' },
            ]}
          >
            <InputNumber
              min={1}
              style={{ width: '100%' }}
              addonAfter="бонусов"
            />
          </Form.Item>

          <Form.Item
            name="reason"
            label="Причина"
            rules={[{ required: true, message: 'Укажите причину' }]}
          >
            <Input.TextArea rows={3} placeholder="Например: Начисление за покупку, Списание за услугу и т.д." />
          </Form.Item>

          <Form.Item style={{ textAlign: 'right' }}>
            <Button onClick={() => setModalVisible(false)} style={{ marginRight: 8 }}>
              Отмена
            </Button>
            <Button type="primary" htmlType="submit" icon={operationType === 'add' ? <PlusOutlined /> : <MinusOutlined />}>
              {operationType === 'add' ? 'Начислить' : 'Списать'}
            </Button>
          </Form.Item>
        </Form>
      </Modal>

      {/* Модальное окно истории операций */}
      <Modal
        title="История операций с бонусами"
        open={historyModalVisible}
        onCancel={() => setHistoryModalVisible(false)}
        footer={null}
        width={800}
      >
        <Descriptions title="Клиент: Иван Иванов" column={1} style={{ marginBottom: 24 }}>
          <Descriptions.Item label="Текущий баланс">
            <Tag color="green" style={{ fontSize: '16px' }}>1,500 бонусов</Tag>
          </Descriptions.Item>
        </Descriptions>

        <Table
          columns={[
            {
              title: 'Дата',
              dataIndex: 'date',
              key: 'date',
            },
            {
              title: 'Тип',
              dataIndex: 'type',
              key: 'type',
              render: (type) => (
                <Tag color={type === 'add' ? 'green' : 'red'}>
                  {type === 'add' ? (
                    <>
                      <ArrowUpOutlined /> Начисление
                    </>
                  ) : (
                    <>
                      <ArrowDownOutlined /> Списание
                    </>
                  )}
                </Tag>
              ),
            },
            {
              title: 'Сумма',
              dataIndex: 'amount',
              key: 'amount',
              render: (amount, record) => (
                <span style={{ color: record.type === 'add' ? '#3f8600' : '#cf1322' }}>
                  {record.type === 'add' ? '+' : '-'}{amount} бонусов
                </span>
              ),
            },
            {
              title: 'Причина',
              dataIndex: 'reason',
              key: 'reason',
            },
            {
              title: 'Баланс после',
              dataIndex: 'balance_after',
              key: 'balance_after',
              render: (balance) => `${balance.toLocaleString()} бонусов`,
            },
          ]}
          dataSource={testHistory}
          rowKey="id"
          pagination={{ pageSize: 5 }}
        />
      </Modal>
    </div>
  );
};

export default Bonuses;