# forte_ai — локальный AI-движок контроля кассовой дисциплины по видео

Полностью локальный движок (Python-пакет + CLI + референсный API-сервер), который анализирует видеозапись
рабочего места кассира и возвращает вердикт `violation` / `no_violation` с типом нарушения, таймкодом,
описанием, кадрами-доказательствами и ссылкой на нормативный акт РК (ТЗ ForteBank, Datathon 2026).

* Никаких облачных AI-сервисов: все модели исполняются локально; после загрузки весов работает офлайн.
* Без распознавания лиц и без аудио. Только open-source модели с коммерчески разрешёнными лицензиями
  (LICENSES.md).
* Цитаты нормативных актов берутся только из `kb/rule_cards.json` и проверяются дословно тестами (SOURCES.md).

## Требования

* Python **3.10–3.12** (разработано на 3.12). Windows, Linux или macOS.
* Для профиля `gpu-small`/`gpu-large`: NVIDIA GPU (6+ ГБ VRAM) с драйвером CUDA 12.x. Без GPU работает
  профиль `cpu` (медленнее, без VLM-проверки).
* ~12 ГБ на диске: зависимости (~7 ГБ с CUDA-сборкой PyTorch) + веса моделей (~5 ГБ).
* Интернет нужен ОДИН раз: `pip install` и загрузка весов. Дальше — офлайн.

## Установка (вместо `make` на Windows используется `python scripts/run.py <target>`)

```bash
git clone <repo> forte-ai && cd forte-ai
python scripts/run.py setup            # создаёт .venv, ставит зависимости (CUDA 12.4), собирает labels.csv
# CPU-машина:  python scripts/run.py setup --cpu
.venv/Scripts/python scripts/download_weights.py --profile gpu-small   # веса: Grounding DINO, RTMPose, Qwen3-VL-2B
```

На Linux/macOS замените `.venv/Scripts/python` на `.venv/bin/python`; цели доступны и через `make`
(Makefile делегирует в `scripts/run.py`).

Обучающие видео кладутся в `public/` (42 файла `X-*.mov` / `Х-*.mov`), разметка — `open/open_labels.xlsx`.
Видео не являются частью репозитория и никогда в него не коммитятся.

## Использование

```bash
# один файл
.venv/Scripts/python -m forte_ai analyze public/X-1.mov --out result.json --evidence-dir evidence/
# каталог
.venv/Scripts/python -m forte_ai batch public/ --out results/
# python API (основная интеграция)
python -c "from forte_ai import Analyzer; a = Analyzer(); print(a.analyze('public/X-1.mov')['verdict'])"
```

Схема результата — ТЗ §10 (`forte_ai/result_schema.json`); подробности интеграции, прогресс-коллбек,
лимит 5 минут и варианты связки с бэкендом — INTEGRATION.md.

## Референсный API-сервер

```bash
set FORTE_API_KEY=your-secret                   # export ... на Linux
.venv/Scripts/python -m server.worker &          # процесс с моделями
.venv/Scripts/python -m uvicorn server.app:app --host 0.0.0.0 --port 8000
# POST /api/v1/analyze (multipart file, заголовок X-API-Key) -> {job_id}
# GET  /api/v1/jobs/{job_id} -> processing|done|failed + результат
```

Docker: `docker build -t forte-ai .` (веса запекаются на этапе сборки), затем
`docker run --gpus all -p 8000:8000 -e FORTE_API_KEY=... forte-ai`.

## Проверки (цели совпадают с Makefile)

```bash
python scripts/run.py test         # pytest: парсеры, правила, схема, KB-цитаты, роли, трекер
python scripts/run.py eval        # метрики на размеченном наборе -> reports/iter_XXX/
python scripts/run.py robustness  # аугментации: флип, повороты, перспектива, яркость, 720p -> reports/
python scripts/run.py timing      # тайминг на 3 самых длинных видео + тест вотчдога
python scripts/run.py offline-check  # HF_HUB_OFFLINE=1 + блокировка сокетов + аудит кода
python scripts/run.py api-test    # поднимает сервер+воркер, гоняет контракт (401/404/жизненный цикл/схема)
python scripts/run.py verify      # всё вместе + валидация reports/final
```

## Документация

| файл | содержание |
|---|---|
| ARCHITECTURE.md | трёхслойная архитектура, измеренные обоснования решений |
| VIOLATION_TYPES.md | таксономия типов (team-assigned), политика таймкодов, FP-риски |
| SOURCES.md | нормативные акты, как получены и проверяются цитаты |
| INTEGRATION.md | как бэкенд-команде подключить движок |
| LICENSES.md | лицензии всех моделей и библиотек |
| LIMITATIONS.md | известные ограничения и случаи ошибок |
| ASSUMPTIONS.md / PROGRESS.md | журнал решений и статуса |
| FINAL_REPORT.md | итоговые метрики, чек-лист соответствия ТЗ |
