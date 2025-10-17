/**
 * RBC Security Integration
 *
 * This module replicates the functionality of the Python rbc_security package
 * for Node.js environments. It configures SSL/TLS certificates for corporate
 * network environments.
 *
 * In Python, rbc_security.enable_certs() sets environment variables for SSL.
 * In Node.js, we need to set NODE_EXTRA_CA_CERTS and potentially other variables.
 */

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
 * Enable SSL certificates for corporate environments
 *
 * This function replicates the behavior of rbc_security.enable_certs()
 * from the Python package. It sets up Node.js to use custom CA certificates.
 *
 * @param config - SSL configuration (uses env vars if not provided)
 * @returns true if SSL was configured, false otherwise
 */
export function enableCerts(config?: SSLConfig): boolean {
  try {
    const sslConfig = config || loadSSLConfig();

    // Check if any SSL config is provided
    if (!sslConfig.caCertPath && !sslConfig.clientCertPath) {
      logServerEvent('info', 'No SSL certificates configured (using system defaults)');
      return false;
    }

    logServerEvent('info', 'Configuring SSL certificates...');

    // Configure CA certificates
    if (sslConfig.caCertPath) {
      if (!fs.existsSync(sslConfig.caCertPath)) {
        logServerEvent('warn', `CA certificate not found: ${sslConfig.caCertPath}`);
      } else {
        // Set NODE_EXTRA_CA_CERTS for Node.js to trust additional CAs
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
        // Note: Client certs need to be passed to fetch/https options
        // They can't be set globally like CA certs
      }
    }

    // Configure TLS rejection behavior
    if (sslConfig.rejectUnauthorized === false) {
      process.env.NODE_TLS_REJECT_UNAUTHORIZED = '0';
      logServerEvent('warn', 'SSL certificate verification DISABLED - use only in development!');
    }

    logServerEvent('info', 'SSL certificates configured successfully');
    return true;

  } catch (error) {
    logServerEvent('error', 'Failed to configure SSL certificates', {
      error: error instanceof Error ? error.message : String(error),
    });
    return false;
  }
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
