import React, { useState } from 'react';
import {
  Box,
  Paper,
  TextField,
  Button,
  Typography,
  Card,
  CardContent,
  LinearProgress,
  Alert,
} from '@mui/material';
import { Grid } from '@mui/material';
import { Search, Send } from '@mui/icons-material';

interface ShoppingRequest {
  query: string;
  context?: Record<string, any>;
  user_id?: string;
  session_id?: string;
}

const HomePage: React.FC = () => {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const requestData: ShoppingRequest = {
        query: query.trim(),
        context: {},
        user_id: 'web-user',
        session_id: `session-${Date.now()}`
      };

      const response = await fetch('http://localhost:8001/api/v1/requests', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestData),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : '요청 처리 중 오류가 발생했습니다.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom>
        쇼핑 에이전트
      </Typography>
      <Typography variant="subtitle1" color="text.secondary" gutterBottom>
        원하는 상품을 검색해보세요. AI가 최적의 쇼핑 결과를 찾아드립니다.
      </Typography>

      <Paper elevation={3} sx={{ p: 3, mt: 3 }}>
        <form onSubmit={handleSubmit}>
          <Grid container spacing={2} alignItems="center">
            <Grid size={{ xs: 12, md: 10 }}>
              <TextField
                fullWidth
                label="쇼핑 요청"
                placeholder="예: 가성비 좋은 노트북 추천해줘"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                disabled={loading}
                InputProps={{
                  startAdornment: <Search sx={{ mr: 1, color: 'action.active' }} />,
                }}
              />
            </Grid>
            <Grid size={{ xs: 12, md: 6 }}>
              <Button
                type="submit"
                variant="contained"
                fullWidth
                disabled={loading || !query.trim()}
                startIcon={<Send />}
                sx={{ height: 56 }}
              >
                {loading ? '처리중...' : '검색'}
              </Button>
            </Grid>
          </Grid>
        </form>

        {loading && (
          <Box sx={{ mt: 3 }}>
            <Typography variant="body2" gutterBottom>
              요청을 처리하고 있습니다...
            </Typography>
            <LinearProgress />
          </Box>
        )}

        {error && (
          <Alert severity="error" sx={{ mt: 3 }}>
            {error}
          </Alert>
        )}

        {result && (
          <Card sx={{ mt: 3 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                요청 결과
              </Typography>
              <Typography variant="body2" color="text.secondary" gutterBottom>
                요청 ID: {result.request_id}
              </Typography>
              <Typography variant="body2" color="text.secondary" gutterBottom>
                상태: {result.status}
              </Typography>
              <Typography variant="body1">
                {result.message || '요청이 성공적으로 접수되었습니다.'}
              </Typography>
            </CardContent>
          </Card>
        )}
      </Paper>

      <Box sx={{ mt: 4 }}>
        <Typography variant="h6" gutterBottom>
          사용 예시
        </Typography>
        <Grid container spacing={2}>
          {[
            '가성비 좋은 노트북 추천해줘',
            '겨울용 패딩 재킷 찾아줘',
            '아이폰 15 최저가 알려줘',
            '운동화 브랜드별 가격 비교해줘'
          ].map((example, index) => (
            <Grid size={{ xs: 12, sm: 6, md: 3 }} key={index}>
              <Card 
                sx={{ 
                  cursor: 'pointer',
                  '&:hover': { bgcolor: 'action.hover' }
                }}
                onClick={() => setQuery(example)}
              >
                <CardContent>
                  <Typography variant="body2">
                    {example}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      </Box>
    </Box>
  );
};

export default HomePage;