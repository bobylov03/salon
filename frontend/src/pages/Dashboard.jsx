// pages/Dashboard.jsx
import React, { useState, useEffect } from 'react';
import {
  Card,
  Row,
  Col,
  Statistic,
  Table,
  Select,
  Spin,
  Typography,
  Tag,
  Progress,
  Alert,
  DatePicker,
} from 'antd';
import {
  CalendarOutlined,
  UserAddOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  TeamOutlined,
  DollarOutlined,
  StarOutlined,
  ClockCircleOutlined,
  RiseOutlined,
} from '@ant-design/icons';
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from 'recharts';
import api from '../services/api'; // Предполагаем, что у вас есть файл api.js для HTTP запросов
import dayjs from 'dayjs';

const { Title } = Typography;
const { RangePicker } = DatePicker;

// Конфигурация API
const API_BASE_URL = '';

// Функция для запросов к API
const fetchApi = async (endpoint, options = {}) => {
  try {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('API request failed:', error);
    throw error;
  }
};

// Генерация данных для графика динамики записей
const generateAppointmentsData = async (days = 30) => {
  try {
    const response = await fetchApi(`/appointments?start_date=${dayjs().subtract(days, 'day').format('YYYY-MM-DD')}&per_page=1000`);
    
    // Группировка по дням
    const appointmentsByDate = {};
    response.items.forEach(appointment => {
      const date = dayjs(appointment.appointment_date).format('DD MMM');
      if (!appointmentsByDate[date]) {
        appointmentsByDate[date] = {
          appointments: 0,
          completed: 0,
          revenue: 0,
        };
      }
      
      appointmentsByDate[date].appointments += 1;
      if (appointment.status === 'completed') {
        appointmentsByDate[date].completed += 1;
        // Рассчитываем выручку (суммируем цены услуг)
        if (appointment.services && Array.isArray(appointment.services)) {
          appointmentsByDate[date].revenue += appointment.services.reduce((sum, service) => sum + (service.price || 0), 0);
        }
      }
    });
    
    // Преобразуем в массив и сортируем по дате
    const data = Object.entries(appointmentsByDate)
      .map(([date, stats]) => ({
        date,
        appointments: stats.appointments,
        completed: stats.completed,
        revenue: stats.revenue,
      }))
      .sort((a, b) => dayjs(a.date, 'DD MMM').diff(dayjs(b.date, 'DD MMM')));
    
    // Если данных нет, возвращаем пустой массив
    return data.length > 0 ? data : generateFallbackData(days);
  } catch (error) {
    console.error('Error generating appointments data:', error);
    return generateFallbackData(days);
  }
};

// Запасные данные если API не работает
const generateFallbackData = (days = 30) => {
  const data = [];
  for (let i = 0; i < days; i++) {
    const date = dayjs().subtract(days - i - 1, 'day');
    data.push({
      date: date.format('DD MMM'),
      appointments: Math.floor(Math.random() * 5) + 1,
      completed: Math.floor(Math.random() * 4) + 1,
      revenue: Math.floor(Math.random() * 5000) + 1000,
    });
  }
  return data;
};

// Получение данных мастеров
const fetchMastersData = async (days = 7) => {
  try {
    const response = await fetchApi(`/analytics/masters-load?days=${days}`);
    
    if (response.success && response.masters) {
      return response.masters.map(master => ({
        master_name: master.name,
        appointment_count: master.appointment_count || 0,
        total_appointments: master.appointment_count || 0,
        completed: master.completed_count || 0,
        utilization_percent: master.load || 0,
      }));
    }
    
    return getFallbackMasters();
  } catch (error) {
    console.error('Error fetching masters data:', error);
    return getFallbackMasters();
  }
};

const getFallbackMasters = () => [
  { master_name: 'Нет данных', appointment_count: 0, total_appointments: 0, completed: 0, utilization_percent: 0 }
];

// Получение данных услуг
const fetchServicesData = async (days = 30) => {
  try {
    const response = await fetchApi(`/analytics/services-popularity?period_days=${days}`);
    
    if (response.success && response.services) {
      return response.services.map(service => ({
        title: service.title,
        service_count: service.service_count,
        revenue: service.revenue,
      }));
    }
    
    return getFallbackServices();
  } catch (error) {
    console.error('Error fetching services data:', error);
    return getFallbackServices();
  }
};

const getFallbackServices = () => [
  { title: 'Нет данных', service_count: 0, revenue: 0 }
];

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8'];

const Dashboard = () => {
  const [loading, setLoading] = useState(true);
  const [period, setPeriod] = useState(30);
  const [chartData, setChartData] = useState([]);
  const [mastersData, setMastersData] = useState([]);
  const [servicesData, setServicesData] = useState([]);
  const [stats, setStats] = useState({
    appointments: { total: 0, completed: 0, cancelled: 0 },
    clients: { new: 0, total: 0, active: 0 },
    revenue: { total: 0, today: 0, change: 0 },
    masters: { total: 0, active: 0, available: 0 },
  });
  const [error, setError] = useState(null);

  const loadDashboardData = async () => {
    setLoading(true);
    setError(null);
    
    try {
      // Загружаем основные статистики
      const dashboardStats = await fetchApi(`/analytics/dashboard?period_days=${period}`);
      
      if (dashboardStats.success) {
        setStats({
          appointments: {
            total: dashboardStats.appointments?.total || 0,
            completed: dashboardStats.appointments?.completed || 0,
            cancelled: dashboardStats.appointments?.cancelled || 0,
          },
          clients: {
            new: dashboardStats.clients?.new || 0,
            total: dashboardStats.clients?.total || 0,
            active: 0, // Пока не реализовано
          },
          revenue: {
            total: dashboardStats.revenue?.total || 0,
            today: dashboardStats.revenue?.today || 0,
            change: dashboardStats.revenue?.change || 0,
          },
          masters: {
            total: 0, // Пока не реализовано
            active: dashboardStats.masters?.active || 0,
            available: 0, // Пока не реализовано
          },
        });
      }

      // Загружаем данные для графиков параллельно
      const [
        appointmentsChartData,
        mastersList,
        servicesList
      ] = await Promise.all([
        generateAppointmentsData(period),
        fetchMastersData(7),
        fetchServicesData(period),
      ]);

      setChartData(appointmentsChartData);
      setMastersData(mastersList);
      setServicesData(servicesList);
      
    } catch (err) {
      console.error('Error loading dashboard data:', err);
      setError('Не удалось загрузить данные. Пожалуйста, проверьте подключение к серверу.');
      // Устанавливаем заглушки
      setChartData(generateFallbackData(period));
      setMastersData(getFallbackMasters());
      setServicesData(getFallbackServices());
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDashboardData();
  }, [period]);

  const handleRefresh = () => {
    loadDashboardData();
  };

  if (loading && !chartData.length) {
    return (
      <div style={{ textAlign: 'center', padding: '50px' }}>
        <Spin size="large" />
        <p>Загрузка данных...</p>
      </div>
    );
  }

  return (
    <div>
      {/* Заголовок и фильтры */}
      <div style={{ marginBottom: 24, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Title level={2}>Дашборд</Title>
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          <Select
            value={period}
            onChange={setPeriod}
            style={{ width: 120 }}
            options={[
              { value: 7, label: '7 дней' },
              { value: 30, label: '30 дней' },
              { value: 90, label: '90 дней' },
              { value: 365, label: 'Год' },
            ]}
          />
          <Tag color="blue" style={{ cursor: 'pointer' }} onClick={handleRefresh}>
            Обновить
          </Tag>
        </div>
      </div>

      {error && (
        <Alert
          message="Ошибка"
          description={error}
          type="warning"
          showIcon
          closable
          style={{ marginBottom: 16 }}
        />
      )}

      {/* Статистика */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="Всего записей"
              value={stats.appointments.total}
              prefix={<CalendarOutlined />}
              valueStyle={{ fontSize: '28px' }}
            />
            <div style={{ marginTop: 8, fontSize: '12px', color: '#666' }}>
              <CheckCircleOutlined style={{ color: '#52c41a', marginRight: 4 }} />
              {stats.appointments.completed} завершено
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="Клиенты"
              value={stats.clients.total}
              prefix={<TeamOutlined />}
              valueStyle={{ fontSize: '28px' }}
            />
            <div style={{ marginTop: 8, fontSize: '12px', color: '#666' }}>
              <UserAddOutlined style={{ color: '#1890ff', marginRight: 4 }} />
              +{stats.clients.new} новых
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="Выручка"
              value={stats.revenue.total}
              prefix={<DollarOutlined />}
              suffix="₺"
              valueStyle={{ fontSize: '28px', color: '#3f8600' }}
            />
            <div style={{ marginTop: 8, fontSize: '12px', color: '#666' }}>
              <RiseOutlined style={{ color: '#3f8600', marginRight: 4 }} />
              +{stats.revenue.change}%
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="Мастера"
              value={stats.masters.active}
              suffix={`/ ${stats.masters.total || '?'}`}
              prefix={<TeamOutlined />}
              valueStyle={{ fontSize: '28px' }}
            />
            <div style={{ marginTop: 8, fontSize: '12px', color: '#666' }}>
              <ClockCircleOutlined style={{ color: '#faad14', marginRight: 4 }} />
              {stats.masters.available} доступно
            </div>
          </Card>
        </Col>
      </Row>

      {/* Графики */}
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <Card 
            title="Динамика записей" 
            style={{ height: 400 }}
            extra={
              <Tag color="blue">{period} дней</Tag>
            }
          >
            {loading && chartData.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '100px' }}>
                <Spin />
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Line 
                    type="monotone" 
                    dataKey="appointments" 
                    stroke="#1890ff" 
                    name="Всего записей"
                    strokeWidth={2}
                  />
                  <Line 
                    type="monotone" 
                    dataKey="completed" 
                    stroke="#52c41a" 
                    name="Завершено"
                    strokeWidth={2}
                  />
                </LineChart>
              </ResponsiveContainer>
            )}
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card 
            title="Топ услуг" 
            style={{ height: 400 }}
            extra={
              <Tag color="green">По выручке</Tag>
            }
          >
            {loading && servicesData.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '100px' }}>
                <Spin />
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={servicesData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="title" />
                  <YAxis />
                  <Tooltip 
                    formatter={(value, name) => {
                      if (name === 'revenue') return [`${value} ₺`, 'Выручка'];
                      return [value, 'Количество'];
                    }}
                  />
                  <Legend />
                  <Bar dataKey="service_count" fill="#8884d8" name="Количество" />
                  <Bar dataKey="revenue" fill="#82ca9d" name="Выручка" />
                </BarChart>
              </ResponsiveContainer>
            )}
          </Card>
        </Col>
      </Row>

      {/* Таблицы */}
      <Row gutter={[16, 16]} style={{ marginTop: 24 }}>
        <Col xs={24} lg={12}>
          <Card 
            title="Топ мастеров" 
            extra={<Tag color="blue">Загрузка</Tag>}
            loading={loading && mastersData.length === 0}
          >
            <Table
              columns={[
                { 
                  title: 'Мастер', 
                  dataIndex: 'master_name',
                  render: (text) => (
                    <div style={{ display: 'flex', alignItems: 'center' }}>
                      <div style={{ 
                        width: 32, 
                        height: 32, 
                        borderRadius: '50%', 
                        background: '#1890ff',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        color: 'white',
                        marginRight: 8,
                        fontSize: 12
                      }}>
                        {text ? text.charAt(0) : '?'}
                      </div>
                      {text || 'Неизвестный мастер'}
                    </div>
                  )
                },
                { 
                  title: 'Записи', 
                  dataIndex: 'appointment_count',
                  sorter: (a, b) => a.appointment_count - b.appointment_count,
                },
                { 
                  title: 'Завершено', 
                  dataIndex: 'completed',
                  sorter: (a, b) => a.completed - b.completed,
                },
                { 
                  title: 'Загрузка', 
                  dataIndex: 'utilization_percent',
                  render: (value) => (
                    <div>
                      <Progress 
                        percent={value} 
                        size="small" 
                        status={value > 80 ? "active" : "normal"}
                        strokeColor={{
                          '0%': value > 80 ? '#ff4d4f' : value > 50 ? '#faad14' : '#52c41a',
                          '100%': value > 80 ? '#ff7875' : value > 50 ? '#ffc069' : '#95de64',
                        }}
                      />
                      <div style={{ fontSize: 12, color: '#666', marginTop: 4 }}>
                        {value}%
                      </div>
                    </div>
                  ),
                  sorter: (a, b) => a.utilization_percent - b.utilization_percent,
                },
              ]}
              dataSource={mastersData}
              rowKey="master_name"
              pagination={false}
              locale={{
                emptyText: 'Нет данных о мастерах',
              }}
            />
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card 
            title="Распределение услуг" 
            extra={<Tag color="purple">Популярность</Tag>}
            loading={loading && servicesData.length === 0}
          >
            {servicesData.length > 0 ? (
              <>
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie
                      data={servicesData}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      label={(entry) => `${entry.title}: ${entry.service_count}`}
                      outerRadius={80}
                      fill="#8884d8"
                      dataKey="service_count"
                      name="Количество"
                    >
                      {servicesData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip 
                      formatter={(value, name) => [value, name === 'service_count' ? 'Количество' : 'Выручка']}
                    />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
                <div style={{ marginTop: 16 }}>
                  <Table
                    columns={[
                      { title: 'Услуга', dataIndex: 'title' },
                      { 
                        title: 'Количество', 
                        dataIndex: 'service_count',
                        sorter: (a, b) => a.service_count - b.service_count,
                      },
                      { 
                        title: 'Выручка', 
                        dataIndex: 'revenue',
                        render: (value) => `${value.toLocaleString()} ₺`,
                        sorter: (a, b) => a.revenue - b.revenue,
                      },
                    ]}
                    dataSource={servicesData}
                    rowKey="title"
                    pagination={false}
                    size="small"
                  />
                </div>
              </>
            ) : (
              <div style={{ textAlign: 'center', padding: '50px', color: '#999' }}>
                Нет данных об услугах
              </div>
            )}
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default Dashboard;