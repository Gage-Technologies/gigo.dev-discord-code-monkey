# Use the official Python image as the base image
FROM python:3.10

# Set the working directory in the container
WORKDIR /app

# Copy the requirements.txt file to the container
COPY requirements.txt ./

# Install the Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the bot.py file to the container
COPY . ./

# Set the command to run the bot.py file
ENTRYPOINT ["python", "bot.py"]