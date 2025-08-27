FROM python:3.11-slim

RUN pip install numpy scipy paho-mqtt influxdb-client

WORKDIR /app
COPY . .
COPY ../wait-for-mqtt.py ./wait-for-mqtt.py

CMD ["sh", "-c", "python wait-for-mqtt.py mqtt-broker 1883 && python plant_simulator.py"]
