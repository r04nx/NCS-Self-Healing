FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN pip install flask numpy requests

# Copy enhanced agent
COPY enhanced_agent.py .

# Run the enhanced agent
CMD ["python", "enhanced_agent.py"]
