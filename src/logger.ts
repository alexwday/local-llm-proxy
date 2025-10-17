import { ApiCallLog, ServerEventLog } from './types';
import { v4 as uuidv4 } from 'uuid';

const apiCallLogs: ApiCallLog[] = [];
const serverEventLogs: ServerEventLog[] = [];
const MAX_LOGS = 1000;

export function logApiCall(log: Omit<ApiCallLog, 'id' | 'timestamp'>): void {
  const entry: ApiCallLog = {
    id: uuidv4(),
    timestamp: new Date().toISOString(),
    ...log,
  };

  apiCallLogs.unshift(entry);

  if (apiCallLogs.length > MAX_LOGS) {
    apiCallLogs.pop();
  }

  console.log(`[API] ${log.method} ${log.path} - ${log.responseStatus} (${log.duration}ms)`);
}

export function logServerEvent(
  level: 'info' | 'warn' | 'error',
  message: string,
  details?: any
): void {
  const entry: ServerEventLog = {
    id: uuidv4(),
    timestamp: new Date().toISOString(),
    level,
    message,
    details,
  };

  serverEventLogs.unshift(entry);

  if (serverEventLogs.length > MAX_LOGS) {
    serverEventLogs.pop();
  }

  const prefix = `[${level.toUpperCase()}]`;
  console.log(`${prefix} ${message}`, details ? JSON.stringify(details) : '');
}

export function getApiCallLogs(limit: number = 100): ApiCallLog[] {
  return apiCallLogs.slice(0, limit);
}

export function getServerEventLogs(limit: number = 100): ServerEventLog[] {
  return serverEventLogs.slice(0, limit);
}

export function clearLogs(): void {
  apiCallLogs.length = 0;
  serverEventLogs.length = 0;
}
