// Schedule.py (с возможностью установки выходного)
import React, { useState, useEffect } from 'react';
import { 
  Card, Table, Button, Select, Row, Col, message, 
  TimePicker, Modal, Form, Input, Tag, Space, Switch,
  Radio, Typography, Popconfirm, Alert
} from 'antd';
import { 
  CalendarOutlined, PlusOutlined, DeleteOutlined, 
  EditOutlined, ClockCircleOutlined, RestOutlined,
  CheckCircleOutlined, CloseCircleOutlined 
} from '@ant-design/icons';
import axios from 'axios';
import dayjs from 'dayjs';

const { Option } = Select;
const { Text } = Typography;

const Schedule = () => {
  const [masters, setMasters] = useState([]);
  const [selectedMaster, setSelectedMaster] = useState(null);
  const [scheduleData, setScheduleData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [form] = Form.useForm();
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [editingDay, setEditingDay] = useState(null);
  const [selectedMasterInfo, setSelectedMasterInfo] = useState(null);
  const [isWorkingDay, setIsWorkingDay] = useState(true);

  // Загружаем мастеров при монтировании
  useEffect(() => {
    fetchMasters();
  }, []);

  // Загружаем график при выборе мастера
  useEffect(() => {
    if (selectedMaster) {
      fetchMasterSchedule(selectedMaster);
      fetchMasterDetails(selectedMaster);
    } else {
      setScheduleData([]);
      setSelectedMasterInfo(null);
    }
  }, [selectedMaster]);

  const fetchMasters = async () => {
    try {
      const response = await axios.get('/masters');
      if (response.data && response.data.items) {
        setMasters(response.data.items);
      }
    } catch (error) {
      message.error('Ошибка при загрузке мастеров');
      console.error('Error fetching masters:', error);
    }
  };

  const fetchMasterDetails = async (masterId) => {
    try {
      const response = await axios.get(`/masters/${masterId}`);
      setSelectedMasterInfo(response.data);
    } catch (error) {
      console.error('Error fetching master details:', error);
    }
  };

  const fetchMasterSchedule = async (masterId) => {
    try {
      setLoading(true);
      const response = await axios.get(`/schedule/masters/${masterId}`);
      setScheduleData(response.data || []);
    } catch (error) {
      console.error('Error fetching schedule:', error);
      setScheduleData([]);
    } finally {
      setLoading(false);
    }
  };

  const handleSaveSchedule = async () => {
    try {
      const values = await form.validateFields();
      
      if (!selectedMaster || editingDay === null) {
        message.error('Ошибка: не выбран мастер или день недели');
        return;
      }
      
      if (isWorkingDay) {
        // Если рабочий день - сохраняем время
        const startTime = values.timeRange[0].format('HH:mm');
        const endTime = values.timeRange[1].format('HH:mm');

        const response = await axios.post(`/schedule/masters/${selectedMaster}`, {
          day_of_week: editingDay,
          start_time: startTime,
          end_time: endTime
        });

        message.success('График успешно сохранен');
      } else {
        // Если выходной - удаляем график (если был) или просто не добавляем
        await axios.delete(`/schedule/masters/${selectedMaster}/days/${editingDay}`);
        message.success('День установлен как выходной');
      }
      
      setIsModalVisible(false);
      form.resetFields();
      fetchMasterSchedule(selectedMaster);
    } catch (error) {
      console.error('Full error:', error);
      if (error.response) {
        message.error(`Ошибка сервера: ${error.response.data.detail || error.response.statusText}`);
      } else if (error.request) {
        message.error('Нет ответа от сервера');
      } else {
        message.error(`Ошибка: ${error.message}`);
      }
    }
  };

  const handleDeleteSchedule = async (dayOfWeek) => {
    Modal.confirm({
      title: 'Удалить график?',
      content: `Вы уверены, что хотите удалить график на ${getDayName(dayOfWeek)}?`,
      okText: 'Удалить',
      okType: 'danger',
      cancelText: 'Отмена',
      onOk: async () => {
        try {
          await axios.delete(`/schedule/masters/${selectedMaster}/days/${dayOfWeek}`);
          message.success('График удален');
          fetchMasterSchedule(selectedMaster);
        } catch (error) {
          message.error('Ошибка при удалении');
          console.error('Error deleting schedule:', error);
        }
      }
    });
  };

  const handleSetDayOff = async (dayOfWeek) => {
    Modal.confirm({
      title: 'Установить выходной?',
      content: `Вы уверены, что хотите установить ${getDayName(dayOfWeek)} как выходной?`,
      okText: 'Установить',
      cancelText: 'Отмена',
      onOk: async () => {
        try {
          await axios.delete(`/schedule/masters/${selectedMaster}/days/${dayOfWeek}`);
          message.success('День установлен как выходной');
          fetchMasterSchedule(selectedMaster);
        } catch (error) {
          message.error('Ошибка при установке выходного');
          console.error('Error setting day off:', error);
        }
      }
    });
  };

  const handleEditSchedule = (dayOfWeek, existingTime = null) => {
    setEditingDay(dayOfWeek);
    
    // Проверяем, есть ли график на этот день
    const hasSchedule = !!existingTime;
    setIsWorkingDay(hasSchedule);
    
    if (hasSchedule && existingTime) {
      form.setFieldsValue({
        timeRange: [
          dayjs(existingTime.start_time, 'HH:mm'),
          dayjs(existingTime.end_time, 'HH:mm')
        ]
      });
    } else {
      form.setFieldsValue({
        timeRange: [dayjs('09:00', 'HH:mm'), dayjs('18:00', 'HH:mm')]
      });
    }
    
    setIsModalVisible(true);
  };

  const getDayName = (dayIndex) => {
    const dayNames = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье'];
    return dayNames[dayIndex] || 'День недели';
  };

  const dayNames = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье'];

  const columns = [
    { 
      title: 'День недели', 
      dataIndex: 'day_of_week',
      width: 200,
      render: (day) => (
        <div>
          <div style={{ fontWeight: 'bold', fontSize: '16px' }}>
            {dayNames[day]}
          </div>
          <div style={{ fontSize: '12px', color: '#666' }}>
            {day === 5 || day === 6 ? 'Выходные дни' : 'Будние дни'}
          </div>
        </div>
      )
    },
    { 
      title: 'Статус', 
      width: 150,
      render: (_, record) => {
        if (record.hasSchedule) {
          return (
            <Tag color="green" icon={<CheckCircleOutlined />}>
              Рабочий день
            </Tag>
          );
        } else {
          return (
            <Tag color="red" icon={<CloseCircleOutlined />}>
              Выходной
            </Tag>
          );
        }
      }
    },
    { 
      title: 'Время работы', 
      render: (_, record) => {
        if (record.hasSchedule) {
          return (
            <Space>
              <ClockCircleOutlined style={{ color: '#52c41a', fontSize: '16px' }} />
              <Text strong style={{ fontSize: '16px' }}>
                {record.start_time} - {record.end_time}
              </Text>
              <Text type="secondary" style={{ fontSize: '12px' }}>
                ({calculateDuration(record.start_time, record.end_time)} часов)
              </Text>
            </Space>
          );
        } else {
          return (
            <Space>
              <RestOutlined style={{ color: '#ff4d4f', fontSize: '16px' }} />
              <Text type="secondary" style={{ fontSize: '14px' }}>
                Выходной
              </Text>
            </Space>
          );
        }
      }
    },
    {
      title: 'Действия',
      width: 250,
      render: (_, record) => (
        <Space>
          {record.hasSchedule ? (
            <>
              <Button
                type="primary"
                size="small"
                icon={<EditOutlined />}
                onClick={() => handleEditSchedule(record.day_of_week, record.existingSchedule)}
              >
                Изменить
              </Button>
              
              <Popconfirm
                title="Установить выходной?"
                description={`Установить ${getDayName(record.day_of_week)} как выходной?`}
                onConfirm={() => handleSetDayOff(record.day_of_week)}
                okText="Да"
                cancelText="Нет"
              >
                <Button
                  type="dashed"
                  size="small"
                  icon={<RestOutlined />}
                >
                  Выходной
                </Button>
              </Popconfirm>
            </>
          ) : (
            <>
              <Button
                type="primary"
                size="small"
                icon={<EditOutlined />}
                onClick={() => handleEditSchedule(record.day_of_week)}
              >
                Настроить
              </Button>
              
              <Button
                type="text"
                size="small"
                disabled
                icon={<RestOutlined />}
              >
                Выходной
              </Button>
            </>
          )}
        </Space>
      )
    }
  ];

  // Расчет длительности рабочего дня
  const calculateDuration = (startTime, endTime) => {
    const start = dayjs(startTime, 'HH:mm');
    const end = dayjs(endTime, 'HH:mm');
    return end.diff(start, 'hour', true).toFixed(1);
  };

  // Генерация всех дней недели с текущим графиком
  const allDays = dayNames.map((dayName, index) => {
    const existingSchedule = scheduleData.find(item => item.day_of_week === index);
    
    return {
      key: index,
      day_of_week: index,
      day: dayName,
      start_time: existingSchedule ? existingSchedule.start_time : null,
      end_time: existingSchedule ? existingSchedule.end_time : null,
      hasSchedule: !!existingSchedule,
      existingSchedule: existingSchedule || null
    };
  });

  return (
    <div>
      <Card 
        title={
          <div>
            <CalendarOutlined style={{ marginRight: 8 }} />
            График работы мастеров
          </div>
        }
        extra={
          selectedMaster && (
            <Button 
              type="primary" 
              icon={<PlusOutlined />}
              onClick={() => {
                setEditingDay(0);
                setIsWorkingDay(true);
                form.setFieldsValue({
                  timeRange: [dayjs('09:00', 'HH:mm'), dayjs('18:00', 'HH:mm')]
                });
                setIsModalVisible(true);
              }}
            >
              Быстрое добавление
            </Button>
          )
        }
      >
        <Row gutter={[16, 12]} style={{ marginBottom: 24 }}>
          <Col xs={24} md={8}>
            <Select
              placeholder="Выберите мастера"
              style={{ width: '100%' }}
              onChange={(value) => {
                setSelectedMaster(value);
                setEditingDay(null);
              }}
              allowClear
              value={selectedMaster}
              showSearch
              optionFilterProp="children"
              size="large"
            >
              {masters.map(master => (
                <Option key={master.id} value={master.id}>
                  <div style={{ display: 'flex', alignItems: 'center' }}>
                    {master.photo_url && (
                      <img 
                        src={master.photo_url} 
                        alt="avatar" 
                        style={{ 
                          width: 24, 
                          height: 24, 
                          borderRadius: '50%',
                          marginRight: 8,
                          objectFit: 'cover' 
                        }} 
                      />
                    )}
                    <div>
                      <div>{master.first_name} {master.last_name}</div>
                      {master.qualification && (
                        <div style={{ fontSize: '12px', color: '#666' }}>
                          {master.qualification}
                        </div>
                      )}
                    </div>
                  </div>
                </Option>
              ))}
            </Select>
          </Col>
          
          <Col xs={24} md={16}>
            {selectedMasterInfo && (
              <Alert
                message={
                  <Space>
                    {selectedMasterInfo.photo_url && (
                      <img 
                        src={selectedMasterInfo.photo_url} 
                        alt="avatar" 
                        style={{ 
                          width: 32, 
                          height: 32, 
                          borderRadius: '50%',
                          objectFit: 'cover' 
                        }} 
                      />
                    )}
                    <div>
                      <strong>{selectedMasterInfo.first_name} {selectedMasterInfo.last_name}</strong>
                      <div style={{ fontSize: '14px', color: '#666' }}>
                        Рабочих дней: <Tag color="green">{scheduleData.length}</Tag>
                        {' '}Выходных: <Tag color="red">{7 - scheduleData.length}</Tag>
                      </div>
                    </div>
                  </Space>
                }
                description={selectedMasterInfo.qualification || 'Мастер'}
                type="info"
                showIcon={false}
                style={{ backgroundColor: '#e6f7ff', border: '1px solid #91d5ff' }}
              />
            )}
          </Col>
        </Row>
        
        {selectedMaster ? (
          <>
            <Table
              columns={columns}
              dataSource={allDays}
              loading={loading}
              pagination={false}
              scroll={{ x: 600 }}
              locale={{ emptyText: 'Загрузка графика...' }}
              style={{ marginTop: 16 }}
            />
            
            <div style={{ 
              marginTop: 24, 
              padding: 16, 
              backgroundColor: '#fafafa', 
              borderRadius: 6,
              border: '1px solid #f0f0f0'
            }}>
              <Text strong>Статистика:</Text>
              <Row gutter={[16, 8]} style={{ marginTop: 8 }}>
                <Col xs={8}>
                  <div style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#52c41a' }}>
                      {scheduleData.length}
                    </div>
                    <div style={{ color: '#666', fontSize: 12 }}>Рабочих дней</div>
                  </div>
                </Col>
                <Col xs={8}>
                  <div style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#ff4d4f' }}>
                      {7 - scheduleData.length}
                    </div>
                    <div style={{ color: '#666', fontSize: 12 }}>Выходных дней</div>
                  </div>
                </Col>
                <Col xs={8}>
                  <div style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#1890ff' }}>
                      {scheduleData.length > 0 ? scheduleData.length * 8 + 'ч' : '0ч'}
                    </div>
                    <div style={{ color: '#666', fontSize: 12 }}>Часов в неделю</div>
                  </div>
                </Col>
              </Row>
            </div>
          </>
        ) : (
          <div style={{ textAlign: 'center', padding: 60 }}>
            <CalendarOutlined style={{ fontSize: 64, color: '#d9d9d9', marginBottom: 16 }} />
            <h3 style={{ color: '#999', marginBottom: 8 }}>Выберите мастера</h3>
            <p style={{ color: '#999' }}>
              Для просмотра и редактирования графика работы выберите мастера из списка выше
            </p>
          </div>
        )}
      </Card>

      {/* Модальное окно для добавления/редактирования графика */}
      <Modal
        title={
          <div>
            <CalendarOutlined style={{ marginRight: 8 }} />
            {editingDay !== null ? `График работы: ${getDayName(editingDay)}` : 'График работы'}
          </div>
        }
        visible={isModalVisible}
        onOk={handleSaveSchedule}
        onCancel={() => {
          setIsModalVisible(false);
          form.resetFields();
          setIsWorkingDay(true);
        }}
        okText="Сохранить"
        cancelText="Отмена"
        width={500}
        okButtonProps={{
          icon: <CheckCircleOutlined />
        }}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            label="День недели"
          >
            <Input 
              value={editingDay !== null ? getDayName(editingDay) : ''} 
              disabled 
              size="large"
            />
          </Form.Item>
          
          <Form.Item
            label="Тип дня"
          >
            <Radio.Group 
              value={isWorkingDay} 
              onChange={(e) => setIsWorkingDay(e.target.value)}
              buttonStyle="solid"
              style={{ width: '100%' }}
            >
              <Radio.Button 
                value={true} 
                style={{ width: '50%', textAlign: 'center' }}
              >
                <CheckCircleOutlined /> Рабочий день
              </Radio.Button>
              <Radio.Button 
                value={false} 
                style={{ width: '50%', textAlign: 'center' }}
              >
                <RestOutlined /> Выходной
              </Radio.Button>
            </Radio.Group>
          </Form.Item>
          
          {isWorkingDay && (
            <Form.Item
              name="timeRange"
              label="Рабочее время"
              rules={[
                { required: true, message: 'Выберите время работы' },
                {
                  validator: (_, value) => {
                    if (!value || value.length < 2) {
                      return Promise.reject('Выберите время начала и окончания');
                    }
                    
                    const [start, end] = value;
                    if (start.isAfter(end)) {
                      return Promise.reject('Время начала должно быть раньше времени окончания');
                    }
                    
                    const duration = end.diff(start, 'hour', true);
                    if (duration > 14) {
                      return Promise.reject('Смена не может длиться более 14 часов');
                    }
                    
                    if (duration < 1) {
                      return Promise.reject('Смена должна быть не менее 1 часа');
                    }
                    
                    return Promise.resolve();
                  }
                }
              ]}
            >
              <TimePicker.RangePicker 
                format="HH:mm"
                style={{ width: '100%' }}
                minuteStep={15}
                placeholder={['Начало работы', 'Окончание работы']}
                size="large"
              />
            </Form.Item>
          )}
          
          <Alert
            message="Информация"
            description={
              isWorkingDay 
                ? "Установите время начала и окончания рабочего дня. Смена должна быть от 1 до 14 часов."
                : "Выбранный день будет отмечен как выходной. Клиенты не смогут записаться на этот день."
            }
            type="info"
            showIcon
            style={{ marginTop: 16 }}
          />
        </Form>
      </Modal>
    </div>
  );
};

export default Schedule;