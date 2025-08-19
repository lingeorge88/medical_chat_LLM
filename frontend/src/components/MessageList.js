import React, { useRef, useEffect } from 'react';
import { List, Typography, CircularProgress, Box } from '@mui/material';
import ChatMessage from './ChatMessage';

function MessageList({ messages, loading }) {
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  return (
    <List sx={{ flexGrow: 1, overflowY: 'auto', padding: '10px', paddingBottom: '100px' }}> {/* Added paddingBottom for fixed input */}
      {messages.map((message, index) => (
        <ChatMessage key={index} message={message} />
      ))}
      {loading && (
        <Box sx={{ display: 'flex', justifyContent: 'center', mt: 2 }}>
          <CircularProgress size={20} color="inherit" />
          <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.7)', ml: 1 }}>
            Assistant is searching the knowledge base for the best answer
          </Typography>
        </Box>
      )}
      <div ref={messagesEndRef} />
    </List>
  );
}

export default MessageList;