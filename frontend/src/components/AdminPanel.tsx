import {
  BarChart,
  Storage,
  ExitToApp,
  AccountCircle,
  InsertDriveFile
} from '@mui/icons-material';
import {
  AppBar,
  Avatar,
  Box,
  Button,
  Card,
  CircularProgress,
  Container,
  Tab,
  Tabs,
  Toolbar,
  Typography,
  useTheme
} from '@mui/material';
import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import DocsManager from './DocsManager';
import Stats from './Stats';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`admin-tabpanel-${index}`}
      aria-labelledby={`admin-tab-${index}`}
      {...other}
    >
      {value === index && (
        <Box sx={{
          p: { xs: 2, sm: 3, md: 4 },
          minHeight: '50vh',
          background: 'transparent',
        }}>
          {children}
        </Box>
      )}
    </div>
  );
}

function a11yProps(index: number) {
  return {
    id: `admin-tab-${index}`,
    'aria-controls': `admin-tabpanel-${index}`,
  };
}

const AdminPanel: React.FC = () => {
  const navigate = useNavigate();
  const theme = useTheme();
  const [tabValue, setTabValue] = React.useState(0);
  const [anchorEl, setAnchorEl] = React.useState<null | HTMLElement>(null);
  const [notificationCount, setNotificationCount] = React.useState(3);
  const [isAuthenticated, setIsAuthenticated] = React.useState(false);
  const [isLoading, setIsLoading] = React.useState(true);
  const [adminUsername, setAdminUsername] = React.useState<string>('');

  // Auth kontrolü
  useEffect(() => {
    const checkAuth = async () => {
      const token = localStorage.getItem('adminToken');
      const username = localStorage.getItem('adminUsername');
      
      if (!token) {
        navigate('/admin/login');
        return;
      }

      // Set the username from localStorage
      if (username) {
        setAdminUsername(username);
      }

      try {
        const response = await fetch('/admin/verify', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ token })
        });

        if (response.ok) {
          setIsAuthenticated(true);
        } else {
          localStorage.removeItem('adminToken');
          localStorage.removeItem('adminUsername');
          navigate('/admin/login');
        }
      } catch (error) {
        console.error('Auth check failed:', error);
        localStorage.removeItem('adminToken');
        localStorage.removeItem('adminUsername');
        navigate('/admin/login');
      } finally {
        setIsLoading(false);
      }
    };

    checkAuth();
  }, [navigate]);

  if (isLoading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" height="100vh">
        <CircularProgress />
      </Box>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  const handleProfileMenuOpen = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleProfileMenuClose = () => {
    setAnchorEl(null);
  };

  const handleLogout = async () => {
    handleProfileMenuClose();

    // Token'ı önce al
    const token = localStorage.getItem('adminToken');
    
    // Sonra localStorage'ı temizle
    localStorage.removeItem('adminToken');
    localStorage.clear();
    
    // Authentication state'ini güncelle
    setIsAuthenticated(false);
    
    // Backend'e logout isteği gönder (arka planda)
    if (token) {
      try {
        fetch('/admin/logout', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ token })
        }).catch(error => console.error('Logout error:', error));
      } catch (error) {
        console.error('Logout error:', error);
      }
    }

    // Direkt yönlendirme - timeout yok
    window.location.href = '/admin/login';
  };

  return (
    <Box sx={{
      minHeight: '100vh',
      background: 'linear-gradient(135deg, #f8fafc 0%, #e2e8f0 25%, #cbd5e1 100%)',
      position: 'relative',
    }}>
      {/* Header */}
      <AppBar
        position="static"
        elevation={0}
        sx={{
          background: 'linear-gradient(135deg, #1e3a8a 0%, #3b82f6 50%, #1e40af 100%)',
          backdropFilter: 'blur(10px)',
          borderBottom: `1px solid rgba(59, 130, 246, 0.2)`,
          boxShadow: '0 4px 20px rgba(30, 58, 138, 0.15)',
        }}
      >
        <Toolbar sx={{
          minHeight: { xs: 60, sm: 70 },
          px: { xs: 2, sm: 3 },
          flexDirection: { xs: 'column', sm: 'row' },
          py: { xs: 1, sm: 0 }
        }}>
          {/* Admin Panel başlığı */}
          <Box sx={{
            display: 'flex',
            alignItems: 'center',
            flexGrow: 1,
            mb: { xs: 1, sm: 0 }
          }}>
            <Box sx={{
              display: 'flex',
              alignItems: 'center',
              mr: { xs: 0, sm: 2 },
              justifyContent: { xs: 'center', sm: 'flex-start' },
              width: { xs: '100%', sm: 'auto' }
            }}>
              { }
              <Avatar
                alt="DocuMind AI Admin"
                sx={{
                  mr: { xs: 2, sm: 3 },
                  background: '#ffffff',
                  color: '#1e3a8a',
                  width: { xs: 40, sm: 50 },
                  height: { xs: 40, sm: 50 },
                  border: '3px solid rgba(255, 255, 255, 0.8)',
                  boxShadow: '0 4px 12px rgba(0, 0, 0, 0.1)',
                  fontWeight: 'bold',
                  fontSize: { xs: '1rem', sm: '1.2rem' },
                }}
              >
                DM
              </Avatar>
              <Box sx={{ textAlign: { xs: 'center', sm: 'left' } }}>
                <Typography
                  variant="h5"
                  component="div"
                  sx={{
                    fontWeight: 700,
                    color: '#ffffff',
                    lineHeight: 1.2,
                    textShadow: '0 2px 4px rgba(0, 0, 0, 0.1)',
                    fontFamily: '"Segoe UI", Tahoma, Geneva, Verdana, sans-serif',
                    fontSize: { xs: '1.3rem', sm: '1.5rem' }
                  }}
                >
                  DocuMind AI Admin
                </Typography>
                <Typography
                  variant="body2"
                  sx={{
                    opacity: 0.9,
                    color: '#e0f2fe',
                    fontSize: { xs: '0.8rem', sm: '0.9rem' },
                    fontWeight: 500,
                    display: { xs: 'none', sm: 'block' }
                  }}
                >
                  Sistem Yönetimi & İstatistikler
                </Typography>
              </Box>
            </Box>
          </Box>
          
          {/* User Info and Logout Section */}
          <Box sx={{ 
            display: 'flex', 
            alignItems: 'center', 
            gap: { xs: 1, sm: 2 },
            flexDirection: 'row',
            mt: { xs: 1, sm: 0 }
          }}>
            {/* User Info */}
            <Box sx={{ 
              display: 'flex', 
              alignItems: 'center', 
              gap: 1,
              color: 'white',
              backgroundColor: 'rgba(255, 255, 255, 0.1)',
              px: { xs: 1.5, sm: 2 },
              py: { xs: 0.5, sm: 1 },
              borderRadius: 2,
              border: '1px solid rgba(255, 255, 255, 0.2)'
            }}>
              <AccountCircle sx={{ 
                fontSize: { xs: '1.125rem', sm: '1.25rem' },
                color: 'rgba(255, 255, 255, 0.9)'
              }} />
              <Typography 
                variant="body2" 
                sx={{ 
                  fontWeight: 600,
                  fontSize: { xs: '0.75rem', sm: '0.875rem' },
                  color: 'rgba(255, 255, 255, 0.95)',
                  whiteSpace: 'nowrap'
                }}
              >
                {adminUsername || 'Admin'}
              </Typography>
            </Box>

            {/* Logout Button */}
            <Button
              onClick={handleLogout}
              variant="outlined"
              size="small"
              sx={{
                color: 'white',
                borderColor: 'rgba(255, 255, 255, 0.3)',
                backgroundColor: 'rgba(255, 255, 255, 0.1)',
                '&:hover': {
                  borderColor: 'rgba(255, 255, 255, 0.5)',
                  backgroundColor: 'rgba(255, 255, 255, 0.2)',
                },
                textTransform: 'none',
                fontWeight: 600,
                fontSize: { xs: '0.75rem', sm: '0.875rem' },
                px: { xs: 1.5, sm: 2 },
                py: { xs: 0.5, sm: 1 },
                whiteSpace: 'nowrap'
              }}
              startIcon={<ExitToApp sx={{ fontSize: { xs: '1rem', sm: '1.125rem' } }} />}
            >
              Çıkış Yap
            </Button>
          </Box>
        </Toolbar>
      </AppBar>

      {/* Profile Menu */}
      {/* Kaldırıldı: Bildirimler ve Hesap menüsü */}

      {/* Main Content */}
      <Container
        maxWidth="xl"
        sx={{
          pb: { xs: 4, sm: 6 },
          position: 'relative',
          pt: { xs: 2, sm: 3 },
          px: { xs: 1, sm: 2, md: 3 }
        }}
      >
        <Card
          elevation={0}
          sx={{
            background: 'linear-gradient(135deg, rgba(248, 250, 252, 0.95) 0%, rgba(241, 245, 249, 0.95) 100%)',
            backdropFilter: 'blur(15px)',
            border: `1px solid rgba(30, 58, 138, 0.08)`,
            borderRadius: { xs: 2, sm: 3 },
            overflow: 'hidden',
            boxShadow: '0 10px 40px rgba(30, 58, 138, 0.08)',
          }}
        >
          {/* Tabs Header */}
          <Box
            sx={{
              borderBottom: `1px solid rgba(30, 58, 138, 0.1)`,
              background: 'linear-gradient(135deg, rgba(255, 255, 255, 0.8) 0%, rgba(248, 250, 252, 0.8) 100%)',
            }}
          >
            <Tabs
              value={tabValue}
              onChange={handleTabChange}
              variant="standard"
              aria-label="admin panel tabs"
              sx={{
                px: { xs: 1, sm: 4 },
                py: 1,
                '& .MuiTab-root': {
                  textTransform: 'none',
                  fontWeight: 600,
                  fontSize: { xs: '0.72rem', sm: '1rem' },
                  minHeight: { xs: 40, sm: 56 },
                  minWidth: { xs: 90, sm: 160 },
                  color: '#64748b',
                  borderRadius: 3,
                  mx: { xs: 0.25, sm: 1 },
                  px: { xs: 1, sm: 2 },
                  py: { xs: 0.5, sm: 1 },
                  transition: 'all 0.3s ease-in-out',
                  whiteSpace: 'normal',
                  lineHeight: 1.1,
                  '&:hover': {
                    bgcolor: 'rgba(30, 58, 138, 0.05)',
                    color: '#1e3a8a',
                  },
                  '&.Mui-selected': {
                    color: '#1e3a8a',
                    bgcolor: 'rgba(30, 58, 138, 0.08)',
                    boxShadow: '0 2px 8px rgba(30, 58, 138, 0.15)',
                    '& .MuiSvgIcon-root': {
                      color: '#1e3a8a',
                    }
                  }
                },
                '& .MuiTabs-indicator': {
                  height: 3,
                  borderRadius: 2,
                  background: 'linear-gradient(90deg, #1e3a8a 0%, #3b82f6 100%)',
                }
              }}
            >
              <Tab
                icon={<BarChart sx={{ fontSize: { xs: 18, sm: 24 } }} />} 
                iconPosition="start"
                label="İstatistikler & Raporlar"
                {...a11yProps(0)}
              />
              <Tab
                icon={<Storage sx={{ fontSize: { xs: 18, sm: 24 } }} />} 
                iconPosition="start"
                label="Dosya Yönetimi"
                {...a11yProps(1)}
              />
            </Tabs>
          </Box>

          {/* Tab Content */}
          <Box sx={{ minHeight: '60vh' }}>
            <TabPanel value={tabValue} index={0}>
              <Stats />
            </TabPanel>
            <TabPanel value={tabValue} index={1}>
              <DocsManager />
            </TabPanel>
          </Box>
        </Card>
      </Container>
    </Box>
  );
};

export default AdminPanel;
