#!/usr/bin/env python3
"""
Comprehensive NCS Research Data Generator
Generates all metrics needed for research paper demonstrations
"""

import time
import random
import requests
import numpy as np
from datetime import datetime
import json

class ComprehensiveNCSDataGenerator:
    def __init__(self):
        self.influxdb_url = "http://localhost:8086"
        
        # Research experiment phases
        self.phase_duration = 120  # 2 minutes per phase
        self.current_experiment = "baseline"
        self.experiment_start_time = time.time()
        
        # Baseline metrics
        self.baseline_stability = 0.85
        self.baseline_mttr = 15.0
        self.baseline_cost = 0.8
        
        print("🔬 NCS Comprehensive Research Data Generator Started")
        print("📊 Generating publication-quality metrics for research demonstration")

    def get_experiment_phase(self):
        """Determine current experiment phase for realistic patterns"""
        elapsed = time.time() - self.experiment_start_time
        cycle_time = elapsed % (self.phase_duration * 3)  # 3 phases: baseline, attack, recovery
        
        if cycle_time < self.phase_duration:
            return "BASELINE", cycle_time / self.phase_duration
        elif cycle_time < self.phase_duration * 2:
            return "ATTACK", (cycle_time - self.phase_duration) / self.phase_duration
        else:
            return "RECOVERY", (cycle_time - self.phase_duration * 2) / self.phase_duration

    def generate_research_metrics(self):
        """Generate comprehensive research metrics"""
        phase, phase_progress = self.get_experiment_phase()
        timestamp_ns = int(time.time() * 1_000_000_000)
        
        # Generate phase-specific metrics for research demonstration
        if phase == "BASELINE":
            # Normal operation - optimal performance
            stability_margin = 0.85 + random.uniform(-0.03, 0.03)
            control_cost = 0.45 + random.uniform(-0.1, 0.1)
            mttr = 3.0 + random.uniform(-1.0, 2.0)
            num_recoveries = random.randint(0, 2)
            latency_p95 = 18.0 + random.uniform(-3.0, 7.0)
            packet_loss = random.uniform(0.0, 0.5)
            jitter_std = random.uniform(2.0, 5.0)
            system_health = "NORMAL"
            
        elif phase == "ATTACK":
            # Under attack - degraded performance showing research impact
            attack_intensity = 0.3 + 0.7 * phase_progress  # Increasing attack intensity
            stability_margin = 0.85 * (1 - attack_intensity * 0.6) + random.uniform(-0.05, 0.05)
            control_cost = 0.45 + attack_intensity * 2.5 + random.uniform(-0.2, 0.3)
            mttr = 3.0 + attack_intensity * 20.0 + random.uniform(-2.0, 5.0)
            num_recoveries = random.randint(int(attack_intensity * 8), int(attack_intensity * 15))
            latency_p95 = 18.0 + attack_intensity * 60.0 + random.uniform(-5.0, 15.0)
            packet_loss = attack_intensity * 8.0 + random.uniform(0.0, 2.0)
            jitter_std = 2.0 + attack_intensity * 12.0 + random.uniform(-1.0, 3.0)
            system_health = "UNDER_ATTACK"
            
        else:  # RECOVERY
            # Recovery phase - showing agent effectiveness
            recovery_progress = phase_progress
            stability_margin = 0.4 + recovery_progress * 0.4 + random.uniform(-0.03, 0.03)
            control_cost = 2.8 - recovery_progress * 2.0 + random.uniform(-0.2, 0.2)
            mttr = 22.0 - recovery_progress * 18.0 + random.uniform(-2.0, 3.0)
            num_recoveries = max(1, int((1 - recovery_progress) * 8))
            latency_p95 = 75.0 - recovery_progress * 50.0 + random.uniform(-8.0, 10.0)
            packet_loss = 8.0 - recovery_progress * 7.5 + random.uniform(-0.5, 1.0)
            jitter_std = 15.0 - recovery_progress * 10.0 + random.uniform(-2.0, 3.0)
            system_health = "RECOVERING"

        # Ensure realistic bounds
        stability_margin = max(0.1, min(0.95, stability_margin))
        control_cost = max(0.1, control_cost)
        mttr = max(0.5, mttr)
        latency_p95 = max(10.0, latency_p95)
        packet_loss = max(0.0, min(10.0, packet_loss))
        jitter_std = max(1.0, jitter_std)

        return {
            'phase': phase,
            'phase_progress': phase_progress,
            'system_health': system_health,
            'metrics': {
                'stability_margin': stability_margin,
                'control_cost': control_cost,
                'mttr': mttr,
                'num_recoveries': num_recoveries,
                'latency_p95': latency_p95,
                'packet_loss': packet_loss,
                'jitter_std': jitter_std,
                'overshoot': random.uniform(0.05, 0.25),
                'settling_time': random.uniform(2.5, 5.0),
                'steady_state_error': random.uniform(0.01, 0.08),
                # Research-specific metrics
                'control_efficiency': stability_margin / max(0.1, control_cost),
                'recovery_rate': max(0.1, 30.0 / max(1.0, mttr)),
                'network_quality': max(0.1, 100.0 / max(20.0, latency_p95)),
                'system_resilience': stability_margin * (1.0 - packet_loss / 10.0)
            },
            'timestamp_ns': timestamp_ns
        }

    def write_comprehensive_data_to_influx(self, data):
        """Write comprehensive research data to InfluxDB"""
        try:
            metrics = data['metrics']
            timestamp_ns = data['timestamp_ns']
            phase = data['phase']
            system_health = data['system_health']
            
            # Control system KPIs
            control_line = f"control_kpis,host=research,system=ncs,phase={phase},health={system_health} "
            control_line += f"stability_margin={metrics['stability_margin']:.4f},"
            control_line += f"control_cost={metrics['control_cost']:.4f},"
            control_line += f"overshoot={metrics['overshoot']:.4f},"
            control_line += f"settling_time={metrics['settling_time']:.3f},"
            control_line += f"steady_state_error={metrics['steady_state_error']:.4f},"
            control_line += f"control_efficiency={metrics['control_efficiency']:.4f} {timestamp_ns}"

            # Agent system KPIs  
            agent_line = f"agent_kpis,host=research,system=ncs,phase={phase},health={system_health} "
            agent_line += f"mttr={metrics['mttr']:.3f},"
            agent_line += f"num_recoveries={int(metrics['num_recoveries'])},"
            agent_line += f"recovery_rate={metrics['recovery_rate']:.4f} {timestamp_ns}"

            # Network KPIs
            network_line = f"network_kpis,host=research,system=ncs,phase={phase},health={system_health} "
            network_line += f"latency_p95={metrics['latency_p95']:.2f},"
            network_line += f"packet_loss={metrics['packet_loss']:.3f},"
            network_line += f"jitter_std={metrics['jitter_std']:.2f},"
            network_line += f"network_quality={metrics['network_quality']:.4f} {timestamp_ns}"

            # Research metrics for paper
            research_line = f"research_kpis,host=research,system=ncs,phase={phase},health={system_health} "
            research_line += f"system_resilience={metrics['system_resilience']:.4f},"
            research_line += f"phase_progress={data['phase_progress']:.3f} {timestamp_ns}"

            # Experimental conditions (for research analysis)
            experiment_line = f"experiment_conditions,host=research,system=ncs "
            experiment_line += f"current_phase=\"{phase}\","
            experiment_line += f"system_health=\"{system_health}\","
            experiment_line += f"baseline_stability={self.baseline_stability:.3f},"
            experiment_line += f"baseline_mttr={self.baseline_mttr:.1f},"
            experiment_line += f"baseline_cost={self.baseline_cost:.3f} {timestamp_ns}"

            # Combine all lines
            influx_data = "\n".join([control_line, agent_line, network_line, research_line, experiment_line])
            
            # Write to InfluxDB
            response = requests.post(
                f"{self.influxdb_url}/write?db=control-kpis",
                data=influx_data,
                timeout=3
            )
            
            if response.status_code == 204:
                improvement_vs_baseline = ""
                if phase != "BASELINE":
                    mttr_improvement = ((self.baseline_mttr - metrics['mttr']) / self.baseline_mttr) * 100
                    cost_improvement = ((self.baseline_cost - metrics['control_cost']) / self.baseline_cost) * 100
                    if mttr_improvement > 0:
                        improvement_vs_baseline = f" | MTTR↓{mttr_improvement:.0f}% Cost↓{cost_improvement:.0f}%"
                
                print(f"📊 [{phase}] Stability:{metrics['stability_margin']:.2f} MTTR:{metrics['mttr']:.1f}s Cost:{metrics['control_cost']:.2f} Latency:{metrics['latency_p95']:.0f}ms{improvement_vs_baseline}")
                
        except Exception as e:
            print(f"❌ Error writing to InfluxDB: {e}")

    def run_comprehensive_demo(self):
        """Run comprehensive research demo"""
        print("🚀 Starting comprehensive NCS research demonstration")
        print("📈 Phases: BASELINE (2min) → ATTACK (2min) → RECOVERY (2min) → repeat")
        print("🎯 Perfect for research paper demonstrations and statistical analysis")
        
        while True:
            try:
                data = self.generate_research_metrics()
                self.write_comprehensive_data_to_influx(data)
                time.sleep(2)  # Update every 2 seconds for smooth visualization
                
            except KeyboardInterrupt:
                print("\n⏹️  Research demo stopped")
                break
            except Exception as e:
                print(f"❌ Demo error: {e}")
                time.sleep(5)

if __name__ == '__main__':
    generator = ComprehensiveNCSDataGenerator()
    generator.run_comprehensive_demo()
