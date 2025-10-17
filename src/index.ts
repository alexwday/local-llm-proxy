import express, { Request, Response, NextFunction } from 'express';
import cors from 'cors';
import path from 'path';
import { config, isOAuthConfigured } from './config';
import { logServerEvent } from './logger';
import { initializeOAuth, getOAuthManager } from './services/oauth-manager';
import { enableCerts, getSSLInfo } from './services/rbc-security';
import openaiRoutes from './routes/openai';
import dashboardRoutes from './routes/dashboard';

const app = express();

// Initialize SSL certificates (RBC Security equivalent)
try {
  logServerEvent('info', 'Configuring SSL certificates...');
  const sslConfigured = enableCerts();

  if (sslConfigured) {
    const sslInfo = getSSLInfo();
    logServerEvent('info', 'SSL certificates configured', sslInfo);
  } else {
    logServerEvent('info', 'No SSL certificates configured, using system defaults');
  }
} catch (error) {
  logServerEvent('warn', 'SSL configuration failed, continuing with system defaults', {
    error: error instanceof Error ? error.message : String(error),
  });
}

// Initialize OAuth if configured
if (isOAuthConfigured() && config.oauth) {
  logServerEvent('info', 'Initializing OAuth token manager...');
  initializeOAuth(config.oauth)
    .then(() => {
      logServerEvent('info', 'OAuth token manager initialized successfully');
      const tokenInfo = getOAuthManager()?.getTokenInfo();
      if (tokenInfo?.hasToken) {
        logServerEvent('info', `OAuth token acquired, expires at: ${tokenInfo.expiresAt}`);
      }
    })
    .catch((error) => {
      logServerEvent('error', 'Failed to initialize OAuth', {
        error: error instanceof Error ? error.message : String(error),
      });
      logServerEvent('warn', 'Continuing without OAuth - requests may fail if target requires authentication');
    });
}

// Middleware
app.use(cors());
app.use(express.json());

// Request logging middleware
app.use((req: Request, res: Response, next: NextFunction) => {
  const start = Date.now();

  res.on('finish', () => {
    const duration = Date.now() - start;
    if (!req.path.startsWith('/api/')) {
      // Don't log dashboard API calls to avoid clutter
      return;
    }
    logServerEvent('info', `${req.method} ${req.path} - ${res.statusCode} (${duration}ms)`);
  });

  next();
});

// Serve static dashboard
app.use(express.static(path.join(__dirname, 'public')));

// OpenAI-compatible API routes
app.use('/v1', openaiRoutes);

// Dashboard API routes
app.use('/api', dashboardRoutes);

// Root route
app.get('/', (req: Request, res: Response) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

// Health check
app.get('/health', (req: Request, res: Response) => {
  res.json({
    status: 'healthy',
    timestamp: new Date().toISOString(),
    config: {
      localPort: config.localPort,
      localBaseUrl: config.localBaseUrl,
    },
  });
});

// Error handler
app.use((err: Error, req: Request, res: Response, next: NextFunction) => {
  logServerEvent('error', `Error: ${err.message}`, { stack: err.stack });
  res.status(500).json({
    error: 'Internal server error',
    message: err.message,
  });
});

// Start server
const PORT = config.localPort;

app.listen(PORT, () => {
  logServerEvent('info', `🚀 Local LLM Proxy started`);
  logServerEvent('info', `📊 Dashboard: http://localhost:${PORT}`);
  logServerEvent('info', `🔌 API Base URL: http://localhost:${PORT}/v1`);
  logServerEvent('info', `🔑 Access Token: ${config.accessToken}`);
  logServerEvent('info', `📡 Target Endpoint: ${config.targetEndpoint}`);

  console.log('\n' + '='.repeat(80));
  console.log('🚀 Local LLM Proxy is running!');
  console.log('='.repeat(80));
  console.log(`\n📊 Dashboard:     http://localhost:${PORT}`);
  console.log(`🔌 API Base URL:  http://localhost:${PORT}/v1`);
  console.log(`🔑 Access Token:  ${config.accessToken}`);
  console.log(`\n💡 Use this configuration in your OpenAI-compatible tools:`);
  console.log(`   Base URL: http://localhost:${PORT}/v1`);
  console.log(`   API Key:  ${config.accessToken}`);
  console.log('\n' + '='.repeat(80) + '\n');
});

// Graceful shutdown
process.on('SIGINT', () => {
  logServerEvent('info', 'Shutting down gracefully...');
  const oauthManager = getOAuthManager();
  if (oauthManager) {
    oauthManager.destroy();
  }
  process.exit(0);
});

process.on('SIGTERM', () => {
  logServerEvent('info', 'Shutting down gracefully...');
  const oauthManager = getOAuthManager();
  if (oauthManager) {
    oauthManager.destroy();
  }
  process.exit(0);
});
