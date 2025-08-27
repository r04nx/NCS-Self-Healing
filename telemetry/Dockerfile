FROM python:3.11-slim

RUN pip install paho-mqtt influxdb-client psutil

WORKDIR /app
COPY . .

CMD ["python", "network_monitor.py"]
