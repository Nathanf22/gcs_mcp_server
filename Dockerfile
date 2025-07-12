# Use an official Python runtime as a parent image
FROM python:3.13-slim

# Set environment variables for Python
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the PATH to include the default uv installation directory
ENV PATH="/root/.local/bin:${PATH}"

# Install system dependencies and uv
RUN apt-get update && \
    apt-get install -y curl && \
    curl -LsSf https://astral.sh/uv/install.sh | sh && \
    apt-get remove -y curl && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy dependency definition files
COPY pyproject.toml uv.lock* ./

# Install dependencies using uv
RUN uv pip install --system --no-cache .

# Copy the rest of the application source code
COPY . .

# Expose the port the app runs on
EXPOSE 8080

# Define the command to run the application
CMD ["uv", "run", "main.py"]
