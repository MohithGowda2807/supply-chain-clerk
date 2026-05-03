@echo off
echo ========================================================
echo Supply Chain Clerk - Starting Infrastructure
echo ========================================================

echo 1. Starting Docker containers (Neo4j, MQTT)...
cd /d "%~dp0"
docker compose up -d neo4j mosquitto

echo.
echo 2. Starting Backend Service...
start cmd /k "cd /d %~dp0\backend && .\venv\Scripts\activate && uvicorn app.main:app --reload"

echo.
echo 3. Starting Frontend App...
start cmd /k "cd /d %~dp0\frontend && npm run dev"

echo.
echo ========================================================
echo Dashboard will be available at: http://localhost:5173
echo API Docs will be available at:  http://localhost:8000/docs
echo Neo4j Browser available at:     http://localhost:7474
echo ========================================================
pause
