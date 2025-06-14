import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Paper,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Switch,
  FormControlLabel,
  Button,
  Alert,
  Divider,
  Grid,
} from '@mui/material';
import { Save, Refresh } from '@mui/icons-material';

interface SystemConfig {
  ai_model: string;
  logging_level: string;
  max_results: number;
  enable_notifications: boolean;
  auto_save_history: boolean;
}

const SettingsPage: React.FC = () => {
  const [config, setConfig] = useState<SystemConfig>({
    ai_model: 'gemini-pro',
    logging_level: 'INFO',
    max_results: 10,
    enable_notifications: true,
    auto_save_history: true,
  });
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  useEffect(() => {
    fetchConfig();
  }, []);

  const fetchConfig = async () => {
    try {
      const response = await fetch('http://localhost:8001/api/v1/system/config');
      if (response.ok) {
        const data = await response.json();
        setConfig(data);
      }
    } catch (err) {
      console.error('Failed to fetch config:', err);
    }
  };

  const handleSave = async () => {
    setLoading(true);
    setMessage(null);

    try {
      const response = await fetch('http://localhost:8001/api/v1/system/config', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(config),
      });

      if (response.ok) {
        setMessage({ type: 'success', text: '설정이 성공적으로 저장되었습니다.' });
      } else {
        throw new Error('Failed to save config');
      }
    } catch (err) {
      setMessage({ type: 'error', text: '설정 저장 중 오류가 발생했습니다.' });
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setConfig({
      ai_model: 'gemini-pro',
      logging_level: 'INFO',
      max_results: 10,
      enable_notifications: true,
      auto_save_history: true,
    });
    setMessage(null);
  };

  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom>
        시스템 설정
      </Typography>
      <Typography variant="subtitle1" color="text.secondary" gutterBottom>
        쇼핑 에이전트의 동작을 설정할 수 있습니다.
      </Typography>

      <Paper elevation={3} sx={{ p: 3, mt: 3 }}>
        {message && (
          <Alert severity={message.type} sx={{ mb: 3 }}>
            {message.text}
          </Alert>
        )}

        <Grid container spacing={3}>
          <Grid size={{ xs: 12, md: 6 }}>
            <Typography variant="h6" gutterBottom>
              AI 모델 설정
            </Typography>
            
            <FormControl fullWidth sx={{ mb: 3 }}>
              <InputLabel>AI 모델</InputLabel>
              <Select
                value={config.ai_model}
                label="AI 모델"
                onChange={(e) => setConfig({ ...config, ai_model: e.target.value })}
              >
                <MenuItem value="gemini-pro">Gemini Pro</MenuItem>
                <MenuItem value="gemini-pro-vision">Gemini Pro Vision</MenuItem>
                <MenuItem value="gpt-4">GPT-4</MenuItem>
                <MenuItem value="gpt-3.5-turbo">GPT-3.5 Turbo</MenuItem>
              </Select>
            </FormControl>

            <FormControl fullWidth sx={{ mb: 3 }}>
              <InputLabel>로깅 레벨</InputLabel>
              <Select
                value={config.logging_level}
                label="로깅 레벨"
                onChange={(e) => setConfig({ ...config, logging_level: e.target.value })}
              >
                <MenuItem value="DEBUG">DEBUG</MenuItem>
                <MenuItem value="INFO">INFO</MenuItem>
                <MenuItem value="WARNING">WARNING</MenuItem>
                <MenuItem value="ERROR">ERROR</MenuItem>
              </Select>
            </FormControl>

            <FormControl fullWidth sx={{ mb: 3 }}>
              <InputLabel>최대 결과 수</InputLabel>
              <Select
                value={config.max_results}
                label="최대 결과 수"
                onChange={(e) => setConfig({ ...config, max_results: Number(e.target.value) })}
              >
                <MenuItem value={5}>5개</MenuItem>
                <MenuItem value={10}>10개</MenuItem>
                <MenuItem value={20}>20개</MenuItem>
                <MenuItem value={50}>50개</MenuItem>
              </Select>
            </FormControl>
          </Grid>

          <Grid size={{ xs: 12, md: 6 }}>
            <Typography variant="h6" gutterBottom>
              기능 설정
            </Typography>
            
            <FormControlLabel
              control={
                <Switch
                  checked={config.enable_notifications}
                  onChange={(e) => setConfig({ ...config, enable_notifications: e.target.checked })}
                />
              }
              label="알림 활성화"
              sx={{ display: 'block', mb: 2 }}
            />

            <FormControlLabel
              control={
                <Switch
                  checked={config.auto_save_history}
                  onChange={(e) => setConfig({ ...config, auto_save_history: e.target.checked })}
                />
              }
              label="히스토리 자동 저장"
              sx={{ display: 'block', mb: 2 }}
            />
          </Grid>
        </Grid>

        <Divider sx={{ my: 3 }} />

        <Box display="flex" gap={2} justifyContent="flex-end">
          <Button
            variant="outlined"
            startIcon={<Refresh />}
            onClick={handleReset}
            disabled={loading}
          >
            초기화
          </Button>
          <Button
            variant="contained"
            startIcon={<Save />}
            onClick={handleSave}
            disabled={loading}
          >
            {loading ? '저장 중...' : '저장'}
          </Button>
        </Box>
      </Paper>
    </Box>
  );
};

export default SettingsPage;