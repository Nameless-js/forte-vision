"""Prompts for the local VLM. The model never produces citations; it only answers what is visible."""

from __future__ import annotations

import json

SYSTEM_RU = (
    "Ты — помощник службы внутреннего контроля банка. Ты видишь несколько последовательных кадров с камеры "
    "над кассовым местом (время кадра выжжено в левом верхнем углу). Отвечай ТОЛЬКО по тому, что видно на кадрах. "
    "Не называй имён, не определяй личность людей, не оценивай суммы и документы. Если не видно — отвечай unclear."
)

CHECKLIST_RU = (
    "Нормальный порядок операции: клиент подходит и садится → предъявляет документ (карточку/удостоверение) → "
    "передаёт/получает наличные → кассир пересчитывает наличные руками (перебирает купюры) или на счётной машине "
    "в присутствии клиента → убирает наличные в сейф/ящик → выдаёт документ → клиент уходит. "
    "Кассир не покидает рабочее место, пока клиент у стола; телефонами на рабочем месте не пользуется; "
    "посторонние не заходят за стол кассира; инкассаторская сумка принимается после осмотра и с документом."
)

VERIFY_SCHEMA_KEYS = ["counted_money", "id_shown", "cashier_left", "phone_visible", "unauthorized_person", "bag_checked", "cash_handover", "what_is_visible_ru", "confidence"]

VERIFY_JSON_TEMPLATE = {
    "counted_money": "yes|no|unclear",
    "id_shown": "yes|no|unclear",
    "cashier_left": "yes|no|unclear",
    "phone_visible": "yes|no|unclear",
    "unauthorized_person": "yes|no|unclear",
    "bag_checked": "yes|no|unclear|no_bag",
    "cash_handover": "cashier_to_client|client_to_cashier|none|unclear",
    "what_is_visible_ru": "1–2 предложения по-русски: что делают люди и что происходит с наличными",
    "confidence": 0.0,
}

TYPE_QUESTIONS_RU = {
    "workplace_left_unsecured": "Уходит ли кассир из помещения, оставляя рабочее место без присмотра (включённый ноутбук, предметы на столе)? Убирала ли она перед уходом ценности в сейф и закрывала ли его?",
    "personal_items_at_workplace": "Видны ли у кассира за рабочим столом личные предметы — стакан с напитком, бутылка, еда? Пьёт или ест ли кассир на рабочем месте?",
    "issue_without_count": "Пересчитывал ли кассир наличные (перебирал купюры руками или пользовался счётной машиной) перед тем, как передать их клиенту?",
    "accept_without_count": "Пересчитывал ли кассир полученные от клиента наличные (перебирал купюры руками или на счётной машине) перед тем, как убрать их?",
    "cashier_left_during_service": "Вставал ли кассир и уходил ли от стола, пока клиент оставался у стола?",
    "cash_left_unattended": "Лежат ли наличные на столе без кассира рядом (кассир отошёл или отсутствует)?",
    "phone_at_workplace": "Держит ли кассир в руке мобильный телефон или смотрит ли в него? (Карточка или купюры в руке — это НЕ телефон.)",
    "unauthorized_in_cash_zone": "Заходит ли кто-то, кроме кассира, за стол на сторону кассира или тянется ли клиент рукой/телом через стол к сейфу/ящику/наличным кассира?",
    "no_id_check": "Предъявлял ли клиент документ (карточку/удостоверение), и смотрел ли на него кассир до передачи наличных?",
    "collection_bag_unchecked": "Осматривал ли кассир переданную сумку (пломбу) и работал ли с сопроводительным документом перед тем, как убрать/выдать сумку?",
    "two_clients_cash_mixed": "Находятся ли у стола одновременно два клиента, пока на столе лежат наличные первой операции?",
    "handover_bypassing_transfer_device": "Передаются ли наличные из рук в руки над барьером, минуя лоток?",
    "protocol_deviation_other": "Есть ли на этих кадрах отклонение от нормального порядка операции? Какое?",
}


def verify_prompt(type_id: str, type_name_ru: str, facts: list[str], t_event: float, t_window: tuple[float, float]) -> str:
    q = TYPE_QUESTIONS_RU.get(type_id, TYPE_QUESTIONS_RU["protocol_deviation_other"])
    facts_txt = "; ".join(facts[:8]) if facts else "нет"
    return (
        f"{SYSTEM_RU}\n\n{CHECKLIST_RU}\n\n"
        f"Кадры охватывают интервал {t_window[0]:.1f}–{t_window[1]:.1f} с; предполагаемое событие на {t_event:.1f} с: "
        f"«{type_name_ru}». Признаки, найденные автоматически: {facts_txt}.\n"
        f"Главный вопрос: {q}\n\n"
        "Верни СТРОГО один JSON-объект без пояснений и без markdown, с полями и допустимыми значениями:\n"
        + json.dumps(VERIFY_JSON_TEMPLATE, ensure_ascii=False, indent=0)
        + "\nconfidence — число от 0 до 1: насколько ты уверен в своих ответах."
    )


CATCH_ALL_TEMPLATE = {
    "deviation": "yes|no|unclear",
    "deviation_type": "none|cashier_left|phone|unauthorized_person|cash_unattended|no_count|no_id|bag_unchecked|other",
    "what_is_visible_ru": "1–2 предложения по-русски",
    "confidence": 0.0,
}


def catch_all_prompt(t0: float, t1: float) -> str:
    return (
        f"{SYSTEM_RU}\n\n{CHECKLIST_RU}\n\n"
        f"Кадры охватывают интервал {t0:.1f}–{t1:.1f} с. Есть ли на них явное отклонение от нормального порядка "
        "(кассир ушёл при клиенте, пользуется телефоном, посторонний за столом кассира, наличные без присмотра, "
        "передача наличных без пересчёта, инкассаторская сумка без осмотра)? Если сомневаешься — отвечай no.\n\n"
        "Верни СТРОГО один JSON-объект без пояснений:\n" + json.dumps(CATCH_ALL_TEMPLATE, ensure_ascii=False, indent=0)
    )


RETRY_SUFFIX = "\n\nОтвет должен быть ТОЛЬКО валидным JSON-объектом (начинается с { и заканчивается }), без текста вокруг."
