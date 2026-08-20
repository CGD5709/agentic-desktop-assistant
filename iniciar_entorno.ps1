Write-Host "Iniciando infraestructura del Asistente Agéntico..." -ForegroundColor Cyan

# 1. Levantar RabbitMQ (asume que tienes Docker Desktop abierto)
Write-Host "Levantando RabbitMQ en Docker..." -ForegroundColor Yellow
docker-compose up -d

# 2. Comprobar que Ollama responde
Write-Host "Verificando conexión con Ollama..." -ForegroundColor Yellow
$ollama_status = ollama list 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Ollama está activo y listo." -ForegroundColor Green
} else {
    Write-Host "⚠️ Ollama no responde. Asegúrate de tener la app abierta." -ForegroundColor Red
}

# 3. Dar instrucciones para el Backend y el Frontend
Write-Host "`nTodo listo. Para ejecutar el sistema completo:" -ForegroundColor Cyan
Write-Host "1. En una terminal (Backend WebSockets):" -ForegroundColor Yellow
Write-Host "   cd reasoning-engine"
Write-Host "   .\.venv\Scripts\Activate.ps1"
Write-Host "   python server.py"
Write-Host "`n2. En otra terminal (Frontend Desktop Client):" -ForegroundColor Yellow
Write-Host "   cd desktop-client"
Write-Host "   npm run dev"