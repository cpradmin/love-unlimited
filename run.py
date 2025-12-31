#!/usr/bin/env python3
"""
Love-Unlimited Hub Runner
Simple standalone runner that bypasses import issues.
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Now import and run
import uvicorn
from hub import main
import yaml

# Load config for port
config_path = "config.yaml"
with open(config_path) as f:
    config = yaml.safe_load(f)

port = config.get("hub", {}).get("port", 9002)

if __name__ == "__main__":
    uvicorn.run(
        main.app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
