// pages/Login.jsx (упрощенная версия)
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Card,
  Form,
  Input,
  Button,
  Typography,
  Space,
  message,
  Layout,
  Row,
  Col,
  Divider,
} from 'antd';
import {
  UserOutlined,
  LockOutlined,
  ShopOutlined,
  SafetyOutlined,
} from '@ant-design/icons';

const { Title, Text } = Typography;
const { Content } = Layout;

const Login = () => {
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const onFinish = async (values) => {
    setLoading(true);
    
    try {
      console.log('Login attempt:', values);
      
      // Имитируем задержку сети
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      // Просто сохраняем пользователя в localStorage
      const user = {
        id: 1,
        email: values.email,
        name: 'Администратор',
        role: 'admin',
        first_name: 'Admin',
        last_name: 'User'
      };
      
      localStorage.setItem('isLoggedIn', 'true');
      localStorage.setItem('user', JSON.stringify(user));
      localStorage.setItem('token', 'demo-token-' + Date.now());
      
      message.success('Добро пожаловать!');
      navigate('/');
      
    } catch (error) {
      message.error('Ошибка входа');
      console.error('Login error:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Layout style={{ minHeight: '100vh', background: '#f0f2f5' }}>
      <Content>
        <Row justify="center" align="middle" style={{ minHeight: '100vh' }}>
          <Col xs={24} sm={20} md={16} lg={12} xl={8}>
            <Card 
              bordered={false}
              style={{
                boxShadow: '0 4px 12px rgba(0, 0, 0, 0.1)',
                borderRadius: 8,
              }}
            >
              <Space direction="vertical" size="large" style={{ width: '100%' }}>
                {/* Заголовок */}
                <div style={{ textAlign: 'center' }}>
                  <ShopOutlined 
                    style={{ 
                      fontSize: 48, 
                      color: '#1890ff',
                      marginBottom: 16 
                    }} 
                  />
                  <Title level={2} style={{ marginBottom: 8 }}>
                    Beauty Salon Admin
                  </Title>
                  <Text type="secondary">
                    Панель управления салоном красоты
                  </Text>
                </div>

                <Divider />

                {/* Форма входа */}
                <Form
                  name="login"
                  onFinish={onFinish}
                  layout="vertical"
                  size="large"
                >
                  <Form.Item
                    name="email"
                    label="Email"
                    rules={[
                      { required: true, message: 'Введите email' },
                      { type: 'email', message: 'Введите корректный email' }
                    ]}
                  >
                    <Input
                      prefix={<UserOutlined />}
                      placeholder="admin@salon.com"
                    />
                  </Form.Item>

                  <Form.Item
                    name="password"
                    label="Пароль"
                    rules={[
                      { required: true, message: 'Введите пароль' }
                    ]}
                  >
                    <Input.Password
                      prefix={<LockOutlined />}
                      placeholder="••••••"
                    />
                  </Form.Item>

                  <Form.Item style={{ marginTop: 24 }}>
                    <Button
                      type="primary"
                      htmlType="submit"
                      loading={loading}
                      block
                      size="large"
                      icon={<SafetyOutlined />}
                    >
                      Войти в систему
                    </Button>
                  </Form.Item>
                </Form>

                {/* Информация */}
                <div style={{ 
                  padding: '12px', 
                  background: '#f6ffed',
                  borderRadius: '6px',
                  border: '1px solid #b7eb8f'
                }}>
                  <Text type="secondary" style={{ fontSize: '12px' }}>
                    <strong>Демо-режим:</strong> Введите любые данные для входа
                  </Text>
                </div>
              </Space>
            </Card>
          </Col>
        </Row>
      </Content>
    </Layout>
  );
};

export default Login;