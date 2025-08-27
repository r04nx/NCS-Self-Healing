#!/bin/bash

echo "🎯 NCS REAL-TIME MONITOR - Press Ctrl+C to stop"
echo "=================================================="

while true; do
    clear
    echo "🚀 NCS Self-Healing System - Real-Time Status"
    echo "Time: $(date)"
    echo "=================================================="
    
    echo "📊 Controller Status:"
    curl -s http://localhost:5001/status | jq -r '
        "  Active: " + (.active | tostring) +
        "\n  Control Type: " + .control_type +
        "\n  Control Cost: " + (.kpis.control_cost | tostring) +
        "\n  Stability: " + (.kpis.overshoot | tostring) + " overshoot" +
        "\n  Settling Time: " + (.kpis.settling_time | tostring) + "s"
    '
    
    echo ""
    echo "🤖 Agent System Status:"
    curl -s http://localhost:5002/status | jq -r '
        "  Active Agents: " + (.active_agents | join(", ")) +
        "\n  Recoveries: " + (.num_recoveries | tostring) +  
        "\n  MTTR: " + (.mttr | tostring) + "s" +
        "\n  Stability Margin: " + (.control_kpis.stability_margin | tostring) +
        "\n  Recovery Active: " + (.recovery_active | tostring) +
        "\n  Network Latency P95: " + (.network_kpis.latency_p95 | tostring) + "ms"
    '
    
    echo ""
    echo "🌐 Access Points:"
    echo "  Grafana Dashboard: http://localhost:3000 (admin/ncs-research-2024)"
    echo "  Controller API: http://localhost:5001"  
    echo "  Agent API: http://localhost:5002"
    
    sleep 5
done
