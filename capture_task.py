import argparse
import os
import sys
import time
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
INPUT_PATH = BASE_DIR / "input" / "task.txt"
OUTPUT_DIR = BASE_DIR / "output"
CAPTURED_IMAGE = OUTPUT_DIR / "captured_task.png"
OCR_DEBUG_IMAGE = OUTPUT_DIR / "ocr_debug.png"
CAPTURE_SECONDS = 3
DEFAULT_TESSERACT_PATHS = [
    Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"),
    Path(r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"),
]


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
    backends = []
    if hasattr(cv2, "CAP_MSMF"):
        backends.append(("CAP_MSMF", cv2.CAP_MSMF))
    backends.extend([
        ("CAP_DSHOW", cv2.CAP_DSHOW),
        ("default", cv2.CAP_ANY),
    ])

    for index in range(3):
        for backend_name, backend in backends:
            print(f"Пробую камеру index={index}, backend={backend_name}")
            camera = cv2.VideoCapture(index, backend)
            if not camera.isOpened():
                camera.release()
                continue

            camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

            for _ in range(5):
                ok, frame = camera.read()
                if ok and frame is not None:
                    print(f"Камера открыта: index={index}, backend={backend_name}")
                    return camera

            camera.release()

    return None


def frame_sharpness(cv2, frame) -> float:
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return cv2.Laplacian(gray, cv2.CV_64F).var()


def capture_best_frame(cv2, camera):
    print(f"Снимаю видео {CAPTURE_SECONDS} секунды и выбираю лучший кадр...")

    best_frame = None
    best_score = -1.0
    end_time = time.time() + CAPTURE_SECONDS

    while time.time() < end_time:
        ok, frame = camera.read()
        if not ok or frame is None:
            continue

        score = frame_sharpness(cv2, frame)
        if score > best_score:
            best_score = score
            best_frame = frame.copy()

        time.sleep(0.05)

    if best_frame is not None:
        print(f"Лучший кадр выбран, резкость: {best_score:.1f}")

    return best_frame


def prepare_for_ocr(cv2, frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, None, fx=1.5, fy=1.5, interpolation=cv2.INTER_CUBIC)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    enhanced = cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)
    return enhanced


def create_paddle_ocr(lang: str):
    from paddleocr import PaddleOCR

    try:
        return PaddleOCR(use_angle_cls=True, lang=lang, use_gpu=False, show_log=False)
    except TypeError:
        return PaddleOCR(lang=lang)


def extract_text_from_result(result) -> str:
    if not result:
        return ""

    lines = result[0] if isinstance(result[0], list) else result
    if not lines:
        return ""

    ordered = []
    for item in lines:
        if not item or len(item) < 2:
            continue

        box, text_info = item[0], item[1]
        if isinstance(text_info, (list, tuple)):
            text = str(text_info[0]).strip()
            confidence = float(text_info[1]) if len(text_info) > 1 else 0.0
        else:
            text = str(text_info).strip()
            confidence = 0.0

        if not text:
            continue

        top = min(point[1] for point in box)
        left = min(point[0] for point in box)
        ordered.append((top, left, confidence, text))

    ordered.sort(key=lambda item: (item[0], item[1]))
    return "\n".join(item[3] for item in ordered).strip()


def configure_tesseract(pytesseract) -> None:
    tesseract_cmd = os.getenv("TESSERACT_CMD")
    if tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
        return

    for candidate in DEFAULT_TESSERACT_PATHS:
        if candidate.exists():
            pytesseract.pytesseract.tesseract_cmd = str(candidate)
            print(f"Tesseract: {candidate}")
            return


def run_tesseract_ocr(pytesseract, prepared) -> str:
    for lang in ("rus+eng", "eng", "rus"):
        try:
            text = pytesseract.image_to_string(prepared, lang=lang)
            if text.strip():
                print(f"Tesseract OCR язык: {lang}")
                return text.strip()
        except Exception as exc:
            print(f"Tesseract OCR ошибка для {lang}: {exc}")

    return ""


def paddle_available() -> bool:
    try:
        import paddleocr  # noqa: F401
        return True
    except ImportError:
        return False


def run_paddle_ocr(frame, prepared) -> str:
    images = [
        ("original", frame),
        ("prepared", prepared),
    ]

    for lang in ("ru", "en"):
        print(f"Запускаю PaddleOCR, язык: {lang}")
        ocr = create_paddle_ocr(lang)

        for image_name, image in images:
            result = ocr.ocr(image, cls=True)
            text = extract_text_from_result(result)
            if text:
                print(f"OCR успешен: lang={lang}, image={image_name}, длина={len(text)}")
                return text

    return ""


def run_ocr(cv2, frame) -> str:
    prepared = prepare_for_ocr(cv2, frame)
    cv2.imwrite(str(OCR_DEBUG_IMAGE), prepared)

    if paddle_available():
        try:
            text = run_paddle_ocr(frame, prepared)
            if text:
                return text
            print("PaddleOCR не распознал текст, пробую Tesseract...")
        except Exception as exc:
            print(f"PaddleOCR ошибка: {exc}, пробую Tesseract...")

    try:
        import pytesseract
    except ImportError:
        return ""

    configure_tesseract(pytesseract)
    return run_tesseract_ocr(pytesseract, prepared)


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture task text from the laptop camera.")
    parser.add_argument("--log", default=None, help="Write all output to this log file.")
    args = parser.parse_args()
    setup_log(args.log)

    print(f"Рабочая папка: {BASE_DIR}")

    try:
        import cv2
    except ImportError:
        return fail("Установи зависимости: python -m pip install -r requirements.txt")

    print(f"Python: {sys.version.split()[0]}")
    if not paddle_available():
        print(
            "PaddleOCR не найден. Для лучшего OCR установи Python 3.12 и запусти install_camera.ps1. "
            "Пока будет использован Tesseract, если он установлен."
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    INPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    camera = open_camera(cv2)
    if camera is None:
        return fail(
            "Не удалось открыть камеру ноутбука. "
            "Проверь доступ к камере для классических приложений в Windows, "
            "что камера не занята другой программой и что она не отключена."
        )

    best_frame = capture_best_frame(cv2, camera)
    camera.release()

    if best_frame is None:
        return fail("Камера не вернула ни одного кадра.")

    cv2.imwrite(str(CAPTURED_IMAGE), best_frame)

    text = run_ocr(cv2, best_frame)

    if not text:
        return fail(
            "OCR не распознал текст. "
            "Для PaddleOCR нужен Python 3.12: запусти install_camera.ps1. "
            "Или установи Tesseract и смотри output/captured_task.png."
        )

    INPUT_PATH.write_text(text + "\n", encoding="utf-8")
    print(f"Готово: условие записано в {INPUT_PATH}")
    print(f"Кадр сохранен в {CAPTURED_IMAGE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
