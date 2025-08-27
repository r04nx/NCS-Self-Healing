#!/bin/bash
set -e

echo "🚀 Building NCS Self-Healing System..."

# Build all Docker images
echo "📦 Building Docker images..."
docker-compose -f config/docker/docker-compose.yml -f ../config/docker/docker-compose -f config/docker/docker-compose.yml.yml build

# Create necessary directories
mkdir -p ../data/results ../data/logs ../src/telemetry/grafana/{dashboards,provisioning}
mkdir -p ../src/src/telemetry/mosquitto/config

# Create mosquitto config
cat > ../src/src/telemetry/mosquitto/config/mosquitto.conf << EOL
allow_anonymous true
listener 1883
listener 9001
protocol websockets
EOL

# Start the system
echo "🏁 Starting system..."
docker-compose -f config/docker/docker-compose.yml -f ../config/docker/docker-compose -f config/docker/docker-compose.yml.yml up -d

# Wait for services
echo "⏳ Waiting for services to be ready..."
sleep 30

# Check service health
echo "🏥 Checking service health..."
services=("controller:5001/status" "agents:5002/status" "grafana:3000")

for service in "${services[@]}"; do
    IFS=':' read -r name endpoint <<< "$service"
    if curl -f -s "http://localhost:${endpoint}" > /dev/null; then
        echo "✅ $name is healthy"
    else
        echo "❌ $name is not responding"
    fi
done

echo "🎯 Quick system test..."
# Test controller API
response=$(curl -s -X POST -H "Content-Type: application/json" \
    -d '{"Ts": 0.01}' http://localhost:5001/set_sampling_period)
echo "Controller response: $response"

# Test agent API
agent_status=$(curl -s http://localhost:5002/status)
echo "Agent status: $(echo $agent_status | jq -r '.active_agents // "N/A"')"

echo ""
echo "🎉 NCS Self-Healing System is ready!"
echo "📊 Grafana Dashboard: http://localhost:3000 (admin/ncs-research-2024)"
echo "🎛️  Controller API: http://localhost:5001/status"
echo "🤖 Agent API: http://localhost:5002/status"
echo ""
echo "To run experiments:"
echo "  cd config/ansible && ansible-playbook experiments.yml -e experiment_type=baseline"
echo "  cd config/ansible && ansible-playbook experiments.yml -e experiment_type=dos_attack"

