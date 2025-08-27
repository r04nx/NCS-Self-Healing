FROM python:3.11-slim

RUN pip install numpy flask requests

WORKDIR /app
COPY . .

EXPOSE 5002

CMD ["python", "simple_agent.py"]
