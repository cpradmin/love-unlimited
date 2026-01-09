#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')
from hub.auth import get_auth_manager
from hub.config import get_config

config = get_config()
auth = get_auth_manager(config.auth_keys_file)

# Generate key for claude-code being
api_key = auth.generate_key('claude-code')
print(f'claude-code API key: {api_key}')
