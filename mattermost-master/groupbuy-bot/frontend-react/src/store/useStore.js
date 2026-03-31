import { create } from 'zustand';
import { api } from '../services/api';

export const useStore = create((set, get) => ({
  // User state
  user: null,
  isLoading: false,
  error: null,

  // Theme
  theme: 'light',

  // Chat state
  currentChat: null,
  procurements: [],
  messages: [],
  unreadCounts: {},

  // Modal state
  loginModalOpen: false,
  procurementModalOpen: false,
  createProcurementModalOpen: false,
  depositModalOpen: false,
  selectedProcurement: null,

  // Toast state
  toasts: [],

  // Sidebar state (mobile)
  sidebarOpen: false,

  // Actions - User
  loadUser: async (userId) => {
    set({ isLoading: true, error: null });
    try {
      const user = await api.getUser(userId);
      set({ user, isLoading: false });
    } catch (error) {
      set({ error: error.message, isLoading: false });
      localStorage.removeItem('userId');
    }
  },

  register: async (data) => {
    set({ isLoading: true, error: null });
    try {
      const platformUserId = `web_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      const user = await api.registerUser({ ...data, platform: 'websocket', platform_user_id: platformUserId });
      localStorage.setItem('userId', user.id);
      set({ user, isLoading: false, loginModalOpen: false });
      get().loadProcurements();
      return user;
    } catch (error) {
      set({ error: error.message, isLoading: false });
      get().addToast('Ошибка регистрации', 'error');
      throw error;
    }
  },

  logout: () => {
    localStorage.removeItem('userId');
    localStorage.removeItem('authToken');
    set({
      user: null,
      currentChat: null,
      messages: [],
      loginModalOpen: true,
    });
  },

  // Actions - Theme
  setTheme: (theme) => {
    localStorage.setItem('theme', theme);
    set({ theme });
  },

  toggleTheme: () => {
    const newTheme = get().theme === 'dark' ? 'light' : 'dark';
    get().setTheme(newTheme);
  },

  // Actions - Procurements
  loadProcurements: async (params = { status: 'active' }) => {
    set({ isLoading: true });
    try {
      const response = await api.getProcurements(params);
      const procurements = response.results || response;
      set({ procurements, isLoading: false });
    } catch (error) {
      set({ error: error.message, isLoading: false });
      get().addToast('Ошибка загрузки закупок', 'error');
    }
  },

  selectProcurement: async (procurementId) => {
    try {
      const procurement = await api.getProcurement(procurementId);
      set({ selectedProcurement: procurement, procurementModalOpen: true });
    } catch (error) {
      get().addToast('Ошибка загрузки закупки', 'error');
    }
  },

  createProcurement: async (data) => {
    set({ isLoading: true });
    try {
      const procurement = await api.createProcurement(data);
      const procurements = [...get().procurements, procurement];
      set({ procurements, isLoading: false, createProcurementModalOpen: false });
      get().addToast('Закупка успешно создана', 'success');
      return procurement;
    } catch (error) {
      set({ isLoading: false });
      get().addToast('Ошибка создания закупки', 'error');
      throw error;
    }
  },

  joinProcurement: async (procurementId, amount) => {
    try {
      await api.joinProcurement(procurementId, { amount });
      set({ procurementModalOpen: false });
      get().addToast('Вы присоединились к закупке', 'success');
      get().loadProcurements();
    } catch (error) {
      get().addToast('Ошибка при присоединении', 'error');
    }
  },

  // Actions - Chat
  setCurrentChat: (chatId) => {
    set({ currentChat: chatId });
    // Clear unread count for this chat
    const unreadCounts = { ...get().unreadCounts };
    delete unreadCounts[chatId];
    set({ unreadCounts });
  },

  loadMessages: async (procurementId) => {
    try {
      const response = await api.getMessages(procurementId);
      const messages = response.results || response;
      set({ messages });
    } catch (error) {
      get().addToast('Ошибка загрузки сообщений', 'error');
    }
  },

  addMessage: (message) => {
    const messages = [...get().messages, message];
    set({ messages });
  },

  sendMessage: async (text) => {
    const { user, currentChat } = get();
    if (!user || !currentChat) return;

    try {
      const message = await api.sendMessage({
        procurement: currentChat,
        user: user.id,
        text,
        message_type: 'text',
      });
      get().addMessage(message);
      return message;
    } catch (error) {
      get().addToast('Ошибка отправки сообщения', 'error');
    }
  },

  // Actions - Modals
  openLoginModal: () => set({ loginModalOpen: true }),
  closeLoginModal: () => set({ loginModalOpen: false }),
  openProcurementModal: () => set({ procurementModalOpen: true }),
  closeProcurementModal: () => set({ procurementModalOpen: false, selectedProcurement: null }),
  openCreateProcurementModal: () => set({ createProcurementModalOpen: true }),
  closeCreateProcurementModal: () => set({ createProcurementModalOpen: false }),
  openDepositModal: () => set({ depositModalOpen: true }),
  closeDepositModal: () => set({ depositModalOpen: false }),

  // Actions - Sidebar
  toggleSidebar: () => set({ sidebarOpen: !get().sidebarOpen }),
  closeSidebar: () => set({ sidebarOpen: false }),

  // Actions - Toast
  addToast: (message, type = 'info') => {
    const id = Date.now();
    const toast = { id, message, type };
    set({ toasts: [...get().toasts, toast] });
    setTimeout(() => {
      get().removeToast(id);
    }, 3000);
  },

  removeToast: (id) => {
    set({ toasts: get().toasts.filter((t) => t.id !== id) });
  },
}));
