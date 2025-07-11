# Use an official Python runtime as a parent image
FROM python:3.13-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV UV_HOME /opt/uv
ENV PATH /opt/uv:$PATH

# Install uv
RUN apt-get update && apt-get install -y curl && \
    curl -LsSf https://astral.sh/uv/install.sh | sh && \
    apt-get remove -y curl && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy the project files
COPY pyproject.toml uv.lock* ./

# Install dependencies using uv
# This command installs the project defined in pyproject.toml and its dependencies
RUN uv pip install --system --no-cache .

# Copy the rest of the application's source code from the context
COPY . .

# Expose the port that the application listens on
EXPOSE 8080

# Define the command to run the application using uv
CMD ["uv", "run", "main.py"]
