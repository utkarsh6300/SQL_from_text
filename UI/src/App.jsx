import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { ThemeProvider, createTheme, CssBaseline } from '@mui/material';
import Layout from './components/Layout';
import ProjectList from './components/ProjectList';
import NewProject from './components/NewProject';
import ChatView from './components/ChatView';
import ApiErrorBoundary from './components/ApiErrorBoundary';

const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#dc004e',
    },
  },
});

function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <div style={{ 
        display: 'flex', 
        flexDirection: 'column', 
        minHeight: '100vh',
        margin: '0 auto',
        width: '100%', // Reduced width to create margins
        alignItems: 'center', // Centers content horizontally
        paddingTop: '2rem',
        paddingLeft: '38rem',
      }}>
        <ApiErrorBoundary>
          {(handleError) => (
            <BrowserRouter>
              <Routes>
                <Route path="/" element={<Layout />}>
                  <Route index element={<ProjectList onError={handleError} />} />
                  <Route path="new-project" element={<NewProject onError={handleError} />} />
                  <Route path="project/:projectId/chat/:chatId?" element={<ChatView onError={handleError} />} />
                </Route>
              </Routes>
            </BrowserRouter>
          )}
        </ApiErrorBoundary>
      </div>
    </ThemeProvider>
  );
}

export default App;
