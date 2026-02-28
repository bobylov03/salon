// App.jsx
import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ConfigProvider } from 'antd';
import ruRU from 'antd/locale/ru_RU';

// Layout and Pages
import AdminLayout from './components/Layout';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Masters from './pages/Masters';
import Schedule from './pages/Schedule';
import Services from './pages/Services';
import Appointments from './pages/Appointments';
import Clients from './pages/Clients';
import Bonuses from './pages/Bonuses';
import Logs from './pages/Logs';

const queryClient = new QueryClient();

// Простой компонент для проверки "авторизации"
const ProtectedRoute = ({ children }) => {
  const user = JSON.parse(localStorage.getItem('user') || 'null');
  
  if (!user) {
    return <Navigate to="/login" replace />;
  }
  
  return children;
};

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ConfigProvider locale={ruRU}>
        <Router>
          <Routes>
            {/* Страница логина */}
            <Route path="/login" element={<Login />} />
            
            {/* Защищенные маршруты */}
            <Route path="/" element={
              <ProtectedRoute>
                <AdminLayout />
              </ProtectedRoute>
            }>
              <Route index element={<Dashboard />} />
              <Route path="masters" element={<Masters />} />
              <Route path="schedule" element={<Schedule />} />
              <Route path="services" element={<Services />} />
              <Route path="appointments" element={<Appointments />} />
              <Route path="clients" element={<Clients />} />
              <Route path="bonuses" element={<Bonuses />} />
              <Route path="logs" element={<Logs />} />
            </Route>
            
            {/* Редирект на логин для несуществующих маршрутов */}
            <Route path="*" element={<Navigate to="/login" replace />} />
          </Routes>
        </Router>
      </ConfigProvider>
    </QueryClientProvider>
  );
}

export default App;