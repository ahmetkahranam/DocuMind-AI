import React, { useEffect, useState, useRef } from 'react';
import { 
  Box, 
  Typography, 
  Button, 
  Stack, 
  Card, 
  CardContent, 
  CardActionArea, 
  CircularProgress, 
  Divider, 
  Snackbar, 
  Alert, 
  Paper, 
  TextField, 
  InputAdornment, 
  Checkbox, 
  Pagination, 
  IconButton,
  Chip,
  Avatar,
  CardHeader,
  useTheme,
  alpha,
  LinearProgress,
  Tooltip,
  Fade,
  Zoom,
  List,
  ListItem,
  ListItemText,
  ListItemAvatar,
  ListItemSecondaryAction,
  Menu,
  MenuItem
} from '@mui/material';
import {
  InsertDriveFile,
  Search,
  CloudUpload,
  Delete,
  SelectAll,
  FilterList,
  Refresh,
  Storage,
  Description,
  Label,
  CheckCircle,
  RadioButtonUnchecked,
  FileUpload,
  DragIndicator,
  Download,
  ArrowDropDown
} from '@mui/icons-material';

const API = process.env.REACT_APP_API_URL || '';
const PAGE_SIZE = 10;

interface DocFile {
  filename: string;
  chunk_count: number;
  total_tokens: number;
  keyword?: string;
}

interface SnackbarState {
  open: boolean;
  message: string;
  severity: 'success' | 'error' | 'info' | 'warning';
}

const DocsManager: React.FC = () => {
  const theme = useTheme();
  const [docs, setDocs] = useState<DocFile[]>([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<string[]>([]);
  const [snackbar, setSnackbar] = useState<SnackbarState>({ open: false, message: '', severity: 'info' });
  const [pendingFile, setPendingFile] = useState<File | null>(null);
  const [keyword, setKeyword] = useState('');
  const [uploading, setUploading] = useState(false);
  const [dropActive, setDropActive] = useState(false);
  const [selectMenuAnchor, setSelectMenuAnchor] = useState<null | HTMLElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const keywordInputRef = useRef<HTMLInputElement>(null);

  const fetchDocs = async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/admin/documents");
      const data = await res.json();
      if (res.ok) {
        setDocs(data.documents || []);
      } else {
        setSnackbar({ open: true, message: data.error || 'Dosya listesi alınamadı', severity: 'error' });
      }
    } catch (err) {
      console.error('Fetch docs error:', err);
      setSnackbar({ open: true, message: `Sunucu hatası: ${err instanceof Error ? err.message : 'Bilinmeyen hata'}`, severity: 'error' });
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchDocs();
    
    // Autocomplete dropdown stil düzenlemesi - varsayılan renkleri koru
    const style = document.createElement('style');
    style.textContent = `
      /* Chrome/Safari autocomplete - varsayılan görünümü koru */
      input:-webkit-autofill,
      input:-webkit-autofill:hover,
      input:-webkit-autofill:focus,
      input:-webkit-autofill:active {
        -webkit-box-shadow: none !important;
        box-shadow: none !important;
        -webkit-text-fill-color: unset !important;
        background: transparent !important;
        background-color: transparent !important;
        background-image: none !important;
        color: inherit !important;
        transition: none !important;
        -webkit-transition: none !important;
      }
      
      /* Firefox autocomplete - varsayılan görünümü koru */
      input:-moz-autofill,
      input:-moz-autofill:hover,
      input:-moz-autofill:focus {
        background: transparent !important;
        background-color: transparent !important;
        color: inherit !important;
      }
      
      /* Tüm autofill durumları için genel reset */
      input[autocomplete]:autofill,
      input:-internal-autofill-selected {
        background-color: transparent !important;
        background-image: none !important;
        color: inherit !important;
      }
    `;
    document.head.appendChild(style);
    
    return () => {
      if (document.head.contains(style)) {
        document.head.removeChild(style);
      }
    };
  }, []);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      setPendingFile(files[0]);
      if (keywordInputRef.current) {
        keywordInputRef.current.focus();
      }
    }
  };

  const handleFileDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDropActive(false);
    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      setPendingFile(files[0]);
      if (keywordInputRef.current) {
        keywordInputRef.current.focus();
      }
    }
  };

  const handleKeywordChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setKeyword(e.target.value);
  };

  const handleManualUpload = async () => {
    if (!pendingFile) {
      setSnackbar({open: true, message: 'Lütfen bir dosya seçin.', severity: 'error'});
      return;
    }
    if (!keyword.trim()) {
      setSnackbar({open: true, message: 'Lütfen anahtar kelime girin.', severity: 'error'});
      return;
    }
    setUploading(true);
    const formData = new FormData();
    formData.append('file', pendingFile);
    formData.append('keyword', keyword.trim());
    try {
      const uploadRes = await fetch("/api/admin/upload_and_process", {
        method: 'POST',
        body: formData,
      });
      const uploadData = await uploadRes.json();
      if (!uploadRes.ok) {
        setSnackbar({open: true, message: uploadData.error || (uploadData.errors && uploadData.errors.join(', ')) || 'Yükleme hatası', severity: 'error'});
        setUploading(false);
        return;
      }
      setSnackbar({open: true, message: 'Dosya başarıyla yüklendi ve işlendi.', severity: 'success'});
      setKeyword('');
      setPendingFile(null);
      fetchDocs();
    } catch (err) {
      console.error('Upload error:', err);
      setSnackbar({open: true, message: `Sunucu hatası: ${err instanceof Error ? err.message : 'Bilinmeyen hata'}`, severity: 'error'});
    }
    setUploading(false);
  };

  const normalize = (str: string) =>
    (str || '')
      .toLocaleLowerCase('tr-TR')
      .replace(/İ/g, 'i')
      .replace(/I/g, 'ı')
      .replace(/Ş/g, 'ş')
      .replace(/Ğ/g, 'ğ')
      .replace(/Ü/g, 'ü')
      .replace(/Ö/g, 'ö')
      .replace(/Ç/g, 'ç')
      .replace(/[^a-z0-9çğıöşü\s]/gi, '')
      .replace(/\s+/g, ' ')
      .trim();

  const filteredDocs = docs.filter(file =>
    normalize(file.filename).includes(normalize(search)) ||
    (file.keyword && normalize(file.keyword).includes(normalize(search)))
  );
  const pageCount = Math.ceil(filteredDocs.length / PAGE_SIZE);
  const pagedDocs = filteredDocs.slice((page-1)*PAGE_SIZE, page*PAGE_SIZE);

  const handleSelect = (filename: string) => {
    setSelected(sel => sel.includes(filename) ? sel.filter(f => f !== filename) : [...sel, filename]);
  };

  const handleSelectAll = () => {
    if (pagedDocs.every(f => selected.includes(f.filename))) {
      setSelected(sel => sel.filter(f => !pagedDocs.some(d => d.filename === f)));
    } else {
      setSelected(sel => [...sel, ...pagedDocs.filter(f => !sel.includes(f.filename)).map(f => f.filename)]);
    }
    setSelectMenuAnchor(null);
  };

  const handleSelectAllFiltered = () => {
    if (filteredDocs.every(f => selected.includes(f.filename))) {
      setSelected(sel => sel.filter(f => !filteredDocs.some(d => d.filename === f)));
    } else {
      setSelected(sel => [...sel, ...filteredDocs.filter(f => !sel.includes(f.filename)).map(f => f.filename)]);
    }
    setSelectMenuAnchor(null);
  };

  const handleSelectMenuOpen = (event: React.MouseEvent<HTMLElement>) => {
    setSelectMenuAnchor(event.currentTarget);
  };

  const handleSelectMenuClose = () => {
    setSelectMenuAnchor(null);
  };

  const handleDeleteSelected = async () => {
    if (selected.length === 0) return;
    if (!window.confirm(`${selected.length} dosyayı silmek istediğinize emin misiniz?`)) return;
    setLoading(true);
    try {
      const res = await fetch("/api/admin/documents/bulk", {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ files: selected })
      });
      const data = await res.json();
      if (res.ok) {
        setSnackbar({open: true, message: data.message || 'Seçili dosyalar silindi ve ChromaDB güncellendi.', severity: 'success'});
        setSelected([]);
        fetchDocs();
      } else {
        setSnackbar({open: true, message: data.error || 'Toplu silme işlemi başarısız.', severity: 'error'});
      }
    } catch (e) {
      console.error('Sunucuya istek atılırken hata:', e);
      setSnackbar({
        open: true,
        message: 'Sunucuya bağlanılamadı. Lütfen sunucunun çalıştığından ve ağ bağlantınızın olduğundan emin olun.',
        severity: 'error'
      });
    }
    setLoading(false);
  };

  const handleDownloadFile = async (filename: string) => {
    try {
      setSnackbar({open: true, message: `${filename} dosyası indiriliyor...`, severity: 'info'});
      
      const response = await fetch(`/api/download/${encodeURIComponent(filename)}`, {
        method: 'GET',
      });

      if (!response.ok) {
        const errorData = await response.json();
        setSnackbar({
          open: true, 
          message: errorData.error || 'Dosya indirilemedi', 
          severity: 'error'
        });
        return;
      }

      // Dosyayı blob olarak al
      const blob = await response.blob();
      
      // Geçici URL oluştur ve indir
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      
      // Temizlik
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      
      setSnackbar({open: true, message: `${filename} başarıyla indirildi`, severity: 'success'});
      
    } catch (error) {
      console.error('Download error:', error);
      setSnackbar({
        open: true, 
        message: `İndirme hatası: ${error instanceof Error ? error.message : 'Bilinmeyen hata'}`, 
        severity: 'error'
      });
    }
  };

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => { 
    e.preventDefault(); 
    setDropActive(true); 
  };

  const handleDragLeave = (e: React.DragEvent<HTMLDivElement>) => { 
    e.preventDefault(); 
    setDropActive(false); 
  };

  return (
    <Box sx={{ p: 0 }}>
      <Stack 
        direction={{ xs: 'column', md: 'row' }} 
        spacing={{ xs: 2, md: 3 }} 
        sx={{ height: '100%' }}
      >
        {/* Dosya Listesi */}
        <Card
          sx={{
            flex: { xs: 'none', md: 1 },
            borderRadius: { xs: 2, sm: 3 },
            border: `1px solid rgba(30, 58, 138, 0.1)`,
            background: 'linear-gradient(135deg, rgba(255, 255, 255, 0.9) 0%, rgba(248, 250, 252, 0.9) 100%)',
            boxShadow: '0 8px 32px rgba(30, 58, 138, 0.08)',
            minHeight: { xs: '400px', md: 'auto' },
          }}
        >
          <CardHeader
            title={
              <Box sx={{ display: 'flex', alignItems: 'center', gap: { xs: 0.5, sm: 1 } }}>
                <Storage sx={{ 
                  color: '#1e3a8a',
                  fontSize: { xs: '1.125rem', sm: '1.25rem', md: '1.5rem' }
                }} />
                <Typography 
                  variant="h6" 
                  sx={{ 
                    fontWeight: 700, 
                    color: '#1e3a8a',
                    fontSize: { xs: '0.875rem', sm: '1rem', md: '1.25rem' }
                  }}
                >
                  Dosya Yönetimi
                </Typography>
                <Chip
                  label={`${docs.length} dosya`}
                  size="small"
                  variant="filled"
                  sx={{
                    borderRadius: 2,
                    fontWeight: 700,
                    color: 'white',
                    backgroundColor: '#1e3a8a',
                    fontSize: { xs: '0.625rem', sm: '0.75rem', md: '0.875rem' },
                    height: { xs: '18px', sm: '22px', md: '24px' },
                    '& .MuiChip-label': {
                      fontSize: { xs: '0.625rem', sm: '0.75rem', md: '0.875rem' },
                      padding: { xs: '0 4px', sm: '0 6px', md: '0 8px' },
                    }
                  }}
                />
              </Box>
            }
            action={
              <Box sx={{ 
                display: 'flex', 
                gap: { xs: 0.5, sm: 1 }, 
                alignItems: 'center',
                width: '100%',
                justifyContent: 'flex-end'
              }}>
                <TextField
                  size="small"
                  placeholder="Dosya ara..."
                  value={search}
                  onChange={e => { setSearch(e.target.value); setPage(1); }}
                  InputProps={{
                    startAdornment: (
                      <InputAdornment position="start">
                        <Search sx={{ color: '#64748b' }} />
                      </InputAdornment>
                    ),
                  }}
                  sx={{ 
                    minWidth: { xs: 120, sm: 180, md: 220 },
                    maxWidth: { xs: 200, sm: 250, md: 300 },
                    '& .MuiOutlinedInput-root': {
                      borderRadius: 2,
                      backgroundColor: 'rgba(255, 255, 255, 0.8)',
                      fontSize: { xs: '0.875rem', sm: '1rem' },
                      '& fieldset': {
                        borderColor: 'rgba(30, 58, 138, 0.2)',
                      },
                      '&:hover fieldset': {
                        borderColor: 'rgba(30, 58, 138, 0.4)',
                      },
                      '&.Mui-focused fieldset': {
                        borderColor: '#1e3a8a',
                      },
                    },
                    '& .MuiInputBase-input': {
                      color: '#1e293b',
                    }
                  }}
                />
              </Box>
            }
            sx={{ pb: 1 }}
          />
          <Divider />
          
          {/* Toplu İşlemler */}
          {pagedDocs.length > 0 && (
            <Box sx={{ 
              p: { xs: 1.5, sm: 2 }, 
              bgcolor: 'rgba(30, 58, 138, 0.02)', 
              borderBottom: `1px solid rgba(30, 58, 138, 0.1)` 
            }}>
              <Box sx={{ 
                display: 'flex', 
                alignItems: 'center', 
                gap: { xs: 1, sm: 2 },
                flexWrap: 'wrap'
              }}>
                <Checkbox 
                  checked={pagedDocs.every(f => selected.includes(f.filename)) && pagedDocs.length > 0} 
                  indeterminate={selected.length > 0 && selected.length < pagedDocs.length} 
                  onChange={handleSelectAll}
                  icon={<RadioButtonUnchecked />}
                  checkedIcon={<CheckCircle />}
                />
                <Button
                  variant="outlined"
                  size="small"
                  startIcon={<SelectAll />}
                  endIcon={<ArrowDropDown />}
                  onClick={handleSelectMenuOpen}
                  sx={{ 
                    borderRadius: 2,
                    textTransform: 'none',
                    fontWeight: 600,
                    color: '#1e3a8a',
                    borderColor: '#1e3a8a',
                    backgroundColor: 'rgba(30, 58, 138, 0.05)',
                    fontSize: { xs: '0.75rem', sm: '0.875rem' },
                    px: { xs: 1.5, sm: 2 },
                    py: { xs: 0.5, sm: 1 },
                    '&:hover': {
                      backgroundColor: 'rgba(30, 58, 138, 0.1)',
                      borderColor: '#1e40af',
                      color: '#1e40af',
                    },
                    '& .MuiSvgIcon-root': {
                      color: '#1e3a8a',
                      fontSize: { xs: '1rem', sm: '1.25rem' },
                    },
                    '&:hover .MuiSvgIcon-root': {
                      color: '#1e40af',
                    }
                  }}
                >
                  Seçim
                </Button>
                <Menu
                  anchorEl={selectMenuAnchor}
                  open={Boolean(selectMenuAnchor)}
                  onClose={handleSelectMenuClose}
                  sx={{
                    '& .MuiPaper-root': {
                      borderRadius: 2,
                      boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
                      minWidth: 200,
                    }
                  }}
                >
                  <MenuItem 
                    onClick={handleSelectAll}
                    sx={{
                      fontSize: '0.875rem',
                      fontWeight: 500,
                      color: '#1e293b',
                      '&:hover': {
                        backgroundColor: 'rgba(30, 58, 138, 0.08)',
                        color: '#1e3a8a',
                      }
                    }}
                  >
                    <SelectAll sx={{ mr: 1, fontSize: '1.125rem' }} />
                    {pagedDocs.every(f => selected.includes(f.filename)) && pagedDocs.length > 0 
                      ? 'Bu Sayfadan Seçimi Kaldır' 
                      : 'Bu Sayfadakileri Seç'
                    }
                  </MenuItem>
                  <MenuItem 
                    onClick={handleSelectAllFiltered}
                    sx={{
                      fontSize: '0.875rem',
                      fontWeight: 500,
                      color: '#1e293b',
                      '&:hover': {
                        backgroundColor: 'rgba(30, 58, 138, 0.08)',
                        color: '#1e3a8a',
                      }
                    }}
                  >
                    <SelectAll sx={{ mr: 1, fontSize: '1.125rem' }} />
                    {filteredDocs.every(f => selected.includes(f.filename)) && filteredDocs.length > 0 
                      ? 'Tüm Seçimleri Kaldır' 
                      : 'Tümünü Seç'
                    }
                  </MenuItem>
                </Menu>
                <Typography variant="body2" sx={{ flex: 1, fontWeight: 500, color: '#1e293b' }}>
                  {selected.length > 0 ? `${selected.length} dosya seçildi` : `${pagedDocs.length} dosya`}
                </Typography>
                <Fade in={selected.length > 0}>
                  <Button
                    variant="outlined"
                    color="error"
                    size="small"
                    startIcon={<Delete />}
                    onClick={handleDeleteSelected}
                    disabled={loading}
                    sx={{ 
                      borderRadius: 2,
                      textTransform: 'none',
                      fontWeight: 600,
                      color: '#dc2626',
                      borderColor: '#dc2626',
                      backgroundColor: 'rgba(220, 38, 38, 0.05)',
                      fontSize: { xs: '0.75rem', sm: '0.875rem' },
                      px: { xs: 1.5, sm: 2 },
                      py: { xs: 0.5, sm: 1 },
                      '&:hover': {
                        backgroundColor: 'rgba(220, 38, 38, 0.1)',
                        borderColor: '#b91c1c',
                        color: '#b91c1c',
                      },
                      '& .MuiSvgIcon-root': {
                        color: '#dc2626',
                        fontSize: { xs: '1rem', sm: '1.25rem' },
                      },
                      '&:hover .MuiSvgIcon-root': {
                        color: '#b91c1c',
                      }
                    }}
                  >
                    Seçili Dosyaları Sil
                  </Button>
                </Fade>
              </Box>
            </Box>
          )}

          <CardContent sx={{ p: 0 }}>
            {loading ? (
              <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
                <CircularProgress />
              </Box>
            ) : pagedDocs.length === 0 ? (
              <Box sx={{ textAlign: 'center', p: 4, color: '#64748b' }}>
                <Description sx={{ fontSize: '4rem', mb: 2, opacity: 0.5, color: '#64748b' }} />
                <Typography variant="h6" sx={{ mb: 1, color: '#1e293b' }}>
                  {search ? 'Arama sonucu bulunamadı' : 'Henüz dosya yüklenmemiş'}
                </Typography>
                <Typography variant="body2" sx={{ color: '#64748b' }}>
                  {search ? 'Farklı bir arama terimi deneyin' : 'Yeni dosya yüklemek için yan taraftaki alanı kullanın'}
                </Typography>
              </Box>
            ) : (
              <List>
                {pagedDocs.map((file, index) => (
                  <Zoom in={true} key={file.filename} style={{ transitionDelay: `${index * 50}ms` }}>
                    <ListItem
                      sx={{
                        py: 2,
                        px: 3,
                        '&:hover': {
                          bgcolor: 'rgba(30, 58, 138, 0.05)',
                        },
                        borderLeft: selected.includes(file.filename) 
                          ? `4px solid #1e3a8a` 
                          : '4px solid transparent',
                        transition: 'all 0.2s ease-in-out',
                      }}
                    >
                      <ListItemAvatar>
                        <Avatar
                          sx={{
                            bgcolor: selected.includes(file.filename) 
                              ? '#1e3a8a' 
                              : 'rgba(30, 58, 138, 0.1)',
                            color: selected.includes(file.filename) 
                              ? 'white' 
                              : '#1e3a8a',
                          }}
                        >
                          <InsertDriveFile />
                        </Avatar>
                      </ListItemAvatar>
                      
                      <ListItemText
                        primary={
                          <Typography
                            variant="subtitle1"
                            sx={{
                              fontWeight: 600,
                              color: '#1e293b',
                              mb: 0.5,
                              fontSize: { xs: '0.8rem', sm: '0.9rem', md: '1rem' },
                              lineHeight: { xs: 1.3, sm: 1.4, md: 1.5 },
                              wordBreak: 'break-word',
                              overflowWrap: 'break-word',
                              pr: { xs: 10, sm: 12, md: 14 }, // Right padding to avoid button overlap
                              maxWidth: '100%',
                              whiteSpace: 'normal', // Allow text wrapping
                            }}
                          >
                            {file.filename}
                          </Typography>
                        }
                        secondary={
                          <React.Fragment>
                            {file.keyword && (
                              <Box component="span" sx={{ display: 'inline-block', mt: 1 }}>
                                <Chip
                                  icon={<Label />}
                                  label={file.keyword}
                                  size="small"
                                  variant="filled"
                                  sx={{
                                    borderRadius: 1,
                                    bgcolor: '#1e3a8a',
                                    color: 'white',
                                    fontWeight: 600,
                                    fontSize: { xs: '0.55rem', sm: '0.65rem', md: '0.75rem' },
                                    height: 'auto',
                                    minHeight: { xs: '18px', sm: '20px', md: '22px' },
                                    whiteSpace: 'normal',
                                    wordBreak: 'break-word',
                                    overflowWrap: 'break-word',
                                    '& .MuiChip-label': {
                                      fontSize: { xs: '0.55rem', sm: '0.65rem', md: '0.75rem' },
                                      padding: { xs: '0 4px', sm: '0 6px', md: '0 8px' },
                                      lineHeight: { xs: 1.2, sm: 1.3, md: 1.4 },
                                      whiteSpace: 'normal',
                                      wordBreak: 'break-word',
                                      overflowWrap: 'break-word',
                                    },
                                    '& .MuiChip-icon': {
                                      color: 'white',
                                      fontSize: { xs: '0.75rem', sm: '0.875rem', md: '1rem' },
                                    }
                                  }}
                                />
                              </Box>
                            )}
                          </React.Fragment>
                        }
                        secondaryTypographyProps={{
                          component: 'span'
                        }}
                      />
                      
                      <ListItemSecondaryAction>
                        <Box sx={{ display: 'flex', gap: 0.5 }}>
                          <IconButton
                            edge="end"
                            size="small"
                            onClick={() => handleDownloadFile(file.filename)}
                            sx={{
                              color: '#059669',
                              width: { xs: 32, sm: 36, md: 40 },
                              height: { xs: 32, sm: 36, md: 40 },
                              '&:hover': {
                                bgcolor: 'rgba(5, 150, 105, 0.1)',
                              },
                            }}
                            title="Dosyayı İndir"
                          >
                            <Download sx={{ fontSize: { xs: '1rem', sm: '1.125rem', md: '1.25rem' } }} />
                          </IconButton>
                          <IconButton
                            edge="end"
                            size="small"
                            onClick={() => handleSelect(file.filename)}
                            sx={{
                              color: selected.includes(file.filename) 
                                ? '#1e3a8a' 
                                : '#64748b',
                              width: { xs: 32, sm: 36, md: 40 },
                              height: { xs: 32, sm: 36, md: 40 },
                              '&:hover': {
                                bgcolor: 'rgba(30, 58, 138, 0.1)',
                              },
                            }}
                          >
                            {selected.includes(file.filename) ? (
                              <CheckCircle sx={{ fontSize: { xs: '1rem', sm: '1.125rem', md: '1.25rem' } }} />
                            ) : (
                              <RadioButtonUnchecked sx={{ fontSize: { xs: '1rem', sm: '1.125rem', md: '1.25rem' } }} />
                            )}
                          </IconButton>
                        </Box>
                      </ListItemSecondaryAction>
                    </ListItem>
                  </Zoom>
                ))}
              </List>
            )}
            
            {/* Pagination */}
            {pageCount > 1 && (
              <Box sx={{ display: 'flex', justifyContent: 'center', p: { xs: 1.5, sm: 2 } }}>
                <Pagination
                  count={pageCount}
                  page={page}
                  onChange={(e, p) => setPage(p)}
                  color="primary"
                  size="medium"
                  sx={{
                    '& .MuiPaginationItem-root': {
                      borderRadius: 2,
                      fontWeight: 600,
                      fontSize: { xs: '0.75rem', sm: '0.875rem' },
                      minWidth: { xs: '28px', sm: '32px' },
                      height: { xs: '28px', sm: '32px' },
                      '&.Mui-selected': {
                        boxShadow: '0 2px 8px rgba(0,0,0,0.2)',
                      }
                    }
                  }}
                />
              </Box>
            )}
          </CardContent>
        </Card>

        {/* Dosya Yükleme Paneli */}
        <Card
          sx={{
            minWidth: { xs: 'auto', md: 380 },
            width: { xs: '100%', md: 'auto' },
            height: 'fit-content',
            background: 'linear-gradient(135deg, rgba(255, 255, 255, 0.9) 0%, rgba(248, 250, 252, 0.9) 100%)',
            borderRadius: { xs: 2, sm: 3 },
            border: `1px solid rgba(30, 58, 138, 0.1)`,
            boxShadow: '0 8px 32px rgba(30, 58, 138, 0.08)',
          }}
        >
          <CardHeader
            avatar={
              <Avatar sx={{ 
                bgcolor: 'linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%)',
                boxShadow: '0 4px 12px rgba(30, 58, 138, 0.2)',
              }}>
                <CloudUpload />
              </Avatar>
            }
            title="Yeni Dosya Yükle"
            subheader="PDF, DOCX, TXT, MD formatları desteklenir"
            sx={{
              '& .MuiCardHeader-title': {
                fontWeight: 700,
                fontSize: '1.25rem',
                color: '#1e3a8a',
              },
              '& .MuiCardHeader-subheader': {
                fontWeight: 500,
                color: '#64748b',
              }
            }}
          />
          
          <CardContent>
            {/* Drag & Drop Alanı */}
            <Box
              onDrop={handleFileDrop}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              sx={{
                border: dropActive 
                  ? `2px dashed #1e3a8a` 
                  : `2px dashed rgba(30, 58, 138, 0.3)`,
                borderRadius: { xs: 2, sm: 3 },
                p: { xs: 2, sm: 3, md: 4 },
                mb: { xs: 2, sm: 3 },
                textAlign: 'center',
                bgcolor: dropActive 
                  ? 'rgba(30, 58, 138, 0.05)' 
                  : 'rgba(255, 255, 255, 0.8)',
                cursor: 'pointer',
                transition: 'all 0.3s ease-in-out',
                '&:hover': {
                  bgcolor: 'rgba(30, 58, 138, 0.05)',
                  borderColor: '#1e3a8a',
                }
              }}
            >
              <Box sx={{ mb: { xs: 1.5, sm: 2 } }}>
                <CloudUpload 
                  sx={{ 
                    fontSize: { xs: 36, sm: 42, md: 48 }, 
                    color: dropActive ? '#1e3a8a' : '#64748b',
                    mb: 1 
                  }} 
                />
                <Typography 
                  variant="h6" 
                  sx={{ 
                    fontWeight: 600,
                    color: dropActive ? '#1e3a8a' : '#1e293b',
                    mb: 1,
                    fontSize: { xs: '1rem', sm: '1.125rem', md: '1.25rem' }
                  }}
                >
                  Dosyayı Sürükle & Bırak
                </Typography>
                <Typography 
                  variant="body2" 
                  sx={{ 
                    mb: { xs: 1.5, sm: 2 },
                    color: '#64748b',
                    fontSize: { xs: '0.75rem', sm: '0.875rem' }
                  }}
                >
                  ya da dosya seçmek için tıklayın
                </Typography>
              </Box>
              
              <Button
                variant="contained"
                component="label"
                startIcon={<FileUpload />}
                sx={{
                  borderRadius: 2,
                  textTransform: 'none',
                  fontWeight: 600,
                  px: { xs: 2, sm: 2.5, md: 3 },
                  py: { xs: 1, sm: 1.25, md: 1.5 },
                  fontSize: { xs: '0.875rem', sm: '1rem' },
                  background: 'linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%)',
                  boxShadow: '0 4px 16px rgba(30, 58, 138, 0.3)',
                  '&:hover': {
                    background: 'linear-gradient(135deg, #1e40af 0%, #2563eb 100%)',
                    transform: 'translateY(-1px)',
                    boxShadow: '0 6px 20px rgba(30, 58, 138, 0.4)',
                  },
                  '& .MuiSvgIcon-root': {
                    fontSize: { xs: '1rem', sm: '1.25rem' }
                  },
                  transition: 'all 0.2s ease-in-out',
                }}
                disabled={uploading}
              >
                Dosya Seç
                <input
                  type="file"
                  hidden
                  ref={fileInputRef}
                  onChange={handleFileChange}
                  accept=".pdf,.docx,.txt,.md"
                />
              </Button>
              
              {pendingFile && (
                <Fade in={true}>
                  <Box sx={{ 
                    mt: 3, 
                    p: 2, 
                    border: `1px solid #1e3a8a`,
                    borderRadius: 2,
                    bgcolor: 'rgba(30, 58, 138, 0.1)',
                    overflowX: 'auto',
                    maxWidth: '100%',
                  }}>
                    <Typography 
                      variant="body2" 
                      sx={{ 
                        color: '#1e293b', // much darker for readability
                        fontWeight: 600,
                        display: 'flex',
                        alignItems: 'center',
                        gap: 1,
                        maxWidth: '100%',
                        whiteSpace: 'nowrap',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        fontSize: { xs: '0.85rem', sm: '1rem' },
                      }}
                    >
                      <InsertDriveFile fontSize="small" />
                      <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', display: 'inline-block', maxWidth: '80vw', color: '#1e293b' }}>{pendingFile.name}</span>
                    </Typography>
                  </Box>
                </Fade>
              )}
            </Box>
            
            {/* Anahtar Kelime */}
            <TextField
              label="Anahtar Kelime"
              value={keyword}
              onChange={handleKeywordChange}
              inputRef={keywordInputRef}
              fullWidth
              variant="outlined"
              sx={{ 
                mb: { xs: 2, sm: 3 },
                fontSize: { xs: '0.95rem', sm: '1rem' },
                '& .MuiInputLabel-root': {
                  color: uploading ? '#94a3b8' : '#64748b',
                  fontSize: { xs: '0.95rem', sm: '1rem' },
                  '&.Mui-focused': {
                    color: uploading ? '#94a3b8' : '#1e3a8a',
                  },
                  '&.Mui-disabled': {
                    color: '#94a3b8',
                  }
                },
                '& .MuiOutlinedInput-root': {
                  borderRadius: 2,
                  bgcolor: uploading ? 'rgba(248, 250, 252, 0.8)' : 'rgba(255, 255, 255, 0.9)',
                  color: uploading ? '#64748b' : '#1e293b',
                  fontSize: { xs: '0.95rem', sm: '1rem' },
                  padding: { xs: '0.5rem 0.75rem', sm: '0.75rem 1rem' },
                  minHeight: { xs: 40, sm: 48 },
                  '& .MuiOutlinedInput-notchedOutline': {
                    borderColor: uploading ? 'rgba(148, 163, 184, 0.3)' : 'rgba(30, 58, 138, 0.2)',
                  },
                  '&:hover .MuiOutlinedInput-notchedOutline': {
                    borderColor: uploading ? 'rgba(148, 163, 184, 0.4)' : 'rgba(30, 58, 138, 0.4)',
                  },
                  '&.Mui-focused .MuiOutlinedInput-notchedOutline': {
                    borderColor: uploading ? 'rgba(148, 163, 184, 0.5)' : '#1e3a8a',
                    borderWidth: 2,
                  },
                  '&.Mui-disabled': {
                    backgroundColor: 'rgba(248, 250, 252, 0.8)',
                    '& .MuiInputBase-input': {
                      color: '#64748b',
                      WebkitTextFillColor: '#64748b',
                    }
                  },
                  '& input': {
                    fontSize: { xs: '0.95rem', sm: '1rem' },
                  }
                },
                '& .MuiFormHelperText-root': {
                  color: uploading ? '#94a3b8' : '#64748b',
                  '&.Mui-disabled': {
                    color: '#94a3b8',
                  }
                }
              }}
              disabled={uploading}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <Label sx={{ color: uploading ? '#94a3b8' : '#1e3a8a' }} />
                  </InputAdornment>
                ),
              }}
              helperText="Dosya içeriğini tanımlayan anahtar kelime"
            />
            
            {/* Yükleme Butonu */}
            <Button
              variant="contained"
              fullWidth
              size="large"
              onClick={handleManualUpload}
              disabled={uploading || !pendingFile || !keyword.trim()}
              sx={{
                borderRadius: 2,
                textTransform: 'none',
                fontWeight: 700,
                py: 1.5,
                fontSize: '1.1rem',
                bgcolor: '#1e3a8a',
                color: 'white',
                boxShadow: '0 4px 12px rgba(30, 58, 138, 0.3)',
                '&:hover': {
                  bgcolor: '#1e40af',
                  transform: 'translateY(-1px)',
                  boxShadow: '0 6px 16px rgba(30, 58, 138, 0.4)',
                },
                '&:disabled': {
                  bgcolor: 'rgba(30, 58, 138, 0.3)',
                  color: 'rgba(255, 255, 255, 0.7)',
                },
                transition: 'all 0.2s ease-in-out',
              }}
            >
              {uploading ? (
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, color: 'white' }}>
                  <CircularProgress size={20} sx={{ color: 'white' }} />
                  Yükleniyor...
                </Box>
              ) : (
                'Dosyayı Yükle ve İşle'
              )}
            </Button>
            
            {uploading && (
              <LinearProgress 
                sx={{ 
                  mt: 2, 
                  borderRadius: 1,
                  height: 6,
                  bgcolor: 'rgba(30, 58, 138, 0.1)',
                  '& .MuiLinearProgress-bar': {
                    bgcolor: '#1e3a8a',
                  }
                }} 
              />
            )}
          </CardContent>
        </Card>
      </Stack>
      
      <Snackbar 
        open={snackbar.open} 
        autoHideDuration={4000} 
        onClose={() => setSnackbar({...snackbar, open: false})}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert 
          severity={snackbar.severity} 
          sx={{ 
            width: '100%',
            borderRadius: 2,
            fontWeight: 600,
          }}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default DocsManager;
