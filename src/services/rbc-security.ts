/**
 * RBC Security Integration
 *
 * This module calls the Python rbc_security package to configure SSL/TLS
 * certificates for corporate network environments.
 *
 * It executes setup_rbc_security.py which calls rbc_security.enable_certs()
 * and returns environment variables that Node.js will use.
 */

import { execSync } from 'child_process';
import * as fs from 'fs';
import * as path from 'path';
import { logServerEvent } from '../logger';

/**
 * SSL Certificate configuration
 */
export interface SSLConfig {
  /** Path to CA certificate bundle (PEM format) */
  caCertPath?: string;
  /** Path to client certificate (PEM format) */
  clientCertPath?: string;
  /** Path to client key (PEM format) */
  clientKeyPath?: string;
  /** Whether to reject unauthorized certificates (default: false for dev) */
  rejectUnauthorized?: boolean;
}

/**
 * Load SSL configuration from environment variables
 */
export function loadSSLConfig(): SSLConfig {
  return {
    caCertPath: process.env.SSL_CA_CERT_PATH,
    clientCertPath: process.env.SSL_CLIENT_CERT_PATH,
    clientKeyPath: process.env.SSL_CLIENT_KEY_PATH,
    rejectUnauthorized: process.env.NODE_TLS_REJECT_UNAUTHORIZED !== '0',
  };
}

/**
 * Enable SSL certificates using Python rbc_security package
 *
 * Calls setup_rbc_security.py which executes rbc_security.enable_certs()
 * and returns environment variables for Node.js to use.
 *
 * @returns true if rbc_security was configured, false otherwise
 */
export function enableCerts(): boolean {
  try {
    logServerEvent('info', 'Attempting to configure RBC Security certificates...');

    // Find the Python script
    const scriptPath = path.join(process.cwd(), 'setup_rbc_security.py');

    if (!fs.existsSync(scriptPath)) {
      logServerEvent('warn', 'setup_rbc_security.py not found, skipping RBC Security setup');
      return setupFallbackSSL();
    }

    // Execute the Python script
    try {
      const output = execSync(`python3 ${scriptPath}`, {
        encoding: 'utf8',
        timeout: 10000, // 10 second timeout
      });

      const result = JSON.parse(output.trim());

      if (result.success) {
        // Apply environment variables from rbc_security
        if (result.env_vars) {
          Object.entries(result.env_vars).forEach(([key, value]) => {
            if (value && typeof value === 'string') {
              process.env[key] = value;
              logServerEvent('info', `Set ${key} from rbc_security`);
            }
          });
        }

        logServerEvent('info', result.message || 'RBC Security configured successfully');
        return true;
      } else {
        // rbc_security not available or failed
        if (result.error === 'rbc_security_not_found') {
          logServerEvent('info', 'rbc_security not available (OK for local development)');
          return setupFallbackSSL();
        } else {
          logServerEvent('warn', result.message || 'RBC Security setup failed');
          return setupFallbackSSL();
        }
      }
    } catch (execError) {
      logServerEvent('warn', 'Failed to execute rbc_security setup', {
        error: execError instanceof Error ? execError.message : String(execError),
      });
      return setupFallbackSSL();
    }
  } catch (error) {
    logServerEvent('error', 'Error in RBC Security setup', {
      error: error instanceof Error ? error.message : String(error),
    });
    return setupFallbackSSL();
  }
}

/**
 * Fallback SSL configuration using environment variables
 * Used when rbc_security is not available
 */
function setupFallbackSSL(): boolean {
  const sslConfig = loadSSLConfig();

  // Check if any SSL config is provided via env vars
  if (!sslConfig.caCertPath && !sslConfig.clientCertPath) {
    logServerEvent('info', 'No SSL certificates configured (using system defaults)');
    return false;
  }

  logServerEvent('info', 'Using fallback SSL configuration from environment variables');

  // Configure CA certificates
  if (sslConfig.caCertPath) {
    if (!fs.existsSync(sslConfig.caCertPath)) {
      logServerEvent('warn', `CA certificate not found: ${sslConfig.caCertPath}`);
    } else {
      process.env.NODE_EXTRA_CA_CERTS = sslConfig.caCertPath;
      logServerEvent('info', `Using CA certificate: ${sslConfig.caCertPath}`);
    }
  }

  // Configure client certificates
  if (sslConfig.clientCertPath && sslConfig.clientKeyPath) {
    if (!fs.existsSync(sslConfig.clientCertPath)) {
      logServerEvent('warn', `Client certificate not found: ${sslConfig.clientCertPath}`);
    } else if (!fs.existsSync(sslConfig.clientKeyPath)) {
      logServerEvent('warn', `Client key not found: ${sslConfig.clientKeyPath}`);
    } else {
      logServerEvent('info', `Using client certificate: ${sslConfig.clientCertPath}`);
    }
  }

  // Configure TLS rejection behavior
  if (sslConfig.rejectUnauthorized === false) {
    process.env.NODE_TLS_REJECT_UNAUTHORIZED = '0';
    logServerEvent('warn', 'SSL certificate verification DISABLED - use only in development!');
  }

  return true;
}

/**
 * Get SSL options for fetch/https requests
 *
 * Returns an object with SSL options that can be passed to fetch or https.request
 * This is needed for client certificates which can't be set globally.
 *
 * @param config - SSL configuration (uses env vars if not provided)
 * @returns Options object for fetch/https
 */
export function getSSLOptions(config?: SSLConfig): {
  ca?: string;
  cert?: string;
  key?: string;
  rejectUnauthorized?: boolean;
} {
  const sslConfig = config || loadSSLConfig();
  const options: ReturnType<typeof getSSLOptions> = {};

  try {
    if (sslConfig.caCertPath && fs.existsSync(sslConfig.caCertPath)) {
      options.ca = fs.readFileSync(sslConfig.caCertPath, 'utf8');
    }

    if (sslConfig.clientCertPath && fs.existsSync(sslConfig.clientCertPath)) {
      options.cert = fs.readFileSync(sslConfig.clientCertPath, 'utf8');
    }

    if (sslConfig.clientKeyPath && fs.existsSync(sslConfig.clientKeyPath)) {
      options.key = fs.readFileSync(sslConfig.clientKeyPath, 'utf8');
    }

    if (sslConfig.rejectUnauthorized !== undefined) {
      options.rejectUnauthorized = sslConfig.rejectUnauthorized;
    }
  } catch (error) {
    logServerEvent('error', 'Failed to read SSL certificate files', {
      error: error instanceof Error ? error.message : String(error),
    });
  }

  return options;
}

/**
 * Check if SSL certificates are configured
 */
export function isSSLConfigured(): boolean {
  const config = loadSSLConfig();
  return !!(config.caCertPath || config.clientCertPath);
}

/**
 * Get SSL configuration info for logging/display
 */
export function getSSLInfo(): {
  configured: boolean;
  caCertConfigured: boolean;
  clientCertConfigured: boolean;
  rejectUnauthorized: boolean;
} {
  const config = loadSSLConfig();
  return {
    configured: isSSLConfigured(),
    caCertConfigured: !!config.caCertPath,
    clientCertConfigured: !!(config.clientCertPath && config.clientKeyPath),
    rejectUnauthorized: config.rejectUnauthorized ?? true,
  };
}

/**
 * Mock mode for local testing without SSL
 * Sets environment to accept self-signed certificates
 */
export function enableMockMode(): void {
  process.env.NODE_TLS_REJECT_UNAUTHORIZED = '0';
  logServerEvent('warn', 'Mock mode enabled - SSL verification disabled (development only!)');
}
