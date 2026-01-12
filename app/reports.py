from datetime import datetime, timedelta, timezone
from sqlalchemy import select, func
from .db import get_session
from .models import Message

def _now_utc():
    return datetime.now(timezone.utc)

def get_daily_stats(hours: int = 24):
    since = _now_utc() - timedelta(hours=hours)
    with get_session() as s:
        rows = s.execute(
            select(Message).where(Message.created_at >= since).order_by(Message.created_at.asc())
        ).scalars().all()

    return rows

def build_daily_report(rows):
    if not rows:
        return "За последние 24 часа сообщений нет."

    total = len(rows)

    def count_by(attr):
        d = {}
        for r in rows:
            k = getattr(r, attr) or "unknown"
            d[k] = d.get(k, 0) + 1
        return d

    by_cat = count_by("category")
    by_urg = count_by("urgency")

    delegate = [r for r in rows if r.delegate_candidate]
    automate = [r for r in rows if r.automate_candidate]
    hire = [r for r in rows if r.hire_candidate]

    top_lines = []
    top_lines.append(f"📊 Ежедневный отчёт (24ч)\nВсего сообщений: {total}\n")
    top_lines.append("Категории:")
    for k, v in sorted(by_cat.items(), key=lambda x: -x[1])[:8]:
        top_lines.append(f"• {k}: {v}")

    top_lines.append("\nСрочность:")
    for k, v in sorted(by_urg.items(), key=lambda x: -x[1]):
        top_lines.append(f"• {k}: {v}")

    def list_block(title, items, limit=7):
        if not items:
            return f"\n{title}: нет"
        lines = [f"\n{title} (топ {min(limit, len(items))}):"]
        for r in items[:limit]:
            lines.append(f"• {r.topic} — {r.summary}")
        return "\n".join(lines)

    top_lines.append(list_block("🧩 Делегировать", delegate))
    top_lines.append(list_block("⚙️ Автоматизировать", automate))
    top_lines.append(list_block("👥 Найм", hire))

    top_lines.append("\n📝 Важное (high urgency):")
    highs = [r for r in rows if r.urgency == "high"]
    if not highs:
        top_lines.append("• нет")
    else:
        for r in highs[:10]:
            top_lines.append(f"• {r.topic}: {r.summary}")

    return "\n".join(top_lines)

def build_21_30_day_summary(days: int = 21):
    since = _now_utc() - timedelta(days=days)
    with get_session() as s:
        rows = s.execute(
            select(Message).where(Message.created_at >= since).order_by(Message.created_at.asc())
        ).scalars().all()

    if not rows:
        return f"За последние {days} дней сообщений нет."

    delegate = [r for r in rows if r.delegate_candidate]
    automate = [r for r in rows if r.automate_candidate]
    hire = [r for r in rows if r.hire_candidate]

    # простая дедупликация по summary/topic
    def uniq(items, key):
        seen = set()
        out = []
        for it in items:
            k = (getattr(it, key) or "").strip().lower()
            if k and k not in seen:
                seen.add(k)
                out.append(it)
        return out

    delegate_u = uniq(delegate, "summary")
    automate_u = uniq(automate, "summary")
    hire_u = uniq(hire, "summary")

    lines = []
    lines.append(f"🧠 Итоговая диагностика за {days} дней")
    lines.append("\n1) ✅ Задачи для делегирования:")
    if not delegate_u:
        lines.append("• нет явных кандидатов")
    else:
        for r in delegate_u[:25]:
            lines.append(f"• {r.summary}")

    lines.append("\n2) ⚙️ Рекомендации по автоматизации:")
    if not automate_u:
        lines.append("• нет явных кандидатов")
    else:
        for r in automate_u[:25]:
            lines.append(f"• {r.summary}")

    lines.append("\n3) 👥 Рекомендации по найму:")
    if not hire_u:
        lines.append("• нет явных кандидатов")
    else:
        for r in hire_u[:15]:
            lines.append(f"• {r.summary}")

    lines.append("\n4) 🗺️ Дорожная карта выхода из операционки (черновик):")
    lines.append("• Неделя 1: сбор сообщений + фиксация повторяющихся задач")
    lines.append("• Неделя 2: делегирование рутинных задач + чек-листы")
    lines.append("• Неделя 3: внедрение 1–2 автоматизаций + KPI исполнителям")
    lines.append("• Неделя 4: корректировка ролей/найм + контроль по метрикам")
    lines.append("\nЕсли хочешь — расширим дорожную карту под твою нишу и процессы (будет точнее).")

    return "\n".join(lines)
