import React from 'react';
import ReactMarkdown from 'react-markdown';
import { ListItem, ListItemText, Avatar } from '@mui/material';

function ChatMessage({ message }) {
  const isUser = message.sender === 'user';

  return (
    <ListItem
      sx={{
        justifyContent: isUser ? 'flex-end' : 'flex-start',
        marginBottom: '10px',
      }}
    >
      {!isUser && (
        <Avatar
          src="/labassistant.avif" // Updated path
          alt="Medical Lab Assistant Avatar"
          sx={{ mr: 1, width: 48, height: 48 }} // Slightly bigger avatars
        />
      )}
      <ListItemText
        primary={<ReactMarkdown>{message.text}</ReactMarkdown>}
        secondary={message.time}
        sx={{
          backgroundColor: isUser ? '#66bb6a' : '#00b0ff', // User: #66bb6a, Assistant: #00b0ff
          color: 'white', // Set text color to white for readability on these backgrounds
          borderRadius: '15px',
          padding: '10px 15px',
          maxWidth: '70%',
          wordBreak: 'break-word',
          boxShadow: '0 1px 2px rgba(0,0,0,0.1)',
          marginLeft: !isUser ? '10px' : '0',
          marginRight: isUser ? '10px' : '0',
          '& .MuiListItemText-secondary': {
            fontSize: '0.75rem',
            color: 'rgba(255,255,255,0.7)', // Lighter white for time
            textAlign: isUser ? 'right' : 'left',
            marginTop: '5px',
          },
        }}
      />
      {isUser && (
        <Avatar
          src="/user.avif" // Updated path
          alt="User Avatar"
          sx={{ ml: 1, width: 48, height: 48 }} // Slightly bigger avatars
        />
      )}
    </ListItem>
  );
}

export default ChatMessage;