import { Router, Request, Response } from 'express';
import { getConfig } from '../config';
import { getApiCallLogs, getServerEventLogs, clearLogs } from '../logger';

const router = Router();

// GET /api/config - Get current configuration
router.get('/config', (req: Request, res: Response) => {
  const config = getConfig();
  res.json(config);
});

// GET /api/logs/api-calls - Get API call logs
router.get('/logs/api-calls', (req: Request, res: Response) => {
  const limit = parseInt(req.query.limit as string) || 100;
  const logs = getApiCallLogs(limit);
  res.json(logs);
});

// GET /api/logs/server-events - Get server event logs
router.get('/logs/server-events', (req: Request, res: Response) => {
  const limit = parseInt(req.query.limit as string) || 100;
  const logs = getServerEventLogs(limit);
  res.json(logs);
});

// DELETE /api/logs - Clear all logs
router.delete('/logs', (req: Request, res: Response) => {
  clearLogs();
  res.json({ success: true, message: 'All logs cleared' });
});

export default router;
