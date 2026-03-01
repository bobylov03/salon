// Layout.jsx
import React, { useState, useEffect } from 'react';
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
import { Layout, Menu, Button, theme, Avatar, Dropdown, Drawer, Typography } from 'antd';
import { Link, useNavigate, Outlet, useLocation } from 'react-router-dom';

const { Header, Sider, Content } = Layout;
const { Text } = Typography;

const SIDEBAR_WIDTH = 260;
const SIDEBAR_COLLAPSED_WIDTH = 80;

const AdminLayout = () => {
  const [collapsed, setCollapsed] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    const check = () => {
      const mobile = window.innerWidth < 768;
      setIsMobile(mobile);
      if (!mobile) setMobileOpen(false);
    };
    check();
    window.addEventListener('resize', check);
    return () => window.removeEventListener('resize', check);
  }, []);

  // Close mobile drawer on route change
  useEffect(() => {
    setMobileOpen(false);
  }, [location.pathname]);

  const {
    token: { colorBgContainer, borderRadiusLG, colorPrimary, colorTextBase, colorBorderSecondary },
  } = theme.useToken();

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    localStorage.removeItem('isLoggedIn');
    navigate('/login');
  };

  const closeMobile = () => setMobileOpen(false);

  const menuItems = [
    {
      key: 'dashboard',
      icon: <DashboardOutlined />,
      label: <Link to="/" onClick={closeMobile}>Дашборд</Link>,
    },
    {
      key: 'masters',
      icon: <UserOutlined />,
      label: <Link to="/masters" onClick={closeMobile}>Мастера</Link>,
    },
    {
      key: 'schedule',
      icon: <ScheduleOutlined />,
      label: <Link to="/schedule" onClick={closeMobile}>График работы</Link>,
    },
    {
      key: 'services',
      icon: <ToolOutlined />,
      label: <Link to="/services" onClick={closeMobile}>Услуги</Link>,
    },
    {
      key: 'appointments',
      icon: <CalendarOutlined />,
      label: <Link to="/appointments" onClick={closeMobile}>Записи</Link>,
    },
    {
      key: 'clients',
      icon: <TeamOutlined />,
      label: <Link to="/clients" onClick={closeMobile}>Клиенты</Link>,
    },
  ];

  const userMenuItems = [
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: 'Выйти',
      danger: true,
      onClick: handleLogout,
    },
  ];

  const getSelectedKeys = () => {
    const path = location.pathname;
    if (path === '/') return ['dashboard'];
    if (path.startsWith('/masters')) return ['masters'];
    if (path.startsWith('/schedule')) return ['schedule'];
    if (path.startsWith('/services')) return ['services'];
    if (path.startsWith('/appointments')) return ['appointments'];
    if (path.startsWith('/clients')) return ['clients'];
    return ['dashboard'];
  };

  const PAGE_TITLES = {
    '/': 'Дашборд',
    '/masters': 'Мастера',
    '/schedule': 'График работы',
    '/services': 'Услуги',
    '/appointments': 'Записи',
    '/clients': 'Клиенты',
  };

  const getPageTitle = () => {
    const path = location.pathname;
    for (const [key, value] of Object.entries(PAGE_TITLES)) {
      if (key === '/' ? path === '/' : path.startsWith(key)) return value;
    }
    return '';
  };

  const renderLogo = (showFull) => (
    <div style={{
      padding: showFull ? '22px 20px' : '18px 16px',
      borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
      marginBottom: '8px',
    }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: showFull ? 'flex-start' : 'center',
        gap: '12px',
      }}>
        <div style={{
          width: showFull ? '40px' : '32px',
          height: showFull ? '40px' : '32px',
          borderRadius: '10px',
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: showFull ? '16px' : '13px',
          fontWeight: 'bold',
          color: 'white',
          boxShadow: '0 4px 12px rgba(102, 126, 234, 0.45)',
          flexShrink: 0,
        }}>
          BS
        </div>
        {showFull && (
          <div style={{ textAlign: 'left' }}>
            <div style={{
              fontSize: '16px',
              fontWeight: '700',
              color: 'white',
              lineHeight: '1.2',
            }}>
              Beauty Salon
            </div>
            <div style={{
              fontSize: '11px',
              color: 'rgba(255, 255, 255, 0.55)',
              marginTop: '2px',
            }}>
              Администратор
            </div>
          </div>
        )}
      </div>
    </div>
  );

  const renderBottomSection = () => (
    <div style={{
      padding: '14px 16px',
      borderTop: '1px solid rgba(255, 255, 255, 0.1)',
      background: 'rgba(0, 0, 0, 0.18)',
    }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '10px',
        marginBottom: '10px',
      }}>
        <Avatar
          size={34}
          style={{
            backgroundColor: '#1890ff',
            boxShadow: '0 2px 8px rgba(24, 144, 255, 0.4)',
            flexShrink: 0,
          }}
        >
          A
        </Avatar>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{
            color: 'white',
            fontWeight: '500',
            fontSize: '13px',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}>
            Администратор
          </div>
          <div style={{
            fontSize: '11px',
            color: 'rgba(255, 255, 255, 0.45)',
          }}>
            admin@salon.com
          </div>
        </div>
      </div>
      <Button
        type="text"
        icon={<LogoutOutlined />}
        onClick={handleLogout}
        style={{
          width: '100%',
          color: 'rgba(255, 255, 255, 0.6)',
          textAlign: 'left',
          padding: '6px 10px',
          borderRadius: '8px',
          height: 'auto',
          fontSize: '13px',
        }}
      >
        Выйти из системы
      </Button>
    </div>
  );

  const renderSidebarContent = (showFull) => (
    <div style={{
      background: 'linear-gradient(180deg, #1a1a2e 0%, #16213e 100%)',
      height: '100%',
      display: 'flex',
      flexDirection: 'column',
      overflow: 'hidden',
    }}>
      {renderLogo(showFull)}
      <div style={{ flex: 1, overflow: 'auto' }}>
        <Menu
          mode="inline"
          selectedKeys={getSelectedKeys()}
          items={menuItems}
          theme="dark"
          style={{
            borderRight: 0,
            background: 'transparent',
            padding: '0 10px',
          }}
          inlineIndent={20}
        />
      </div>
      {showFull && renderBottomSection()}
    </div>
  );

  return (
    <Layout style={{ minHeight: '100vh', background: '#f5f7fa' }}>
      {/* Desktop sidebar */}
      {!isMobile && (
        <Sider
          trigger={null}
          collapsible
          collapsed={collapsed}
          width={SIDEBAR_WIDTH}
          collapsedWidth={SIDEBAR_COLLAPSED_WIDTH}
          style={{
            background: 'linear-gradient(180deg, #1a1a2e 0%, #16213e 100%)',
            boxShadow: '2px 0 16px rgba(0, 0, 0, 0.12)',
            position: 'fixed',
            height: '100vh',
            left: 0,
            top: 0,
            bottom: 0,
            zIndex: 1000,
            overflow: 'hidden',
          }}
          theme="dark"
        >
          {renderSidebarContent(!collapsed)}
        </Sider>
      )}

      {/* Mobile drawer */}
      {isMobile && (
        <Drawer
          placement="left"
          open={mobileOpen}
          onClose={() => setMobileOpen(false)}
          width={SIDEBAR_WIDTH}
          styles={{
            body: {
              padding: 0,
              background: 'linear-gradient(180deg, #1a1a2e 0%, #16213e 100%)',
              display: 'flex',
              flexDirection: 'column',
            },
            header: { display: 'none' },
            wrapper: { boxShadow: '4px 0 24px rgba(0, 0, 0, 0.22)' },
          }}
          closable={false}
        >
          {renderSidebarContent(true)}
        </Drawer>
      )}

      <Layout style={{
        marginLeft: isMobile ? 0 : (collapsed ? SIDEBAR_COLLAPSED_WIDTH : SIDEBAR_WIDTH),
        transition: 'margin-left 0.2s ease',
        minHeight: '100vh',
      }}>
        <Header style={{
          padding: 0,
          background: colorBgContainer,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          paddingRight: isMobile ? '12px' : '24px',
          borderBottom: `1px solid ${colorBorderSecondary}`,
          boxShadow: '0 2px 8px rgba(0, 0, 0, 0.05)',
          height: '64px',
          position: 'sticky',
          top: 0,
          zIndex: 999,
        }}>
          <div style={{ display: 'flex', alignItems: 'center' }}>
            <Button
              type="text"
              icon={
                isMobile
                  ? (mobileOpen ? <MenuFoldOutlined /> : <MenuUnfoldOutlined />)
                  : (collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />)
              }
              onClick={() => isMobile ? setMobileOpen(!mobileOpen) : setCollapsed(!collapsed)}
              style={{
                fontSize: '18px',
                width: '64px',
                height: '64px',
                color: colorTextBase,
              }}
            />
            <Text strong style={{ fontSize: isMobile ? '15px' : '17px' }}>
              {getPageTitle()}
            </Text>
          </div>

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
              padding: '8px 10px',
              borderRadius: '8px',
              transition: 'background 0.2s',
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
              {!isMobile && (
                <div style={{ display: 'flex', flexDirection: 'column', lineHeight: 1.3 }}>
                  <Text style={{ fontSize: '13px', fontWeight: '600' }}>Администратор</Text>
                  <Text style={{ fontSize: '11px', color: '#999' }}>Онлайн</Text>
                </div>
              )}
            </div>
          </Dropdown>
        </Header>

        <Content style={{
          margin: isMobile ? '12px 8px 0' : '20px 20px 0',
          padding: 0,
          minHeight: 280,
        }}>
          <div style={{
            padding: isMobile ? '14px 12px' : '24px',
            background: colorBgContainer,
            borderRadius: isMobile ? 8 : borderRadiusLG,
            boxShadow: '0 2px 10px rgba(0, 0, 0, 0.04)',
            minHeight: 'calc(100vh - 112px)',
            overflow: 'hidden',
          }}>
            <Outlet />
          </div>

          <div style={{
            padding: '10px 16px',
            textAlign: 'center',
            color: '#bbb',
            fontSize: '12px',
          }}>
            <Text type="secondary">
              © {new Date().getFullYear()} Beauty Salon Admin Panel
            </Text>
          </div>
        </Content>
      </Layout>
    </Layout>
  );
};

export default AdminLayout;
