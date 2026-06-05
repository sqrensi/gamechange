# Offline C++ Solver MVP

Минимальная тестовая версия: Python-скрипт читает условие задачи из файла и создает файл с C++ решением.
Само решение задачи генерируется на простом C++20 с минимальным количеством стандартных библиотек.
В решениях используется `using namespace std;`.

## Что нужно установить

1. Установи Ollama: https://ollama.com
2. Скачай локальную модель:

```powershell
ollama pull qwen2.5-coder:7b
```

Если компьютер слабый, можно попробовать модель меньше:

```powershell
ollama pull qwen2.5-coder:3b
```

Для считывания условия через камеру также нужны Python-зависимости и локальный Tesseract OCR:

```powershell
python -m pip install -r requirements.txt
```

Tesseract можно установить через winget:

```powershell
winget install UB-Mannheim.TesseractOCR
```

Если Python не найдет Tesseract автоматически, укажи путь:

```powershell
$env:TESSERACT_CMD="C:\Program Files\Tesseract-OCR\tesseract.exe"
```

## Как пользоваться

1. Запиши условие задачи в файл:

```text
input/task.txt
```

2. Запусти:

```powershell
python solve_task.py
```

3. Готовый код появится тут:

```text
exam/1.txt
```

## Фоновый запуск по горячей клавише

Можно собрать маленький exe без окна. Он постоянно работает в фоне и слушает две горячие клавиши:

- `Ctrl + Alt + C` — 3 секунды считывает условие через камеру и записывает текст в `input/task.txt`.
- `Ctrl + Alt + S` — запускает генерацию решения из `input/task.txt` в `exam/1.txt`.

Сборка через MinGW g++ (статическая линковка, чтобы exe работал на других ноутбуках без `libstdc++-6.dll` и `libgcc_s_seh-1.dll`):

```powershell
g++ hotkey_runner.cpp -std=c++17 -mwindows -static -static-libgcc -static-libstdc++ -o hotkey_runner.exe
```

Запуск:

```powershell
.\hotkey_runner.exe
```

После запуска можно сначала нажать `Ctrl + Alt + C`, а потом `Ctrl + Alt + S`. Готовый код появится в:

```text
exam/1.txt
```

Логи сохраняются тут:

```text
output/hotkey_runner.log
output/capture_task.log
output/solve_task.log
output/captured_task.png
```

## Другая модель

Можно выбрать модель через аргумент:

```powershell
python solve_task.py --model qwen2.5-coder:3b
```

Или через переменную окружения:

```powershell
$env:OLLAMA_MODEL="qwen2.5-coder:3b"
python solve_task.py
```
