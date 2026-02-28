// Layout.jsx
import React, { useState } from 'react';
import {
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  DashboardOutlined,
  UserOutlined,
  CalendarOutlined,
  ToolOutlined,
  ScheduleOutlined,
  TeamOutlined,
  LogoutOutlined,
} from '@ant-design/icons';
import { Layout, Menu, Button, theme, Avatar, Dropdown, Space, Typography } from 'antd';
import { Link, useNavigate, Outlet, useLocation } from 'react-router-dom';

const { Header, Sider, Content } = Layout;
const { Text } = Typography;

const AdminLayout = () => {
  const [collapsed, setCollapsed] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  
  const {
    token: { 
      colorBgContainer, 
      borderRadiusLG,
      colorPrimary,
      colorTextBase,
      colorBorderSecondary,
      colorFillSecondary
    },
  } = theme.useToken();

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    localStorage.removeItem('isLoggedIn');
    navigate('/login');
  };

  const menuItems = [
    {
      key: 'dashboard',
      icon: <DashboardOutlined />,
      label: <Link to="/">Дашборд</Link>,
    },
    {
      key: 'masters',
      icon: <UserOutlined />,
      label: <Link to="/masters">Мастера</Link>,
    },
    {
      key: 'schedule',
      icon: <ScheduleOutlined />,
      label: <Link to="/schedule">График работы</Link>,
    },
    {
      key: 'services',
      icon: <ToolOutlined />,
      label: <Link to="/services">Услуги</Link>,
    },
    {
      key: 'appointments',
      icon: <CalendarOutlined />,
      label: <Link to="/appointments">Записи</Link>,
    },
    {
      key: 'clients',
      icon: <TeamOutlined />,
      label: <Link to="/clients">Клиенты</Link>,
    },
  ];

  const userMenuItems = [
    {
      key: 'profile',
      icon: <UserOutlined />,
      label: 'Мой профиль',
      onClick: () => navigate('/profile'),
    },
    {
      type: 'divider',
    },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: 'Выйти',
      danger: true,
      onClick: handleLogout,
    },
  ];

  // Определяем активный пункт меню на основе текущего пути
  const getSelectedKeys = () => {
    const path = location.pathname;
    if (path === '/') return ['dashboard'];
    if (path.startsWith('/masters')) return ['masters'];
    if (path.startsWith('/schedule')) return ['schedule'];
    if (path.startsWith('/services')) {
      if (path.includes('/categories')) return ['categories'];
      return ['services-list'];
    }
    if (path.startsWith('/appointments')) return ['appointments'];
    if (path.startsWith('/clients')) return ['clients'];
    if (path.startsWith('/analytics')) return ['analytics'];
    return ['dashboard'];
  };

  const getOpenKeys = () => {
    const path = location.pathname;
    if (path.startsWith('/services')) return ['services'];
    return [];
  };

  return (
    <Layout style={{ minHeight: '100vh', background: '#f5f5f5' }}>
      <Sider 
        trigger={null} 
        collapsible 
        collapsed={collapsed}
        width={280}
        style={{
          background: 'linear-gradient(180deg, #1a1a2e 0%, #16213e 100%)',
          boxShadow: '2px 0 20px rgba(0, 0, 0, 0.15)',
          position: 'fixed',
          height: '100vh',
          left: 0,
          top: 0,
          bottom: 0,
          zIndex: 1000,
        }}
        theme="dark"
      >
        <div style={{ 
          padding: collapsed ? '20px 16px' : '24px 20px', 
          textAlign: 'center',
          borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
          marginBottom: '8px',
        }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: collapsed ? 'center' : 'flex-start',
            gap: '12px',
          }}>
            <div style={{
              width: collapsed ? '32px' : '40px',
              height: collapsed ? '32px' : '40px',
              borderRadius: '8px',
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: collapsed ? '16px' : '20px',
              fontWeight: 'bold',
              color: 'white',
              boxShadow: '0 4px 12px rgba(102, 126, 234, 0.4)',
            }}>
              {collapsed ? 'B' : 'BS'}
            </div>
            {!collapsed && (
              <div style={{ textAlign: 'left' }}>
                <h3 style={{ 
                  margin: 0,
                  fontSize: '18px',
                  fontWeight: '700',
                  color: 'white',
                  lineHeight: '1.2',
                }}>
                  Beauty Salon
                </h3>
                <Text style={{ 
                  fontSize: '12px', 
                  color: 'rgba(255, 255, 255, 0.7)',
                  margin: 0,
                }}>
                  Администратор
                </Text>
              </div>
            )}
          </div>
        </div>
        
        <Menu
          mode="inline"
          defaultSelectedKeys={getSelectedKeys()}
          defaultOpenKeys={getOpenKeys()}
          selectedKeys={getSelectedKeys()}
          items={menuItems}
          theme="dark"
          style={{ 
            borderRight: 0,
            background: 'transparent',
            padding: '0 12px',
          }}
          inlineIndent={24}
        />
        
        {/* Нижняя часть сайдбара */}
        {!collapsed && (
          <div style={{
            position: 'absolute',
            bottom: 0,
            left: 0,
            right: 0,
            padding: '20px',
            borderTop: '1px solid rgba(255, 255, 255, 0.1)',
            background: 'rgba(0, 0, 0, 0.2)',
          }}>
            <div style={{ 
              display: 'flex', 
              alignItems: 'center', 
              gap: '12px',
              marginBottom: '12px',
            }}>
              <Avatar 
                size="large"
                style={{ 
                  backgroundColor: '#1890ff',
                  boxShadow: '0 4px 12px rgba(24, 144, 255, 0.4)',
                }}
              >
                A
              </Avatar>
              <div style={{ flex: 1 }}>
                <Text style={{ 
                  color: 'white', 
                  fontWeight: '500',
                  display: 'block',
                }}>
                  Администратор
                </Text>
                <Text style={{ 
                  fontSize: '12px', 
                  color: 'rgba(255, 255, 255, 0.6)',
                  display: 'block',
                }}>
                  admin@salon.com
                </Text>
              </div>
            </div>
            <Button
              type="text"
              icon={<LogoutOutlined />}
              onClick={handleLogout}
              style={{
                width: '100%',
                color: 'rgba(255, 255, 255, 0.7)',
                textAlign: 'left',
                padding: '8px 16px',
                borderRadius: '6px',
              }}
            >
              Выйти из системы
            </Button>
          </div>
        )}
      </Sider>
      
      <Layout style={{ 
        marginLeft: collapsed ? 80 : 280,
        transition: 'margin-left 0.2s ease',
        minHeight: '100vh',
      }}>
        <Header style={{ 
          padding: 0, 
          background: colorBgContainer,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          paddingRight: '24px',
          borderBottom: `1px solid ${colorBorderSecondary}`,
          boxShadow: '0 2px 12px rgba(0, 0, 0, 0.04)',
          height: '64px',
          position: 'sticky',
          top: 0,
          zIndex: 999,
        }}>
          <div style={{ display: 'flex', alignItems: 'center' }}>
            <Button
              type="text"
              icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
              onClick={() => setCollapsed(!collapsed)}
              style={{
                fontSize: '18px',
                width: '64px',
                height: '64px',
                color: colorTextBase,
              }}
            />
            <div style={{ marginLeft: '16px' }}>
              <Text strong style={{ fontSize: '18px' }}>
                {location.pathname === '/' && 'Дашборд'}
                {location.pathname.startsWith('/masters') && 'Мастера'}
                {location.pathname.startsWith('/schedule') && 'График работы'}
                {location.pathname.startsWith('/services') && 'Услуги'}
                {location.pathname.startsWith('/appointments') && 'Записи'}
                {location.pathname.startsWith('/clients') && 'Клиенты'}
                {location.pathname.startsWith('/analytics') && 'Аналитика'}
              </Text>
              {location.pathname !== '/' && (
                <Text style={{ 
                  fontSize: '12px', 
                  color: '#666',
                  marginLeft: '8px',
                  display: 'inline-block',
                }}>
                  {location.pathname === '/' && 'Общая статистика'}
                  {location.pathname.startsWith('/masters') && 'Управление мастерами'}
                  {location.pathname.startsWith('/schedule') && 'Расписание мастеров'}
                  {location.pathname.startsWith('/services') && 'Каталог услуг и категорий'}
                  {location.pathname.startsWith('/appointments') && 'Записи клиентов'}
                  {location.pathname.startsWith('/clients') && 'База клиентов'}
                  {location.pathname.startsWith('/analytics') && 'Статистика и отчеты'}
                </Text>
              )}
            </div>
          </div>
          
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            <Dropdown 
              menu={{ items: userMenuItems }}
              placement="bottomRight"
              arrow={{ pointAtCenter: true }}
              trigger={['click']}
            >
              <div style={{ 
                display: 'flex', 
                alignItems: 'center', 
                gap: '8px',
                cursor: 'pointer',
                padding: '8px 12px',
                borderRadius: '8px',
                transition: 'all 0.2s',
                ':hover': {
                  background: colorFillSecondary,
                },
              }}>
                <Avatar 
                  size="default"
                  style={{ 
                    backgroundColor: colorPrimary,
                    boxShadow: '0 2px 8px rgba(24, 144, 255, 0.3)',
                  }}
                >
                  A
                </Avatar>
                <div style={{ display: 'flex', flexDirection: 'column' }}>
                  <Text style={{ 
                    fontSize: '14px', 
                    fontWeight: '500',
                    lineHeight: '1.2',
                  }}>
                    Администратор
                  </Text>
                  <Text style={{ 
                    fontSize: '12px', 
                    color: '#666',
                    lineHeight: '1.2',
                  }}>
                    Онлайн
                  </Text>
                </div>
              </div>
            </Dropdown>
          </div>
        </Header>
        
        <Content style={{ 
          margin: '24px 24px 0',
          padding: 0,
          minHeight: 280,
          overflow: 'initial',
        }}>
          <div style={{
            padding: '24px',
            background: colorBgContainer,
            borderRadius: borderRadiusLG,
            boxShadow: '0 2px 8px rgba(0, 0, 0, 0.04)',
            minHeight: 'calc(100vh - 112px)',
          }}>
            <Outlet />
          </div>
          
          {/* Footer */}
          <div style={{
            margin: '24px 0',
            padding: '16px 24px',
            textAlign: 'center',
            color: '#666',
            fontSize: '12px',
            borderTop: `1px solid ${colorBorderSecondary}`,
          }}>
            <Text>
              © {new Date().getFullYear()} Beauty Salon Admin Panel. Версия 1.0.0
            </Text>
            <div style={{ marginTop: '4px' }}>
              <Text type="secondary">
                Последнее обновление: {new Date().toLocaleDateString('ru-RU')}
              </Text>
            </div>
          </div>
        </Content>
      </Layout>
    </Layout>
  );
};

export default AdminLayout;

