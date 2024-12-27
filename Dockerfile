# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /usr/src/app

# Copy the current directory contents into the container
COPY . .

# Install any necessary dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port 8080 for Flask (or any other services you need to access)
EXPOSE 8080

# Define environment variable
ENV API_TOKEN="your_telegram_bot_api_token"

# Run the bot when the container launches
CMD ["python", "./main.py"]
