"""
Learning Assistant — CLI.
Сценарий: ввод текста → конспект и вопросы → по очереди ответ на каждый вопрос (или пропуск) → разбор и оценка.
Текст урока можно передать из файла: python main.py урок.txt (удобно, если в тексте есть код).
"""

import argparse
import re
import sys
from pathlib import Path
from typing import List, Optional

from chains.resumer import build_resumer_output
from chains.answer_checker import check_answer
import config


def log(message: str) -> None:
    """Печать лога (без секретов)."""
    print(message, flush=True)


def read_lesson_text_from_console() -> str:
    """Чтение текста урока из консоли (многострочный ввод до пустой строки)."""
    print(
        "Введите текст урока (несколько строк — для завершения введите пустую строку).",
        flush=True,
    )
    print(
        "Если в тексте есть код — лучше сохраните урок в файл и запустите: python main.py путь/к/файлу.txt",
        flush=True,
    )
    lines = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line.strip() == "":
            break
        lines.append(line)
    return "\n".join(lines).strip()


def read_lesson_text_from_file(path: Path) -> str:
    """Чтение текста урока из файла (безопасно для текста с кодом)."""
    try:
        return path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        log(f"[INFO] Файл не найден: {path}")
        return ""
    except Exception as e:
        log(f"[INFO] Ошибка чтения файла: {e}")
        return ""


def read_lesson_text(file_path: Optional[Path] = None) -> str:
    """Текст урока: из файла, если передан путь, иначе из консоли."""
    if file_path is not None:
        log(f"[INFO] Загрузка текста урока из файла: {file_path}")
        return read_lesson_text_from_file(file_path)
    return read_lesson_text_from_console()


def parse_score_from_feedback(feedback: str) -> Optional[int]:
    """Извлекает оценку X из блока «Оценка: X/5» в тексте разбора. Возвращает None, если не найдено."""
    match = re.search(r"(\d)/5", feedback)
    if match:
        score = int(match.group(1))
        if 1 <= score <= 5:
            return score
    return None


def read_answer(skip_hint: bool = False) -> str:
    """Чтение ответа ученика (многострочный ввод до пустой строки)."""
    if skip_hint:
        print("Введите ответ (пустая строка или «пропустить» — пропустить вопрос):", flush=True)
    else:
        print("Введите ваш ответ (для завершения — пустая строка):", flush=True)
    lines = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line.strip() == "":
            break
        lines.append(line)
    return "\n".join(lines).strip()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Learning Assistant — конспект и проверка ответов по учебному тексту.",
        epilog="Пример с файлом (удобно, если в уроке есть код): python main.py урок.txt",
    )
    parser.add_argument(
        "lesson_file",
        nargs="?",
        type=Path,
        default=None,
        help="Путь к файлу с текстом урока (опционально; если не указан — ввод с консоли)",
    )
    args = parser.parse_args()

    # 1. Инициализация
    log("[INFO] Конфигурация загружена.")
    config.get_llm()
    log(f"[INFO] Используемая модель: {config.OPENAI_MODEL}.")

    # 2. Получение текста урока (из файла или консоли)
    input_text = read_lesson_text(args.lesson_file)
    if not input_text:
        log("[INFO] Текст урока не введён. Завершение.")
        sys.exit(0)

    log("[А] Получен текст урока, запускаю цепочку резюмирования...")

    # 3. Запуск цепочки А (с пошаговыми логами)
    result = build_resumer_output(input_text, log_callback=log)

    summary = result["summary"]
    key_points = result["key_points"]
    questions = result["questions"]

    # 4. Вывод результата А
    print()
    print("=== РЕЗЮМЕ ===", flush=True)
    print(summary or "(нет резюме)", flush=True)
    print()
    print("=== КЛЮЧЕВЫЕ ИДЕИ ===", flush=True)
    print(key_points or "(нет ключевых идей)", flush=True)
    print()
    print("=== ВОПРОСЫ ДЛЯ САМОПРОВЕРКИ ===", flush=True)
    for i, q in enumerate(questions, 1):
        print(f"  {i}. {q}", flush=True)
    print()

    # 5. Переход к цепочке Б — вопросы по очереди
    if not questions:
        log("[Б] Вопросы не сгенерированы, проверка ответов невозможна.")
        return

    n = len(questions)
    context = (key_points + "\n\n" + summary).strip()
    log("[Б] Переходим к ответам по порядку.")
    print("Ответы по порядку (вопрос 1 из N, затем 2 из N и т.д.):", flush=True)

    scores: List[int] = []

    for i, question in enumerate(questions, 1):
        print()
        print(f"--- Вопрос {i} из {n} ---", flush=True)
        print(question, flush=True)
        print()

        user_answer = read_answer(skip_hint=True)

        # Пропуск: пустой ответ или слово «пропустить»
        if not user_answer or user_answer.strip().lower() in ("пропустить", "пропустить."):
            log("[Б] Вопрос пропущен.")
            continue

        # 6. Запуск цепочки Б для ответа
        log("[Б] Анализирую ответ ученика...")
        feedback = check_answer(question, user_answer, context)
        log("[Б] Оценка и идеальный ответ получены.")

        # 7. Вывод результата Б
        print()
        print("=== РАЗБОР ОТВЕТА ===", flush=True)
        print(feedback, flush=True)

        # Собираем оценку для среднего балла
        score = parse_score_from_feedback(feedback)
        if score is not None:
            scores.append(score)

    log("[Б] Все вопросы пройдены.")

    # Средний балл по ответам (пропуски не учитываются)
    if scores:
        avg = sum(scores) / len(scores)
        print()
        print(f"=== СРЕДНИЙ БАЛЛ === {avg:.1f}/5 (по {len(scores)} из {n} ответов)", flush=True)
    else:
        print()
        print("=== СРЕДНИЙ БАЛЛ === не определён (все вопросы пропущены)", flush=True)

    log("Работа завершена.")


if __name__ == "__main__":
    main()
