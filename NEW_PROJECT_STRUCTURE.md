# NCS Self-Healing System - Reorganized Project Structure

## 📁 Directory Structure

### `/src/` - Source Code
All source code is now organized under the `src/` directory with proper Python package structure:

- **`src/agents/`** - Multi-agent system components
  - `bandit/` - Contextual bandit agents
  - `marl/` - Multi-agent reinforcement learning
  - `reflex/` - Reflex-based agents
  - Core agent files: `agent_coordinator.py`, `enhanced_agent.py`, `simple_agent.py`

- **`src/controllers/`** - Control system implementations  
  - LQR/PID controllers with runtime reconfiguration
  - Files: `controller_service.py`, `enhanced_controller.py`, etc.

- **`src/chaos/`** - Chaos engineering and adversarial components
  - Network disruption, DoS attacks, fault injection
  - File: `adversary_service.py`

- **`src/plants/`** - Plant/system simulations
  - Inverted pendulum, unstable systems
  - File: `plant_simulator.py`

- **`src/telemetry/`** - Monitoring and data collection
  - MQTT, InfluxDB integration, Grafana dashboards
  - Files: `data_collector.py`, `network_monitor.py`, `simple_demo_data.py`
  - Subdirectories: `grafana/`, `mosquitto/`

- **`src/utils/`** - Utility scripts and helpers
  - Data generators, MQTT utilities
  - Files: `comprehensive_ncs_data.py`, `demo_data_generator.py`, `wait-for-mqtt.py`

### `/config/` - Configuration Files
All configuration files organized by type:

- **`config/docker/`** - Docker and container configurations
  - `docker-compose.yml` - Main orchestration file

- **`config/ansible/`** - Automation and experiment scripts
  - `experiments.yml` - Main experiment playbook
  - `tasks/` - Individual automation tasks

- **`config/dashboards/`** - Grafana dashboard configurations
  - Various `.json` dashboard files

### `/data/` - Data and Results
All data, results, and logs:

- **`data/results/`** - Experiment results and metrics
  - Timestamped directories for each experiment run
  - Contains: metrics CSV files, logs, final states

- **`data/logs/`** - Application logs
  - System-wide logs and experiment logs

- **`data/exports/`** - Research outputs and analysis
  - Research papers, analysis scripts, figures
  - Jupyter notebooks and generated reports

### `/scripts/` - Executable Scripts
Operational and utility scripts:

- `build_and_test.sh` - Main build and test script
- `real_time_monitor.sh` - System monitoring
- `run_dos_attack.py` - Attack simulation script

### `/docs/` - Documentation
Organized documentation:

- `api/` - API documentation
- `architecture/` - System architecture docs  
- `user-guide/` - User guides and manuals

### `/tests/` - Test Suite
Test organization:

- `unit/` - Unit tests
- `integration/` - Integration tests
- `e2e/` - End-to-end tests

## 🔧 Path Updates Made

### Docker Compose
- Updated all build contexts to reference `../../src/[component]/`
- Updated volume mounts to reference correct telemetry paths

### Scripts
- Updated `build_and_test.sh` to use new docker-compose location
- Updated directory creation paths
- Updated ansible references

### Python Code
- Added `__init__.py` files for proper Python package structure
- Updated any imports that referenced old directory structure
- Updated file path references in code

### Configuration Files
- Updated Ansible playbooks to reference new result/log locations
- Updated `.gitignore` to match new directory structure

## 🚀 Usage After Reorganization

### Running the System
```bash
# From project root
cd scripts
./build_and_test.sh
```

### Running Experiments  
```bash
# From project root
cd config/ansible
ansible-playbook experiments.yml -e experiment_type=baseline
```

### Accessing Services
- Grafana Dashboard: http://localhost:3000
- Controller API: http://localhost:5001/status  
- Agent API: http://localhost:5002/status

## ✅ Benefits of New Structure

1. **Clear Separation**: Source code, config, data, and docs are clearly separated
2. **Python Package Structure**: Proper `__init__.py` files for clean imports
3. **Scalable**: Easy to add new components in organized locations
4. **Professional**: Follows standard project layout conventions
5. **Maintainable**: Easier to find and modify specific components
6. **Docker-Friendly**: Clear build contexts for containerization

## 🔍 Quick Verification

To verify the reorganization worked:

1. Check Docker builds: `cd config/docker && docker-compose build`
2. Check Python imports: `python -c "import src.agents.simple_agent"`
3. Check scripts: `cd scripts && ./build_and_test.sh --dry-run`

The project is now properly organized and all path references have been updated!
