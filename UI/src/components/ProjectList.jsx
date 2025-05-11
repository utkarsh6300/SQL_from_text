import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Card,
  CardContent,
  CardActions,
  Typography,
  Button,
  Grid,
  CircularProgress
} from '@mui/material';
import ChatIcon from '@mui/icons-material/Chat';
import { projectApi } from '../services/api';

function ProjectList({ onError }) {
  const navigate = useNavigate();
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadProjects();
  }, []);

  const loadProjects = async () => {
    try {
      const data = await projectApi.getProjects();
      setProjects(data);
    } catch (err) {
      onError(err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4, width: '100%' }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ width: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
      <Typography variant="h4" sx={{ mb: 4, textAlign: 'center' }}>Your Projects</Typography>

      {projects.length === 0 ? (
        <Typography color="text.secondary" sx={{ textAlign: 'center' }}>
          No projects yet. Click "New Project" to create one.
        </Typography>
      ) : (
        <Grid container spacing={3} sx={{ width: '100%', justifyContent: 'center' }}>
          {projects.map((project) => (
            <Grid item xs={12} sm={6} md={4} key={project.id}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    {project.name}
                  </Typography>
                  <Typography color="text.secondary">
                    {project.chatsCount || 0} chats
                  </Typography>
                </CardContent>
                <CardActions>
                  <Button 
                    size="small" 
                    startIcon={<ChatIcon />}
                    onClick={() => navigate(`/project/${project.id}/chat`)}
                  >
                    Open Chat
                  </Button>
                </CardActions>
              </Card>
            </Grid>
          ))}
        </Grid>
      )}
    </Box>
  );
}

export default ProjectList;