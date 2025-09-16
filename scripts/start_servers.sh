#!/bin/bash

# Start the Health Assistant Web Application servers

echo "🚀 Starting Health Assistant Web Application..."

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    echo "❌ Error: Please run this script from the project root directory"
    exit 1
fi

# Start Python FastAPI backend
echo "📦 Starting Python backend server..."
python -m uvicorn src.web.api.main:app --reload --port 8000 &
BACKEND_PID=$!

# Wait for backend to start
sleep 3

# Start Next.js frontend
echo "🌐 Starting Next.js frontend..."
cd web && npm run dev &
FRONTEND_PID=$!

echo "✅ Servers started!"
echo "   Backend: http://localhost:8000"
echo "   Frontend: http://localhost:3000"
echo ""
echo "Press Ctrl+C to stop all servers"

# Function to handle shutdown
cleanup() {
    echo "\n🛑 Shutting down servers..."
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    exit 0
}

# Set up trap to catch Ctrl+C
trap cleanup INT

# Wait for processes
wait