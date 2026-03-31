import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useStore } from '../store/useStore';
import { formatCurrency, getStatusText } from '../utils/helpers';
import { CloseIcon } from './Icons';

function ProcurementModal() {
  const navigate = useNavigate();
  const {
    procurementModalOpen,
    closeProcurementModal,
    selectedProcurement,
    joinProcurement,
    setCurrentChat,
  } = useStore();
  const [amount, setAmount] = useState('');

  if (!procurementModalOpen || !selectedProcurement) return null;

  const handleJoin = async () => {
    const joinAmount = parseFloat(amount) || 0;
    await joinProcurement(selectedProcurement.id, joinAmount);
  };

  const handleOpenChat = () => {
    setCurrentChat(selectedProcurement.id);
    navigate(`/chat/${selectedProcurement.id}`);
    closeProcurementModal();
  };

  return (
    <div className="modal-overlay active" onClick={(e) => e.target === e.currentTarget && closeProcurementModal()}>
      <div className="modal">
        <div className="modal-header">
          <h3 className="modal-title">{selectedProcurement.title}</h3>
          <button className="modal-close" onClick={closeProcurementModal}>
            <CloseIcon />
          </button>
        </div>
        <div className="modal-body">
          <div className="form-group">
            <label className="form-label">Описание</label>
            <p>{selectedProcurement.description || 'Нет описания'}</p>
          </div>
          <div className="form-group">
            <label className="form-label">Город</label>
            <p>{selectedProcurement.city || 'Не указан'}</p>
          </div>
          <div className="form-group">
            <label className="form-label">Прогресс</label>
            <div className="procurement-progress mt-sm">
              <div
                className="procurement-progress-bar"
                style={{ width: `${selectedProcurement.progress || 0}%` }}
              />
            </div>
            <p className="mt-sm text-secondary">
              {formatCurrency(selectedProcurement.current_amount)} из{' '}
              {formatCurrency(selectedProcurement.target_amount)}
            </p>
          </div>
          <div className="form-group">
            <label className="form-label">Участники</label>
            <p>{selectedProcurement.participant_count || 0} человек</p>
          </div>
          <div className="form-group">
            <label className="form-label">Статус</label>
            <span className={`status-badge status-${selectedProcurement.status}`}>
              {getStatusText(selectedProcurement.status)}
            </span>
          </div>
          {selectedProcurement.status === 'active' && (
            <div className="form-group">
              <label className="form-label">Сумма участия (руб.)</label>
              <input
                type="number"
                className="form-input"
                placeholder="Введите сумму"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                min="0"
              />
            </div>
          )}
        </div>
        <div className="modal-footer">
          <button className="btn btn-secondary btn-round" onClick={handleOpenChat}>
            Открыть чат
          </button>
          {selectedProcurement.status === 'active' && (
            <button className="btn btn-primary btn-round" onClick={handleJoin}>
              Участвовать
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

export default ProcurementModal;
