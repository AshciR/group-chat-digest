# Use an official Python runtime as a parent image
FROM python:3.12-slim

ENV WORKDIR="/app"

# Tells Python to not write .pyc files which are the compiled bytecode files Python creates
ENV PYTHONDONTWRITEBYTECODE=1

# When Python is running in a container in Docker,
# you often want to see the output of your application (like logs) in real-time, which can help in debugging.
# By setting PYTHONUNBUFFERED to 1, Python won't buffer these outputs, meaning it prints them immediately.
ENV PYTHONUNBUFFERED=1

# This environment variable is used to specify additional directories where
# Python should look for modules and packages before using the standard modules.
ENV PYTHONPATH="/app/src:$PYTHONPATH"

# Set the working directory in the container
WORKDIR $WORKDIR

# Copy the requirements and src code
COPY requirements.lock ./
COPY src src

# Install uv. UV is a super fast package manager in the Python ecosystem.
# It also works with pip and pip tools.
RUN pip install uv
# UV will create a .venv directory for us. We need to add it to system path to gain access to the binaries
ENV PATH="$WORKDIR/.venv/bin:$PATH"
RUN uv venv && uv pip install --no-cache-dir -r requirements.lock

# Make HTTP and Redis ports available to the world outside this container
EXPOSE 80
EXPOSE 6379

# Run app.py when the container launches
CMD ["python", "src/main.py"]