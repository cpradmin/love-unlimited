#!/bin/bash

# Generate keys
N8N_ENCRYPTION_KEY=$(openssl rand -base64 32)
N8N_BRIDGE_TOKEN=$(openssl rand -hex 32)

# Append to .env
echo "N8N_ENCRYPTION_KEY=$N8N_ENCRYPTION_KEY" >> .env
echo "N8N_BRIDGE_TOKEN=$N8N_BRIDGE_TOKEN" >> .env
echo "N8N_MCP_TOKEN=<your-existing-mcp-token>" >> .env
echo "GROK_API_TOKEN=<your-grok-key>" >> .env
echo "DISCORD_WEBHOOK_URL=<your-discord-webhook>" >> .env

# Create directories
mkdir -p n8n-data logs/bridge

# Create Dockerfile.bridge
cat > Dockerfile.bridge << 'EOF'
FROM python:3.9-slim
WORKDIR /app
COPY memory_bridge_v2_n8n.py .
RUN pip install flask requests
EXPOSE 5000
CMD ["python", "memory_bridge_v2_n8n.py"]
EOF

# Create memory_bridge_v2_n8n.py
cat > memory_bridge_v2_n8n.py << 'EOF'
from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/health')
def health():
    return jsonify({"status": "operational", "bridge_version": "2.0"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
EOF

echo "Phase 1 setup complete."