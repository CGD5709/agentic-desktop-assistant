Write-Host "Starting Agentic Assistant infrastructure..." -ForegroundColor Cyan

# 1. Start RabbitMQ (assumes Docker Desktop is running)
Write-Host "Starting RabbitMQ in Docker..." -ForegroundColor Yellow
docker-compose up -d

# 2. Check that Ollama responds
Write-Host "Verifying connection with Ollama..." -ForegroundColor Yellow
$ollama_status = ollama list 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] Ollama is active and ready." -ForegroundColor Green
} else {
    Write-Host "[WARNING] Ollama is not responding. Ensure the app is open." -ForegroundColor Red
}

# 3. Provide instructions for Backend and Frontend
Write-Host "`nAll set. To run the full system:" -ForegroundColor Cyan
Write-Host "1. In one terminal (Python Reasoning Engine):" -ForegroundColor Yellow
Write-Host "   cd reasoning-engine"
Write-Host "   .\.venv\Scripts\Activate.ps1"
Write-Host "   python main.py"
Write-Host "`n2. In a second terminal (Java Execution Service):" -ForegroundColor Yellow
Write-Host "   cd execution-service"
Write-Host "   ./mvnw spring-boot:run"
Write-Host "`n3. In a third terminal (React Desktop Client):" -ForegroundColor Yellow
Write-Host "   cd desktop-client"
Write-Host "   npm run dev"