// pages/Login.jsx
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
import { authAPI } from '../services/api';

const { Title, Text } = Typography;
const { Content } = Layout;

const Login = () => {
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const onFinish = async (values) => {
    setLoading(true);

    try {
      const response = await authAPI.login(values.username, values.password);
      const { access_token } = response.data;

      const user = {
        id: 1,
        username: values.username,
        name: 'Администратор',
        role: 'admin',
        first_name: 'Admin',
        last_name: 'User',
      };

      localStorage.setItem('isLoggedIn', 'true');
      localStorage.setItem('user', JSON.stringify(user));
      localStorage.setItem('token', access_token);

      message.success('Добро пожаловать!');
      navigate('/');
    } catch (error) {
      const detail = error.response?.data?.detail;
      message.error(detail || 'Неверный логин или пароль');
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
                    name="username"
                    label="Логин"
                    rules={[{ required: true, message: 'Введите логин' }]}
                  >
                    <Input
                      prefix={<UserOutlined />}
                      placeholder="salon_admin"
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

              </Space>
            </Card>
          </Col>
        </Row>
      </Content>
    </Layout>
  );
};

export default Login;