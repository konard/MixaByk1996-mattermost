/**
 * Format date to Telegram-like format
 */
export function formatTime(date) {
  const d = new Date(date);
  const now = new Date();
  const isToday = d.toDateString() === now.toDateString();

  if (isToday) {
    return d.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });
  }

  const yesterday = new Date(now);
  yesterday.setDate(yesterday.getDate() - 1);
  if (d.toDateString() === yesterday.toDateString()) {
    return 'Вчера';
  }

  return d.toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit' });
}

/**
 * Format date for message dividers
 */
export function formatMessageDate(date) {
  const d = new Date(date);
  const now = new Date();
  const diff = now - d;

  if (diff < 86400000) return 'Сегодня';
  if (diff < 172800000) return 'Вчера';

  return d.toLocaleDateString('ru-RU', {
    day: 'numeric',
    month: 'long',
    year: d.getFullYear() !== now.getFullYear() ? 'numeric' : undefined,
  });
}

/**
 * Format currency
 */
export function formatCurrency(amount) {
  return new Intl.NumberFormat('ru-RU', {
    style: 'currency',
    currency: 'RUB',
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(amount || 0);
}

/**
 * Get initials from name
 */
export function getInitials(firstName, lastName = '') {
  const first = firstName ? firstName.charAt(0).toUpperCase() : '';
  const last = lastName ? lastName.charAt(0).toUpperCase() : '';
  return first + last || '?';
}

/**
 * Generate avatar background color based on name
 */
export function getAvatarColor(name) {
  const colors = [
    '#e17076',
    '#faa774',
    '#a695e7',
    '#7bc862',
    '#6ec9cb',
    '#65aadd',
    '#ee7aae',
    '#f5a623',
  ];
  let hash = 0;
  const str = name || '';
  for (let i = 0; i < str.length; i++) {
    hash = str.charCodeAt(i) + ((hash << 5) - hash);
  }
  return colors[Math.abs(hash) % colors.length];
}

/**
 * Get status display text
 */
export function getStatusText(status) {
  const statuses = {
    draft: 'Черновик',
    active: 'Активная',
    stopped: 'Остановлена',
    payment: 'Оплата',
    completed: 'Завершена',
    cancelled: 'Отменена',
  };
  return statuses[status] || status;
}

/**
 * Get role display text
 */
export function getRoleText(role) {
  const roles = {
    buyer: 'Покупатель',
    organizer: 'Организатор',
    supplier: 'Поставщик',
  };
  return roles[role] || role;
}

/**
 * Escape HTML to prevent XSS
 */
export function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

/**
 * Debounce function
 */
export function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}
