import React, { useState, useRef, useEffect } from 'react';
import { fetchAuthSession } from 'aws-amplify/auth';
import ReactMarkdown from 'react-markdown';
import { awsConfig } from '../aws-config';
import './ContractChat.css';

const API_ENDPOINT = awsConfig.API.REST.ContractAnalyzer.endpoint.replace(/\/$/, '');

function ContractChat({ contractId }) {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const sendMessage = async (e) => {
    e.preventDefault();
    
    if (!inputMessage.trim()) return;

    const userMessage = inputMessage.trim();
    setInputMessage('');
    setError('');

    // Add user message to chat
    const newUserMessage = {
      role: 'user',
      content: userMessage,
      timestamp: new Date().toISOString()
    };
    setMessages(prev => [...prev, newUserMessage]);
    setLoading(true);

    try {
      const session = await fetchAuthSession();
      const token = session.tokens?.idToken?.toString();

      const response = await fetch(
        `${API_ENDPOINT}/contracts/${contractId}/chat`,
        {
          method: 'POST',
          headers: {
            'Authorization': token,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            contractId,
            message: userMessage,
            history: messages
          })
        }
      );

      const data = await response.json();

      if (response.ok) {
        const botMessage = {
          role: 'assistant',
          content: data.message,
          timestamp: new Date().toISOString()
        };
        setMessages(prev => [...prev, botMessage]);
      } else {
        setError(data.error || 'Failed to get response');
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const clearChat = () => {
    setMessages([]);
    setError('');
  };

  const toggleChat = () => {
    setIsOpen(!isOpen);
  };

  const closeChat = () => {
    setIsOpen(false);
  };

  return (
    <>
      {/* Floating Chat Button */}
      <button 
        className="chat-widget-button" 
        onClick={toggleChat}
        aria-label="Open chat"
      >
        <span className="chat-icon">💬</span>
        <span className="chat-label">Ask Questions</span>
      </button>

      {/* Chat Overlay */}
      {isOpen && (
        <div className="chat-overlay" onClick={closeChat}>
          <div className="chat-container" onClick={(e) => e.stopPropagation()}>
            <div className="chat-header">
              <h3>💬 Ask Questions About This Contract</h3>
              <div className="chat-header-actions">
                {messages.length > 0 && (
                  <button onClick={clearChat} className="btn-clear-chat">
                    Clear
                  </button>
                )}
                <button onClick={closeChat} className="btn-close-chat">
                  ✕
                </button>
              </div>
            </div>

      <div className="chat-messages">
        {messages.length === 0 ? (
          <div className="chat-empty-state">
            <p>👋 Hi! I'm your contract assistant.</p>
            <p>Ask me anything about this contract:</p>
            <ul>
              <li>"What are the payment terms?"</li>
              <li>"Who are the parties involved?"</li>
              <li>"What are the key deadlines?"</li>
              <li>"Summarize the termination clause"</li>
            </ul>
          </div>
        ) : (
          messages.map((msg, idx) => (
            <div key={idx} className={`message message-${msg.role}`}>
              <div className="message-avatar">
                {msg.role === 'user' ? '👤' : '🤖'}
              </div>
              <div className="message-content">
                <div className="message-text">
                  {msg.role === 'assistant' ? (
                    <ReactMarkdown>{msg.content}</ReactMarkdown>
                  ) : (
                    msg.content
                  )}
                </div>
                <div className="message-time">
                  {new Date(msg.timestamp).toLocaleTimeString()}
                </div>
              </div>
            </div>
          ))
        )}
        {loading && (
          <div className="message message-assistant">
            <div className="message-avatar">🤖</div>
            <div className="message-content">
              <div className="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {error && <div className="chat-error">{error}</div>}

      <form onSubmit={sendMessage} className="chat-input-form">
        <input
          type="text"
          value={inputMessage}
          onChange={(e) => setInputMessage(e.target.value)}
          placeholder="Type your question..."
          className="chat-input"
          disabled={loading}
        />
        <button 
          type="submit" 
          className="btn-send"
          disabled={loading || !inputMessage.trim()}
        >
          Send
        </button>
      </form>
          </div>
        </div>
      )}
    </>
  );
}

export default ContractChat;
