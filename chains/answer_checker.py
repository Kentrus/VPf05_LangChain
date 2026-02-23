"""
Цепочка Б — «Проверка ответов ученика».
Один LLM-шаг: анализ ответа, плюсы/минусы, оценка 1–5, идеальный ответ.
"""

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

import config


def check_answer(question: str, user_answer: str, context: str) -> str:
    """
    Проверяет ответ ученика на вопрос.
    question — вопрос из цепочки А,
    user_answer — ответ ученика,
    context — конкатенация key_points + summary.
    Возвращает отформатированный текст с блоками Анализ, Плюсы, Минусы, Оценка, Идеальный ответ.
    """
    question = (question or "").strip()
    user_answer = (user_answer or "").strip()
    context = (context or "").strip()

    if not question or not context:
        return "Ошибка: не указан вопрос или контекст для проверки."

    llm = config.get_llm()

    user_template = """Проверь ответ ученика на вопрос. Контекст (резюме и ключевые идеи) дан для опоры.

Вопрос: {question}

Ответ ученика: {user_answer}

Контекст (материал урока):
{context}

Выведи разбор строго в формате:

Анализ:
...

Плюсы:
...

Минусы:
...

Оценка:
X/5 — краткое объяснение

Идеальный ответ:
..."""

    prompt = ChatPromptTemplate.from_messages([
        ("system", config.LEARNING_ANSWER_CHECKER_SYSTEM_PROMPT),
        ("human", user_template),
    ])
    chain = prompt | llm | StrOutputParser()
    return chain.invoke({
        "question": question,
        "user_answer": user_answer or "(ученик не дал ответа)",
        "context": context,
    }).strip()
