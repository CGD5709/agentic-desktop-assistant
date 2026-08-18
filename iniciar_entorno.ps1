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

# 3. Dar instrucciones para Python
Write-Host "`nTodo listo. Para ejecutar el motor de razonamiento, usa estos comandos:" -ForegroundColor Cyan
Write-Host "1. cd reasoning-engine"
Write-Host "2. .\.venv\Scripts\Activate.ps1"
Write-Host "3. python main.py"