import { useState, useEffect, useRef } from 'react';
import { useParams } from 'react-router-dom';
import {
  Box,
  Paper,
  TextField,
  Button,
  Typography,
  Stack,
  IconButton,
  CircularProgress,
  Alert,
} from '@mui/material';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { materialDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import CancelIcon from '@mui/icons-material/Cancel';
import AddCircleIcon from '@mui/icons-material/AddCircle';
import { projectApi, chatApi } from '../services/api';

function ChatView({ onError }) {
  const { projectId, chatId } = useParams();
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [project, setProject] = useState(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    loadProjectAndChat();
  }, [projectId, chatId]);

  const loadProjectAndChat = async () => {
    try {
      const [projectData, chatData] = await Promise.all([
        projectApi.getProject(projectId),
        chatId ? chatApi.getChats(projectId) : chatApi.createChat(projectId)
      ]);
      
      setProject(projectData);
      setMessages(chatData.messages || []);
    } catch (err) {
      onError(err);
    } finally {
      setLoading(false);
    }
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim() || generating) return;

    const newMessage = {
      id: Date.now(),
      text: input,
      sql: null,
      correct: null,
    };

    setMessages(prev => [...prev, newMessage]);
    setInput('');
    setGenerating(true);

    try {
      const response = await chatApi.generateSql(projectId, chatId, input);
      setMessages(prev => prev.map(msg => 
        msg.id === newMessage.id 
          ? { ...msg, sql: response.sql }
          : msg
      ));
    } catch (err) {
      onError(err);
      setMessages(prev => prev.filter(msg => msg.id !== newMessage.id));
    } finally {
      setGenerating(false);
    }
  };

  const handleFeedback = async (messageId, isCorrect) => {
    setMessages(prev => prev.map(msg => 
      msg.id === messageId 
        ? { ...msg, correct: isCorrect }
        : msg
    ));

    if (!isCorrect) {
      try {
        const response = await chatApi.regenerateSql(projectId, chatId, messageId);
        setMessages(prev => prev.map(msg => 
          msg.id === messageId 
            ? { ...msg, sql: response.sql, correct: null }
            : msg
        ));
      } catch (err) {
        onError(err);
        // Revert the feedback state on error
        setMessages(prev => prev.map(msg => 
          msg.id === messageId 
            ? { ...msg, correct: null }
            : msg
        ));
      }
    }
  };

  const handleAddSample = async (messageId) => {
    const message = messages.find(m => m.id === messageId);
    if (!message || !message.correct) return;

    try {
      await projectApi.addSampleQuery(projectId, {
        text: message.text,
        sql: message.sql
      });
    } catch (err) {
      onError(err);
    }
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ height: 'calc(100vh - 120px)', display: 'flex', flexDirection: 'column' }}>
      <Typography variant="h5" sx={{ mb: 2 }}>
        {project?.name} - Chat
      </Typography>

      <Paper 
        sx={{ 
          flex: 1, 
          mb: 2, 
          p: 2, 
          overflowY: 'auto',
          display: 'flex',
          flexDirection: 'column',
          gap: 2
        }}
      >
        {messages.map((message) => (
          <Box key={message.id}>
            <Typography variant="body1" sx={{ mb: 1 }}>
              {message.text}
            </Typography>
            {message.sql && (
              <Box sx={{ position: 'relative' }}>
                <SyntaxHighlighter 
                  language="sql" 
                  style={materialDark}
                  customStyle={{ margin: 0 }}
                >
                  {message.sql}
                </SyntaxHighlighter>
                <Stack 
                  direction="row" 
                  spacing={1} 
                  sx={{ 
                    position: 'absolute', 
                    top: 8, 
                    right: 8 
                  }}
                >
                  {message.correct === null && (
                    <>
                      <IconButton 
                        size="small" 
                        color="success"
                        onClick={() => handleFeedback(message.id, true)}
                      >
                        <CheckCircleIcon />
                      </IconButton>
                      <IconButton 
                        size="small" 
                        color="error"
                        onClick={() => handleFeedback(message.id, false)}
                      >
                        <CancelIcon />
                      </IconButton>
                    </>
                  )}
                  {message.correct === true && (
                    <IconButton 
                      size="small" 
                      color="primary"
                      onClick={() => handleAddSample(message.id)}
                      title="Add as sample query"
                    >
                      <AddCircleIcon />
                    </IconButton>
                  )}
                </Stack>
              </Box>
            )}
          </Box>
        ))}
        <div ref={messagesEndRef} />
      </Paper>

      <Box component="form" onSubmit={handleSubmit}>
        <TextField
          fullWidth
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Describe the SQL query you need..."
          multiline
          rows={2}
          sx={{ mb: 1 }}
          disabled={generating}
        />
        <Button 
          type="submit" 
          variant="contained"
          disabled={!input.trim() || generating}
        >
          {generating ? <CircularProgress size={24} /> : 'Generate SQL'}
        </Button>
      </Box>
    </Box>
  );
}

export default ChatView;