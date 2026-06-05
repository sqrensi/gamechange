import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_INPUT = BASE_DIR / "input" / "task.txt"
DEFAULT_OUTPUT = BASE_DIR / "exam" / "1.txt"
DEFAULT_MODEL = "qwen2.5-coder:7b"
OLLAMA_URL = "http://127.0.0.1:11434/api/generate"


def build_prompt(task_text: str) -> str:
    return f"""Ты решаешь простую задачу по программированию.

Верни только полный код на C++20 без Markdown, без объяснений и без текста вокруг.
Код должен читать входные данные из stdin и писать ответ в stdout.
Используй максимально простой код и минимальное количество стандартных библиотек.
Не используй #include <bits/stdc++.h>, если достаточно #include <iostream> или пары обычных заголовков.
Используй using namespace std;.
Не добавляй сложные шаблоны, классы и макросы без необходимости.

Условие задачи:
{task_text.strip()}
"""


def ask_ollama(prompt: str, model: str) -> str:
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.1,
            "num_predict": 4096,
        },
    }

    request = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise RuntimeError(
            "Не удалось подключиться к Ollama. Запусти Ollama и проверь, что модель установлена: "
            f"ollama pull {model}"
        ) from exc

    text = data.get("response", "").strip()
    if not text:
        raise RuntimeError("Ollama вернул пустой ответ.")

    return text


def setup_log(log_path: str | None) -> None:
    if not log_path:
        return

    path = Path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    log_file = path.open("w", encoding="utf-8")
    sys.stdout = log_file
    sys.stderr = log_file


def extract_cpp_code(text: str) -> str:
    match = re.search(r"```(?:cpp|c\+\+|cc)?\s*(.*?)```", text, re.IGNORECASE | re.DOTALL)
    if match:
        text = match.group(1).strip()

    return text.strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a C++ solution from a task statement.")
    parser.add_argument("--input", default=str(DEFAULT_INPUT), help="Path to the task statement file.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Path to the generated C++ file.")
    parser.add_argument("--model", default=os.getenv("OLLAMA_MODEL", DEFAULT_MODEL), help="Ollama model name.")
    parser.add_argument("--log", default=None, help="Write all output to this log file.")
    args = parser.parse_args()

    setup_log(args.log)

    print(f"Рабочая папка: {BASE_DIR}")

    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        input_path.parent.mkdir(parents=True, exist_ok=True)
        input_path.write_text(
            "Вставь сюда условие задачи, затем запусти: python solve_task.py\n",
            encoding="utf-8",
        )
        print(f"Создан файл {input_path}. Заполни его условием задачи и запусти скрипт еще раз.")
        return 1

    task_text = input_path.read_text(encoding="utf-8").strip()
    if not task_text:
        print(f"Файл {input_path} пустой. Вставь туда условие задачи.")
        return 1

    print(f"Читаю условие из {input_path}")
    print(f"Спрашиваю локальную модель {args.model}")

    response = ask_ollama(build_prompt(task_text), args.model)
    code = extract_cpp_code(response)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(code, encoding="utf-8")

    print(f"Готово: решение сохранено в {output_path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(f"Ошибка: {exc}", file=sys.stderr)
        raise SystemExit(1)
