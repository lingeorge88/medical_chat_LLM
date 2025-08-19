import React, { useState } from 'react';
import { Box } from '@mui/material';
import MessageList from './MessageList';
import MessageInput from './MessageInput';

function ChatContainer() {
  const [messages, setMessages] = useState([
    {
      text: "Hello! I am your Medical Lab Assistant. I can provide information about medical laboratory equipment, procedures, and diagnostics based on the provided documentation. Ask me anything related to these topics!",
      time: new Date().getHours() + ":" + new Date().getMinutes(),
      sender: 'bot' // Keep sender as 'bot' for internal logic/styling
    }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSend = async (e) => {
    e.preventDefault();
    if (input.trim() === '') return;

    const date = new Date();
    const hour = date.getHours();
    const minute = date.getMinutes();
    const str_time = hour + ":" + minute;

    const userMessage = {
      text: input,
      time: str_time,
      sender: 'user'
    };

    setMessages(prevMessages => [...prevMessages, userMessage]);
    setInput(''); // Clear input immediately after sending
    setLoading(true); // Set loading to true before API call

    try {
      const response = await fetch('http://localhost:8080/get', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: `msg=${userMessage.text}`,
      });
      const data = await response.text();
      const botMessage = {
        text: data,
        time: str_time,
        sender: 'bot'
      };
      setMessages(prevMessages => [...prevMessages, botMessage]);
    } catch (error) {
      console.error("Error fetching response:", error);
      const errorMessage = {
        text: "Sorry, something went wrong. Please try again later.",
        time: str_time,
        sender: 'bot'
      };
      setMessages(prevMessages => [...prevMessages, errorMessage]);
    } finally {
      setLoading(false); // Set loading to false after API call (success or error)
    }
  };

  return (
    <Box
      sx={{
        height: '100vh',
        display: 'flex',
        flexDirection: 'column',
        width: '100%', // Full width
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
          width: '100%', // Full width
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