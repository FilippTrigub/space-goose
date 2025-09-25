#!/bin/bash

echo "Starting K8s Environment Manager..."
echo "======================================"

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "⚠️  No virtual environment found. Creating one..."
    python -m venv .venv
    echo "✓ Virtual environment created"
fi

# Activate virtual environment
source .venv/bin/activate
echo "✓ Virtual environment activated"

# Install/upgrade dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
echo "✓ Dependencies installed"

# Check for .env file
if [ ! -f ".env" ]; then
    echo "ℹ️  No .env file found. You can create one based on .env.example"
fi

# Start the application
echo "\nStarting application..."
echo "======================================"
python main.py
