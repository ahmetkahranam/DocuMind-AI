import {
  AdminPanelSettings,
  Lock,
  Person,
  Security,
  Visibility,
  VisibilityOff,
} from '@mui/icons-material';
import {
  Alert,
  Avatar,
  Box,
  Button,
  Card,
  CardContent,
  CircularProgress,
  Divider,
  Fade,
  IconButton,
  InputAdornment,
  Stack,
  TextField,
  Typography,
  useTheme,
  Zoom,
} from '@mui/material';
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';

interface LoginCredentials {
  username: string;
  password: string;
}

interface LoginResponse {
  success: boolean;
  message?: string;
  error?: string;
  token?: string;
  admin_id?: number;
  username?: string;
  expires_at?: string;
}

const AdminLogin: React.FC = () => {
  const navigate = useNavigate();
  const theme = useTheme();

  const [credentials, setCredentials] = useState<LoginCredentials>({
    username: '',
    password: '',
  });

  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const handleInputChange = (field: keyof LoginCredentials) => (
    event: React.ChangeEvent<HTMLInputElement>
  ) => {
    setCredentials(prev => ({
      ...prev,
      [field]: event.target.value,
    }));
    // Clear error when user starts typing
    if (error) setError(null);
  };

  const handleTogglePassword = () => {
    setShowPassword(!showPassword);
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();

    if (!credentials.username || !credentials.password) {
      setError('Kullanıcı adı ve şifre gereklidir');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await fetch('/admin/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          username: credentials.username,
          password: credentials.password,
        }),
      });

      const data: LoginResponse = await response.json();

      console.log('Login response:', { status: response.status, ok: response.ok, data });

      if (response.ok && data.success) {
        // Token'ı localStorage'a kaydet
        localStorage.setItem('adminToken', data.token || '');
        localStorage.setItem('adminUsername', data.username || '');
        localStorage.setItem('adminId', data.admin_id?.toString() || '');
        localStorage.setItem('tokenExpiry', data.expires_at || '');

        setSuccess('Giriş başarılı! Yönlendiriliyorsunuz...');

        // Direkt admin paneline yönlendir - timeout yok
        navigate('/admin');
      } else {
        console.error('Login failed:', data);
        setError(data.error || data.message || `Giriş başarısız (${response.status})`);
      }
    } catch (err) {
      console.error('Login error:', err);
      setError(`Sunucu bağlantı hatası: ${err instanceof Error ? err.message : 'Bilinmeyen hata'}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box
      sx={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: `linear-gradient(135deg,
          ${theme.palette.primary.dark} 0%,
          ${theme.palette.background.default} 50%,
          ${theme.palette.secondary.dark} 100%)`,
        p: 2,
        position: 'relative',
      }}
    >
      <Fade in timeout={800}>
        <Card
          sx={{
            maxWidth: 460,
            width: '100%',
            background: 'rgba(255, 255, 255, 0.05)',
            backdropFilter: 'blur(20px)',
            border: '1px solid rgba(100, 150, 200, 0.2)',
            borderRadius: 3,
            overflow: 'visible',
            position: 'relative',
          }}
        >
          <CardContent sx={{ p: { xs: 3, sm: 4 } }}>
            {/* Logo ve Başlık */}
            <Box sx={{ textAlign: 'center', mb: 4 }}>
              <Zoom in timeout={1000}>
                <Avatar
                  alt="DocuMind AI"
                  sx={{
                    width: 80,
                    height: 80,
                    mx: 'auto',
                    mb: 2,
                    border: `3px solid ${theme.palette.primary.main}`,
                    boxShadow: `0 0 20px ${theme.palette.primary.main}40`,
                    fontWeight: 'bold',
                    fontSize: '2rem',
                    bgcolor: '#1e3a8a',
                    color: 'white',
                  }}
                >
                  DM
                </Avatar>
              </Zoom>

              <Typography
                variant="h4"
                component="h1"
                sx={{
                  fontWeight: 700,
                  background: `linear-gradient(45deg,
                    ${theme.palette.primary.light},
                    ${theme.palette.secondary.light})`,
                  backgroundClip: 'text',
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent',
                  mb: 1,
                }}
              >
                Admin Paneli
              </Typography>

              <Stack direction="row" spacing={1} justifyContent="center" alignItems="center" sx={{ mb: 2 }}>
                <Security color="primary" fontSize="small" />
                <Typography variant="body2" color="text.secondary">
                  Güvenli Admin Girişi
                </Typography>
              </Stack>

              <Divider sx={{
                '&::before, &::after': {
                  borderColor: 'rgba(100, 150, 200, 0.3)'
                }
              }} />
            </Box>

            {/* Hata/Başarı Mesajları */}
            {error && (
              <Fade in>
                <Alert
                  severity="error"
                  sx={{
                    mb: 3,
                    background: 'rgba(255, 69, 68, 0.1)',
                    border: '1px solid rgba(255, 69, 68, 0.3)',
                  }}
                >
                  {error}
                </Alert>
              </Fade>
            )}

            {success && (
              <Fade in>
                <Alert
                  severity="success"
                  sx={{
                    mb: 3,
                    background: 'rgba(0, 200, 81, 0.1)',
                    border: '1px solid rgba(0, 200, 81, 0.3)',
                  }}
                >
                  {success}
                </Alert>
              </Fade>
            )}

            {/* Login Form */}
            <Box component="form" onSubmit={handleSubmit}>
              <TextField
                fullWidth
                label="Kullanıcı Adı"
                value={credentials.username}
                onChange={handleInputChange('username')}
                disabled={loading}
                sx={{ mb: 3 }}
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <Person color="primary" />
                    </InputAdornment>
                  ),
                }}
                autoComplete="username"
                autoFocus
              />

              <TextField
                fullWidth
                label="Şifre"
                type={showPassword ? 'text' : 'password'}
                value={credentials.password}
                onChange={handleInputChange('password')}
                disabled={loading}
                sx={{ mb: 4 }}
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <Lock color="primary" />
                    </InputAdornment>
                  ),
                  endAdornment: (
                    <InputAdornment position="end">
                      <IconButton
                        onClick={handleTogglePassword}
                        disabled={loading}
                        edge="end"
                      >
                        {showPassword ? <VisibilityOff /> : <Visibility />}
                      </IconButton>
                    </InputAdornment>
                  ),
                }}
                autoComplete="current-password"
              />

              <Button
                type="submit"
                fullWidth
                variant="contained"
                disabled={loading || !credentials.username || !credentials.password}
                sx={{
                  py: 1.5,
                  fontSize: '1.1rem',
                  fontWeight: 600,
                  background: `linear-gradient(45deg,
                    ${theme.palette.primary.main},
                    ${theme.palette.primary.light})`,
                  '&:hover': {
                    background: `linear-gradient(45deg,
                      ${theme.palette.primary.dark},
                      ${theme.palette.primary.main})`,
                  },
                  '&:disabled': {
                    background: 'rgba(255, 255, 255, 0.1)',
                  },
                }}
                startIcon={
                  loading ? (
                    <CircularProgress size={20} color="inherit" />
                  ) : (
                    <AdminPanelSettings />
                  )
                }
              >
                {loading ? 'Giriş Yapılıyor...' : 'Admin Paneline Giriş'}
              </Button>
            </Box>

            {/* Alt Bilgi */}
            <Box sx={{ mt: 3, textAlign: 'center' }}>
              <Typography variant="caption" color="text.secondary">
                Bu sayfa yalnızca yetkili admin kullanıcıları içindir.
              </Typography>
            </Box>
          </CardContent>
        </Card>
      </Fade>
    </Box>
  );
};

export default AdminLogin;
