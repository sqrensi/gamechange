import argparse
import os
import sys
import time
from pathlib import Path


INPUT_PATH = Path("input") / "task.txt"
OUTPUT_DIR = Path("output")
CAPTURED_IMAGE = OUTPUT_DIR / "captured_task.png"


def setup_log(log_path: str | None) -> None:
    if not log_path:
        return

    path = Path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    log_file = path.open("w", encoding="utf-8")
    sys.stdout = log_file
    sys.stderr = log_file


def fail(message: str) -> int:
    print(f"Ошибка: {message}", file=sys.stderr)
    return 1


def open_camera(cv2):
    backends = [
        ("CAP_DSHOW", cv2.CAP_DSHOW),
        ("default", cv2.CAP_ANY),
    ]

    for index in range(3):
        for backend_name, backend in backends:
            camera = cv2.VideoCapture(index, backend)
            if not camera.isOpened():
                camera.release()
                continue

            ok, frame = camera.read()
            if ok and frame is not None:
                print(f"Камера открыта: index={index}, backend={backend_name}")
                return camera

            camera.release()

    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture task text from the laptop camera.")
    parser.add_argument("--log", default=None, help="Write all output to this log file.")
    args = parser.parse_args()
    setup_log(args.log)

    try:
        import cv2
        import pytesseract
    except ImportError:
        return fail("Установи зависимости: python -m pip install opencv-python pytesseract")

    tesseract_cmd = os.getenv("TESSERACT_CMD")
    if tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    INPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    camera = open_camera(cv2)
    if camera is None:
        return fail(
            "Не удалось открыть камеру ноутбука. "
            "Проверь: доступ к камере в Windows для классических приложений, "
            "что камера не занята другой программой, и что она не отключена."
        )

    print("Считываю изображение с камеры 3 секунды...")

    best_frame = None
    best_score = -1.0
    end_time = time.time() + 3

    while time.time() < end_time:
        ok, frame = camera.read()
        if not ok:
            continue

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        score = cv2.Laplacian(gray, cv2.CV_64F).var()
        if score > best_score:
            best_score = score
            best_frame = frame

        time.sleep(0.05)

    camera.release()

    if best_frame is None:
        return fail("Камера не вернула ни одного кадра.")

    cv2.imwrite(str(CAPTURED_IMAGE), best_frame)

    gray = cv2.cvtColor(best_frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, None, fx=1.5, fy=1.5, interpolation=cv2.INTER_CUBIC)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    _, prepared = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    try:
        text = pytesseract.image_to_string(prepared, lang="rus+eng")
    except pytesseract.TesseractNotFoundError:
        return fail(
            "Tesseract OCR не найден. Установи Tesseract и при необходимости укажи путь "
            "через переменную TESSERACT_CMD."
        )

    text = text.strip()
    if not text:
        return fail("OCR не распознал текст. Попробуй лучшее освещение и крупнее показать условие.")

    INPUT_PATH.write_text(text + "\n", encoding="utf-8")
    print(f"Готово: условие записано в {INPUT_PATH}")
    print(f"Кадр сохранен в {CAPTURED_IMAGE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
