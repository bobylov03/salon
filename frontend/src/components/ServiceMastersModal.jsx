// components/ServiceMastersModal.jsx
import React, { useState, useEffect } from 'react';
import {
  Modal,
  Table,
  Avatar,
  Tag,
  Space,
  Spin,
  Empty,
  Card,
  Row,
  Col,
  Typography,
  Button,
  Tooltip,
} from 'antd';
import {
  UserOutlined,
  PhoneOutlined,
  MailOutlined,
  StarOutlined,
  StarFilled,
  EyeOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';

const { Text } = Typography;

const ServiceMastersModal = ({ visible, serviceId, serviceTitle, onClose }) => {
  const [masters, setMasters] = useState([]);
  const [loading, setLoading] = useState(false);
  const [serviceInfo, setServiceInfo] = useState(null);

  useEffect(() => {
    if (visible && serviceId) {
      fetchServiceMasters();
      fetchServiceInfo();
    } else {
      setMasters([]);
      setServiceInfo(null);
    }
  }, [visible, serviceId]);

  const fetchServiceMasters = async () => {
    setLoading(true);
    try {
      const response = await fetch(`/api/services/${serviceId}/masters`);
      const data = await response.json();
      
      if (data.success) {
        setMasters(data.items || []);
      } else {
        console.error('Error fetching service masters:', data.message);
      }
    } catch (error) {
      console.error('Error fetching service masters:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchServiceInfo = async () => {
    try {
      const response = await fetch(`/api/services/${serviceId}`);
      const data = await response.json();
      setServiceInfo(data);
    } catch (error) {
      console.error('Error fetching service info:', error);
    }
  };

  const columns = [
    {
      title: 'Мастер',
      key: 'master',
      render: (record) => (
        <Space>
          <Avatar 
            src={record.photo_url} 
            size={40} 
            icon={<UserOutlined />}
          />
          <div>
            <div style={{ fontWeight: 500 }}>
              {record.first_name} {record.last_name}
            </div>
            <div style={{ fontSize: 12, color: '#666' }}>
              {record.qualification}
            </div>
          </div>
        </Space>
      ),
    },
    {
      title: 'Контакт',
      key: 'contact',
      render: (record) => (
        <div>
          {record.phone && (
            <div style={{ fontSize: 12 }}>
              <PhoneOutlined /> {record.phone}
            </div>
          )}
          {record.email && (
            <div style={{ fontSize: 12 }}>
              <MailOutlined /> {record.email}
            </div>
          )}
        </div>
      ),
    },
    {
      title: 'Тип услуги',
      dataIndex: 'is_primary',
      key: 'type',
      render: (isPrimary) => (
        <Tag color={isPrimary ? 'gold' : 'blue'} icon={isPrimary ? <StarFilled /> : <StarOutlined />}>
          {isPrimary ? 'Основная' : 'Дополнительная'}
        </Tag>
      ),
    },
    {
      title: 'Статус',
      dataIndex: 'is_active',
      key: 'status',
      render: (active) => (
        <Tag color={active ? 'green' : 'red'}>
          {active ? 'Активен' : 'Неактивен'}
        </Tag>
      ),
    },
    {
      title: 'Действия',
      key: 'actions',
      render: (record) => (
        <Tooltip title="Просмотр мастера">
          <Button
            type="link"
            icon={<EyeOutlined />}
            onClick={() => window.open(`/masters?masterId=${record.id}`, '_blank')}
          />
        </Tooltip>
      ),
    },
  ];

  if (!serviceInfo) {
    return (
      <Modal
        title="Мастера услуги"
        open={visible}
        onCancel={onClose}
        footer={null}
        width={800}
      >
        <Spin tip="Загрузка данных..." />
      </Modal>
    );
  }

  return (
    <Modal
      title={
        <Space>
          <span>Мастера для услуги</span>
          <Tag color="blue">{serviceTitle || serviceInfo.title}</Tag>
        </Space>
      }
      open={visible}
      onCancel={onClose}
      footer={null}
      width={900}
    >
      {serviceInfo && (
        <Card size="small" style={{ marginBottom: 16 }}>
          <Row gutter={16}>
            <Col span={8}>
              <div style={{ fontSize: 12, color: '#666' }}>Название</div>
              <div style={{ fontWeight: 500 }}>{serviceInfo.title}</div>
            </Col>
            <Col span={4}>
              <div style={{ fontSize: 12, color: '#666' }}>Цена</div>
              <div style={{ fontWeight: 500 }}>{serviceInfo.price} ₽</div>
            </Col>
            <Col span={4}>
              <div style={{ fontSize: 12, color: '#666' }}>Длительность</div>
              <div style={{ fontWeight: 500 }}>{serviceInfo.duration_minutes} мин</div>
            </Col>
            <Col span={8}>
              <div style={{ fontSize: 12, color: '#666' }}>Категория</div>
              <div style={{ fontWeight: 500 }}>{serviceInfo.category_title}</div>
            </Col>
          </Row>
        </Card>
      )}

      <Card
        title={
          <Space>
            <span>Мастера, предоставляющие услугу</span>
            <Tag>{masters.length}</Tag>
          </Space>
        }
      >
        <Table
          columns={columns}
          dataSource={masters}
          rowKey="id"
          loading={loading}
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showTotal: (total) => `Всего ${total} мастеров`,
          }}
          locale={{
            emptyText: (
              <Empty description="Нет мастеров, предоставляющих эту услугу" />
            ),
          }}
        />
      </Card>
    </Modal>
  );
};

export default ServiceMastersModal;