// pages/Login.jsx
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Card,
  Form,
  Input,
  Button,
  Typography,
  message,
} from 'antd';
import {
  UserOutlined,
  LockOutlined,
  SafetyOutlined,
} from '@ant-design/icons';
import { authAPI } from '../services/api';

const { Title, Text } = Typography;

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
    <div style={{
      minHeight: '100vh',
      background: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '20px',
    }}>
      <div style={{ width: '100%', maxWidth: '400px' }}>
        {/* Logo area */}
        <div style={{ textAlign: 'center', marginBottom: '32px' }}>
          <div style={{
            width: '68px',
            height: '68px',
            borderRadius: '18px',
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            margin: '0 auto 16px',
            boxShadow: '0 10px 30px rgba(102, 126, 234, 0.5)',
            fontSize: '26px',
            fontWeight: 'bold',
            color: 'white',
          }}>
            BS
          </div>
          <Title level={2} style={{ color: 'white', marginBottom: '6px' }}>
            Beauty Salon
          </Title>
          <Text style={{ color: 'rgba(255, 255, 255, 0.55)', fontSize: '14px' }}>
            Панель администратора
          </Text>
        </div>

        {/* Login card */}
        <Card
          bordered={false}
          style={{
            borderRadius: '16px',
            boxShadow: '0 20px 60px rgba(0, 0, 0, 0.35)',
            padding: '8px',
          }}
        >
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
                prefix={<UserOutlined style={{ color: '#bbb' }} />}
                placeholder="Введите логин"
              />
            </Form.Item>

            <Form.Item
              name="password"
              label="Пароль"
              rules={[{ required: true, message: 'Введите пароль' }]}
            >
              <Input.Password
                prefix={<LockOutlined style={{ color: '#bbb' }} />}
                placeholder="Введите пароль"
              />
            </Form.Item>

            <Form.Item style={{ marginTop: '28px', marginBottom: 0 }}>
              <Button
                type="primary"
                htmlType="submit"
                loading={loading}
                block
                size="large"
                icon={<SafetyOutlined />}
                style={{
                  height: '48px',
                  borderRadius: '10px',
                  background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                  border: 'none',
                  fontSize: '15px',
                  fontWeight: '600',
                  boxShadow: '0 4px 16px rgba(102, 126, 234, 0.45)',
                }}
              >
                Войти в систему
              </Button>
            </Form.Item>
          </Form>
        </Card>
      </div>
    </div>
  );
};

export default Login;
