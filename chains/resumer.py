"""
Цепочка А — «Учебный резюмер».
Три последовательных LLM-шага: резюме → ключевые идеи → вопросы для самопроверки.
"""

from typing import List

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

import config


def _step_summary(llm, input_text: str) -> str:
    """Шаг 1: генерация краткого резюме (2–4 предложения)."""
    prompt = ChatPromptTemplate.from_messages([
        ("system", config.LEARNING_SUMMARIZER_SYSTEM_PROMPT),
        ("human", "По следующему учебному тексту составь краткое резюме в 2–4 предложения: о чём текст, основные темы и идеи, что главное должен унести ученик. Только резюме, без вступлений.\n\nТекст:\n{input_text}"),
    ])
    chain = prompt | llm | StrOutputParser()
    return chain.invoke({"input_text": input_text}).strip()


def _step_key_points(llm, input_text: str, summary: str) -> str:
    """Шаг 2: выделение ключевых идей в три блока — Понятия, Шаги/алгоритмы, Примеры."""
    prompt = ChatPromptTemplate.from_messages([
        ("system", config.LEARNING_SUMMARIZER_SYSTEM_PROMPT),
        ("human", """Учебный текст и его краткое резюме даны ниже. Выдели ключевые идеи в три блока с подзаголовками:
- «Понятия»: термины и краткие объяснения простым языком
- «Шаги/алгоритмы»: последовательности действий или логики (если есть)
- «Примеры»: 1–2 понятных примера из жизни или практики

Только эти три блока, без вступлений и заключений.

Резюме:
{summary}

Исходный текст:
{input_text}"""),
    ])
    chain = prompt | llm | StrOutputParser()
    return chain.invoke({"input_text": input_text, "summary": summary}).strip()


def _step_questions(llm, key_points: str) -> str:
    """Шаг 3: генерация 3–5 вопросов для самопроверки, каждый с новой строки."""
    prompt = ChatPromptTemplate.from_messages([
        ("system", config.LEARNING_SUMMARIZER_SYSTEM_PROMPT),
        ("human", """По следующим ключевым идеям сформируй 3–5 вопросов для самопроверки. Без вариантов ответа. Каждый вопрос — с новой строки. Простые и конкретные формулировки.\n\nКлючевые идеи:\n{key_points}"""),
    ])
    chain = prompt | llm | StrOutputParser()
    return chain.invoke({"key_points": key_points}).strip()


def _parse_questions(raw: str) -> List[str]:
    """Парсинг сырого текста вопросов в список строк без пустых и лишних пробелов."""
    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    # Убираем нумерацию вида "1.", "2)" и т.п. в начале строки
    result = []
    for line in lines:
        s = line.lstrip()
        i = 0
        while i < len(s) and s[i].isdigit():
            i += 1
        if i < len(s) and s[i] in ".)-)":
            s = s[i + 1:].lstrip()
        result.append(s)
    return result


def build_resumer_output(input_text: str, log_callback=None) -> dict:
    """
    Публичный интерфейс цепочки А.
    Принимает учебный текст, возвращает словарь с summary, key_points и questions.
    log_callback(message: str) — опционально вызывается после каждого шага для логирования.
    """
    input_text = (input_text or "").strip()
    if not input_text:
        return {"summary": "", "key_points": "", "questions": []}

    def log(msg: str) -> None:
        if log_callback:
            log_callback(msg)

    llm = config.get_llm()

    # Шаг 1: резюме
    log("[А] Начинаю построение резюме...")
    summary = _step_summary(llm, input_text)
    log("[А] Резюме получено.")

    # Шаг 2: ключевые идеи
    log("[А] Выделяю ключевые идеи...")
    key_points = _step_key_points(llm, input_text, summary)
    log("[А] Ключевые идеи готовы.")

    # Шаг 3: вопросы
    log("[А] Генерирую вопросы для самопроверки...")
    questions_raw = _step_questions(llm, key_points)
    questions_list = _parse_questions(questions_raw)
    log(f"[А] Вопросы сгенерированы: {len(questions_list)} шт.")

    return {
        "summary": summary,
        "key_points": key_points,
        "questions": questions_list,
    }
