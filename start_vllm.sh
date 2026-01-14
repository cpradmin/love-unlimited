#!/bin/bash

cd /home/kntrnjb/ai-dream-team/micro-ai-swarm/love-unlimited

# Kill any existing vLLM processes
pkill -9 -f "vllm" 2>/dev/null || true
sleep 2

# Clean Ray artifacts
rm -rf /tmp/ray 2>/dev/null || true
rm -f /tmp/vllm_ray_socket* 2>/dev/null || true

# Start vLLM
/home/kntrnjb/ai-dream-team/micro-ai-swarm/love-unlimited/.venv/bin/python -m vllm.entrypoints.openai.api_server \
  --model Qwen/Qwen2.5-Coder-7B \
  --host 0.0.0.0 \
  --port 8000 \
  --gpu-memory-utilization 0.5 \
  --trust-remote-code \
  >> vllm.log 2>&1 &

echo "vLLM started in background"
echo "Waiting 120 seconds for startup..."
sleep 120

# Test health
if curl -s http://localhost:8000/health > /dev/null; then
  echo "✅ vLLM is healthy and ready!"
else
  echo "⚠️  vLLM health check failed, but process may still be starting..."
  tail -20 vllm.log
fi
