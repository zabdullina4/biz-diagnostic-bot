import os
from tenacity import retry, stop_after_attempt, wait_exponential
from openai import OpenAI

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))

SYSTEM_CLASSIFIER = """Ты бизнес-диагност. На вход: сообщение владельца бизнеса (часто "грязное").
Верни ТОЛЬКО валидный JSON со строгими ключами:
{
 "normalized_text": "...",
 "category": "операционка|продажи|маркетинг|финансы|HR|сервис|продукт|стратегия|прочее",
 "topic": "... (коротко 2-5 слов)",
 "urgency": "low|medium|high",
 "sentiment": "negative|neutral|positive",
 "delegate_candidate": true|false,
 "automate_candidate": true|false,
 "hire_candidate": true|false,
 "summary": "выжимка 1-2 предложения"
}
Правила:
- normalized_text: убери мусор, сохрани смысл, русский язык.
- urgency high если есть сроки/пожар/клиент срывается/деньги горят.
- delegate_candidate true если задача рутинная/повторяемая/не требует собственника.
- automate_candidate true если повторяется и формализуется.
- hire_candidate true если "некому делать" или постоянная нагрузка требует роли.
"""

@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=6))
def classify_text(text: str) -> dict:
    resp = client.chat.completions.create(
        model="gpt-4.1-mini",
        temperature=0.2,
        messages=[
            {"role": "system", "content": SYSTEM_CLASSIFIER},
            {"role": "user", "content": text[:8000]},
        ],
        response_format={"type": "json_object"},
    )
    return resp.choices[0].message.content and __import__("json").loads(resp.choices[0].message.content)

@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=6))
def transcribe_ogg(file_bytes: bytes) -> str:
    # Telegram voice обычно ogg/opus
    # OpenAI SDK: audio.transcriptions.create(file=..., model=...)
    import io
    f = io.BytesIO(file_bytes)
    f.name = "voice.ogg"
    out = client.audio.transcriptions.create(
        model="gpt-4o-mini-transcribe",
        file=f
    )
    return getattr(out, "text", "") or ""
