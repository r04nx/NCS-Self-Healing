FROM python:3.11-slim

RUN pip install flask numpy requests

WORKDIR /app
COPY . .

EXPOSE 5001

CMD ["python", "simple_controller.py"]
