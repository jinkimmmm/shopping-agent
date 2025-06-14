import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Paper,
  List,
  ListItem,
  ListItemText,
  TextField,
  InputAdornment,
  Chip,
  Divider,
  Alert,
  CircularProgress,
} from '@mui/material';
import { Search, AccessTime } from '@mui/icons-material';

interface HistoryItem {
  id: string;
  query: string;
  status: string;
  created_at: string;
  updated_at: string;
}

const HistoryPage: React.FC = () => {
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    fetchHistory();
  }, []);

  const fetchHistory = async () => {
    try {
      const response = await fetch('http://localhost:8001/api/v1/history');
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      setHistory(data.requests || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : '히스토리를 불러오는 중 오류가 발생했습니다.');
    } finally {
      setLoading(false);
    }
  };

  const filteredHistory = history.filter(item =>
    item.query.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'completed':
        return 'success';
      case 'processing':
        return 'warning';
      case 'failed':
        return 'error';
      default:
        return 'default';
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('ko-KR');
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom>
        요청 히스토리
      </Typography>
      <Typography variant="subtitle1" color="text.secondary" gutterBottom>
        이전에 요청했던 쇼핑 검색 기록을 확인할 수 있습니다.
      </Typography>

      <Paper elevation={3} sx={{ p: 3, mt: 3 }}>
        <TextField
          fullWidth
          label="히스토리 검색"
          placeholder="검색어를 입력하세요"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <Search />
              </InputAdornment>
            ),
          }}
          sx={{ mb: 3 }}
        />

        {error && (
          <Alert severity="error" sx={{ mb: 3 }}>
            {error}
          </Alert>
        )}

        {filteredHistory.length === 0 ? (
          <Box textAlign="center" py={4}>
            <Typography variant="body1" color="text.secondary">
              {searchTerm ? '검색 결과가 없습니다.' : '아직 요청 기록이 없습니다.'}
            </Typography>
          </Box>
        ) : (
          <List>
            {filteredHistory.map((item, index) => (
              <React.Fragment key={item.id}>
                <ListItem alignItems="flex-start">
                  <ListItemText
                    primary={
                      <Box display="flex" alignItems="center" gap={1}>
                        <Typography variant="subtitle1">
                          {item.query}
                        </Typography>
                        <Chip
                          label={item.status}
                          color={getStatusColor(item.status) as any}
                          size="small"
                        />
                      </Box>
                    }
                    secondary={
                      <Box display="flex" alignItems="center" gap={1} mt={1}>
                        <AccessTime fontSize="small" color="action" />
                        <Typography variant="body2" color="text.secondary">
                          요청: {formatDate(item.created_at)}
                        </Typography>
                        {item.updated_at !== item.created_at && (
                          <Typography variant="body2" color="text.secondary">
                            • 업데이트: {formatDate(item.updated_at)}
                          </Typography>
                        )}
                      </Box>
                    }
                  />
                </ListItem>
                {index < filteredHistory.length - 1 && <Divider />}
              </React.Fragment>
            ))}
          </List>
        )}
      </Paper>
    </Box>
  );
};

export default HistoryPage;