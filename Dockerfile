FROM python:3.10-slim

# start point
WORKDIR /app

# dependency list
COPY requirements.txt .

# install dependencies
RUN pip install --no-cache-dir -r requirements.txt

COPY . .