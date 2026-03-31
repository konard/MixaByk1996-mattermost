import React, { useEffect } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { useStore } from './store/useStore';
import Layout from './components/Layout';
import ChatList from './components/ChatList';
import ChatView from './components/ChatView';
import Cabinet from './components/Cabinet';
import LoginModal from './components/LoginModal';
import ProcurementModal from './components/ProcurementModal';
import CreateProcurementModal from './components/CreateProcurementModal';
import DepositModal from './components/DepositModal';
import Toast from './components/Toast';

function App() {
  const { user, loadUser, theme, setTheme } = useStore();

  useEffect(() => {
    // Load theme from localStorage
    const savedTheme = localStorage.getItem('theme') || 'light';
    setTheme(savedTheme);
    document.documentElement.setAttribute('data-theme', savedTheme);

    // Try to load user from storage
    const userId = localStorage.getItem('userId');
    if (userId) {
      loadUser(userId);
    }
  }, [loadUser, setTheme]);

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
  }, [theme]);

  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<ChatList />} />
          <Route path="/chat/:procurementId" element={<ChatView />} />
          <Route path="/cabinet" element={<Cabinet />} />
        </Routes>
      </Layout>
      <LoginModal />
      <ProcurementModal />
      <CreateProcurementModal />
      <DepositModal />
      <Toast />
    </BrowserRouter>
  );
}

export default App;
