#!/bin/bash
set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}           DSPy Forge - Start Script            ${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}Warning: .env file not found. Please create one based on .env.example${NC}"
    echo ""
fi

# Step 1: Build Frontend
echo -e "${GREEN}[1/2] Building Frontend...${NC}"
cd ui

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}node_modules not found. Running npm install...${NC}"
    npm install
fi

# Build the React app
echo -e "${BLUE}Running npm build...${NC}"
npm run build

if [ $? -ne 0 ]; then
    echo -e "${RED}Frontend build failed!${NC}"
    exit 1
fi

echo -e "${GREEN}Frontend build completed successfully!${NC}"
echo ""

# Step 2: Start Backend (which serves the frontend)
cd ..
echo -e "${GREEN}[2/2] Starting Backend Server...${NC}"
echo -e "${BLUE}The backend will serve the frontend at http://localhost:8000${NC}"
echo ""

# Check if uv is available
if command -v uv &> /dev/null; then
    echo -e "${BLUE}Starting server with 'uv run dspy-forge'...${NC}"
    uv run dspy-forge
else
    echo -e "${YELLOW}uv not found."
    exit 1
fi
