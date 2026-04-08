FROM python:3.9-slim

# Create a non-root user (Standard for HF Spaces / OpenEnv)
RUN useradd -m -u 1000 appuser

# Switch to the non-root user
USER appuser
ENV PATH="/home/appuser/.local/bin:${PATH}"

WORKDIR /home/appuser/app

# Copy and install dependencies
COPY --chown=appuser:appuser requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY --chown=appuser:appuser . .

# Set standard environment variables
ENV FLASK_ENV=production
# HF Spaces and OpenEnv default port mapping
ENV FLASK_PORT=7860
EXPOSE 7860

# Run the application
CMD ["python", "app.py"]
