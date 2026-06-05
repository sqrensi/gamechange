Write-Host "Проверяю Python 3.12..."

$python312 = $null
if (Get-Command py -ErrorAction SilentlyContinue) {
    $python312 = "py -3.12"
} elseif (Test-Path "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe") {
    $python312 = "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe"
}

if (-not $python312) {
    Write-Host "Python 3.12 не найден."
    Write-Host "Скачай Python 3.12 с https://www.python.org/downloads/release/python-3120/"
    Write-Host "При установке поставь галочку Add python.exe to PATH."
    exit 1
}

Write-Host "Базовые зависимости..."
Invoke-Expression "$python312 -m pip install -r requirements.txt"

Write-Host "PaddlePaddle CPU..."
Invoke-Expression "$python312 -m pip install paddlepaddle==3.3.0 -i https://www.paddlepaddle.org.cn/packages/stable/cpu/"

Write-Host "PaddleOCR..."
Invoke-Expression "$python312 -m pip install paddleocr"

Write-Host "Готово. Используй Python 3.12 для камеры и hotkey_runner."
