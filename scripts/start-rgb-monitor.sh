#!/bin/bash
set -e

# Start OpenRGB server in background
openrgb --server &
OPENRGB_PID=$!

# Wait for server to be ready
sleep 2

# Start the RGB monitor
cd /infra/experiments/rgb
uv run python main.py effect system

# Clean up on exit
trap "kill $OPENRGB_PID 2>/dev/null || true" EXIT
wait