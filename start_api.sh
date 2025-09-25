#!/bin/bash

# Start the Step-Up Pricing API
echo "🚀 Starting Step-Up Pricing API..."
echo "📡 API will be available at: http://localhost:8000"
echo "📋 Step-up pricing endpoint: http://localhost:8000/api/stepup-pricing"
echo "🏥 Health check: http://localhost:8000/api/stepup-pricing/health"
echo ""
echo "Press Ctrl+C to stop the API server"
echo ""

# Install dependencies if needed
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install API dependencies
echo "Installing API dependencies..."
pip install -r api_requirements.txt

# Start the API server
python stepup_pricing_api.py

