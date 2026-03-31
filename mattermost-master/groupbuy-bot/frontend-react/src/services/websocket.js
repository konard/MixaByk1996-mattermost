class WebSocketManager {
  constructor() {
    this.connection = null;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.listeners = new Map();
  }

  connect(procurementId) {
    const token = localStorage.getItem('authToken') || '';
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/procurement/${procurementId}/?token=${token}`;

    this.connection = new WebSocket(wsUrl);

    this.connection.onopen = () => {
      console.log('WebSocket connected');
      this.reconnectAttempts = 0;
      this.emit('connected');
    };

    this.connection.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        this.handleMessage(data);
      } catch (error) {
        console.error('WebSocket message parse error:', error);
      }
    };

    this.connection.onclose = () => {
      console.log('WebSocket disconnected');
      this.emit('disconnected');
      this.attemptReconnect(procurementId);
    };

    this.connection.onerror = (error) => {
      console.error('WebSocket error:', error);
      this.emit('error', error);
    };
  }

  disconnect() {
    if (this.connection) {
      this.connection.close();
      this.connection = null;
    }
  }

  send(data) {
    if (this.connection && this.connection.readyState === WebSocket.OPEN) {
      this.connection.send(JSON.stringify(data));
    }
  }

  handleMessage(data) {
    switch (data.type) {
      case 'message':
        this.emit('message', data.message);
        break;
      case 'typing':
        this.emit('typing', data.user);
        break;
      case 'user_joined':
        this.emit('user_joined', data.user);
        break;
      case 'user_left':
        this.emit('user_left', data.user);
        break;
      default:
        this.emit(data.type, data);
    }
  }

  attemptReconnect(procurementId) {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      const delay = 2000 * this.reconnectAttempts;
      console.log(`Attempting to reconnect in ${delay}ms...`);
      setTimeout(() => this.connect(procurementId), delay);
    }
  }

  sendTyping() {
    this.send({ type: 'typing' });
  }

  sendMessage(message) {
    this.send({ type: 'message', message });
  }

  on(event, callback) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set());
    }
    this.listeners.get(event).add(callback);
    return () => this.off(event, callback);
  }

  off(event, callback) {
    const callbacks = this.listeners.get(event);
    if (callbacks) {
      callbacks.delete(callback);
    }
  }

  emit(event, data) {
    const callbacks = this.listeners.get(event);
    if (callbacks) {
      callbacks.forEach((callback) => callback(data));
    }
  }
}

export const wsManager = new WebSocketManager();
