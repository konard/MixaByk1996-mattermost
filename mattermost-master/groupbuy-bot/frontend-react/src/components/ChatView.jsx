import React, { useEffect, useState, useRef, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useStore } from '../store/useStore';
import { useWebSocket } from '../hooks/useWebSocket';
import {
  formatTime,
  formatMessageDate,
  getInitials,
  getAvatarColor,
} from '../utils/helpers';
import { BackIcon, MoreIcon, AttachIcon, SendIcon } from './Icons';

function ChatView() {
  const { procurementId } = useParams();
  const navigate = useNavigate();
  const [messageText, setMessageText] = useState('');
  const messageAreaRef = useRef(null);
  const textareaRef = useRef(null);

  const {
    user,
    messages,
    procurements,
    loadMessages,
    sendMessage,
    setCurrentChat,
    closeSidebar,
    selectProcurement,
  } = useStore();

  const { sendTyping } = useWebSocket(procurementId);

  const currentProcurement = procurements.find(
    (p) => p.id === parseInt(procurementId)
  );

  useEffect(() => {
    if (procurementId) {
      setCurrentChat(parseInt(procurementId));
      loadMessages(procurementId);
    }
  }, [procurementId, setCurrentChat, loadMessages]);

  useEffect(() => {
    if (messageAreaRef.current) {
      messageAreaRef.current.scrollTop = messageAreaRef.current.scrollHeight;
    }
  }, [messages]);

  const handleBack = () => {
    navigate('/');
    closeSidebar();
  };

  const handleOpenDetails = () => {
    if (currentProcurement) {
      selectProcurement(currentProcurement.id);
    }
  };

  const handleSendMessage = useCallback(async () => {
    const text = messageText.trim();
    if (!text || !user) return;

    setMessageText('');
    await sendMessage(text);

    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  }, [messageText, user, sendMessage]);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleInput = () => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height =
        Math.min(textareaRef.current.scrollHeight, 150) + 'px';
    }
    sendTyping();
  };

  const formatMessageText = (text) => {
    if (!text) return '';
    // Convert URLs to links
    let formatted = text.replace(
      /(https?:\/\/[^\s]+)/g,
      '<a href="$1" target="_blank" rel="noopener">$1</a>'
    );
    // Convert line breaks
    formatted = formatted.replace(/\n/g, '<br>');
    return formatted;
  };

  const renderMessages = () => {
    if (!messages || messages.length === 0) {
      return (
        <div className="p-lg text-center text-muted">
          <p>Нет сообщений</p>
        </div>
      );
    }

    let lastDate = null;
    const elements = [];

    messages.forEach((msg, index) => {
      const msgDate = new Date(msg.created_at).toDateString();
      if (msgDate !== lastDate) {
        elements.push(
          <div key={`date-${index}`} className="message-date-divider">
            <span>{formatMessageDate(msg.created_at)}</span>
          </div>
        );
        lastDate = msgDate;
      }

      const isOwn = user && msg.user && msg.user.id === user.id;

      if (msg.message_type === 'system') {
        elements.push(
          <div key={msg.id || index} className="message system">
            {msg.text}
          </div>
        );
      } else {
        elements.push(
          <div
            key={msg.id || index}
            className={`message ${isOwn ? 'outgoing' : 'incoming'}`}
          >
            {!isOwn && msg.user && (
              <div className="message-sender">{msg.user.first_name}</div>
            )}
            <div
              className="message-text"
              dangerouslySetInnerHTML={{ __html: formatMessageText(msg.text) }}
            />
            <div className="message-time">{formatTime(msg.created_at)}</div>
          </div>
        );
      }
    });

    return elements;
  };

  if (!currentProcurement) {
    return (
      <div className="flex flex-col items-center justify-center" style={{ flex: 1 }}>
        <p className="text-muted">Закупка не найдена</p>
        <button className="btn btn-primary mt-md" onClick={handleBack}>
          Вернуться
        </button>
      </div>
    );
  }

  return (
    <>
      <header className="header">
        <button className="btn btn-icon mobile-back" onClick={handleBack}>
          <BackIcon />
        </button>
        <div
          className="chat-avatar"
          style={{ backgroundColor: getAvatarColor(currentProcurement.title) }}
        >
          {getInitials(currentProcurement.title)}
        </div>
        <div className="flex-col">
          <h2 className="header-title">{currentProcurement.title}</h2>
          <p className="header-subtitle">
            {currentProcurement.participant_count || 0} участников
          </p>
        </div>
        <button className="btn btn-icon" onClick={handleOpenDetails}>
          <MoreIcon />
        </button>
      </header>

      <div className="message-area" ref={messageAreaRef}>
        {renderMessages()}
      </div>

      <div className="message-input-area">
        <button className="btn btn-icon" aria-label="Attach file">
          <AttachIcon />
        </button>
        <div className="message-input-container">
          <textarea
            ref={textareaRef}
            className="message-input"
            placeholder="Сообщение..."
            rows="1"
            value={messageText}
            onChange={(e) => setMessageText(e.target.value)}
            onKeyDown={handleKeyDown}
            onInput={handleInput}
          />
        </div>
        <button
          className="send-button"
          aria-label="Send message"
          onClick={handleSendMessage}
        >
          <SendIcon />
        </button>
      </div>
    </>
  );
}

export default ChatView;
