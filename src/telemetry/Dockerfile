FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN pip install influxdb-client requests psutil paho-mqtt

# Copy telemetry scripts
COPY . .

# Wait for other services to be ready
RUN pip install wait-for-it

# Run the enhanced data collector
CMD ["python", "data_collector.py"]
