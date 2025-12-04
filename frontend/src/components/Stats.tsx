import React, { useEffect, useState } from "react";
import { 
  Box, 
  Typography, 
  Paper, 
  List, 
  ListItem, 
  ListItemText, 
  Stack, 
  Button, 
  Dialog, 
  DialogTitle, 
  DialogContent, 
  DialogActions,
  Chip,
  Alert,
  Card,
  CardContent,
  CardHeader,
  Grid,
  Divider,
  IconButton,
  Tooltip,
  useTheme,
  alpha,
  Avatar,
  ListItemAvatar,
  CircularProgress,
  LinearProgress,
  Menu,
  MenuItem,
  ListItemIcon,
  Pagination
} from "@mui/material";
import { 
  QuestionAnswer, 
  Delete, 
  TrendingUp, 
  Today, 
  LibraryBooks,
  HelpOutline,
  Source,
  QueryStats,
  AutorenewRounded,
  People,
  ExpandMore,
  DeleteForever,
  ClearAll
} from "@mui/icons-material";

const API = process.env.REACT_APP_API_URL || '';

interface StatData {
  totalQuestions: number;
  dailyQuestions: number;
  dailyUsers: number;
  totalUsers: number;
  totalEntries: number;
  weeklyActivity: [string, number][];
  topSources: { source: string; keyword: string; count: number }[];
  topQuestions: { question: string; answer: string; count: number; topic: string }[];
}

interface DailyQuestion {
  id: number;
  question: string;
  answer: string;
  count: number;
  created_at: string;
  source_file?: string;
  source_keyword?: string;
  topic?: string;
}

const Stats: React.FC = () => {
  const [stats, setStats] = useState<StatData | null>(null);
  const [error, setError] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(false);
  const [selectedQuestion, setSelectedQuestion] = useState<{question: string; answer: string} | null>(null);
  const [autoRefresh, setAutoRefresh] = useState<boolean>(true);
  const [clearMenuAnchor, setClearMenuAnchor] = useState<null | HTMLElement>(null);
  
  // Günlük sorular modal state'leri
  const [dailyQuestionsModal, setDailyQuestionsModal] = useState(false);
  const [dailyQuestions, setDailyQuestions] = useState<DailyQuestion[]>([]);
  const [dailyLoading, setDailyLoading] = useState(false);
  const [dailyPage, setDailyPage] = useState(1);
  const [dailyTotalPages, setDailyTotalPages] = useState(1);
  
  // En çok sorulan sorular modal state'leri
  const [allQuestionsModal, setAllQuestionsModal] = useState(false);
  const [allQuestions, setAllQuestions] = useState<DailyQuestion[]>([]);
  const [allQuestionsLoading, setAllQuestionsLoading] = useState(false);
  const [allQuestionsPage, setAllQuestionsPage] = useState(1);
  const [allQuestionsTotalPages, setAllQuestionsTotalPages] = useState(1);
  
  const theme = useTheme();

  // Topic temizleme fonksiyonu
  const cleanTopicFromQuestion = (question: string): string => {
    // [Topic] formatını kaldır
    return question.replace(/^\[.*?\]\s*/, '').trim();
  };

  const fetchStats = async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/admin/stats", { cache: "no-store" });
      if (!res.ok) throw new Error("API hatası");
      const data = await res.json();
      
      if (data.error) {
        setError("İstatistikler alınamadı: " + data.error);
        setStats(null);
      } else {
        setStats(data);
        setError("");
      }
    } catch (e: any) {
      setError("İstatistikler alınamadı: " + e.message);
      
      // API çalışmıyorsa test için mock data kullan
      setStats({
        totalQuestions: 5,
        dailyQuestions: 1,
        dailyUsers: 2,
        totalUsers: 10,
        totalEntries: 50,
        weeklyActivity: [
          ["Monday", 5],
          ["Tuesday", 3],
          ["Wednesday", 8],
          ["Thursday", 6],
          ["Friday", 4],
          ["Saturday", 2],
          ["Sunday", 1]
        ],
        topSources: [
          { source: 'docs/sample_document_1.pdf', keyword: 'teknoloji', count: 5 },
          { source: 'docs/sample_document_2.pdf', keyword: 'bilim', count: 3 },
          { source: 'docs/sample_document_3.pdf', keyword: 'araştırma', count: 2 },
        ],
        topQuestions: [
          { question: 'örnek soru 1', answer: 'örnek cevap', count: 3, topic: 'genel' },
          { question: 'örnek soru 2', answer: 'örnek cevap 2', count: 2, topic: 'araştırma' }
        ]
      });
      console.log("Mock data kullanılıyor - API çalışmıyor");
    } finally {
      setLoading(false);
    }
  };

  const clearAllQuestions = async () => {
    if (!window.confirm("Tüm soru geçmişini silmek istediğinizden emin misiniz?")) {
      return;
    }
    
    try {
      const res = await fetch("/api/admin/clear_questions", { method: "POST" });
      if (!res.ok) throw new Error("API hatası");
      
      alert("Tüm sorular başarıyla temizlendi!");
      fetchStats(); // İstatistikleri yenile
    } catch (e: any) {
      alert("Sorular temizlenirken hata oluştu: " + e.message);
    }
    setClearMenuAnchor(null);
  };

  const clearTodayQuestions = async () => {
    if (!window.confirm("Bugünkü tüm soruları silmek istediğinizden emin misiniz?")) {
      return;
    }
    
    try {
      const res = await fetch("/api/admin/clear_questions_advanced", { 
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ period_type: "today" })
      });
      if (!res.ok) throw new Error("API hatası");
      
      const data = await res.json();
      alert(data.message);
      fetchStats(); // İstatistikleri yenile
    } catch (e: any) {
      alert("Bugünkü sorular temizlenirken hata oluştu: " + e.message);
    }
    setClearMenuAnchor(null);
  };

  const handleClearMenuOpen = (event: React.MouseEvent<HTMLElement>) => {
    setClearMenuAnchor(event.currentTarget);
  };

  const handleClearMenuClose = () => {
    setClearMenuAnchor(null);
  };

  const fetchDailyQuestions = async (pageNum: number = 1) => {
    setDailyLoading(true);
    try {
      const limit = 10;
      const response = await fetch(`/api/admin/daily-questions?page=${pageNum}&limit=${limit}`);
      const data = await response.json();
      
      setDailyQuestions(data.questions || []);
      setDailyTotalPages(data.totalPages || 1);
      setDailyPage(pageNum);
    } catch (error) {
      console.error('Günlük sorular yüklenirken hata:', error);
    } finally {
      setDailyLoading(false);
    }
  };

  const handleDailyQuestionsClick = () => {
    setDailyQuestionsModal(true);
    fetchDailyQuestions(1);
  };

  const handleDailyPageChange = (event: React.ChangeEvent<unknown>, value: number) => {
    fetchDailyQuestions(value);
  };

  const fetchAllQuestions = async (pageNum: number = 1) => {
    setAllQuestionsLoading(true);
    try {
      const limit = 10;
      const response = await fetch(`/api/admin/all-questions?page=${pageNum}&limit=${limit}`);
      const data = await response.json();
      
      setAllQuestions(data.questions || []);
      setAllQuestionsTotalPages(data.totalPages || 1);
      setAllQuestionsPage(pageNum);
    } catch (error) {
      console.error('Tüm sorular yüklenirken hata:', error);
    } finally {
      setAllQuestionsLoading(false);
    }
  };

  const handleAllQuestionsClick = () => {
    setAllQuestionsModal(true);
    fetchAllQuestions(1);
  };

  const handleAllQuestionsPageChange = (event: React.ChangeEvent<unknown>, value: number) => {
    fetchAllQuestions(value);
  };

  useEffect(() => {
    fetchStats();
    let interval: NodeJS.Timeout;
    
    if (autoRefresh) {
      interval = setInterval(fetchStats, 30000);
    }
    
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [autoRefresh]);

  // Link dönüştürme fonksiyonu
  const renderTextWithLinks = (text: string) => {
    // https ile başlayan linkleri bul ve tıklanabilir hale getir
    const linkRegex = /(https:\/\/[^\s]+)/g;
    const parts = text.split(linkRegex);
    
    return (
      <>
        {parts.map((part, index) => {
          if (part.match(linkRegex)) {
            return (
              <a 
                key={index}
                href={part}
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  color: '#3b82f6',
                  textDecoration: 'none',
                  fontWeight: 600,
                  borderRadius: '4px',
                  padding: '2px 4px',
                  backgroundColor: 'rgba(59, 130, 246, 0.1)',
                  border: '1px solid rgba(59, 130, 246, 0.2)',
                  transition: 'all 0.2s ease',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.backgroundColor = 'rgba(59, 130, 246, 0.2)';
                  e.currentTarget.style.transform = 'translateY(-1px)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.backgroundColor = 'rgba(59, 130, 246, 0.1)';
                  e.currentTarget.style.transform = 'translateY(0)';
                }}
              >
                {part}
              </a>
            );
          }
          return part;
        })}
      </>
    );
  };

  if (error) return <Alert severity="error" sx={{ m: 2 }}>{error}</Alert>;
  if (!stats) return (      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', p: 4 }}>
      <CircularProgress sx={{ color: '#1e3a8a' }} />
      <Typography sx={{ ml: 2, color: '#1e293b' }}>İstatistikler yükleniyor...</Typography>
    </Box>
  );

  return (
    <Box sx={{ 
      p: 3,
      minHeight: '100vh',
      background: 'linear-gradient(135deg, #f8fafc 0%, #e2e8f0 25%, #cbd5e1 100%)',
    }}>
      {/* Header */}
      <Box sx={{ mb: 4 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: { xs: 0.5, sm: 1 } }}>
            <QueryStats sx={{ 
              color: '#1e3a8a', 
              fontSize: { xs: '1.25rem', sm: '1.5rem', md: '2rem' }
            }} />
            <Typography 
              variant="h4" 
              sx={{ 
                fontWeight: 700, 
                color: '#1e3a8a',
                fontFamily: '"Segoe UI", Tahoma, Geneva, Verdana, sans-serif',
                fontSize: { xs: '1rem', sm: '1.25rem', md: '2rem' }
              }}
            >
              Soru İstatistikleri
            </Typography>
          </Box>
          
          <Box sx={{ display: 'flex', gap: { xs: 0.5, sm: 1 } }}>
            <Button
              variant="outlined"
              startIcon={<Delete sx={{ 
                color: '#dc2626',
                fontSize: { xs: '1rem', sm: '1.125rem', md: '1.25rem' }
              }} />}
              endIcon={<ExpandMore sx={{ 
                color: '#dc2626',
                fontSize: { xs: '1rem', sm: '1.125rem', md: '1.25rem' }
              }} />}
              onClick={handleClearMenuOpen}
              size="small"
              sx={{ 
                borderRadius: 2,
                textTransform: 'none',
                fontWeight: 600,
                borderColor: '#dc2626',
                color: '#dc2626',
                fontSize: { xs: '0.75rem', sm: '0.875rem', md: '1rem' },
                px: { xs: 1, sm: 1.5, md: 2 },
                py: { xs: 0.5, sm: 1 },
                '&:hover': {
                  borderColor: '#b91c1c',
                  backgroundColor: 'rgba(220, 38, 38, 0.05)',
                },
              }}
            >
              Temizle
            </Button>
            
            <Menu
              anchorEl={clearMenuAnchor}
              open={Boolean(clearMenuAnchor)}
              onClose={handleClearMenuClose}
              PaperProps={{
                sx: {
                  background: 'linear-gradient(135deg, rgba(248, 250, 252, 0.95) 0%, rgba(255, 255, 255, 0.95) 100%)',
                  backdropFilter: 'blur(15px)',
                  border: '1px solid rgba(30, 58, 138, 0.1)',
                  borderRadius: 2,
                  boxShadow: '0 8px 32px rgba(30, 58, 138, 0.15)',
                }
              }}
            >
              <MenuItem onClick={clearTodayQuestions}>
                <ListItemIcon>
                  <Today fontSize="small" sx={{ color: '#f59e0b' }} />
                </ListItemIcon>
                <Typography sx={{ color: '#1e293b', fontWeight: 500 }}>Bugünkü Soruları Sil</Typography>
              </MenuItem>
              
              <MenuItem onClick={clearAllQuestions}>
                <ListItemIcon>
                  <DeleteForever fontSize="small" sx={{ color: '#dc2626' }} />
                </ListItemIcon>
                <Typography sx={{ color: '#1e293b', fontWeight: 500 }}>Tüm Soruları Sil</Typography>
              </MenuItem>
            </Menu>
          </Box>
        </Box>
        
        {loading && <LinearProgress sx={{ borderRadius: 1 }} />}
      </Box>

      <Stack spacing={3} sx={{ mt: 3 }}>
        {/* Özet Kartları */}
        <Box sx={{ 
          display: 'grid', 
          gridTemplateColumns: { xs: 'repeat(2, 1fr)', sm: '1fr 1fr', md: 'repeat(4, 1fr)' },
          gap: { xs: 2, sm: 3 }
        }}>
          <Card 
            elevation={0}
            sx={{ 
              background: 'linear-gradient(135deg, rgba(255, 255, 255, 0.9) 0%, rgba(248, 250, 252, 0.9) 100%)',
              border: '1px solid rgba(30, 58, 138, 0.1)',
              borderRadius: 3,
              height: '100%',
              boxShadow: '0 8px 32px rgba(30, 58, 138, 0.08)',
            }}
          >
            <CardContent sx={{ p: { xs: 2, sm: 3 } }}>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: { xs: 1, sm: 2 } }}>
                <Avatar sx={{ 
                  bgcolor: 'linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%)', 
                  mr: { xs: 1, sm: 2 },
                  boxShadow: '0 4px 12px rgba(30, 58, 138, 0.2)',
                  width: { xs: 35, sm: 40 },
                  height: { xs: 35, sm: 40 }
                }}>
                  <TrendingUp sx={{ fontSize: { xs: '1.125rem', sm: '1.25rem' } }} />
                </Avatar>
                <Typography 
                  variant="h6" 
                  fontWeight={700} 
                  color="#1e3a8a"
                  sx={{ fontSize: { xs: '1rem', sm: '1.125rem', md: '1.25rem' } }}
                >
                  Toplam Sorular
                </Typography>
              </Box>
              <Typography 
                variant="h3" 
                fontWeight={800} 
                color="#1e3a8a"
                sx={{ fontSize: { xs: '1.75rem', sm: '2.25rem', md: '3rem' } }}
              >
                {stats?.totalQuestions || 0}
              </Typography>
              <Typography 
                variant="body2" 
                color="#64748b" 
                sx={{ 
                  mt: { xs: 0.5, sm: 1 }, 
                  fontWeight: 500,
                  fontSize: { xs: '0.8rem', sm: '0.875rem' }
                }}
              >
                Tüm zamanlar
              </Typography>
            </CardContent>
          </Card>

          <Card 
            elevation={0}
            onClick={handleDailyQuestionsClick}
            sx={{ 
              background: 'linear-gradient(135deg, rgba(255, 255, 255, 0.9) 0%, rgba(248, 250, 252, 0.9) 100%)',
              border: '1px solid rgba(30, 58, 138, 0.1)',
              borderRadius: 3,
              height: '100%',
              boxShadow: '0 8px 32px rgba(30, 58, 138, 0.08)',
              cursor: 'pointer',
              '&:hover': {
                backgroundColor: 'rgba(30, 58, 138, 0.05)',
                transform: 'translateY(-2px)',
                transition: 'all 0.2s ease-in-out',
                boxShadow: '0 12px 40px rgba(30, 58, 138, 0.12)',
              }
            }}
          >
            <CardContent sx={{ p: { xs: 2, sm: 3 } }}>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: { xs: 1, sm: 2 } }}>
                <Avatar sx={{ 
                  bgcolor: 'linear-gradient(135deg, #059669 0%, #10b981 100%)', 
                  mr: { xs: 1, sm: 2 },
                  boxShadow: '0 4px 12px rgba(5, 150, 105, 0.2)',
                  width: { xs: 35, sm: 40 },
                  height: { xs: 35, sm: 40 }
                }}>
                  <Today sx={{ fontSize: { xs: '1.125rem', sm: '1.25rem' } }} />
                </Avatar>
                <Typography 
                  variant="h6" 
                  fontWeight={700} 
                  color="#1e3a8a"
                  sx={{ fontSize: { xs: '1rem', sm: '1.125rem', md: '1.25rem' } }}
                >
                  Bugünkü Sorular
                </Typography>
              </Box>
              <Typography 
                variant="h3" 
                fontWeight={800} 
                color="#1e3a8a"
                sx={{ fontSize: { xs: '1.75rem', sm: '2.25rem', md: '3rem' } }}
              >
                {stats?.dailyQuestions || 0}
              </Typography>
              <Typography 
                variant="body2" 
                color="#64748b" 
                sx={{ 
                  mt: { xs: 0.5, sm: 1 }, 
                  fontWeight: 500,
                  fontSize: { xs: '0.8rem', sm: '0.875rem' }
                }}
              >
                Detayları görmek için tıklayın
              </Typography>
            </CardContent>
          </Card>

          <Card 
            elevation={0}
            sx={{ 
              background: 'linear-gradient(135deg, rgba(255, 255, 255, 0.9) 0%, rgba(248, 250, 252, 0.9) 100%)',
              border: '1px solid rgba(30, 58, 138, 0.1)',
              borderRadius: 3,
              height: '100%',
              boxShadow: '0 8px 32px rgba(30, 58, 138, 0.08)',
            }}
          >
            <CardContent sx={{ p: { xs: 2, sm: 3 } }}>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: { xs: 1, sm: 2 } }}>
                <Avatar sx={{ 
                  bgcolor: 'linear-gradient(135deg, #7c3aed 0%, #a855f7 100%)', 
                  mr: { xs: 1, sm: 2 },
                  boxShadow: '0 4px 12px rgba(124, 58, 237, 0.2)',
                  width: { xs: 35, sm: 40 },
                  height: { xs: 35, sm: 40 }
                }}>
                  <People sx={{ fontSize: { xs: '1.125rem', sm: '1.25rem' } }} />
                </Avatar>
                <Typography 
                  variant="h6" 
                  fontWeight={700} 
                  color="#1e3a8a"
                  sx={{ fontSize: { xs: '1rem', sm: '1.125rem', md: '1.25rem' } }}
                >
                  Günlük Kullanıcılar
                </Typography>
              </Box>
              <Typography 
                variant="h3" 
                fontWeight={800} 
                color="#1e3a8a"
                sx={{ fontSize: { xs: '1.75rem', sm: '2.25rem', md: '3rem' } }}
              >
                {stats?.dailyUsers || 0}
              </Typography>
              <Typography 
                variant="body2" 
                color="#64748b" 
                sx={{ 
                  mt: { xs: 0.5, sm: 1 }, 
                  fontWeight: 500,
                  fontSize: { xs: '0.8rem', sm: '0.875rem' }
                }}
              >
                Bugün aktif
              </Typography>
            </CardContent>
          </Card>

          <Card 
            elevation={0}
            sx={{ 
              background: 'linear-gradient(135deg, rgba(255, 255, 255, 0.9) 0%, rgba(248, 250, 252, 0.9) 100%)',
              border: '1px solid rgba(30, 58, 138, 0.1)',
              borderRadius: 3,
              height: '100%',
              boxShadow: '0 8px 32px rgba(30, 58, 138, 0.08)',
            }}
          >
            <CardContent sx={{ p: { xs: 2, sm: 3 } }}>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: { xs: 1, sm: 2 } }}>
                <Avatar sx={{ 
                  bgcolor: 'linear-gradient(135deg, #ea580c 0%, #f97316 100%)', 
                  mr: { xs: 1, sm: 2 },
                  boxShadow: '0 4px 12px rgba(234, 88, 12, 0.2)',
                  width: { xs: 35, sm: 40 },
                  height: { xs: 35, sm: 40 }
                }}>
                  <QueryStats sx={{ fontSize: { xs: '1.125rem', sm: '1.25rem' } }} />
                </Avatar>
                <Typography 
                  variant="h6" 
                  fontWeight={700} 
                  color="#1e3a8a"
                  sx={{ fontSize: { xs: '1rem', sm: '1.125rem', md: '1.25rem' } }}
                >
                  Toplam Girişler
                </Typography>
              </Box>
              <Typography 
                variant="h3" 
                fontWeight={800} 
                color="#1e3a8a"
                sx={{ fontSize: { xs: '1.75rem', sm: '2.25rem', md: '3rem' } }}
              >
                {stats?.totalEntries || 0}
              </Typography>
              <Typography 
                variant="body2" 
                color="#64748b" 
                sx={{ 
                  mt: { xs: 0.5, sm: 1 }, 
                  fontWeight: 500,
                  fontSize: { xs: '0.8rem', sm: '0.875rem' }
                }}
              >
                Tüm session'lar
              </Typography>
            </CardContent>
          </Card>
        </Box>

        {/* Alt Kısım - Detaylar */}
        <Stack direction={{ xs: 'column', lg: 'row' }} spacing={3}>
          {/* En Çok Kullanılan Kaynaklar */}
          <Card 
            elevation={0}
            sx={{ 
              background: 'rgba(255, 255, 255, 0.9)',
              border: `1px solid rgba(30, 58, 138, 0.2)`,
              borderRadius: 2,
              flex: 1,
            }}
          >
            <CardHeader
              avatar={
                <Avatar sx={{ bgcolor: '#1e3a8a' }}>
                  <Source sx={{ color: 'white' }} />
                </Avatar>
              }
              title="En Çok Kullanılan Kaynaklar"
              titleTypographyProps={{ fontWeight: 600, variant: 'h6', color: '#1e293b' }}
              sx={{ pb: 1 }}
            />
            <Divider />
            <CardContent sx={{ p: 0 }}>
              <List>
                {stats.topSources && stats.topSources.length > 0 ? (
                  stats.topSources.map((item, index) => {
                    const displayName = item.source;
                    
                    return (
                      <ListItem key={index} sx={{ py: 2, px: 3 }}>
                        <ListItemAvatar>
                          <Avatar sx={{ bgcolor: '#1e3a8a', fontSize: '0.875rem', color: 'white' }}>
                            {index + 1}
                          </Avatar>
                        </ListItemAvatar>
                        <ListItemText 
                          primary={displayName}
                          secondary={
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 1 }}>
                              {item.keyword && (
                                <Chip
                                  label={item.keyword}
                                  size="small"
                                  variant="filled"
                                  sx={{
                                    borderRadius: 2,
                                    color: 'white',
                                    bgcolor: '#7c3aed',
                                    fontWeight: 600,
                                    fontSize: { xs: '0.6rem', sm: '0.7rem', md: '0.75rem' },
                                    height: 'auto',
                                    minHeight: { xs: '20px', sm: '22px', md: '24px' },
                                    whiteSpace: 'normal',
                                    wordBreak: 'break-word',
                                    overflowWrap: 'break-word',
                                    '& .MuiChip-label': {
                                      fontSize: { xs: '0.6rem', sm: '0.7rem', md: '0.75rem' },
                                      padding: { xs: '0 4px', sm: '0 6px', md: '0 8px' },
                                      lineHeight: { xs: 1.2, sm: 1.3, md: 1.4 },
                                      whiteSpace: 'normal',
                                      wordBreak: 'break-word',
                                      overflowWrap: 'break-word',
                                    }
                                  }}
                                />
                              )}
                              <Chip 
                                label={`${item.count} kullanım`}
                                size="small" 
                                variant="filled"
                                sx={{ 
                                  borderRadius: 2, 
                                  color: 'white', 
                                  bgcolor: '#1e3a8a', 
                                  fontWeight: 600,
                                  fontSize: { xs: '0.6rem', sm: '0.7rem', md: '0.75rem' },
                                  height: { xs: '20px', sm: '22px', md: '24px' },
                                  '& .MuiChip-label': {
                                    fontSize: { xs: '0.6rem', sm: '0.7rem', md: '0.75rem' },
                                    padding: { xs: '0 4px', sm: '0 6px', md: '0 8px' },
                                  }
                                }}
                              />
                            </Box>
                          }
                          sx={{ 
                            '& .MuiListItemText-primary': { 
                              fontWeight: 600,
                              color: '#1e293b',
                              mb: 0.5,
                              fontSize: { xs: '0.8rem', sm: '0.9rem', md: '1rem' },
                              lineHeight: { xs: 1.3, sm: 1.4, md: 1.5 },
                              wordBreak: 'break-all',
                              overflowWrap: 'anywhere',
                              whiteSpace: 'normal',
                              display: 'block'
                            }
                          }}
                        />
                      </ListItem>
                    );
                  })
                ) : (
                  <ListItem sx={{ py: 4, justifyContent: 'center' }}>
                    <Box sx={{ textAlign: 'center', color: '#64748b' }}>
                      <Source sx={{ fontSize: '3rem', mb: 2, opacity: 0.5 }} />
                      <Typography variant="body1" color="#64748b">
                        Henüz kaynak kullanılmamış
                      </Typography>
                    </Box>
                  </ListItem>
                )}
              </List>
            </CardContent>
          </Card>

          {/* En Çok Sorulan Sorular */}
          <Card 
            elevation={0}
            sx={{ 
              background: 'rgba(255, 255, 255, 0.9)',
              border: `1px solid rgba(30, 58, 138, 0.2)`,
              borderRadius: 2,
              flex: 1,
            }}
          >
            <CardHeader
              avatar={
                <Avatar sx={{ 
                  bgcolor: '#1e3a8a',
                  width: { xs: 35, sm: 40 },
                  height: { xs: 35, sm: 40 }
                }}>
                  <HelpOutline sx={{ 
                    color: 'white',
                    fontSize: { xs: '1.125rem', sm: '1.25rem' }
                  }} />
                </Avatar>
              }
              title="En Çok Sorulan Sorular"
              titleTypographyProps={{ 
                fontWeight: 600, 
                variant: 'h6', 
                color: '#1e293b',
                fontSize: { xs: '0.95rem', sm: '1.1rem', md: '1.25rem' },
                lineHeight: { xs: 1.2, sm: 1.3, md: 1.4 },
                letterSpacing: { xs: 0, sm: 0.1, md: 0.2 }
              }}
              action={
                stats.topQuestions && stats.topQuestions.length > 0 && (
                  <Button
                    size="small"
                    variant="outlined"
                    onClick={handleAllQuestionsClick}
                    sx={{
                      borderRadius: 2,
                      textTransform: 'none',
                      fontWeight: 600,
                      borderColor: '#1e3a8a',
                      color: '#1e3a8a',
                      fontSize: { xs: '0.7rem', sm: '0.85rem', md: '0.95rem' },
                      px: { xs: 1, sm: 1.5, md: 2 },
                      py: { xs: 0.25, sm: 0.5, md: 1 },
                      minHeight: { xs: 28, sm: 32, md: 36 },
                      '&:hover': {
                        borderColor: '#1e40af',
                        backgroundColor: 'rgba(30, 58, 138, 0.05)',
                      }
                    }}
                  >
                    Tümünü Görüntüle
                  </Button>
                )
              }
              sx={{ pb: 1 }}
            />
            <Divider />
            <CardContent sx={{ p: 0 }}>
              <List>
                {stats.topQuestions && stats.topQuestions.length > 0 ? (
                  stats.topQuestions.map((item, index) => (
                    <ListItem key={index} sx={{ py: 2, px: 3, flexDirection: 'column', alignItems: 'flex-start' }}>
                      <Box sx={{ display: 'flex', alignItems: 'flex-start', width: '100%', mb: 1 }}>
                        <Avatar sx={{ bgcolor: '#1e3a8a', fontSize: '0.875rem', mr: 2, mt: 0.5, color: 'white' }}>
                          {index + 1}
                        </Avatar>
                        <Box sx={{ flexGrow: 1 }}>
                          <Typography 
                            variant="body1" 
                            fontWeight={600}
                            sx={{ 
                              color: '#1e293b',
                              mb: 1,
                              display: '-webkit-box',
                              WebkitLineClamp: 2,
                              WebkitBoxOrient: 'vertical',
                              overflow: 'hidden',
                            }}
                          >
                            {cleanTopicFromQuestion(item.question)}
                          </Typography>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, justifyContent: 'space-between' }}>
                            <Chip 
                              label={`${item.count} kez soruldu`}
                              size="small" 
                              sx={{ 
                                borderRadius: 2, 
                                bgcolor: '#1e3a8a', 
                                color: 'white',
                                fontWeight: 500
                              }}
                            />
                            <Button
                              size="small"
                              variant="outlined"
                              startIcon={<QuestionAnswer sx={{ color: '#059669' }} />}
                              onClick={() => setSelectedQuestion({
                                question: cleanTopicFromQuestion(item.question),
                                answer: item.answer
                              })}
                              sx={{ 
                                borderRadius: 2,
                                textTransform: 'none',
                                fontWeight: 500,
                                minWidth: 'auto',
                                px: 2,
                                borderColor: '#059669',
                                color: '#059669',
                                '&:hover': {
                                  bgcolor: 'rgba(5, 150, 105, 0.05)',
                                }
                              }}
                            >
                              Cevabı Gör
                            </Button>
                          </Box>
                        </Box>
                      </Box>
                    </ListItem>
                  ))
                ) : (
                  <ListItem sx={{ py: 4, justifyContent: 'center' }}>
                    <Box sx={{ textAlign: 'center', color: '#64748b' }}>
                      <HelpOutline sx={{ fontSize: '3rem', mb: 2, opacity: 0.5 }} />
                      <Typography variant="body1" color="#64748b">
                        Henüz soru sorulmamış
                      </Typography>
                    </Box>
                  </ListItem>
                )}
              </List>
            </CardContent>
          </Card>
        </Stack>
      </Stack>

      {/* Cevap Dialog'u */}
      <Dialog
        open={!!selectedQuestion}
        onClose={() => setSelectedQuestion(null)}
        maxWidth="md"
        fullWidth
        sx={{
          '& .MuiDialog-paper': {
            borderRadius: 3,
            boxShadow: `0 24px 48px rgba(30, 58, 138, 0.25)`,
            background: 'linear-gradient(135deg, rgba(255, 255, 255, 0.98) 0%, rgba(248, 250, 252, 0.98) 100%)',
            backdropFilter: 'blur(20px)',
            border: '1px solid rgba(59, 130, 246, 0.1)',
          },
          '& .MuiBackdrop-root': {
            background: 'rgba(30, 58, 138, 0.4)',
            backdropFilter: 'blur(8px)',
          }
        }}
      >
        <DialogTitle 
          sx={{ 
            pb: 1,
            background: 'linear-gradient(135deg, #1e3a8a 0%, #3b82f6 50%, #1e40af 100%)',
            color: 'white'
          }}
        >
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <QuestionAnswer sx={{ color: 'white' }} />
            <Typography variant="h6" component="div" fontWeight={700} sx={{ color: 'white' }}>
              Soru ve Cevap Detayı
            </Typography>
          </Box>
        </DialogTitle>
        <DialogContent sx={{ p: 4, background: 'rgba(248, 250, 252, 0.5)' }}>
          {selectedQuestion && (
            <Box>
              <Typography 
                variant="subtitle1" 
                fontWeight={700} 
                sx={{ 
                  mb: 2, 
                  color: '#1e3a8a',
                  fontSize: '1.1rem',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 1
                }}
              >
                <HelpOutline sx={{ color: '#1e3a8a', fontSize: '1.2rem' }} />
                Soru:
              </Typography>
              <Paper 
                elevation={0}
                sx={{ 
                  p: 3, 
                  background: 'linear-gradient(135deg, rgba(255, 255, 255, 0.9) 0%, rgba(248, 250, 252, 0.9) 100%)',
                  border: `2px solid rgba(30, 58, 138, 0.2)`,
                  borderRadius: 3,
                  mb: 4,
                  boxShadow: '0 4px 20px rgba(30, 58, 138, 0.08)'
                }}
              >
                <Typography 
                  variant="body1" 
                  sx={{ 
                    lineHeight: 1.7, 
                    color: '#1e293b',
                    fontSize: '1rem',
                    fontWeight: 500
                  }}
                >
                  {selectedQuestion.question}
                </Typography>
              </Paper>
              
              <Typography 
                variant="subtitle1" 
                fontWeight={700} 
                sx={{ 
                  mb: 2, 
                  color: '#059669',
                  fontSize: '1.1rem',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 1
                }}
              >
                <QuestionAnswer sx={{ color: '#059669', fontSize: '1.2rem' }} />
                Cevap:
              </Typography>
              <Paper 
                elevation={0}
                sx={{ 
                  p: 3, 
                  background: 'linear-gradient(135deg, rgba(255, 255, 255, 0.9) 0%, rgba(240, 253, 250, 0.9) 100%)',
                  border: `2px solid rgba(5, 150, 105, 0.2)`,
                  borderRadius: 3,
                  whiteSpace: 'pre-line',
                  boxShadow: '0 4px 20px rgba(5, 150, 105, 0.08)'
                }}
              >
                <Typography 
                  variant="body1"                  sx={{
                    color: '#1e293b',
                    lineHeight: 1.7,
                    fontSize: '1rem',
                    fontWeight: 500
                  }}
                >
                  {renderTextWithLinks(selectedQuestion.answer)}
                </Typography>
              </Paper>
            </Box>
          )}
        </DialogContent>
        <DialogActions 
          sx={{ 
            p: 3, 
            pt: 2,
            background: 'linear-gradient(135deg, rgba(248, 250, 252, 0.8) 0%, rgba(241, 245, 249, 0.8) 100%)',
            borderTop: '1px solid rgba(59, 130, 246, 0.1)'
          }}
        >
          <Button 
            onClick={() => setSelectedQuestion(null)}
            variant="contained"
            sx={{ 
              background: 'linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%)',
              color: 'white',
              borderRadius: 3,
              textTransform: 'none',
              fontWeight: 600,
              px: 4,
              py: 1.5,
              boxShadow: '0 4px 15px rgba(30, 58, 138, 0.3)',
              '&:hover': {
                background: 'linear-gradient(135deg, #1e40af 0%, #2563eb 100%)',
                boxShadow: '0 6px 20px rgba(30, 58, 138, 0.4)',
                transform: 'translateY(-2px)',
              },
              transition: 'all 0.3s ease'
            }}
          >
            Kapat
          </Button>
        </DialogActions>
      </Dialog>

      {/* Günlük Sorular Modal */}
      <Dialog 
        open={dailyQuestionsModal} 
        onClose={() => setDailyQuestionsModal(false)}
        maxWidth="lg"
        fullWidth
        sx={{
          '& .MuiDialog-paper': {
            borderRadius: 4,
            background: 'linear-gradient(135deg, rgba(255, 255, 255, 0.98) 0%, rgba(248, 250, 252, 0.98) 100%)',
            boxShadow: '0 32px 64px rgba(30, 58, 138, 0.25)',
            border: '1px solid rgba(59, 130, 246, 0.15)',
            backdropFilter: 'blur(20px)',
            maxHeight: '85vh',
          },
          '& .MuiBackdrop-root': {
            background: 'linear-gradient(135deg, rgba(30, 58, 138, 0.4) 0%, rgba(59, 130, 246, 0.3) 100%)',
            backdropFilter: 'blur(12px)',
          }
        }}
      >
        <DialogTitle sx={{ 
          p: 0,
          background: 'linear-gradient(135deg, #1e3a8a 0%, #3b82f6 50%, #1e40af 100%)',
          color: 'white',
          borderRadius: '16px 16px 0 0',
        }}>
          <Box sx={{ 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'space-between',
            p: 3,
            background: 'linear-gradient(135deg, rgba(255, 255, 255, 0.1) 0%, transparent 100%)',
          }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              <Today sx={{ 
                color: 'white', 
                fontSize: '2rem',
                filter: 'drop-shadow(0 2px 4px rgba(0,0,0,0.2))'
              }} />
              <Box>
                <Typography variant="h5" fontWeight={700} sx={{ color: 'white' }}>
                  Bugün Sorulan Sorular
                </Typography>
                <Typography variant="body2" sx={{ color: 'rgba(255, 255, 255, 0.8)', mt: 0.5 }}>
                  Son 24 saatteki sorular ve detayları
                </Typography>
              </Box>
            </Box>
            {dailyQuestions.length > 0 && (
              <Chip 
                label={`${dailyQuestions.length} soru listeleniyor`} 
                size="medium" 
                sx={{ 
                  backgroundColor: 'rgba(255, 255, 255, 0.2)',
                  color: 'white',
                  fontWeight: 600,
                  fontSize: '0.875rem',
                  border: '1px solid rgba(255, 255, 255, 0.3)',
                  backdropFilter: 'blur(10px)',
                }}
              />
            )}
          </Box>
        </DialogTitle>
        
        <DialogContent sx={{ 
          p: 0, 
          background: 'linear-gradient(135deg, rgba(248, 250, 252, 0.6) 0%, rgba(241, 245, 249, 0.6) 100%)',
        }}>
          {dailyLoading ? (
            <Box sx={{ 
              display: 'flex', 
              flexDirection: 'column',
              justifyContent: 'center', 
              alignItems: 'center',
              p: 6,
              gap: 2
            }}>
              <CircularProgress 
                size={48} 
                sx={{ 
                  color: '#1e3a8a',
                  filter: 'drop-shadow(0 2px 4px rgba(30, 58, 138, 0.3))'
                }} 
              />
              <Typography variant="body1" sx={{ color: '#64748b', fontWeight: 500 }}>
                Günlük sorular yükleniyor...
              </Typography>
            </Box>
          ) : dailyQuestions.length === 0 ? (
            <Box sx={{ 
              display: 'flex', 
              flexDirection: 'column',
              justifyContent: 'center', 
              alignItems: 'center',
              p: 6,
              gap: 2
            }}>
              <Today sx={{ 
                fontSize: '4rem', 
                color: '#cbd5e1', 
                filter: 'drop-shadow(0 2px 4px rgba(0,0,0,0.1))'
              }} />
              <Typography variant="h6" sx={{ color: '#64748b', fontWeight: 600 }}>
                Henüz bugün soru sorulmamış
              </Typography>
              <Typography variant="body2" sx={{ color: '#94a3b8', textAlign: 'center' }}>
                İlk soru sorulduğunda burada görünecek
              </Typography>
            </Box>
          ) : (
            <>
              <List sx={{ p: 0 }}>
                {dailyQuestions.map((q, index) => (
                  <ListItem 
                    key={q.id} 
                    divider
                    sx={{
                      p: 3,
                      background: index % 2 === 0 
                        ? 'linear-gradient(135deg, rgba(255, 255, 255, 0.7) 0%, rgba(248, 250, 252, 0.7) 100%)'
                        : 'linear-gradient(135deg, rgba(248, 250, 252, 0.4) 0%, rgba(241, 245, 249, 0.4) 100%)',
                      borderLeft: '4px solid transparent',
                      '&:hover': {
                        borderLeftColor: '#3b82f6',
                        background: 'linear-gradient(135deg, rgba(30, 58, 138, 0.05) 0%, rgba(59, 130, 246, 0.05) 100%)',
                        transform: 'translateX(4px)',
                        transition: 'all 0.3s ease',
                      }
                    }}
                  >
                    <ListItemAvatar>
                      <Avatar sx={{ 
                        bgcolor: 'linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%)', 
                        color: 'white',
                        fontWeight: 700,
                        width: 45,
                        height: 45,
                        boxShadow: '0 4px 12px rgba(30, 58, 138, 0.3)',
                      }}>
                        {(dailyPage - 1) * 10 + index + 1}
                      </Avatar>
                    </ListItemAvatar>
                    
                    <ListItemText
                      primary={
                        <Box sx={{ mb: 2 }}>
                          <Typography 
                            variant="h6" 
                            sx={{ 
                              color: '#1e293b', 
                              fontWeight: 600,
                              lineHeight: 1.4,
                              mb: 1
                            }}
                          >
                            {cleanTopicFromQuestion(q.question)}
                          </Typography>
                          
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, flexWrap: 'wrap' }}>
                            <Chip 
                              label={`${q.count} kez soruldu`} 
                              size="small" 
                              sx={{ 
                                background: 'linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%)',
                                color: 'white',
                                fontWeight: 600,
                                borderRadius: 2,
                                boxShadow: '0 2px 8px rgba(30, 58, 138, 0.25)',
                              }}
                            />
                            {q.source_file && (
                              <Chip 
                                icon={<Source sx={{ color: 'white !important' }} />}
                                label={q.source_keyword || q.source_file} 
                                size="small" 
                                sx={{ 
                                  background: 'linear-gradient(135deg, #7c3aed 0%, #a855f7 100%)',
                                  color: 'white',
                                  fontWeight: 600,
                                  borderRadius: 2,
                                  boxShadow: '0 2px 8px rgba(124, 58, 237, 0.25)',
                                  fontSize: { xs: '0.625rem', sm: '0.75rem', md: '0.875rem' },
                                  height: { xs: '20px', sm: '24px', md: '24px' },
                                  '& .MuiChip-label': {
                                    fontSize: { xs: '0.625rem', sm: '0.75rem', md: '0.875rem' },
                                    padding: { xs: '0 6px', sm: '0 8px', md: '0 12px' },
                                    lineHeight: { xs: 1.2, sm: 1.3, md: 1.4 },
                                    whiteSpace: 'nowrap',
                                    overflow: 'hidden',
                                    textOverflow: 'ellipsis',
                                    maxWidth: { xs: '120px', sm: '200px', md: 'none' },
                                  },
                                  '& .MuiChip-icon': {
                                    fontSize: { xs: '0.875rem', sm: '1rem', md: '1.125rem' },
                                  },
                                }}
                              />
                            )}
                          </Box>
                        </Box>
                      }
                      secondary={
                        <Box sx={{ mt: 2 }}>
                          <Typography 
                            variant="body1" 
                            sx={{ 
                              color: '#1e293b', 
                              lineHeight: 1.7,
                              background: 'rgba(248, 250, 252, 0.9)',
                              p: 2.5,
                              borderRadius: 2,
                              border: '1px solid rgba(203, 213, 225, 0.5)',
                              fontWeight: 500,
                              fontSize: '0.95rem',
                              whiteSpace: 'pre-wrap'
                            }}
                          >
                            {renderTextWithLinks(q.answer)}
                          </Typography>
                          {q.source_file && (
                            <Typography 
                              variant="caption" 
                              sx={{ 
                                mt: 1.5, 
                                display: 'flex',
                                alignItems: 'center',
                                gap: 0.5,
                                color: '#64748b',
                                fontWeight: 500,
                                background: 'rgba(241, 245, 249, 0.8)',
                                p: 1,
                                borderRadius: 1,
                                border: '1px solid rgba(203, 213, 225, 0.3)',
                              }}
                            >
                              📄 Kaynak Dosya: {q.source_file}
                            </Typography>
                          )}
                        </Box>
                      }
                    />
                  </ListItem>
                ))}
              </List>

              {dailyTotalPages > 1 && (
                <Box sx={{ 
                  display: 'flex', 
                  justifyContent: 'center', 
                  p: 3,
                  background: 'linear-gradient(135deg, rgba(248, 250, 252, 0.8) 0%, rgba(241, 245, 249, 0.8) 100%)',
                  borderTop: '1px solid rgba(203, 213, 225, 0.3)',
                }}>
                  <Pagination 
                    count={dailyTotalPages} 
                    page={dailyPage} 
                    onChange={handleDailyPageChange}
                    color="primary"
                    size="large"
                    sx={{
                      '& .MuiPaginationItem-root': {
                        fontWeight: 600,
                        color: '#1e3a8a',
                        '&.Mui-selected': {
                          background: 'linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%)',
                          color: 'white',
                          boxShadow: '0 4px 12px rgba(30, 58, 138, 0.3)',
                        },
                        '&:hover': {
                          backgroundColor: 'rgba(30, 58, 138, 0.1)',
                        }
                      }
                    }}
                  />
                </Box>
              )}
            </>
          )}
        </DialogContent>
        
        <DialogActions sx={{ 
          p: 3, 
          background: 'linear-gradient(135deg, rgba(248, 250, 252, 0.9) 0%, rgba(241, 245, 249, 0.9) 100%)',
          borderTop: '1px solid rgba(59, 130, 246, 0.15)',
          backdropFilter: 'blur(10px)',
        }}>
          <Button 
            onClick={() => setDailyQuestionsModal(false)}
            variant="contained"
            sx={{ 
              background: 'linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%)',
              color: 'white',
              borderRadius: 3,
              textTransform: 'none',
              fontWeight: 600,
              px: 4,
              py: 1.5,
              fontSize: '1rem',
              boxShadow: '0 6px 20px rgba(30, 58, 138, 0.35)',
              '&:hover': {
                background: 'linear-gradient(135deg, #1e40af 0%, #2563eb 100%)',
                boxShadow: '0 8px 25px rgba(30, 58, 138, 0.45)',
                transform: 'translateY(-2px)',
              },
              transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)'
            }}
          >
            Kapat
          </Button>
        </DialogActions>
      </Dialog>

      {/* Tüm Sorular Modal */}
      <Dialog 
        open={allQuestionsModal} 
        onClose={() => setAllQuestionsModal(false)}
        maxWidth="lg"
        fullWidth
        sx={{
          '& .MuiDialog-paper': {
            borderRadius: 4,
            background: 'linear-gradient(135deg, rgba(255, 255, 255, 0.98) 0%, rgba(248, 250, 252, 0.98) 100%)',
            boxShadow: '0 32px 64px rgba(30, 58, 138, 0.25)',
            border: '1px solid rgba(59, 130, 246, 0.15)',
            backdropFilter: 'blur(20px)',
            maxHeight: '85vh',
          },
          '& .MuiBackdrop-root': {
            background: 'linear-gradient(135deg, rgba(30, 58, 138, 0.4) 0%, rgba(59, 130, 246, 0.3) 100%)',
            backdropFilter: 'blur(12px)',
          }
        }}
      >
        <DialogTitle sx={{ 
          p: 0,
          background: 'linear-gradient(135deg, #1e3a8a 0%, #3b82f6 50%, #1e40af 100%)',
          color: 'white',
          borderRadius: '16px 16px 0 0',
        }}>
          <Box sx={{ 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'space-between',
            p: 3,
            background: 'linear-gradient(135deg, rgba(255, 255, 255, 0.1) 0%, transparent 100%)',
          }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              <HelpOutline sx={{ 
                color: 'white', 
                fontSize: '2rem',
                filter: 'drop-shadow(0 2px 4px rgba(0,0,0,0.2))'
              }} />
              <Box>
                <Typography variant="h5" fontWeight={700} sx={{ color: 'white' }}>
                  En Çok Sorulan Sorular
                </Typography>
                <Typography variant="body2" sx={{ color: 'rgba(255, 255, 255, 0.8)', mt: 0.5 }}>
                  Tüm sorular ve detayları
                </Typography>
              </Box>
            </Box>
            {allQuestions.length > 0 && (
              <Chip 
                label={`${allQuestions.length} soru listeleniyor`} 
                size="medium" 
                sx={{ 
                  backgroundColor: 'rgba(255, 255, 255, 0.2)',
                  color: 'white',
                  fontWeight: 600,
                  fontSize: '0.875rem',
                  border: '1px solid rgba(255, 255, 255, 0.3)',
                  backdropFilter: 'blur(10px)',
                }}
              />
            )}
          </Box>
        </DialogTitle>
        
        <DialogContent sx={{ 
          p: 0, 
          background: 'linear-gradient(135deg, rgba(248, 250, 252, 0.6) 0%, rgba(241, 245, 249, 0.6) 100%)',
        }}>
          {allQuestionsLoading ? (
            <Box sx={{ 
              display: 'flex', 
              flexDirection: 'column',
              justifyContent: 'center', 
              alignItems: 'center',
              p: 6,
              gap: 2
            }}>
              <CircularProgress 
                size={48} 
                sx={{ 
                  color: '#1e3a8a',
                  filter: 'drop-shadow(0 2px 4px rgba(30, 58, 138, 0.3))'
                }} 
              />
              <Typography variant="body1" sx={{ color: '#64748b', fontWeight: 500 }}>
                Sorular yükleniyor...
              </Typography>
            </Box>
          ) : allQuestions.length === 0 ? (
            <Box sx={{ 
              display: 'flex', 
              flexDirection: 'column',
              justifyContent: 'center', 
              alignItems: 'center',
              p: 6,
              gap: 2
            }}>
              <HelpOutline sx={{ 
                fontSize: '4rem', 
                color: '#cbd5e1', 
                filter: 'drop-shadow(0 2px 4px rgba(0,0,0,0.1))'
              }} />
              <Typography variant="h6" sx={{ color: '#64748b', fontWeight: 600 }}>
                Henüz soru sorulmamış
              </Typography>
              <Typography variant="body2" sx={{ color: '#94a3b8', textAlign: 'center' }}>
                İlk soru sorulduğunda burada görünecek
              </Typography>
            </Box>
          ) : (
            <>
              <List sx={{ p: 0 }}>
                {allQuestions.map((q, index) => (
                  <ListItem 
                    key={q.id} 
                    divider
                    sx={{
                      p: 3,
                      background: index % 2 === 0 
                        ? 'linear-gradient(135deg, rgba(255, 255, 255, 0.7) 0%, rgba(248, 250, 252, 0.7) 100%)'
                        : 'linear-gradient(135deg, rgba(248, 250, 252, 0.4) 0%, rgba(241, 245, 249, 0.4) 100%)',
                      borderLeft: '4px solid transparent',
                      '&:hover': {
                        borderLeftColor: '#3b82f6',
                        background: 'linear-gradient(135deg, rgba(30, 58, 138, 0.05) 0%, rgba(59, 130, 246, 0.05) 100%)',
                        transform: 'translateX(4px)',
                        transition: 'all 0.3s ease',
                      }
                    }}
                  >
                    <ListItemAvatar>
                      <Avatar sx={{ 
                        bgcolor: 'linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%)', 
                        color: 'white',
                        fontWeight: 700,
                        width: 45,
                        height: 45,
                        boxShadow: '0 4px 12px rgba(30, 58, 138, 0.3)',
                      }}>
                        {(allQuestionsPage - 1) * 10 + index + 1}
                      </Avatar>
                    </ListItemAvatar>
                    
                    <ListItemText
                      primary={
                        <Box sx={{ mb: 2 }}>
                          <Typography 
                            variant="h6" 
                            sx={{ 
                              color: '#1e293b', 
                              fontWeight: 600,
                              lineHeight: 1.4,
                              mb: 1
                            }}
                          >
                            {cleanTopicFromQuestion(q.question)}
                          </Typography>
                          
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, flexWrap: 'wrap' }}>
                            <Chip 
                              label={`${q.count} kez soruldu`} 
                              size="small" 
                              sx={{ 
                                background: 'linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%)',
                                color: 'white',
                                fontWeight: 600,
                                borderRadius: 2,
                                boxShadow: '0 2px 8px rgba(30, 58, 138, 0.25)',
                              }}
                            />
                            {q.source_file && (
                              <Chip 
                                icon={<Source sx={{ color: 'white !important' }} />}
                                label={q.source_keyword || q.source_file} 
                                size="small" 
                                sx={{ 
                                  background: 'linear-gradient(135deg, #7c3aed 0%, #a855f7 100%)',
                                  color: 'white',
                                  fontWeight: 600,
                                  borderRadius: 2,
                                  boxShadow: '0 2px 8px rgba(124, 58, 237, 0.25)',
                                  fontSize: { xs: '0.625rem', sm: '0.75rem', md: '0.875rem' },
                                  height: { xs: '20px', sm: '24px', md: '24px' },
                                  '& .MuiChip-label': {
                                    fontSize: { xs: '0.625rem', sm: '0.75rem', md: '0.875rem' },
                                    padding: { xs: '0 6px', sm: '0 8px', md: '0 12px' },
                                    lineHeight: { xs: 1.2, sm: 1.3, md: 1.4 },
                                    whiteSpace: 'nowrap',
                                    overflow: 'hidden',
                                    textOverflow: 'ellipsis',
                                    maxWidth: { xs: '120px', sm: '200px', md: 'none' },
                                  },
                                  '& .MuiChip-icon': {
                                    fontSize: { xs: '0.875rem', sm: '1rem', md: '1.125rem' },
                                  },
                                }}
                              />
                            )}
                          </Box>
                        </Box>
                      }
                      secondary={
                        <Box sx={{ mt: 2 }}>
                          <Typography 
                            variant="body1" 
                            sx={{ 
                              color: '#1e293b', 
                              lineHeight: 1.7,
                              background: 'rgba(248, 250, 252, 0.9)',
                              p: 2.5,
                              borderRadius: 2,
                              border: '1px solid rgba(203, 213, 225, 0.5)',
                              fontWeight: 500,
                              fontSize: '0.95rem',
                              whiteSpace: 'pre-wrap'
                            }}
                          >
                            {renderTextWithLinks(q.answer)}
                          </Typography>
                          {q.source_file && (
                            <Typography 
                              variant="caption" 
                              sx={{ 
                                mt: 1.5, 
                                display: 'flex',
                                alignItems: 'center',
                                gap: 0.5,
                                color: '#64748b',
                                fontWeight: 500,
                                background: 'rgba(241, 245, 249, 0.8)',
                                p: 1,
                                borderRadius: 1,
                                border: '1px solid rgba(203, 213, 225, 0.3)',
                              }}
                            >
                              📄 Kaynak Dosya: {q.source_file}
                            </Typography>
                          )}
                        </Box>
                      }
                    />
                  </ListItem>
                ))}
              </List>

              {allQuestionsTotalPages > 1 && (
                <Box sx={{ 
                  display: 'flex', 
                  justifyContent: 'center', 
                  p: 3,
                  background: 'linear-gradient(135deg, rgba(248, 250, 252, 0.8) 0%, rgba(241, 245, 249, 0.8) 100%)',
                  borderTop: '1px solid rgba(203, 213, 225, 0.3)',
                }}>
                  <Pagination 
                    count={allQuestionsTotalPages} 
                    page={allQuestionsPage} 
                    onChange={handleAllQuestionsPageChange}
                    color="primary"
                    size="large"
                    sx={{
                      '& .MuiPaginationItem-root': {
                        fontWeight: 600,
                        color: '#1e3a8a',
                        '&.Mui-selected': {
                          background: 'linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%)',
                          color: 'white',
                          boxShadow: '0 4px 12px rgba(30, 58, 138, 0.3)',
                        },
                        '&:hover': {
                          backgroundColor: 'rgba(30, 58, 138, 0.1)',
                        }
                      }
                    }}
                  />
                </Box>
              )}
            </>
          )}
        </DialogContent>
        
        <DialogActions sx={{ 
          p: 3, 
          background: 'linear-gradient(135deg, rgba(248, 250, 252, 0.9) 0%, rgba(241, 245, 249, 0.9) 100%)',
          borderTop: '1px solid rgba(59, 130, 246, 0.15)',
          backdropFilter: 'blur(10px)',
        }}>
          <Button 
            onClick={() => setAllQuestionsModal(false)}
            variant="contained"
            sx={{ 
              background: 'linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%)',
              color: 'white',
              borderRadius: 3,
              textTransform: 'none',
              fontWeight: 600,
              px: 4,
              py: 1.5,
              fontSize: '1rem',
              boxShadow: '0 6px 20px rgba(30, 58, 138, 0.35)',
              '&:hover': {
                background: 'linear-gradient(135deg, #1e40af 0%, #2563eb 100%)',
                boxShadow: '0 8px 25px rgba(30, 58, 138, 0.45)',
                transform: 'translateY(-2px)',
              },
              transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)'
            }}
          >
            Kapat
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default Stats;


