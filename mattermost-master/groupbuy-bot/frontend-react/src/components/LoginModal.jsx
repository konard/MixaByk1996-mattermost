import React, { useState } from 'react';
import { useStore } from '../store/useStore';

function LoginModal() {
  const { loginModalOpen, closeLoginModal, register, isLoading } = useStore();
  const [formData, setFormData] = useState({
    first_name: '',
    last_name: '',
    phone: '',
    email: '',
    role: 'buyer',
  });

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await register(formData);
    } catch (error) {
      // Error is handled in the store
    }
  };

  if (!loginModalOpen) return null;

  return (
    <div className="modal-overlay active" onClick={(e) => e.target === e.currentTarget && closeLoginModal()}>
      <div className="modal">
        <div className="modal-header">
          <h3 className="modal-title">Регистрация</h3>
        </div>
        <div className="modal-body">
          <form id="register-form" onSubmit={handleSubmit}>
            <div className="form-group">
              <label className="form-label">Имя *</label>
              <input
                type="text"
                className="form-input"
                name="first_name"
                required
                placeholder="Введите имя"
                value={formData.first_name}
                onChange={handleChange}
              />
            </div>
            <div className="form-group">
              <label className="form-label">Фамилия</label>
              <input
                type="text"
                className="form-input"
                name="last_name"
                placeholder="Введите фамилию"
                value={formData.last_name}
                onChange={handleChange}
              />
            </div>
            <div className="form-group">
              <label className="form-label">Телефон</label>
              <input
                type="tel"
                className="form-input"
                name="phone"
                placeholder="+7 999 123 4567"
                value={formData.phone}
                onChange={handleChange}
              />
            </div>
            <div className="form-group">
              <label className="form-label">Email</label>
              <input
                type="email"
                className="form-input"
                name="email"
                placeholder="email@example.com"
                value={formData.email}
                onChange={handleChange}
              />
            </div>
            <div className="form-group">
              <label className="form-label">Роль *</label>
              <select
                className="form-input form-select"
                name="role"
                required
                value={formData.role}
                onChange={handleChange}
              >
                <option value="buyer">Покупатель</option>
                <option value="organizer">Организатор</option>
                <option value="supplier">Поставщик</option>
              </select>
            </div>
          </form>
        </div>
        <div className="modal-footer">
          <button
            className="btn btn-primary btn-round"
            onClick={handleSubmit}
            disabled={isLoading}
          >
            {isLoading ? 'Загрузка...' : 'Зарегистрироваться'}
          </button>
        </div>
      </div>
    </div>
  );
}

export default LoginModal;
