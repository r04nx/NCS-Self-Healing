FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    iperf3 \
    iproute2 \
    tcpdump \
    net-tools \
    && rm -rf /var/lib/apt/lists/*

RUN pip install paho-mqtt requests numpy

WORKDIR /app
COPY . .

CMD ["python", "adversary_service.py"]
