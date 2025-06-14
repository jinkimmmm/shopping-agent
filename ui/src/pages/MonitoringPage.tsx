import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Paper,
  Card,
  CardContent,
  LinearProgress,
  Chip,
  List,
  ListItem,
  ListItemText,
  Divider,
  Alert,
  CircularProgress,
  Grid,
} from '@mui/material';
import {
  Computer,
  Memory,
  Storage,
  Speed,
  CheckCircle,
  Error,
  Warning,
} from '@mui/icons-material';

interface SystemStatus {
  status: string;
  uptime: string;
  version: string;
  cpu_usage?: number;
  memory_usage?: number;
  disk_usage?: number;
  active_requests?: number;
  total_requests?: number;
}

interface LogEntry {
  timestamp: string;
  level: string;
  message: string;
}

const MonitoringPage: React.FC = () => {
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchSystemStatus();
    const interval = setInterval(fetchSystemStatus, 30000); // 30초마다 업데이트
    return () => clearInterval(interval);
  }, []);

  const fetchSystemStatus = async () => {
    try {
      const response = await fetch('http://localhost:8001/api/v1/system/status');
      if (!response.ok) {
        throw new (Error as any)(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      setSystemStatus(data);
      setError(null);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError((err as Error).message);
      } else {
        setError('시스템 상태를 불러오는 중 오류가 발생했습니다.');
      }
    } finally {
      setLoading(false);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status.toLowerCase()) {
      case 'healthy':
      case 'running':
        return <CheckCircle color="success" />;
      case 'warning':
        return <Warning color="warning" />;
      case 'error':
      case 'down':
        return <Error color="error" />;
      default:
        return <CheckCircle color="action" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'healthy':
      case 'running':
        return 'success';
      case 'warning':
        return 'warning';
      case 'error':
      case 'down':
        return 'error';
      default:
        return 'default';
    }
  };

  const formatUptime = (uptime: string) => {
    // 간단한 업타임 포맷팅
    return uptime || '알 수 없음';
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
        시스템 모니터링
      </Typography>
      <Typography variant="subtitle1" color="text.secondary" gutterBottom>
        쇼핑 에이전트 시스템의 실시간 상태를 모니터링합니다.
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mt: 3, mb: 3 }}>
          {error}
        </Alert>
      )}

      {systemStatus && (
        <>
          <Grid container spacing={3} sx={{ mt: 1 }}>
            <Grid size={{ xs: 12, md: 3 }}>
              <Card>
                <CardContent>
                  <Box display="flex" alignItems="center" gap={1}>
                    {getStatusIcon(systemStatus.status)}
                    <Typography variant="h6">시스템 상태</Typography>
                  </Box>
                  <Chip
                    label={systemStatus.status}
                    color={getStatusColor(systemStatus.status) as any}
                    sx={{ mt: 1 }}
                  />
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                    업타임: {formatUptime(systemStatus.uptime)}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    버전: {systemStatus.version}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>

            <Grid size={{ xs: 12, md: 3 }}>
              <Card>
                <CardContent>
                  <Box display="flex" alignItems="center" gap={1}>
                    <Speed color="primary" />
                    <Typography variant="h6">CPU 사용률</Typography>
                  </Box>
                  <Typography variant="h4" sx={{ mt: 1 }}>
                    {systemStatus.cpu_usage || 0}%
                  </Typography>
                  <LinearProgress
                    variant="determinate"
                    value={systemStatus.cpu_usage || 0}
                    sx={{ mt: 1 }}
                  />
                </CardContent>
              </Card>
            </Grid>

            <Grid size={{ xs: 12, md: 3 }}>
              <Card>
                <CardContent>
                  <Box display="flex" alignItems="center" gap={1}>
                    <Memory color="primary" />
                    <Typography variant="h6">메모리 사용률</Typography>
                  </Box>
                  <Typography variant="h4" sx={{ mt: 1 }}>
                    {systemStatus.memory_usage || 0}%
                  </Typography>
                  <LinearProgress
                    variant="determinate"
                    value={systemStatus.memory_usage || 0}
                    sx={{ mt: 1 }}
                  />
                </CardContent>
              </Card>
            </Grid>

            <Grid size={{ xs: 12, md: 3 }}>
              <Card>
                <CardContent>
                  <Box display="flex" alignItems="center" gap={1}>
                    <Storage color="primary" />
                    <Typography variant="h6">디스크 사용률</Typography>
                  </Box>
                  <Typography variant="h4" sx={{ mt: 1 }}>
                    {systemStatus.disk_usage || 0}%
                  </Typography>
                  <LinearProgress
                    variant="determinate"
                    value={systemStatus.disk_usage || 0}
                    sx={{ mt: 1 }}
                  />
                </CardContent>
              </Card>
            </Grid>
          </Grid>

          <Paper elevation={3} sx={{ p: 3, mt: 3 }}>
            <Typography variant="h6" gutterBottom>
              요청 통계
            </Typography>
            <Grid container spacing={2}>
              <Grid size={{ xs: 12, sm: 4 }}>
                <Box textAlign="center">
                  <Typography variant="h4" color="primary">
                    {systemStatus.active_requests || 0}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    활성 요청
                  </Typography>
                </Box>
              </Grid>
              <Grid size={{ xs: 12, sm: 4 }}>
                <Box textAlign="center">
                  <Typography variant="h4" color="success.main">
                    {systemStatus.total_requests || 0}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    총 요청 수
                  </Typography>
                </Box>
              </Grid>
              <Grid size={{ xs: 12, sm: 4 }}>
                <Box textAlign="center">
                  <Typography variant="h4" color="info.main">
                    {((systemStatus.total_requests || 0) - (systemStatus.active_requests || 0))}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    완료된 요청
                  </Typography>
                </Box>
              </Grid>
            </Grid>
          </Paper>

          <Paper elevation={3} sx={{ p: 3, mt: 3 }}>
            <Typography variant="h6" gutterBottom>
              시스템 로그
            </Typography>
            {logs.length === 0 ? (
              <Typography variant="body2" color="text.secondary">
                로그가 없습니다.
              </Typography>
            ) : (
              <List>
                {logs.map((log, index) => (
                  <React.Fragment key={index}>
                    <ListItem>
                      <ListItemText
                        primary={log.message}
                        secondary={
                          <Box display="flex" alignItems="center" gap={1}>
                            <Chip
                              label={log.level}
                              size="small"
                              color={
                                log.level === 'ERROR' ? 'error' :
                                log.level === 'WARNING' ? 'warning' : 'default'
                              }
                            />
                            <Typography variant="caption">
                              {new Date(log.timestamp).toLocaleString('ko-KR')}
                            </Typography>
                          </Box>
                        }
                      />
                    </ListItem>
                    {index < logs.length - 1 && <Divider />}
                  </React.Fragment>
                ))}
              </List>
            )}
          </Paper>
        </>
      )}
    </Box>
  );
};

export default MonitoringPage;