#!/usr/bin/env python3
"""
RBC Security Setup Script

This script calls rbc_security.enable_certs() to configure SSL certificates
for the Node.js proxy. It's called from Node.js on startup.

The script sets environment variables that Node.js will inherit.
"""

import sys
import os
import json

def setup_rbc_security():
    """Call rbc_security.enable_certs() and return environment variables."""
    try:
        import rbc_security

        # Call enable_certs() to set up SSL environment
        rbc_security.enable_certs()

        # Get all environment variables that rbc_security set
        # These will be returned to Node.js
        env_vars = {
            'NODE_EXTRA_CA_CERTS': os.environ.get('REQUESTS_CA_BUNDLE', ''),
            'SSL_CERT_FILE': os.environ.get('SSL_CERT_FILE', ''),
            'REQUESTS_CA_BUNDLE': os.environ.get('REQUESTS_CA_BUNDLE', ''),
            'CURL_CA_BUNDLE': os.environ.get('CURL_CA_BUNDLE', ''),
        }

        # Filter out empty values
        env_vars = {k: v for k, v in env_vars.items() if v}

        # Return success with environment variables
        result = {
            'success': True,
            'env_vars': env_vars,
            'message': 'RBC Security certificates configured successfully'
        }

        print(json.dumps(result))
        sys.exit(0)

    except ImportError:
        # rbc_security not available (OK for local/personal development)
        result = {
            'success': False,
            'error': 'rbc_security_not_found',
            'message': 'rbc_security package not available (OK for local development)',
            'env_vars': {}
        }
        print(json.dumps(result))
        sys.exit(0)

    except Exception as e:
        # Other errors
        result = {
            'success': False,
            'error': 'setup_failed',
            'message': f'Failed to setup RBC security: {str(e)}',
            'env_vars': {}
        }
        print(json.dumps(result))
        sys.exit(1)

if __name__ == '__main__':
    setup_rbc_security()
