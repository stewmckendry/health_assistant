#!/bin/bash

# =============================================================================
# AI Health Assistant - Complete Startup Script
# =============================================================================
# This script starts all services needed to run the AI Health Assistant:
# - Python FastAPI backend with environment variables
# - Next.js frontend development server
# - Proper dependency management and error handling
# =============================================================================

set -e  # Exit on any error

echo "🩺 AI Health Assistant - Starting Application..."
echo "================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to handle shutdown
cleanup() {
    echo ""
    print_status "Shutting down servers..."
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null || true
        print_status "Backend server stopped"
    fi
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null || true
        print_status "Frontend server stopped"
    fi
    echo ""
    print_success "All servers stopped. Goodbye! 👋"
    exit 0
}

# Set up trap to catch Ctrl+C
trap cleanup INT TERM

# =============================================================================
# Pre-flight Checks
# =============================================================================

print_status "Running pre-flight checks..."

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    print_error "Please run this script from the project root directory"
    print_error "Expected files: pyproject.toml, .env, web/package.json"
    exit 1
fi

# Check for required files
if [ ! -f ".env" ]; then
    print_error ".env file not found. Please create one with your API keys."
    print_error "See .env.example for the required format."
    exit 1
fi

if [ ! -f "web/package.json" ]; then
    print_error "web/package.json not found. Frontend dependencies missing."
    exit 1
fi

# Check for virtual environment
if [ ! -d "/Users/liammckendry/spacy_env" ]; then
    print_warning "Virtual environment not found at /Users/liammckendry/spacy_env"
    print_warning "Using system Python instead"
    PYTHON_CMD="python"
else
    print_success "Virtual environment found"
    PYTHON_CMD="/Users/liammckendry/spacy_env/bin/python"
fi

# Check Python dependencies
print_status "Checking Python dependencies..."
if ! $PYTHON_CMD -c "import uvicorn, fastapi, anthropic" >/dev/null 2>&1; then
    print_error "Missing Python dependencies. Please install them:"
    print_error "pip install -r requirements.txt"
    exit 1
fi

# Check Node.js dependencies
print_status "Checking Node.js dependencies..."
if [ ! -d "web/node_modules" ]; then
    print_warning "Node.js dependencies not found. Installing..."
    cd web && npm install
    if [ $? -ne 0 ]; then
        print_error "Failed to install Node.js dependencies"
        exit 1
    fi
    cd ..
    print_success "Node.js dependencies installed"
fi

# Verify environment variables
print_status "Verifying environment variables..."
if ! grep -q "ANTHROPIC_API_KEY" .env || [ -z "$(grep ANTHROPIC_API_KEY .env | cut -d'=' -f2 | tr -d '\"')" ]; then
    print_error "ANTHROPIC_API_KEY not found or empty in .env file"
    print_error "Please add your Anthropic API key to .env"
    exit 1
fi

print_success "Pre-flight checks completed"

# =============================================================================
# Start Backend Server
# =============================================================================

print_status "Starting Python FastAPI backend server..."

# Load environment variables and start backend
export $(grep -v '^#' .env | xargs)

# Verify API key is loaded
if [ -z "$ANTHROPIC_API_KEY" ]; then
    print_error "Failed to load ANTHROPIC_API_KEY from .env"
    exit 1
fi

print_success "Environment variables loaded"
print_status "ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY:0:20}..."

# Start backend server
$PYTHON_CMD -m uvicorn src.web.api.main:app --reload --port 8000 &
BACKEND_PID=$!

# Wait for backend to start
print_status "Waiting for backend to initialize..."
for i in {1..10}; do
    if curl -s http://localhost:8000/health >/dev/null 2>&1; then
        print_success "Backend server started successfully"
        break
    fi
    if [ $i -eq 10 ]; then
        print_error "Backend server failed to start after 30 seconds"
        cleanup
        exit 1
    fi
    sleep 3
done

# =============================================================================
# Start Frontend Server
# =============================================================================

print_status "Starting Next.js frontend development server..."

cd web
npm run dev &
FRONTEND_PID=$!
cd ..

# Wait for frontend to start
print_status "Waiting for frontend to initialize..."
for i in {1..10}; do
    if curl -s http://localhost:3000 >/dev/null 2>&1; then
        print_success "Frontend server started successfully"
        break
    fi
    if [ $i -eq 10 ]; then
        print_error "Frontend server failed to start after 30 seconds"
        cleanup
        exit 1
    fi
    sleep 3
done

# =============================================================================
# Application Ready
# =============================================================================

echo ""
echo "🎉 AI Health Assistant is ready!"
echo "================================="
echo ""
print_success "Backend API:  http://localhost:8000"
print_success "Frontend App: http://localhost:3000"
print_success "API Docs:     http://localhost:8000/docs"
echo ""
print_status "Application Features:"
echo "  • Patient mode for general health education"
echo "  • Provider mode for healthcare professionals"
echo "  • Real-time streaming responses"
echo "  • Session management and feedback"
echo "  • Comprehensive safety guardrails"
echo ""
print_warning "This is a demo application for educational purposes only."
print_warning "Always consult healthcare professionals for medical advice."
echo ""
print_status "Press Ctrl+C to stop all servers"
echo ""

# Wait for processes to complete
wait $BACKEND_PID $FRONTEND_PID