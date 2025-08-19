import React from 'react';
import { TextField, Button } from '@mui/material';
import SendIcon from '@mui/icons-material/Send';

function MessageInput({ input, setInput, handleSend }) {
  return (
    <form onSubmit={handleSend} style={{ padding: '10px', display: 'flex', alignItems: 'center' }}>
      <TextField
        fullWidth
        variant="outlined"
        placeholder="Type your message..."
        value={input}
        onChange={(e) => setInput(e.target.value)}
        sx={{
          marginRight: '5px', // Reduced margin to make TextField wider
          '& .MuiOutlinedInput-root': {
            borderRadius: '25px', // Rounded corners for the input field
            backgroundColor: 'rgba(255, 255, 255, 0.1)', // Slightly transparent background
            color: 'white', // Text color
            '& fieldset': {
              borderColor: 'rgba(255, 255, 255, 0.3)', // Border color
            },
            '&:hover fieldset': {
              borderColor: 'rgba(255, 255, 255, 0.5)', // Hover border color
            },
            '&.Mui-focused fieldset': {
              borderColor: '#90caf9', // Focused border color
            },
          },
          '& .MuiInputBase-input': {
            color: 'white', // Input text color
          },
          '& .MuiInputLabel-root': {
            color: 'rgba(255, 255, 255, 0.7)', // Placeholder color
          },
        }}
        aria-label="Type your message"
      />
      <Button
        type="submit"
        variant="contained"
        color="primary"
        endIcon={<SendIcon />}
        sx={{
          borderRadius: '25px', // Rounded corners for the button
          padding: '12px 20px',
          backgroundColor: '#4CAF50', // Green send button
          '&:hover': {
            backgroundColor: '#45a049',
          },
        }}
      >
        Send
      </Button>
    </form>
  );
}

export default MessageInput;