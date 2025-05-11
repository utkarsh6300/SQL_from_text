import { Outlet, useNavigate } from 'react-router-dom';
import { AppBar, Toolbar, Typography, Button, Container, Box } from '@mui/material';
import AddIcon from '@mui/icons-material/Add';

function Layout() {
  const navigate = useNavigate();

  return (
    <Box sx={{ 
      display: 'flex', 
      flexDirection: 'column', 
      minHeight: '100vh', 
      width: '100%' 
    }}>
      <AppBar position="static">
        <Container maxWidth="lg">
          <Toolbar>
            <Typography 
              variant="h6" 
              component="div" 
              sx={{ flexGrow: 1, cursor: 'pointer' }}
              onClick={() => navigate('/')}
            >
              Text to SQL Generator
            </Typography>
            <Button 
              color="inherit" 
              startIcon={<AddIcon />}
              onClick={() => navigate('/new-project')}
            >
              New Project
            </Button>
          </Toolbar>
        </Container>
      </AppBar>
      <Box sx={{ 
        display: 'flex', 
        flexDirection: 'column', 
        flexGrow: 1, 
        width: '100%', 
        alignItems: 'center' 
      }}>
        <Container 
          maxWidth="lg" 
          sx={{ 
            mt: 4,
            width: '100%',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center'
          }}
        >
          <Outlet />
        </Container>
      </Box>
    </Box>
  );
}

export default Layout;