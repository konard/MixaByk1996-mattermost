import React from 'react';
import { useStore } from '../store/useStore';
import {
  formatCurrency,
  getInitials,
  getAvatarColor,
  getRoleText,
} from '../utils/helpers';
import {
  RequestsIcon,
  ShoppingBagIcon,
  MailIcon,
  HistoryIcon,
  PlusIcon,
  HomeIcon,
  FileIcon,
} from './Icons';

function Cabinet() {
  const { user, openDepositModal, openCreateProcurementModal, logout } = useStore();

  if (!user) {
    return (
      <div className="cabinet flex flex-col items-center justify-center" style={{ flex: 1 }}>
        <p className="text-muted">Войдите для доступа к личному кабинету</p>
      </div>
    );
  }

  const renderRoleItems = () => {
    if (user.role === 'organizer') {
      return (
        <div className="cabinet-menu-item" onClick={openCreateProcurementModal}>
          <PlusIcon />
          <span className="cabinet-menu-text">Создать закупку</span>
        </div>
      );
    }

    if (user.role === 'supplier') {
      return (
        <>
          <div className="cabinet-menu-item">
            <HomeIcon />
            <span className="cabinet-menu-text">Карточка компании</span>
          </div>
          <div className="cabinet-menu-item">
            <FileIcon />
            <span className="cabinet-menu-text">Прайс-листы</span>
          </div>
        </>
      );
    }

    return null;
  };

  return (
    <div className="cabinet" style={{ flex: 1, overflowY: 'auto' }}>
      <div className="cabinet-header">
        <div
          className="cabinet-avatar"
          style={{ backgroundColor: getAvatarColor(user.first_name || '') }}
        >
          {getInitials(user.first_name, user.last_name)}
        </div>
        <div className="cabinet-info">
          <h2>
            {user.first_name} {user.last_name || ''}
          </h2>
          <div className="cabinet-role">{getRoleText(user.role)}</div>
        </div>
      </div>

      <div className="cabinet-balance">
        <div className="balance-label">Баланс</div>
        <div className="balance-amount">{formatCurrency(user.balance || 0)}</div>
        <div className="balance-actions">
          <button className="btn btn-primary btn-round" onClick={openDepositModal}>
            Пополнить
          </button>
          <button className="btn btn-outline btn-round">Вывести</button>
        </div>
      </div>

      <div className="cabinet-menu">
        {renderRoleItems()}

        <div className="cabinet-menu-item">
          <RequestsIcon />
          <span className="cabinet-menu-text">Мои запросы</span>
        </div>

        <div className="cabinet-menu-item">
          <ShoppingBagIcon />
          <span className="cabinet-menu-text">Мои закупки</span>
        </div>

        <div className="cabinet-menu-item">
          <MailIcon />
          <span className="cabinet-menu-text">Сообщения</span>
        </div>

        <div className="cabinet-menu-item">
          <HistoryIcon />
          <span className="cabinet-menu-text">История закупок</span>
        </div>

        <div className="cabinet-menu-item" onClick={logout}>
          <svg
            className="cabinet-menu-icon"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
            <polyline points="16 17 21 12 16 7" />
            <line x1="21" y1="12" x2="9" y2="12" />
          </svg>
          <span className="cabinet-menu-text text-error">Выйти</span>
        </div>
      </div>
    </div>
  );
}

export default Cabinet;
