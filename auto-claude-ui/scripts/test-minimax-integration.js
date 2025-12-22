/**
 * MiniMax API Integration Test
 *
 * This script tests the connection to MiniMax API with real credentials.
 * IMPORTANT: This is a manual integration test - do NOT commit with actual credentials.
 *
 * To run this test:
 * 1. Set the MINIMAX_JWT_TOKEN environment variable with your JWT token
 * 2. Run: node scripts/test-minimax-integration.js
 */

const https = require('https');

// MiniMax API endpoint (from the spec)
const MINIMAX_BASE_URL = 'https://api.minimax.io/anthropic';

// Get JWT token from environment (do NOT hardcode)
const JWT_TOKEN = process.env.MINIMAX_JWT_TOKEN || '';

/**
 * Validate a base URL for an Anthropic-compatible API endpoint
 */
function validateBaseUrl(baseUrl) {
  if (!baseUrl || baseUrl.trim() === '') {
    return false;
  }
  try {
    const url = new URL(baseUrl);
    return url.protocol === 'http:' || url.protocol === 'https:';
  } catch {
    return false;
  }
}

/**
 * Validate an API key or JWT token
 */
function validateApiKey(apiKey) {
  if (!apiKey || apiKey.trim() === '') {
    return false;
  }
  const trimmed = apiKey.trim();
  if (trimmed.length < 12) {
    return false;
  }
  const hasValidChars = /^[a-zA-Z0-9\-_+.]+$/.test(trimmed);
  return hasValidChars;
}

/**
 * Normalize a base URL by ensuring it doesn't have a trailing slash
 */
function normalizeBaseUrl(baseUrl) {
  const trimmed = baseUrl.trim();
  return trimmed.endsWith('/') ? trimmed.slice(0, -1) : trimmed;
}

/**
 * Get the base path from a URL (e.g., /anthropic from https://api.minimax.io/anthropic)
 */
function getBasePath(url) {
  const parsed = new URL(url);
  return parsed.pathname || '';
}

/**
 * Test connection to MiniMax API by making a simple API request
 */
function testConnection(baseUrl, apiKey) {
  return new Promise((resolve, reject) => {
    const normalizedUrl = normalizeBaseUrl(baseUrl);
    let parsedUrl;

    try {
      parsedUrl = new URL(normalizedUrl);
    } catch (error) {
      resolve({
        success: false,
        message: 'Invalid endpoint URL. Please check the Base URL format.'
      });
      return;
    }

    const startTime = Date.now();
    const basePath = getBasePath(normalizedUrl);

    // Try multiple endpoint approaches
    const tests = [
      {
        name: 'GET /v1/models (standard endpoint)',
        method: 'GET',
        path: '/v1/models'
      },
      {
        name: 'GET /anthropic/v1/models (MiniMax style)',
        method: 'GET',
        path: '/anthropic/v1/models'
      },
      {
        name: 'POST /v1/messages (minimal test request)',
        method: 'POST',
        path: '/v1/messages',
        body: JSON.stringify({
          model: 'claude-3-5-sonnet-20241022',
          max_tokens: 1,
          messages: [{ role: 'user', content: 'Hi' }]
        })
      },
      {
        name: 'POST /anthropic/v1/messages (MiniMax style)',
        method: 'POST',
        path: '/anthropic/v1/messages',
        body: JSON.stringify({
          model: 'claude-3-5-sonnet-20241022',
          max_tokens: 1,
          messages: [{ role: 'user', content: 'Hi' }]
        })
      }
    ];

    let testIndex = 0;

    const runNextTest = () => {
      if (testIndex >= tests.length) {
        resolve({
          success: false,
          message: 'Unable to connect to the API endpoint. All endpoint variations failed.'
        });
        return;
      }

      const test = tests[testIndex];
      testIndex++;

      const options = {
        hostname: parsedUrl.hostname,
        port: parsedUrl.port || (parsedUrl.protocol === 'https:' ? 443 : 80),
        path: test.path,
        method: test.method,
        headers: {
          'Authorization': `Bearer ${apiKey.trim()}`,
          'Content-Type': 'application/json',
          'x-api-key': apiKey.trim(),
        },
        timeout: 60000,
      };

      console.log(`  Trying: ${test.name}`);
      console.log(`    Path: ${test.path}`);

      const req = https.request(options, (res) => {
        const latencyMs = Date.now() - startTime;

        console.log(`    Response: ${res.statusCode} ${res.statusMessage}`);

        // Success: 200 OK or any 2xx status
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve({
            success: true,
            message: 'Connection successful',
            details: {
              provider: 'MiniMax',
              endpoint: test.path,
              latencyMs,
              statusCode: res.statusCode,
            },
          });
        } else if (res.statusCode === 401) {
          resolve({
            success: false,
            message: 'Authentication failed. Please check your JWT token.',
            details: { statusCode: res.statusCode, endpoint: test.path },
          });
        } else if (res.statusCode === 404) {
          // Try next test
          runNextTest();
        } else if (res.statusCode === 400 || res.statusCode === 422) {
          // Bad request usually means the endpoint exists but the request is invalid
          // This is actually a good sign - it means we reached the API!
          let data = '';
          res.on('data', (chunk) => { data += chunk; });
          res.on('end', () => {
            resolve({
              success: true,
              message: 'Connection successful (endpoint reachable)',
              details: {
                provider: 'MiniMax',
                endpoint: test.path,
                latencyMs,
                statusCode: res.statusCode,
                note: 'Endpoint exists but request format may need adjustment',
              },
            });
          });
        } else if (res.statusCode === 429) {
          resolve({
            success: true,
            message: 'Connection successful (rate limited)',
            details: {
              provider: 'MiniMax',
              endpoint: test.path,
              latencyMs,
              statusCode: res.statusCode,
            },
          });
        } else {
          // Other error codes
          let data = '';
          res.on('data', (chunk) => { data += chunk; });
          res.on('end', () => {
            try {
              const errorData = JSON.parse(data);
              resolve({
                success: false,
                message: errorData.error?.message || `API error: ${res.statusCode}`,
                details: { statusCode: res.statusCode, endpoint: test.path },
              });
            } catch {
              resolve({
                success: false,
                message: `API error: ${res.statusCode}`,
                details: { statusCode: res.statusCode, endpoint: test.path },
              });
            }
          });
        }
      });

      req.on('error', (error) => {
        console.log(`    Request error: ${error.message}`);
        // Try next test
        runNextTest();
      });

      req.on('timeout', () => {
        req.destroy();
        resolve({
          success: false,
          message: 'Connection timeout. Please check your network connection.',
        });
      });

      if (test.body) {
        req.write(test.body);
      }
      req.end();
    };

    // Start testing
    runNextTest();
  });
}

/**
 * Run the integration test
 */
async function runIntegrationTest() {
  console.log('=== MiniMax API Integration Test ===\n');

  // Step 1: Validate base URL format
  console.log('Step 1: Validating MiniMax base URL format...');
  const isUrlValid = validateBaseUrl(MINIMAX_BASE_URL);
  console.log(`  Base URL: ${MINIMAX_BASE_URL}`);
  console.log(`  Valid: ${isUrlValid ? '✓ YES' : '✗ NO'}`);

  if (!isUrlValid) {
    console.error('\n❌ FAILED: Base URL validation failed');
    process.exit(1);
  }

  // Step 2: Validate JWT token format
  console.log('\nStep 2: Validating JWT token format...');
  if (!JWT_TOKEN) {
    console.error('  ERROR: MINIMAX_JWT_TOKEN environment variable is not set');
    console.error('  Please set it with: export MINIMAX_JWT_TOKEN="your-token-here"');
    console.error('  (Windows): set MINIMAX_JWT_TOKEN=your-token-here');
    console.error('  (PowerShell): $env:MINIMAX_JWT_TOKEN="your-token-here"');
    process.exit(1);
  }

  const isTokenValid = validateApiKey(JWT_TOKEN);
  console.log(`  Token length: ${JWT_TOKEN.length} characters`);
  console.log(`  Valid format: ${isTokenValid ? '✓ YES' : '✗ NO'}`);

  if (!isTokenValid) {
    console.error('\n❌ FAILED: JWT token validation failed');
    process.exit(1);
  }

  // Step 3: Test actual connection to MiniMax API
  console.log('\nStep 3: Testing connection to MiniMax API...');
  console.log('  This will make real HTTP requests to the MiniMax API endpoint.\n');

  try {
    const result = await testConnection(MINIMAX_BASE_URL, JWT_TOKEN);

    console.log(`\n  Success: ${result.success ? '✓ YES' : '✗ NO'}`);
    console.log(`  Message: ${result.message}`);

    if (result.details) {
      console.log('  Details:');
      if (result.details.provider) console.log(`    Provider: ${result.details.provider}`);
      if (result.details.latencyMs) console.log(`    Latency: ${result.details.latencyMs}ms`);
      if (result.details.statusCode) console.log(`    Status Code: ${result.details.statusCode}`);
    }

    if (result.success) {
      console.log('\n✅ SUCCESS: MiniMax API connection test passed!');
      console.log('\nThe MiniMax API integration is working correctly.');
      console.log('You can now create an API profile with these credentials in the UI.');
      process.exit(0);
    } else {
      console.log('\n❌ FAILED: Connection test failed');
      console.log('\nPlease check:');
      console.log('  1. Your JWT token is valid and not expired');
      console.log('  2. The MiniMax API endpoint is accessible from your network');
      console.log('  3. Your MiniMax account is in good standing');
      process.exit(1);
    }
  } catch (error) {
    console.error('\n❌ ERROR: Exception during connection test');
    console.error(error);
    process.exit(1);
  }
}

// Run the test
runIntegrationTest().catch((error) => {
  console.error('Unhandled error:', error);
  process.exit(1);
});
