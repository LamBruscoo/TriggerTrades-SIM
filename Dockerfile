FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all project files
COPY *.py ./
COPY .env* ./

# Create runtime directory
RUN mkdir -p runtime

# Expose Streamlit port
EXPOSE 8501

# Run both demo and dashboard
CMD python run_demo.py & streamlit run dashboard.py --server.port=8501 --server.address=0.0.0.0
