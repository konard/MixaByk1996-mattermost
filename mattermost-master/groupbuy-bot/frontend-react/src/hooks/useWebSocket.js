import { useEffect, useCallback } from 'react';
import { wsManager } from '../services/websocket';
import { useStore } from '../store/useStore';

export function useWebSocket(procurementId) {
  const { addMessage } = useStore();

  useEffect(() => {
    if (!procurementId) return;

    wsManager.connect(procurementId);

    const unsubscribeMessage = wsManager.on('message', (message) => {
      addMessage(message);
    });

    return () => {
      unsubscribeMessage();
      wsManager.disconnect();
    };
  }, [procurementId, addMessage]);

  const sendMessage = useCallback((message) => {
    wsManager.sendMessage(message);
  }, []);

  const sendTyping = useCallback(() => {
    wsManager.sendTyping();
  }, []);

  return { sendMessage, sendTyping };
}
