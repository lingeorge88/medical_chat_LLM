import React, { useState, useCallback } from 'react';
import { Box } from '@mui/material';
import MessageList from './MessageList';
import MessageInput from './MessageInput';

function ChatContainer() {
  const [messages, setMessages] = useState([
    {
      text: "Hello! I am your Medical Lab Assistant. I can provide information about medical laboratory equipment, procedures, and diagnostics based on the provided documentation. Ask me anything related to these topics!",
      time: new Date().getHours() + ":" + new Date().getMinutes(),
      sender: 'bot'
    }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [sessionId] = useState(() => {
    let id = localStorage.getItem('chat_session_id');
    if (!id) {
      id = crypto.randomUUID();
      localStorage.setItem('chat_session_id', id);
    }
    return id;
  });

  const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8080';

  const handleSend = useCallback(async (e) => {
    e.preventDefault();
    if (input.trim() === '' || loading) return;

    const now = new Date();
    const str_time = now.getHours() + ":" + String(now.getMinutes()).padStart(2, '0');

    const userMessage = { text: input, time: str_time, sender: 'user' };
    const botMessage = { text: '', time: str_time, sender: 'bot', streaming: true };

    setMessages(prev => [...prev, userMessage, botMessage]);
    setInput('');
    setLoading(true);

    try {
      const response = await fetch(`${API_URL}/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ msg: input, session_id: sessionId }),
      });

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let accumulated = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ') && line !== 'data: [DONE]') {
            try {
              const data = JSON.parse(line.slice(6));
              accumulated += data.token;
              setMessages(prev => {
                const updated = [...prev];
                updated[updated.length - 1] = {
                  ...updated[updated.length - 1],
                  text: accumulated,
                };
                return updated;
              });
            } catch {
              // skip malformed SSE lines
            }
          }
        }
      }

      setMessages(prev => {
        const updated = [...prev];
        updated[updated.length - 1] = {
          ...updated[updated.length - 1],
          streaming: false,
        };
        return updated;
      });
    } catch (error) {
      console.error("Error fetching response:", error);
      setMessages(prev => {
        const updated = [...prev];
        updated[updated.length - 1] = {
          text: "Sorry, something went wrong. Please try again later.",
          time: str_time,
          sender: 'bot',
          streaming: false,
        };
        return updated;
      });
    } finally {
      setLoading(false);
    }
  }, [input, loading, sessionId, API_URL]);

  return (
    <Box
      sx={{
        height: '100vh',
        display: 'flex',
        flexDirection: 'column',
        width: '100%',
        margin: '0 auto',
        paddingTop: '20px',
      }}
    >
      <Box sx={{ backgroundColor: 'rgba(0,0,0,0.3)', padding: '15px', borderBottom: '1px solid rgba(255,255,255,0.1)', color: 'white', fontSize: '1.2rem', fontWeight: 'bold', textAlign: 'center', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <img src="/applogo.png" alt="App Logo" style={{ height: '30px', marginRight: '10px' }} />
        Medical Lab Assistant
      </Box>
      <MessageList messages={messages} loading={loading} />
      <Box
        sx={{
          position: 'fixed',
          bottom: 0,
          left: 0,
          right: 0,
          width: '100%',
          margin: '0 auto',
          backgroundColor: 'rgba(0,0,0,0.5)',
          padding: '10px 20px',
          boxSizing: 'border-box',
          display: 'flex',
          justifyContent: 'center',
          zIndex: 1000,
        }}
      >
        <MessageInput input={input} setInput={setInput} handleSend={handleSend} />
      </Box>
    </Box>
  );
}

export default ChatContainer;
