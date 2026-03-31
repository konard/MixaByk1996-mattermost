import React, { useEffect } from 'react';
import { useStore } from '../store/useStore';
import Sidebar from './Sidebar';
import ProcurementSlider from './ProcurementSlider';

function Layout({ children }) {
  const { user, loadProcurements, openLoginModal } = useStore();

  useEffect(() => {
    if (user) {
      loadProcurements();
    } else {
      const userId = localStorage.getItem('userId');
      if (!userId) {
        openLoginModal();
      }
    }
  }, [user, loadProcurements, openLoginModal]);

  return (
    <div className="app-container">
      <Sidebar />
      <main className="main-content">
        <ProcurementSlider />
        {children}
      </main>
    </div>
  );
}

export default Layout;
