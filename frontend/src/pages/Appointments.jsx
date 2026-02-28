// Appointments.jsx
import React, { useState, useEffect } from 'react';
import {
  Table,
  Button,
  Modal,
  Form,
  Input,
  Select,
  DatePicker,
  TimePicker,
  Space,
  Tag,
  message,
  Card,
  Row,
  Col,
  Statistic,
  Tooltip,
  Badge,
  Timeline,
  Divider,
  Typography,
  Avatar,
  Popover,
  AutoComplete,
  Spin,
  Tabs,
  Calendar,
  List,
  Dropdown,
  Menu,
  InputNumber,
  Checkbox,
  Radio,
  Switch,
  Progress,
  Empty,
  Alert,
  Drawer,
  Collapse,
  Carousel,
  Image,
  Rate,
  Slider,
  Upload,
  Pagination,
  Result,
  notification
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  CalendarOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ClockCircleOutlined,
  UserOutlined,
  TeamOutlined,
  EyeOutlined,
  ScheduleOutlined,
  UnorderedListOutlined,
  SearchOutlined,
  PhoneOutlined,
  MailOutlined,
  LoadingOutlined,
  ReloadOutlined,
  FilterOutlined,
  ExportOutlined,
  ImportOutlined,
  StarOutlined,
  HeartOutlined,
  SettingOutlined,
  DashboardOutlined,
  TableOutlined,
  AppstoreOutlined,
  OrderedListOutlined,
  SyncOutlined,
  BarChartOutlined,
  PieChartOutlined,
  LineChartOutlined,
  AreaChartOutlined,
  EnvironmentOutlined,
  ShopOutlined,
  CustomerServiceOutlined,
  SafetyCertificateOutlined,
  TrophyOutlined,
  CrownOutlined,
  FireOutlined,
  ThunderboltOutlined,
  RocketOutlined,
  CompassOutlined,
  GlobalOutlined,
  BankOutlined,
  HomeOutlined,
  BuildOutlined,
  ApiOutlined,
  BugOutlined,
  CloudSyncOutlined,
  CloudUploadOutlined,
  CloudDownloadOutlined,
  CloudOutlined,
  CodeOutlined,
  CodepenOutlined,
  CoffeeOutlined,
  ExperimentOutlined,
  FileDoneOutlined,
  FileExcelOutlined,
  FilePdfOutlined,
  FileWordOutlined,
  FileZipOutlined,
  FolderOpenOutlined,
  FolderOutlined,
  GiftOutlined,
  GoldOutlined,
  InsuranceOutlined,
  LikeOutlined,
  LockOutlined,
  MoneyCollectOutlined,
  NotificationOutlined,
  PayCircleOutlined,
  PropertySafetyOutlined,
  ReadOutlined,
  ReconciliationOutlined,
  RedEnvelopeOutlined,
  SafetyOutlined,
  SaveOutlined,
  SecurityScanOutlined,
  SolutionOutlined,
  SoundOutlined,
  StarFilled,
  TabletOutlined,
  TagsOutlined,
  TransactionOutlined,
  UsergroupAddOutlined,
  WalletOutlined,
  WarningOutlined,
  WifiOutlined
} from '@ant-design/icons';
import dayjs from 'dayjs';
import axios from 'axios';
import isBetween from 'dayjs/plugin/isBetween';
import weekday from 'dayjs/plugin/weekday';
import localeData from 'dayjs/plugin/localeData';
import 'dayjs/locale/ru';

// Расширяем dayjs
dayjs.extend(isBetween);
dayjs.extend(weekday);
dayjs.extend(localeData);
dayjs.locale('ru');

const { Option } = Select;
const { Text, Title } = Typography;
const { TabPane } = Tabs;
const { Panel } = Collapse;

const statusColors = {
  pending: 'blue',
  confirmed: 'green',
  cancelled: 'red',
  completed: 'purple',
  no_show: 'orange',
  rescheduled: 'cyan',
  waitlisted: 'gold',
  in_progress: 'processing'
};

const statusLabels = {
  pending: 'Ожидает',
  confirmed: 'Подтверждена',
  cancelled: 'Отменена',
  completed: 'Завершена',
  no_show: 'Неявка',
  rescheduled: 'Перенесена',
  waitlisted: 'В листе ожидания',
  in_progress: 'В процессе'
};

const timeSlots = [
  '09:00', '09:30', '10:00', '10:30', '11:00', '11:30',
  '12:00', '12:30', '13:00', '13:30', '14:00', '14:30',
  '15:00', '15:30', '16:00', '16:30', '17:00', '17:30',
  '18:00', '18:30', '19:00', '19:30', '20:00'
];

const Appointments = () => {
  const [appointments, setAppointments] = useState([]);
  const [masters, setMasters] = useState([]);
  const [clients, setClients] = useState([]);
  const [services, setServices] = useState([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingAppointment, setEditingAppointment] = useState(null);
  const [filters, setFilters] = useState({
    start_date: dayjs().startOf('week'),
    end_date: dayjs().endOf('week'),
    master_id: null,
    status: null,
  });
  const [form] = Form.useForm();
  const [newClientModalVisible, setNewClientModalVisible] = useState(false);
  const [newClientForm] = Form.useForm();
  const [searchClientText, setSearchClientText] = useState('');
  const [filteredClients, setFilteredClients] = useState([]);
  const [loadingClients, setLoadingClients] = useState(false);
  const [clientOptions, setClientOptions] = useState([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [activeView, setActiveView] = useState('table'); // 'table', 'calendar', 'timeline'
  const [selectedDate, setSelectedDate] = useState(dayjs());
  const [calendarDate, setCalendarDate] = useState(dayjs());
  const [selectedMaster, setSelectedMaster] = useState(null);
  const [dailySchedule, setDailySchedule] = useState([]);
  const [weeklySchedule, setWeeklySchedule] = useState([]);
  const [loadingSchedule, setLoadingSchedule] = useState(false);
  const [quickFilters, setQuickFilters] = useState({
    today: false,
    tomorrow: false,
    week: true,
    month: false,
    past: false
  });
  const [appointmentDrawerVisible, setAppointmentDrawerVisible] = useState(false);
  const [selectedAppointment, setSelectedAppointment] = useState(null);
  const [notificationApi, notificationContextHolder] = notification.useNotification();
  const [bulkActions, setBulkActions] = useState([]);
  const [selectedRowKeys, setSelectedRowKeys] = useState([]);
  const [exportLoading, setExportLoading] = useState(false);
  const [importVisible, setImportVisible] = useState(false);
  const [recurringModalVisible, setRecurringModalVisible] = useState(false);
  const [recurringForm] = Form.useForm();
  const [stats, setStats] = useState({
    total: 0,
    confirmed: 0,
    completed: 0,
    pending: 0,
    cancelled: 0,
    revenue: 0,
    averageTime: 0,
    utilizationRate: 0
  });

  // Загрузка всех необходимых данных
  useEffect(() => {
    fetchAllData();
  }, [filters, quickFilters]);

  useEffect(() => {
    if (activeView === 'calendar' && selectedDate) {
      fetchDailySchedule(selectedDate);
    }
  }, [selectedDate, activeView, appointments]);

  useEffect(() => {
    if (activeView === 'timeline' && selectedMaster) {
      fetchWeeklySchedule(selectedMaster);
    }
  }, [selectedMaster, activeView]);

  useEffect(() => {
    calculateStats();
  }, [appointments]);

  const fetchAllData = async () => {
    setLoading(true);
    try {
      await Promise.all([
        fetchAppointments(),
        fetchMasters(),
        fetchClients(),
        fetchServices()
      ]);
    } catch (error) {
      console.error('Error fetching all data:', error);
      message.error('Ошибка при загрузке данных');
    } finally {
      setLoading(false);
    }
  };

  const fetchAppointments = async () => {
    try {
      const params = {};
      if (filters.start_date) params.start_date = filters.start_date.format('YYYY-MM-DD');
      if (filters.end_date) params.end_date = filters.end_date.format('YYYY-MM-DD');
      if (filters.master_id) params.master_id = filters.master_id;
      if (filters.status) params.status = filters.status;

      // Применяем быстрые фильтры
      if (quickFilters.today) {
        params.start_date = dayjs().format('YYYY-MM-DD');
        params.end_date = dayjs().format('YYYY-MM-DD');
      } else if (quickFilters.tomorrow) {
        params.start_date = dayjs().add(1, 'day').format('YYYY-MM-DD');
        params.end_date = dayjs().add(1, 'day').format('YYYY-MM-DD');
      } else if (quickFilters.week) {
        params.start_date = dayjs().startOf('week').format('YYYY-MM-DD');
        params.end_date = dayjs().endOf('week').format('YYYY-MM-DD');
      } else if (quickFilters.month) {
        params.start_date = dayjs().startOf('month').format('YYYY-MM-DD');
        params.end_date = dayjs().endOf('month').format('YYYY-MM-DD');
      } else if (quickFilters.past) {
        params.start_date = dayjs().subtract(1, 'month').format('YYYY-MM-DD');
        params.end_date = dayjs().format('YYYY-MM-DD');
      }

      const response = await axios.get('/appointments', { params });
      setAppointments(response.data.items || response.data || []);
    } catch (error) {
      console.error('Error fetching appointments:', error);
      message.error('Ошибка при загрузке записей');
    }
  };

  const fetchMasters = async () => {
    try {
      const response = await axios.get('/masters');
      setMasters(response.data.items || response.data || []);
      if (response.data.items?.length > 0 && !selectedMaster) {
        setSelectedMaster(response.data.items[0].id);
      }
    } catch (error) {
      console.error('Error fetching masters:', error);
    }
  };

  const fetchClients = async () => {
    try {
      setLoadingClients(true);
      const response = await axios.get('/clients', {
        params: { 
          page: 1,
          per_page: 100,
        }
      });
      
      let clientsData = [];
      if (response.data && response.data.items) {
        clientsData = response.data.items;
      } else if (Array.isArray(response.data)) {
        clientsData = response.data;
      } else if (response.data && Array.isArray(response.data.clients)) {
        clientsData = response.data.clients;
      } else if (response.data && response.data.success && response.data.clients) {
        clientsData = response.data.clients;
      } else if (response.data && response.data.data) {
        clientsData = response.data.data;
      }
      
      setClients(clientsData);
      setFilteredClients(clientsData);
    } catch (error) {
      console.error('Error fetching clients:', error);
      console.error('Error details:', error.response?.data);
      
      if (error.response?.status === 422) {
        try {
          const response = await axios.get('/clients');
          
          let clientsData = [];
          if (response.data && response.data.items) {
            clientsData = response.data.items;
          } else if (Array.isArray(response.data)) {
            clientsData = response.data;
          }
          
          setClients(clientsData);
          setFilteredClients(clientsData);
          message.success('Клиенты загружены');
        } catch (retryError) {
          message.error('Ошибка при загрузке клиентов');
          setClients([]);
          setFilteredClients([]);
        }
      } else {
        message.error('Ошибка при загрузке клиентов');
        setClients([]);
        setFilteredClients([]);
      }
    } finally {
      setLoadingClients(false);
    }
  };

  const fetchServices = async () => {
    try {
      const response = await axios.get('/services');
      setServices(response.data.items || response.data || []);
    } catch (error) {
      console.error('Error fetching services:', error);
    }
  };

  const fetchDailySchedule = (date) => {
    setLoadingSchedule(true);
    try {
      const selectedDay = date.format('YYYY-MM-DD');
      const dayAppointments = appointments.filter(app => 
        app.appointment_date === selectedDay
      );
      
      // Создаем расписание на день
      const schedule = timeSlots.map(timeSlot => {
        const slotDateTime = dayjs(`${selectedDay} ${timeSlot}`);
        const appointmentsInSlot = dayAppointments.filter(app => {
          const appStart = dayjs(`${app.appointment_date} ${app.start_time}`);
          const appEnd = dayjs(`${app.appointment_date} ${app.end_time}`);
          return slotDateTime.isBetween(appStart, appEnd, null, '[)');
        });
        
        return {
          time: timeSlot,
          datetime: slotDateTime,
          appointments: appointmentsInSlot,
          isAvailable: appointmentsInSlot.length === 0,
          isPast: slotDateTime.isBefore(dayjs())
        };
      });
      
      setDailySchedule(schedule);
    } catch (error) {
      console.error('Error fetching daily schedule:', error);
    } finally {
      setLoadingSchedule(false);
    }
  };

  const fetchWeeklySchedule = async (masterId) => {
    setLoadingSchedule(true);
    try {
      // Получаем график работы мастера
      const scheduleResponse = await axios.get(`/schedule/masters/${masterId}`);
      const masterSchedule = scheduleResponse.data;
      
      // Получаем записи мастера на неделю
      const weekStart = dayjs().startOf('week');
      const weekEnd = dayjs().endOf('week');
      
      const masterAppointments = appointments.filter(app => 
        app.master_id === masterId &&
        dayjs(app.appointment_date).isBetween(weekStart, weekEnd, null, '[]')
      );
      
      // Создаем недельное расписание
      const weekly = [];
      for (let i = 0; i < 7; i++) {
        const day = weekStart.add(i, 'day');
        const daySchedule = masterSchedule.find(s => s.day_of_week === day.day());
        const dayAppointments = masterAppointments.filter(app => 
          app.appointment_date === day.format('YYYY-MM-DD')
        );
        
        weekly.push({
          day: day.format('dddd, DD.MM.YYYY'),
          date: day.format('YYYY-MM-DD'),
          schedule: daySchedule,
          appointments: dayAppointments,
          isWorkDay: !!daySchedule
        });
      }
      
      setWeeklySchedule(weekly);
    } catch (error) {
      console.error('Error fetching weekly schedule:', error);
    } finally {
      setLoadingSchedule(false);
    }
  };

  const handleSubmit = async (values) => {
    setIsSubmitting(true);
    try {
      // ВАЖНО: Преобразуем данные в точном формате, который ожидает API
      const formattedData = {
        client_id: parseInt(values.client_id),
        master_id: values.master_id ? parseInt(values.master_id) : null,
        appointment_date: values.appointment_date.format('YYYY-MM-DD'),
        start_time: values.start_time.format('HH:mm'),
        services: Array.isArray(values.services) ? values.services.map(s => parseInt(s)) : [],
        status: values.status || 'pending'
      };

      console.log("Отправляемые данные записи:", formattedData);

      if (editingAppointment) {
        const updateData = {
          master_id: formattedData.master_id,
          appointment_date: formattedData.appointment_date,
          start_time: formattedData.start_time,
          status: formattedData.status
        };
        
        await axios.put(`/appointments/${editingAppointment.id}`, updateData);
        
        // Обновляем услуги отдельно
        if (formattedData.services.length > 0) {
          // Сначала удаляем старые услуги
          await axios.delete(`/appointments/${editingAppointment.id}/services`);
          
          // Добавляем новые услуги
          for (const serviceId of formattedData.services) {
            await axios.post(`/appointments/${editingAppointment.id}/services`, {
              service_id: serviceId
            });
          }
        }
        
        message.success('Запись обновлена');
      } else {
        const response = await axios.post('/appointments', formattedData);
        console.log("Ответ сервера:", response.data);
        message.success('Запись создана');
      }
      
      setModalVisible(false);
      form.resetFields();
      fetchAppointments();
    } catch (error) {
      console.error('Error saving appointment:', error);
      console.error('Error response:', error.response?.data);
      message.error(`Ошибка при сохранении записи: ${error.response?.data?.detail || error.message}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCreateNewClient = async (values) => {
    setIsSubmitting(true);
    try {
      const clientData = {
        first_name: values.first_name?.trim() || '',
        last_name: values.last_name?.trim() || '',
        phone: values.phone?.trim() || '',
        email: values.email?.trim() || '',
      };

      if (!clientData.first_name) {
        message.error('Имя обязательно для заполнения');
        return;
      }

      if (!clientData.phone) {
        message.error('Телефон обязателен для заполнения');
        return;
      }

      console.log('Отправка данных клиента:', clientData);
      
      let response;
      try {
        response = await axios.post('/clients', clientData);
      } catch (firstError) {
        if (firstError.response?.status === 422 || firstError.response?.status === 400) {
          response = await axios.post('/clients', 
            JSON.stringify(clientData),
            {
              headers: {
                'Content-Type': 'application/json',
              }
            }
          );
        } else {
          throw firstError;
        }
      }
      
      console.log('Ответ при создании клиента:', response.data);
      
      if (response.data && (response.data.id || response.data.client_id || response.data.success)) {
        message.success('Клиент успешно создан');
        setNewClientModalVisible(false);
        newClientForm.resetFields();
        
        await fetchClients();
        
        if (response.data.id) {
          form.setFieldsValue({ client_id: response.data.id });
        } else if (response.data.client_id) {
          form.setFieldsValue({ client_id: response.data.client_id });
        } else if (response.data.client && response.data.client.id) {
          form.setFieldsValue({ client_id: response.data.client.id });
        }
        
      } else {
        message.error('Не удалось получить ID нового клиента');
      }
    } catch (error) {
      console.error('Error creating client:', error);
      console.error('Error response:', error.response?.data);
      
      if (error.response?.status === 400) {
        message.error(error.response.data.detail || 'Ошибка валидации данных');
      } else if (error.response?.status === 409) {
        message.error('Клиент с таким телефоном или email уже существует');
      } else if (error.response?.status === 422) {
        const errors = error.response.data.detail;
        if (Array.isArray(errors)) {
          const errorMessages = errors.map(err => {
            if (err.loc && err.msg) {
              return `${err.loc[err.loc.length - 1]}: ${err.msg}`;
            }
            return err.msg || 'Ошибка валидации';
          });
          message.error(errorMessages.join(', '));
        } else if (errors && typeof errors === 'object') {
          const errorMessages = Object.values(errors).flat();
          message.error(errorMessages.join(', '));
        } else if (typeof errors === 'string') {
          message.error(errors);
        } else {
          message.error('Некорректные данные');
        }
      } else {
        message.error(`Ошибка при сохранении: ${error.response?.data?.detail || error.message}`);
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleStatusChange = async (id, newStatus) => {
    try {
      await axios.put(`/appointments/${id}/status`, null, {
        params: { status: newStatus }
      });
      message.success(`Статус изменен на: ${statusLabels[newStatus]}`);
      fetchAppointments();
    } catch (error) {
      message.error('Ошибка при изменении статуса');
    }
  };

  const handleEdit = (record) => {
    setEditingAppointment(record);
    form.setFieldsValue({
      client_id: record.client_id,
      master_id: record.master_id,
      appointment_date: dayjs(record.appointment_date),
      start_time: dayjs(record.start_time, 'HH:mm'),
      services: record.services?.map(s => s.id) || [],
      status: record.status,
    });
    setModalVisible(true);
  };

  const handleDelete = async (id) => {
    Modal.confirm({
      title: 'Удалить запись?',
      content: 'Вы уверены, что хотите удалить эту запись?',
      okText: 'Да, удалить',
      okType: 'danger',
      cancelText: 'Отмена',
      onOk: async () => {
        try {
          await axios.delete(`/appointments/${id}`);
          message.success('Запись удалена');
          fetchAppointments();
        } catch (error) {
          message.error('Ошибка при удалении');
        }
      },
    });
  };

  const handleQuickFilter = (filter) => {
    setQuickFilters({
      today: filter === 'today',
      tomorrow: filter === 'tomorrow',
      week: filter === 'week',
      month: filter === 'month',
      past: filter === 'past'
    });
  };

  const handleCalendarSelect = (value) => {
    setSelectedDate(value);
    if (activeView === 'calendar') {
      fetchDailySchedule(value);
    }
  };

  const calculateStats = () => {
    const total = appointments.length;
    const confirmed = appointments.filter(a => a.status === 'confirmed').length;
    const completed = appointments.filter(a => a.status === 'completed').length;
    const pending = appointments.filter(a => a.status === 'pending').length;
    const cancelled = appointments.filter(a => a.status === 'cancelled').length;
    
    // Рассчитываем выручку
    const revenue = appointments
      .filter(a => a.status === 'completed')
      .reduce((sum, app) => {
        const servicesTotal = app.services?.reduce((s, service) => s + (service.price || 0), 0) || 0;
        return sum + servicesTotal;
      }, 0);
    
    // Рассчитываем среднее время услуг
    const totalDuration = appointments.reduce((sum, app) => {
      const duration = app.services?.reduce((s, service) => s + (service.duration_minutes || 0), 0) || 0;
      return sum + duration;
    }, 0);
    const averageTime = total > 0 ? Math.round(totalDuration / total) : 0;
    
    // Рассчитываем коэффициент использования (пример)
    const workHoursPerDay = 8;
    const totalPossibleSlots = appointments.length > 0 ? appointments.length * workHoursPerDay * 60 : 1;
    const utilizationRate = Math.round((totalDuration / totalPossibleSlots) * 100);
    
    setStats({
      total,
      confirmed,
      completed,
      pending,
      cancelled,
      revenue,
      averageTime,
      utilizationRate
    });
  };

  const renderCalendarCell = (date) => {
    const dateStr = date.format('YYYY-MM-DD');
    const dayAppointments = appointments.filter(app => app.appointment_date === dateStr);
    
    if (dayAppointments.length === 0) {
      return null;
    }
    
    return (
      <div style={{ padding: '2px' }}>
        {dayAppointments.slice(0, 3).map(app => (
          <div key={app.id} style={{ marginBottom: 2 }}>
            <Badge 
              status={statusColors[app.status] || 'default'} 
              text={
                <span style={{ fontSize: '10px' }}>
                  {app.start_time}
                </span>
              } 
            />
          </div>
        ))}
        {dayAppointments.length > 3 && (
          <div style={{ fontSize: '10px', color: '#666' }}>
            +{dayAppointments.length - 3} ещё
          </div>
        )}
      </div>
    );
  };

  const renderDailySchedule = () => {
    return (
      <div style={{ padding: '20px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <Title level={4}>
            <CalendarOutlined /> Расписание на {selectedDate.format('DD.MM.YYYY dddd')}
          </Title>
          <Space>
            <Button onClick={() => setSelectedDate(selectedDate.subtract(1, 'day'))}>
              ← Предыдущий день
            </Button>
            <Button type="primary" onClick={() => setSelectedDate(dayjs())}>
              Сегодня
            </Button>
            <Button onClick={() => setSelectedDate(selectedDate.add(1, 'day'))}>
              Следующий день →
            </Button>
          </Space>
        </div>
        
        {loadingSchedule ? (
          <div style={{ textAlign: 'center', padding: '40px' }}>
            <Spin size="large" />
            <div style={{ marginTop: '10px' }}>Загрузка расписания...</div>
          </div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '16px' }}>
            {dailySchedule.map(slot => (
              <Card 
                key={slot.time}
                size="small"
                style={{
                  borderColor: slot.isPast ? '#f0f0f0' : 
                              slot.appointments.length > 0 ? '#ff4d4f' : '#52c41a',
                  backgroundColor: slot.isPast ? '#fafafa' : 
                                  slot.appointments.length > 0 ? '#fff1f0' : '#f6ffed'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <Text strong style={{ fontSize: '16px' }}>{slot.time}</Text>
                    {slot.isPast && <Text type="secondary"> (прошло)</Text>}
                  </div>
                  <Tag color={slot.appointments.length > 0 ? 'red' : 'green'}>
                    {slot.appointments.length > 0 ? 'Занято' : 'Свободно'}
                  </Tag>
                </div>
                
                {slot.appointments.length > 0 && (
                  <div style={{ marginTop: '10px' }}>
                    {slot.appointments.map(app => (
                      <Card 
                        key={app.id}
                        size="small" 
                        style={{ 
                          marginBottom: '8px',
                          borderLeft: `4px solid ${statusColors[app.status] || '#1890ff'}`,
                          cursor: 'pointer'
                        }}
                        onClick={() => {
                          setSelectedAppointment(app);
                          setAppointmentDrawerVisible(true);
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                          <div>
                            <Text strong>
                              {app.client_first_name} {app.client_last_name}
                            </Text>
                            <div style={{ fontSize: '12px', color: '#666' }}>
                              Мастер: {app.master_first_name} {app.master_last_name}
                            </div>
                            <div style={{ fontSize: '12px', color: '#666' }}>
                              Услуг: {app.services?.length || 0}
                            </div>
                          </div>
                          <Tag color={statusColors[app.status]} style={{ marginLeft: '8px' }}>
                            {statusLabels[app.status]}
                          </Tag>
                        </div>
                      </Card>
                    ))}
                  </div>
                )}
                
                {slot.appointments.length === 0 && !slot.isPast && (
                  <div style={{ marginTop: '10px', textAlign: 'center' }}>
                    <Button 
                      type="dashed" 
                      size="small" 
                      icon={<PlusOutlined />}
                      onClick={() => {
                        setEditingAppointment(null);
                        form.resetFields();
                        form.setFieldsValue({
                          appointment_date: selectedDate,
                          start_time: dayjs(slot.time, 'HH:mm'),
                          status: 'pending',
                        });
                        setModalVisible(true);
                      }}
                    >
                      Забронировать это время
                    </Button>
                  </div>
                )}
              </Card>
            ))}
          </div>
        )}
      </div>
    );
  };

  const renderTimelineView = () => {
    return (
      <div style={{ padding: '20px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <Title level={4}>
            <ScheduleOutlined /> Расписание мастеров
          </Title>
          <Select
            style={{ width: '200px' }}
            placeholder="Выберите мастера"
            value={selectedMaster}
            onChange={setSelectedMaster}
          >
            {masters.map(master => (
              <Option key={master.id} value={master.id}>
                {master.first_name} {master.last_name}
              </Option>
            ))}
          </Select>
        </div>
        
        {loadingSchedule ? (
          <div style={{ textAlign: 'center', padding: '40px' }}>
            <Spin size="large" />
            <div style={{ marginTop: '10px' }}>Загрузка расписания...</div>
          </div>
        ) : (
          <Row gutter={[16, 16]}>
            {weeklySchedule.map(day => (
              <Col span={24} key={day.date}>
                <Card 
                  title={
                    <Space>
                      <CalendarOutlined />
                      {day.day}
                      {day.schedule && (
                        <Text type="secondary">
                          ({day.schedule.start_time} - {day.schedule.end_time})
                        </Text>
                      )}
                    </Space>
                  }
                  extra={
                    <Tag color={day.isWorkDay ? 'green' : 'red'}>
                      {day.isWorkDay ? 'Рабочий день' : 'Выходной'}
                    </Tag>
                  }
                >
                  {day.isWorkDay ? (
                    day.appointments.length > 0 ? (
                      <Timeline>
                        {day.appointments.map(app => (
                          <Timeline.Item 
                            key={app.id}
                            color={statusColors[app.status]}
                            dot={<ClockCircleOutlined />}
                          >
                            <Card 
                              size="small"
                              style={{ 
                                borderLeft: `3px solid ${statusColors[app.status]}`,
                                cursor: 'pointer'
                              }}
                              onClick={() => {
                                setSelectedAppointment(app);
                                setAppointmentDrawerVisible(true);
                              }}
                            >
                              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <div>
                                  <Text strong>
                                    {app.start_time} - {app.end_time}
                                  </Text>
                                  <div style={{ marginTop: '4px' }}>
                                    <Avatar 
                                      size="small" 
                                      icon={<UserOutlined />}
                                      style={{ backgroundColor: '#1890ff', marginRight: '8px' }}
                                    />
                                    <Text>
                                      {app.client_first_name} {app.client_last_name}
                                    </Text>
                                  </div>
                                  <div style={{ marginTop: '4px', fontSize: '12px' }}>
                                    {app.services?.map(s => s.title).join(', ')}
                                  </div>
                                </div>
                                <Space>
                                  <Tag color={statusColors[app.status]}>
                                    {statusLabels[app.status]}
                                  </Tag>
                                  <Button
                                    size="small"
                                    icon={<EditOutlined />}
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      handleEdit(app);
                                    }}
                                  />
                                </Space>
                              </div>
                            </Card>
                          </Timeline.Item>
                        ))}
                      </Timeline>
                    ) : (
                      <Empty 
                        description="Нет записей на этот день"
                        image={Empty.PRESENTED_IMAGE_SIMPLE}
                      >
                        <Button 
                          type="primary"
                          icon={<PlusOutlined />}
                          onClick={() => {
                            setEditingAppointment(null);
                            form.resetFields();
                            form.setFieldsValue({
                              master_id: selectedMaster,
                              appointment_date: dayjs(day.date),
                              status: 'pending',
                              start_time: dayjs('09:00', 'HH:mm')
                            });
                            setModalVisible(true);
                          }}
                        >
                          Создать запись
                        </Button>
                      </Empty>
                    )
                  ) : (
                    <Empty 
                      description="Выходной день"
                      image={<CloseCircleOutlined style={{ fontSize: '48px', color: '#ff4d4f' }} />}
                    />
                  )}
                </Card>
              </Col>
            ))}
          </Row>
        )}
      </div>
    );
  };

  const renderAppointmentDrawer = () => {
    if (!selectedAppointment) return null;
    
    const totalPrice = selectedAppointment.services?.reduce((sum, s) => sum + (s.price || 0), 0) || 0;
    const totalDuration = selectedAppointment.services?.reduce((sum, s) => sum + (s.duration_minutes || 0), 0) || 0;
    
    return (
      <Drawer
        title="Детали записи"
        placement="right"
        onClose={() => setAppointmentDrawerVisible(false)}
        open={appointmentDrawerVisible}
        width={500}
        extra={
          <Space>
            <Button 
              icon={<EditOutlined />} 
              onClick={() => {
                handleEdit(selectedAppointment);
                setAppointmentDrawerVisible(false);
              }}
            >
              Редактировать
            </Button>
            <Button 
              danger 
              icon={<DeleteOutlined />}
              onClick={() => {
                setAppointmentDrawerVisible(false);
                handleDelete(selectedAppointment.id);
              }}
            >
              Удалить
            </Button>
          </Space>
        }
      >
        <div style={{ marginBottom: '24px' }}>
          <Title level={5} style={{ marginBottom: '16px' }}>
            <UserOutlined /> Клиент
          </Title>
          <Card size="small">
            <div style={{ display: 'flex', alignItems: 'center', marginBottom: '12px' }}>
              <Avatar 
                size="large" 
                icon={<UserOutlined />}
                style={{ backgroundColor: '#1890ff', marginRight: '12px' }}
              />
              <div>
                <Text strong style={{ fontSize: '16px' }}>
                  {selectedAppointment.client_first_name} {selectedAppointment.client_last_name}
                </Text>
                {selectedAppointment.phone && (
                  <div style={{ marginTop: '4px' }}>
                    <PhoneOutlined style={{ marginRight: '8px' }} />
                    <Text copyable>{selectedAppointment.phone}</Text>
                  </div>
                )}
              </div>
            </div>
          </Card>
        </div>
        
        <div style={{ marginBottom: '24px' }}>
          <Title level={5} style={{ marginBottom: '16px' }}>
            <TeamOutlined /> Мастер
          </Title>
          <Card size="small">
            <div style={{ display: 'flex', alignItems: 'center' }}>
              <Avatar 
                size="large" 
                icon={<TeamOutlined />}
                style={{ backgroundColor: '#52c41a', marginRight: '12px' }}
              />
              <div>
                <Text strong style={{ fontSize: '16px' }}>
                  {selectedAppointment.master_first_name} {selectedAppointment.master_last_name}
                </Text>
                {selectedAppointment.qualification && (
                  <div style={{ marginTop: '4px', color: '#666' }}>
                    {selectedAppointment.qualification}
                  </div>
                )}
              </div>
            </div>
          </Card>
        </div>
        
        <div style={{ marginBottom: '24px' }}>
          <Title level={5} style={{ marginBottom: '16px' }}>
            <CalendarOutlined /> Время и дата
          </Title>
          <Card size="small">
            <Row gutter={[16, 16]}>
              <Col span={12}>
                <Statistic
                  title="Дата"
                  value={dayjs(selectedAppointment.appointment_date).format('DD.MM.YYYY')}
                  prefix={<CalendarOutlined />}
                />
              </Col>
              <Col span={12}>
                <Statistic
                  title="Время"
                  value={`${selectedAppointment.start_time} - ${selectedAppointment.end_time}`}
                  prefix={<ClockCircleOutlined />}
                />
              </Col>
              <Col span={24}>
                <Divider style={{ margin: '8px 0' }} />
                <Statistic
                  title="Длительность"
                  value={totalDuration}
                  suffix="минут"
                />
              </Col>
            </Row>
          </Card>
        </div>
        
        <div style={{ marginBottom: '24px' }}>
          <Title level={5} style={{ marginBottom: '16px' }}>
            <UnorderedListOutlined /> Услуги
          </Title>
          <Card size="small">
            <List
              dataSource={selectedAppointment.services || []}
              renderItem={service => (
                <List.Item>
                  <List.Item.Meta
                    title={service.title}
                    description={`${service.duration_minutes} мин • ${service.price} ₺`}
                  />
                </List.Item>
              )}
            />
            <Divider style={{ margin: '12px 0' }} />
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <Text strong>Итого:</Text>
              <Text strong type="success" style={{ fontSize: '18px' }}>
                {totalPrice} ₺
              </Text>
            </div>
          </Card>
        </div>
        
        <div style={{ marginBottom: '24px' }}>
          <Title level={5} style={{ marginBottom: '16px' }}>
            <SafetyCertificateOutlined /> Статус
          </Title>
          <Card size="small">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Tag color={statusColors[selectedAppointment.status]} style={{ fontSize: '14px', padding: '6px 12px' }}>
                {statusLabels[selectedAppointment.status]}
              </Tag>
              <Select
                value={selectedAppointment.status}
                style={{ width: '150px' }}
                onChange={(value) => {
                  handleStatusChange(selectedAppointment.id, value);
                  setAppointmentDrawerVisible(false);
                }}
              >
                <Option value="pending">Ожидает</Option>
                <Option value="confirmed">Подтверждена</Option>
                <Option value="in_progress">В процессе</Option>
                <Option value="completed">Завершена</Option>
                <Option value="cancelled">Отменена</Option>
                <Option value="no_show">Неявка</Option>
              </Select>
            </div>
          </Card>
        </div>
        
        <div>
          <Title level={5} style={{ marginBottom: '16px' }}>
            <SolutionOutlined /> Дополнительная информация
          </Title>
          <Card size="small">
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
              <Text type="secondary">ID записи:</Text>
              <Text copyable>{selectedAppointment.id}</Text>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
              <Text type="secondary">Создана:</Text>
              <Text>{dayjs(selectedAppointment.created_at).format('DD.MM.YYYY HH:mm')}</Text>
            </div>
          </Card>
        </div>
      </Drawer>
    );
  };

  const columns = [
    {
      title: 'Клиент',
      key: 'client',
      width: 200,
      render: (record) => {
        const clientName = record.client_first_name && record.client_last_name 
          ? `${record.client_first_name} ${record.client_last_name}`
          : 'Не указан';
        
        return (
          <div style={{ display: 'flex', alignItems: 'center' }}>
            <Avatar 
              size="small" 
              style={{ backgroundColor: '#1890ff', marginRight: 8 }}
              icon={<UserOutlined />}
            />
            <div>
              <div style={{ fontWeight: 500 }}>
                {clientName}
              </div>
              {record.phone && (
                <div style={{ fontSize: '12px', color: '#666' }}>
                  <PhoneOutlined /> {record.phone}
                </div>
              )}
            </div>
          </div>
        );
      },
    },
    {
      title: 'Мастер',
      key: 'master',
      width: 150,
      render: (record) => (
        <div style={{ display: 'flex', alignItems: 'center' }}>
          <Avatar 
            size="small" 
            style={{ backgroundColor: '#52c41a', marginRight: 8 }}
            icon={<TeamOutlined />}
          />
          <div>
            {record.master_first_name} {record.master_last_name}
          </div>
        </div>
      ),
    },
    {
      title: 'Дата и время',
      key: 'datetime',
      width: 150,
      render: (record) => (
        <div>
          <div>
            <CalendarOutlined style={{ marginRight: 4 }} />
            {dayjs(record.appointment_date).format('DD.MM.YYYY')}
          </div>
          <div style={{ fontSize: '12px', color: '#666' }}>
            <ClockCircleOutlined style={{ marginRight: 4 }} />
            {record.start_time} - {record.end_time}
          </div>
        </div>
      ),
    },
    {
      title: 'Услуги',
      key: 'services',
      width: 200,
      render: (record) => {
        const totalPrice = record.services?.reduce((sum, s) => sum + (s.price || 0), 0) || 0;
        const totalDuration = record.services?.reduce((sum, s) => sum + (s.duration_minutes || 0), 0) || 0;
        
        return (
          <Popover
            title="Услуги"
            content={
              <div style={{ maxWidth: 300 }}>
                {record.services?.map(service => (
                  <div key={service.id} style={{ marginBottom: 4 }}>
                    <div style={{ fontWeight: 500 }}>{service.title}</div>
                    <div style={{ fontSize: '12px', color: '#666' }}>
                      {service.price} ₺ • {service.duration_minutes} мин
                    </div>
                  </div>
                ))}
                <Divider style={{ margin: '8px 0' }} />
                <div style={{ fontWeight: 'bold' }}>
                  Итого: {totalPrice} ₺ • {totalDuration} мин
                </div>
              </div>
            }
          >
            <div style={{ cursor: 'pointer' }}>
              <UnorderedListOutlined style={{ marginRight: 4 }} />
              {record.services?.length || 0} услуг
              <div style={{ fontSize: '12px', color: '#666' }}>
                {totalPrice} ₺ • {totalDuration} мин
              </div>
            </div>
          </Popover>
        );
      },
    },
    {
      title: 'Статус',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (status) => (
        <Tag color={statusColors[status]}>
          {statusLabels[status]}
        </Tag>
      ),
    },
    {
      title: 'Действия',
      key: 'actions',
      fixed: 'right',
      width: 180,
      render: (_, record) => (
        <Space>
          <Select
            value={record.status}
            style={{ width: 120 }}
            onChange={(value) => handleStatusChange(record.id, value)}
            size="small"
          >
            <Option value="pending">Ожидает</Option>
            <Option value="confirmed">Подтверждена</Option>
            <Option value="in_progress">В процессе</Option>
            <Option value="completed">Завершена</Option>
            <Option value="cancelled">Отменена</Option>
            <Option value="no_show">Неявка</Option>
          </Select>
          <Tooltip title="Редактировать">
            <Button
              type="text"
              size="small"
              icon={<EditOutlined />}
              onClick={() => handleEdit(record)}
            />
          </Tooltip>
          <Tooltip title="Просмотреть">
            <Button
              type="text"
              size="small"
              icon={<EyeOutlined />}
              onClick={() => {
                setSelectedAppointment(record);
                setAppointmentDrawerVisible(true);
              }}
            />
          </Tooltip>
        </Space>
      ),
    },
  ];

  return (
    <div>
      {notificationContextHolder}
      
      {/* Статистика */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={3}>
          <Card size="small" hoverable>
            <Statistic
              title="Всего записей"
              value={stats.total}
              prefix={<CalendarOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col span={3}>
          <Card size="small" hoverable>
            <Statistic
              title="Подтверждено"
              value={stats.confirmed}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#3f8600' }}
            />
          </Card>
        </Col>
        <Col span={3}>
          <Card size="small" hoverable>
            <Statistic
              title="Ожидает"
              value={stats.pending}
              prefix={<ClockCircleOutlined />}
              valueStyle={{ color: '#fa8c16' }}
            />
          </Card>
        </Col>
        <Col span={3}>
          <Card size="small" hoverable>
            <Statistic
              title="Завершено"
              value={stats.completed}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#722ed1' }}
            />
          </Card>
        </Col>
        <Col span={3}>
          <Card size="small" hoverable>
            <Statistic
              title="Выручка"
              value={stats.revenue}
              prefix={<MoneyCollectOutlined />}
              valueStyle={{ color: '#13c2c2' }}
              suffix="₺"
            />
          </Card>
        </Col>
        <Col span={3}>
          <Card size="small" hoverable>
            <Statistic
              title="Ср. время"
              value={stats.averageTime}
              prefix={<ClockCircleOutlined />}
              valueStyle={{ color: '#eb2f96' }}
              suffix="мин"
            />
          </Card>
        </Col>
        <Col span={3}>
          <Card size="small" hoverable>
            <Progress
              type="dashboard"
              percent={stats.utilizationRate}
              strokeColor={{
                '0%': '#108ee9',
                '100%': '#87d068',
              }}
              format={percent => `${percent}%`}
              width={80}
            />
            <div style={{ textAlign: 'center', marginTop: '8px', fontSize: '12px' }}>
              Загруженность
            </div>
          </Card>
        </Col>
        <Col span={3}>
          <Card size="small" hoverable>
            <Button
              type="primary"
              onClick={fetchAllData}
              icon={<SyncOutlined spin={loading} />}
              style={{ width: '100%', height: '100%' }}
            >
              Обновить
            </Button>
          </Card>
        </Col>
      </Row>

      {/* Быстрые фильтры */}
      <Card size="small" style={{ marginBottom: 16 }}>
        <Space wrap>
          <Button
            type={quickFilters.today ? 'primary' : 'default'}
            icon={<CalendarOutlined />}
            onClick={() => handleQuickFilter('today')}
          >
            Сегодня
          </Button>
          <Button
            type={quickFilters.tomorrow ? 'primary' : 'default'}
            icon={<CalendarOutlined />}
            onClick={() => handleQuickFilter('tomorrow')}
          >
            Завтра
          </Button>
          <Button
            type={quickFilters.week ? 'primary' : 'default'}
            icon={<CalendarOutlined />}
            onClick={() => handleQuickFilter('week')}
          >
            Эта неделя
          </Button>
          <Button
            type={quickFilters.month ? 'primary' : 'default'}
            icon={<CalendarOutlined />}
            onClick={() => handleQuickFilter('month')}
          >
            Этот месяц
          </Button>
          <Button
            type={quickFilters.past ? 'primary' : 'default'}
            icon={<CalendarOutlined />}
            onClick={() => handleQuickFilter('past')}
          >
            Прошедшие
          </Button>
          <Divider type="vertical" />
          <Select
            placeholder="Статус"
            style={{ width: 120 }}
            allowClear
            onChange={(value) => setFilters({ ...filters, status: value })}
          >
            <Option value="pending">Ожидает</Option>
            <Option value="confirmed">Подтверждена</Option>
            <Option value="in_progress">В процессе</Option>
            <Option value="completed">Завершена</Option>
            <Option value="cancelled">Отменена</Option>
            <Option value="no_show">Неявка</Option>
          </Select>
          <Select
            placeholder="Мастер"
            style={{ width: 150 }}
            allowClear
            onChange={(value) => setFilters({ ...filters, master_id: value })}
          >
            {masters.map(master => (
              <Option key={master.id} value={master.id}>
                {master.first_name} {master.last_name}
              </Option>
            ))}
          </Select>
        </Space>
      </Card>

      {/* Основной контент */}
      <Card
        title={
          <Space>
            <ScheduleOutlined />
            Записи на услуги
            <Badge count={appointments.length} showZero style={{ backgroundColor: '#52c41a' }} />
          </Space>
        }
        extra={
          <Space>
            <Radio.Group 
              value={activeView} 
              onChange={(e) => setActiveView(e.target.value)}
              buttonStyle="solid"
            >
              <Radio.Button value="table">
                <TableOutlined /> Таблица
              </Radio.Button>
              <Radio.Button value="calendar">
                <CalendarOutlined /> Календарь
              </Radio.Button>
              <Radio.Button value="timeline">
                <ScheduleOutlined /> Расписание
              </Radio.Button>
            </Radio.Group>
            <Divider type="vertical" />
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => {
                setEditingAppointment(null);
                form.resetFields();
                form.setFieldsValue({
                  status: 'pending',
                  appointment_date: dayjs(),
                  start_time: dayjs().add(1, 'hour').startOf('hour'),
                });
                setModalVisible(true);
              }}
              disabled={loadingClients}
            >
              Новая запись
            </Button>
          </Space>
        }
      >
        {activeView === 'table' && (
          <>
            <Table
              columns={columns}
              dataSource={appointments}
              rowKey="id"
              loading={loading}
              pagination={{
                pageSize: 10,
                showSizeChanger: true,
                showQuickJumper: true,
                showTotal: (total, range) => `${range[0]}-${range[1]} из ${total} записей`
              }}
              scroll={{ x: 1200 }}
              rowSelection={{
                selectedRowKeys,
                onChange: setSelectedRowKeys,
              }}
            />
          </>
        )}

        {activeView === 'calendar' && (
          <>
            <Row gutter={[16, 16]}>
              <Col span={8}>
                <Card size="small" title="Календарь">
                  <Calendar
                    value={selectedDate}
                    onChange={handleCalendarSelect}
                    onSelect={handleCalendarSelect}
                    dateCellRender={renderCalendarCell}
                    headerRender={({ value, onChange }) => {
                      const current = value;
                      const localeData = value.localeData();
                      const months = [];
                      for (let i = 0; i < 12; i++) {
                        months.push(localeData.monthsShort(current.month(i)));
                      }
                      
                      const year = current.year();
                      const month = current.month();
                      
                      return (
                        <div style={{ padding: 8, textAlign: 'center' }}>
                          <Space>
                            <Select
                              size="small"
                              value={month}
                              onChange={(newMonth) => {
                                const now = current.clone().month(newMonth);
                                onChange(now);
                              }}
                            >
                              {months.map((monthName, index) => (
                                <Option key={monthName} value={index}>
                                  {monthName}
                                </Option>
                              ))}
                            </Select>
                            <Select
                              size="small"
                              value={year}
                              onChange={(newYear) => {
                                const now = current.clone().year(newYear);
                                onChange(now);
                              }}
                            >
                              {Array.from({ length: 10 }, (_, i) => year - 5 + i).map((y) => (
                                <Option key={y} value={y}>
                                  {y}
                                </Option>
                              ))}
                            </Select>
                          </Space>
                        </div>
                      );
                    }}
                  />
                </Card>
              </Col>
              <Col span={16}>
                {renderDailySchedule()}
              </Col>
            </Row>
          </>
        )}

        {activeView === 'timeline' && (
          renderTimelineView()
        )}
      </Card>

      {/* Модальное окно создания/редактирования записи */}
      <Modal
        title={
          <Space>
            {editingAppointment ? (
              <>
                <EditOutlined />
                Редактировать запись #{editingAppointment?.id}
              </>
            ) : (
              <>
                <PlusOutlined />
                Новая запись
              </>
            )}
          </Space>
        }
        open={modalVisible}
        onCancel={() => {
          setModalVisible(false);
          form.resetFields();
          setEditingAppointment(null);
        }}
        footer={null}
        width={700}
        destroyOnClose
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
          initialValues={{
            status: 'pending',
            appointment_date: dayjs(),
            start_time: dayjs().add(1, 'hour').startOf('hour'),
          }}
        >
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="client_id"
                label={
                  <Space>
                    <UserOutlined />
                    <span>Клиент</span>
                  </Space>
                }
                rules={[{ required: true, message: 'Выберите клиента' }]}
                extra={
                  <Button 
                    type="link" 
                    size="small" 
                    onClick={() => setNewClientModalVisible(true)}
                    style={{ padding: 0, marginTop: 4 }}
                    icon={<PlusOutlined />}
                  >
                    Добавить нового клиента
                  </Button>
                }
              >
                <Select
                  placeholder="Выберите клиента"
                  showSearch
                  optionFilterProp="children"
                  filterOption={(input, option) =>
                    (option?.children?.toLowerCase() || '').includes(input.toLowerCase())
                  }
                  loading={loadingClients}
                  notFoundContent={
                    <div style={{ textAlign: 'center', padding: 8 }}>
                      {loadingClients ? (
                        <Spin size="small" />
                      ) : (
                        <Button 
                          type="link" 
                          onClick={() => setNewClientModalVisible(true)}
                          icon={<PlusOutlined />}
                        >
                          Добавить нового клиента
                        </Button>
                      )}
                    </div>
                  }
                >
                  {clients.map(client => (
                    <Option key={client.id} value={client.id}>
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <span>{client.first_name} {client.last_name || ''}</span>
                        <span style={{ color: '#666', fontSize: '12px' }}>
                          {client.phone || 'без телефона'}
                        </span>
                      </div>
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="master_id"
                label={
                  <Space>
                    <TeamOutlined />
                    <span>Мастер</span>
                  </Space>
                }
                rules={[{ required: true, message: 'Выберите мастера' }]}
              >
                <Select
                  placeholder="Выберите мастера"
                  showSearch
                  optionFilterProp="children"
                >
                  {masters.map(master => (
                    <Option key={master.id} value={master.id}>
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <span>{master.first_name} {master.last_name}</span>
                        {master.qualification && (
                          <span style={{ color: '#666', fontSize: '12px' }}>
                            {master.qualification}
                          </span>
                        )}
                      </div>
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="appointment_date"
                label={
                  <Space>
                    <CalendarOutlined />
                    <span>Дата</span>
                  </Space>
                }
                rules={[{ required: true, message: 'Выберите дату' }]}
              >
                <DatePicker 
                  style={{ width: '100%' }} 
                  disabledDate={(current) => current && current < dayjs().startOf('day')}
                  format="DD.MM.YYYY"
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="start_time"
                label={
                  <Space>
                    <ClockCircleOutlined />
                    <span>Время начала</span>
                  </Space>
                }
                rules={[{ required: true, message: 'Выберите время' }]}
              >
                <TimePicker 
                  format="HH:mm" 
                  style={{ width: '100%' }}
                  minuteStep={30}
                  showNow={false}
                  placeholder="Выберите время"
                />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="services"
            label={
              <Space>
                <UnorderedListOutlined />
                <span>Услуги</span>
              </Space>
            }
            rules={[{ required: true, message: 'Выберите хотя бы одну услугу' }]}
          >
            <Select
              mode="multiple"
              placeholder="Выберите услуги"
              style={{ width: '100%' }}
              optionLabelProp="label"
              showSearch
              filterOption={(input, option) =>
                (option?.children?.toLowerCase() || '').includes(input.toLowerCase())
              }
            >
              {services.map(service => (
                <Option 
                  key={service.id} 
                  value={service.id}
                  label={service.title}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span>{service.title}</span>
                    <span style={{ color: '#666', fontSize: '12px' }}>
                      {service.price} ₺ ({service.duration_minutes} мин)
                    </span>
                  </div>
                </Option>
              ))}
            </Select>
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="status"
                label={
                  <Space>
                    <SafetyCertificateOutlined />
                    <span>Статус</span>
                  </Space>
                }
                initialValue="pending"
              >
                <Select>
                  <Option value="pending">Ожидает</Option>
                  <Option value="confirmed">Подтверждена</Option>
                  <Option value="in_progress">В процессе</Option>
                  <Option value="completed">Завершена</Option>
                  <Option value="cancelled">Отменена</Option>
                  <Option value="no_show">Неявка</Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label=" "
                colon={false}
                style={{ marginTop: 30 }}
              >
                <Space style={{ float: 'right' }}>
                  <Button 
                    onClick={() => {
                      setModalVisible(false);
                      form.resetFields();
                      setEditingAppointment(null);
                    }}
                    disabled={isSubmitting}
                  >
                    Отмена
                  </Button>
                  <Button 
                    type="primary" 
                    htmlType="submit"
                    loading={isSubmitting}
                    icon={editingAppointment ? <EditOutlined /> : <PlusOutlined />}
                  >
                    {editingAppointment ? 'Обновить' : 'Создать'}
                  </Button>
                </Space>
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Modal>

      {/* Модальное окно создания нового клиента */}
      <Modal
        title={
          <Space>
            <PlusOutlined />
            <span>Добавить нового клиента</span>
          </Space>
        }
        open={newClientModalVisible}
        onCancel={() => {
          setNewClientModalVisible(false);
          newClientForm.resetFields();
        }}
        onOk={() => newClientForm.submit()}
        okText="Создать"
        cancelText="Отмена"
        confirmLoading={isSubmitting}
        width={500}
        destroyOnClose
      >
        <Form
          form={newClientForm}
          layout="vertical"
          onFinish={handleCreateNewClient}
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
              { pattern: /^[\d\s\+\-\(\)]+$/, message: 'Введите корректный номер телефона' }
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

      {/* Drawer с деталями записи */}
      {renderAppointmentDrawer()}
    </div>
  );
};

export default Appointments;