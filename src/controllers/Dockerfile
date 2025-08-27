FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN pip install flask numpy requests scipy control

# Copy enhanced controller
COPY enhanced_controller.py .

# Run the enhanced controller
CMD ["python", "enhanced_controller.py"]
