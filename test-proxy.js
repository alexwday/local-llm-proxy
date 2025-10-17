#!/usr/bin/env node

/**
 * Test script for Local LLM Proxy
 * Validates that the proxy is working correctly
 */

const https = require('https');
const http = require('http');

// Configuration
const PROXY_URL = process.env.PROXY_URL || 'http://localhost:3000';
const PROXY_TOKEN = process.env.PROXY_ACCESS_TOKEN || '';

if (!PROXY_TOKEN) {
  console.error('❌ Error: PROXY_ACCESS_TOKEN environment variable is required');
  console.error('   Usage: PROXY_ACCESS_TOKEN=your-token node test-proxy.js');
  process.exit(1);
}

// Test utilities
let testsPassed = 0;
let testsFailed = 0;

function log(emoji, message) {
  console.log(`${emoji} ${message}`);
}

function logSuccess(message) {
  testsPassed++;
  log('✅', message);
}

function logError(message) {
  testsFailed++;
  log('❌', message);
}

function logInfo(message) {
  log('ℹ️ ', message);
}

function makeRequest(path, options = {}) {
  return new Promise((resolve, reject) => {
    const url = new URL(path, PROXY_URL);
    const protocol = url.protocol === 'https:' ? https : http;

    const requestOptions = {
      method: options.method || 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${PROXY_TOKEN}`,
        ...options.headers,
      },
    };

    const req = protocol.request(url, requestOptions, (res) => {
      let data = '';

      res.on('data', (chunk) => {
        data += chunk;
      });

      res.on('end', () => {
        try {
          const parsed = JSON.parse(data);
          resolve({
            status: res.statusCode,
            headers: res.headers,
            data: parsed,
          });
        } catch (error) {
          resolve({
            status: res.statusCode,
            headers: res.headers,
            data: data,
            parseError: error.message,
          });
        }
      });
    });

    req.on('error', (error) => {
      reject(error);
    });

    if (options.body) {
      req.write(JSON.stringify(options.body));
    }

    req.end();
  });
}

// Test suite
async function runTests() {
  console.log('\n' + '='.repeat(80));
  console.log('🧪 Local LLM Proxy Test Suite');
  console.log('='.repeat(80));
  console.log(`\n🔗 Testing proxy at: ${PROXY_URL}`);
  console.log(`🔑 Using access token: ${PROXY_TOKEN.substring(0, 20)}...\n`);

  // Test 1: Health check
  try {
    logInfo('Test 1: Health check endpoint');
    const response = await makeRequest('/health');

    if (response.status === 200 && response.data.status === 'healthy') {
      logSuccess('Health check passed');
    } else {
      logError(`Health check failed: ${response.status}`);
    }
  } catch (error) {
    logError(`Health check error: ${error.message}`);
  }

  // Test 2: List models
  try {
    logInfo('Test 2: List models endpoint (/v1/models)');
    const response = await makeRequest('/v1/models');

    if (response.status === 200 && response.data.object === 'list' && Array.isArray(response.data.data)) {
      logSuccess(`Models list retrieved (${response.data.data.length} models)`);
    } else {
      logError(`Models list failed: ${response.status}`);
    }
  } catch (error) {
    logError(`Models list error: ${error.message}`);
  }

  // Test 3: Get specific model
  try {
    logInfo('Test 3: Get specific model (/v1/models/gpt-4)');
    const response = await makeRequest('/v1/models/gpt-4');

    if (response.status === 200 && response.data.id === 'gpt-4') {
      logSuccess('Specific model retrieved');
    } else {
      logError(`Get model failed: ${response.status}`);
    }
  } catch (error) {
    logError(`Get model error: ${error.message}`);
  }

  // Test 4: Chat completion (basic)
  try {
    logInfo('Test 4: Chat completion (basic)');
    const response = await makeRequest('/v1/chat/completions', {
      method: 'POST',
      body: {
        model: 'gpt-4',
        messages: [
          { role: 'user', content: 'Say "test successful" if you can read this.' }
        ],
      },
    });

    if (response.status === 200 && response.data.choices && response.data.choices.length > 0) {
      const message = response.data.choices[0].message;
      logSuccess(`Chat completion successful (response: ${message.content?.substring(0, 50)}...)`);
    } else if (response.status >= 500) {
      logError(`Chat completion failed with server error: ${response.status} - This may indicate target endpoint issues`);
      if (response.data.error) {
        logInfo(`   Error details: ${response.data.error.message}`);
      }
    } else {
      logError(`Chat completion failed: ${response.status}`);
    }
  } catch (error) {
    logError(`Chat completion error: ${error.message}`);
  }

  // Test 5: Chat completion with parameters
  try {
    logInfo('Test 5: Chat completion with parameters (temperature, max_tokens)');
    const response = await makeRequest('/v1/chat/completions', {
      method: 'POST',
      body: {
        model: 'gpt-4',
        messages: [
          { role: 'system', content: 'You are a helpful assistant.' },
          { role: 'user', content: 'What is 2+2?' }
        ],
        temperature: 0.7,
        max_tokens: 100,
        n: 1,
      },
    });

    if (response.status === 200 && response.data.choices) {
      logSuccess('Chat completion with parameters successful');
    } else if (response.status >= 500) {
      logError(`Chat completion with params failed with server error: ${response.status}`);
    } else {
      logError(`Chat completion with parameters failed: ${response.status}`);
    }
  } catch (error) {
    logError(`Chat completion with parameters error: ${error.message}`);
  }

  // Test 6: Text completion (legacy)
  try {
    logInfo('Test 6: Text completion (legacy endpoint)');
    const response = await makeRequest('/v1/completions', {
      method: 'POST',
      body: {
        model: 'gpt-3.5-turbo',
        prompt: 'Once upon a time',
        max_tokens: 50,
      },
    });

    if (response.status === 200 && response.data.choices) {
      logSuccess('Text completion successful');
    } else if (response.status >= 500) {
      logError(`Text completion failed with server error: ${response.status}`);
    } else {
      logError(`Text completion failed: ${response.status}`);
    }
  } catch (error) {
    logError(`Text completion error: ${error.message}`);
  }

  // Test 7: Authentication test (should fail without token)
  try {
    logInfo('Test 7: Authentication validation (should reject invalid token)');
    const url = new URL('/v1/models', PROXY_URL);
    const protocol = url.protocol === 'https:' ? https : http;

    const response = await new Promise((resolve, reject) => {
      const req = protocol.request(url, {
        method: 'GET',
        headers: {
          'Authorization': 'Bearer invalid-token-12345',
        },
      }, (res) => {
        let data = '';
        res.on('data', (chunk) => { data += chunk; });
        res.on('end', () => {
          try {
            resolve({ status: res.statusCode, data: JSON.parse(data) });
          } catch {
            resolve({ status: res.statusCode, data });
          }
        });
      });
      req.on('error', reject);
      req.end();
    });

    if (response.status === 401) {
      logSuccess('Authentication validation working correctly');
    } else {
      logError(`Authentication should reject invalid tokens (got ${response.status})`);
    }
  } catch (error) {
    logError(`Authentication test error: ${error.message}`);
  }

  // Test 8: Dashboard access
  try {
    logInfo('Test 8: Dashboard accessibility');
    const response = await makeRequest('/');

    if (response.status === 200) {
      logSuccess('Dashboard is accessible');
    } else {
      logError(`Dashboard not accessible: ${response.status}`);
    }
  } catch (error) {
    logError(`Dashboard access error: ${error.message}`);
  }

  // Test 9: Dashboard API - config
  try {
    logInfo('Test 9: Dashboard API - configuration endpoint');
    const response = await makeRequest('/api/config');

    if (response.status === 200 && response.data.localPort) {
      logSuccess('Dashboard API config endpoint working');
    } else {
      logError(`Dashboard API config failed: ${response.status}`);
    }
  } catch (error) {
    logError(`Dashboard API config error: ${error.message}`);
  }

  // Test 10: Dashboard API - logs
  try {
    logInfo('Test 10: Dashboard API - logs endpoint');
    const response = await makeRequest('/api/logs');

    if (response.status === 200 && response.data.apiCalls && response.data.serverEvents) {
      logSuccess('Dashboard API logs endpoint working');
    } else {
      logError(`Dashboard API logs failed: ${response.status}`);
    }
  } catch (error) {
    logError(`Dashboard API logs error: ${error.message}`);
  }

  // Summary
  console.log('\n' + '='.repeat(80));
  console.log('📊 Test Results Summary');
  console.log('='.repeat(80));
  console.log(`✅ Tests passed: ${testsPassed}`);
  console.log(`❌ Tests failed: ${testsFailed}`);
  console.log(`📈 Success rate: ${Math.round((testsPassed / (testsPassed + testsFailed)) * 100)}%`);

  if (testsFailed === 0) {
    console.log('\n🎉 All tests passed! The proxy is working correctly.');
  } else if (testsFailed <= 2 && testsPassed >= 8) {
    console.log('\n⚠️  Most tests passed. Some failures may be due to target endpoint configuration.');
    console.log('   Check the logs above for details.');
  } else {
    console.log('\n❌ Multiple tests failed. Please check the configuration and logs.');
  }

  console.log('\n' + '='.repeat(80) + '\n');

  process.exit(testsFailed > 0 ? 1 : 0);
}

// Run tests
runTests().catch((error) => {
  console.error('Fatal error running tests:', error);
  process.exit(1);
});
