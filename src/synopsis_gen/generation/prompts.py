from typing import Dict

from src.synopsis_gen.llm.yandex_client import LLMClient
from src.synopsis_gen.llm.json_utils import llm_json

def _mode_constraints(mode: str, inn: str) -> str:
    if inn.strip().lower() != "palbociclib":
        return ""
    if mode == "cns_pk":
        return (
            "ВАЖНО: для палбоциклиба в режиме cns_pk цели НЕ должны быть 'эффективность/выживаемость/качество жизни'. "
            "Фокус: фармакокинетика, экспозиция (в т.ч. в ЦНС/СМЖ/опухолевой ткани если применимо), сравнение концентраций, "
            "и безопасность как сопутствующая оценка. "
            "В критериях включения желательно отразить сохранённую функцию пути Rb (Rb-позитивный статус), если применимо."
        )
    return (
        "ВАЖНО: для палбоциклиба в режиме be_fed цели НЕ должны быть 'эффективность/выживаемость/качество жизни'. "
        "Фокус: сравнительная фармакокинетика/биоэквивалентность (AUC/Cmax), влияние пищи (если fed), "
        "и безопасность однократного/кратковременного дозирования."
    )

def llm_part_a(llm: LLMClient, inn: str, indication: str, regimen: str, evidence: str, mode: str) -> Dict:
    system = (
        "Ты — медицинский писатель и клинический фармаколог. "
        "Пиши строго на русском. Не вставляй английские фразы. "
        "Не используй слова 'черновик', 'предварительно'. "
        "Численные данные указывай только если они есть в EVIDENCE, иначе не выдумывай числа. "
        "Если поле относится к пользователю (спонсор/номер/центры/названия Т/R) — ставь null. "
        + _mode_constraints(mode, inn)
    )
    user = f"""
Верни валидный JSON по схеме:
{{
  "study_title": str,
  "phase": str,
  "objectives": {{"primary": str, "secondary": str}},
  "rationale": str,
  "drug_profile": str
}}

МНН: {inn}
Контекст/показание: {indication}
Условия питания: {regimen}

ОБЪЁМ (СТРОГО):
- rationale: 1400–2200 слов
- drug_profile: 1100–1900 слов

ФОРМАТ:
- Подзаголовки, нумерация/маркированные списки.
- Не сокращай разделы до 2–3 абзацев.

EVIDENCE:
{evidence}
""".strip()
    return llm_json(llm, system, user)

def llm_part_b_design(llm: LLMClient, inn: str, indication: str, regimen: str, evidence: str, mode: str) -> Dict:
    system = (
        "Ты — медицинский писатель/координатор клинических исследований. "
        "Пиши строго на русском. Без английских вставок. "
        "Не используй слово 'черновик'. "
        "ДИЗАЙН ИССЛЕДОВАНИЯ — самый важный раздел: дай конкретную структуру (тип, периоды, последовательности, washout, условия питания, "
        "дозирование, рандомизация, открытое/слепое, эндпоинты). "
        "Если нельзя обосновать числа evidence-ом — пиши общими корректными формулировками без чисел. "
        "Пользовательские поля — null. "
        + _mode_constraints(mode, inn)
    )
    user = f"""
Верни валидный JSON по схеме:
{{
  "design": {{
     "type": str,
     "setting": str,
     "periods": str,
     "sequences": str,
     "washout": str,
     "randomization": str,
     "blinding": str,
     "feeding": str,
     "dose_admin": str,
     "endpoints": str
  }},
  "population": str,
  "inclusion": [str,...],
  "exclusion": [str,...],
  "treatments": str,
  "schedule_brief": str
}}

МНН: {inn}
Контекст/показание: {indication}
Условия питания: {regimen}

ОБЪЁМ (СТРОГО):
- design (design.* суммарно): 1200–2100 слов
- population+criteria: 1200–2000 слов
- treatments: 700–1400 слов
- schedule_brief: 250–450 слов (кратко; полный график будет отдельно)

ОБЯЗАТЕЛЬНО:
- В exclusion включи пункт: "Несоответствие критериям включения".
- Критерии невключения должны быть конкретными и детализированными.
- Не использовать размытые формулировки типа "хронические заболевания" без уточнения.
- Вместо этого указывать категории и примеры:
  • сердечно-сосудистые заболевания (ИБС, сердечная недостаточность, нарушения ритма)
  • заболевания печени (повышение АЛТ/АСТ, цирроз)
  • заболевания почек (снижение СКФ)
  • эндокринные нарушения (неконтролируемый сахарный диабет)
  • психические расстройства
  • онкологические заболевания (если не относятся к целевой популяции)
- Указывать клиническую значимость состояния для ФК/безопасности.
- Формулировать критерии так, как это делается в клинических синопсисах.
- Для palbociclib в режиме cns_pk добавь в inclusion упоминание Rb/путь Rb (Rb-позитивный статус), если это релевантно.

EVIDENCE:
{evidence}
""".strip()
    return llm_json(llm, system, user)

def llm_part_d_schedule(llm: LLMClient, inn: str, indication: str, regimen: str, evidence: str, mode: str) -> Dict:
    system = (
        "Ты — клинический координатор и фармакокинетик. Пиши строго на русском. "
        "Сделай очень подробный раздел 'План процедур и график отбора проб' как в синопсисах. "
        "Не используй слово 'черновик'. "
        "Числа указывай только если они есть в EVIDENCE; иначе описывай график словами без конкретных часов. "
        + _mode_constraints(mode, inn)
    )
    user = f"""
Верни валидный JSON:
{{"schedule": str}}

МНН: {inn}
Контекст: {indication}
Условия питания: {regimen}

ОБЪЁМ (СТРОГО): 2400–3700 слов.

Структура внутри schedule:
- Общая схема визитов/периодов и временные окна
- Госпитализация/наблюдение/выписка
- Условия питания/вода/запреты/контроль сопутствующих
- PK sampling: логика ранних точек + "хвост" до достаточного времени (без конкретных часов, если нет evidence)
- Какие обследования когда: ЭКГ, лаборатория, витальные, осмотр, регистрация НЯ
- Обращение с образцами: центрифугирование, заморозка, транспортировка, цепочка поставок (без чисел, если нет)

EVIDENCE:
{evidence}
""".strip()
    return llm_json(llm, system, user)

def llm_part_e_bio_stats(llm: LLMClient, inn: str, indication: str, regimen: str, evidence: str, mode: str) -> Dict:
    system = (
        "Ты — руководитель биоаналитики и биостатистик. Пиши строго на русском. "
        "Не используй английские вставки. Не используй слово 'черновик'. "
        "Числа только из EVIDENCE; если чисел нет — без чисел, но с требованиями/шаблоном. "
        "Размер выборки: опиши формулы/подход (TOST/ANOVA), а конкретное N будет подставлено автоматически в документ. "
        + _mode_constraints(mode, inn)
    )
    user = f"""
Верни валидный JSON:
{{"bioanalytics": str, "statistics": str, "sample_size_template": str}}

МНН: {inn}
Контекст: {indication}
Условия питания: {regimen}

ОБЪЁМ (СТРОГО):
- bioanalytics: 1200–2000 слов
- statistics: 1500–2600 слов
- sample_size_template: 600–1000 слов

Требования к sample_size_template:
- Поясни, что расчет для 2×2 crossover (если режим be_fed) или для выбранного дизайна (если cns_pk).
- Обязательно упомяни: CVintra, мощность, α, ожидаемое отношение геом. средних (GMR), учет выбывания (dropout).
- НЕ выдумывай конкретные числа, если их нет в evidence.

EVIDENCE:
{evidence}
""".strip()
    return llm_json(llm, system, user)

def llm_part_c_safety(llm: LLMClient, inn: str, indication: str, regimen: str, evidence: str, mode: str) -> Dict:
    system = (
        "Ты — специалист по безопасности, этике и качеству клинических исследований. "
        "Пиши строго на русском. Без английских вставок. "
        "Не используй слово 'черновик'. "
        "Не выдумывай численные пороги/нормативные номера, если их нет в evidence. "
        + _mode_constraints(mode, inn)
    )
    user = f"""
Верни валидный JSON:
{{
  "pk_parameters": {{"primary": [str,...], "secondary": [str,...]}},
  "randomization": str,
  "safety": str,
  "ethics": str,
  "data_quality": str,
  "risks_limits": str
}}

МНН: {inn}
Контекст/показание: {indication}
Условия питания: {regimen}

ОБЪЁМ (СТРОГО):
- safety: 900–1600 слов
- ethics: 650–1200 слов
- data_quality: 650–1200 слов
- risks_limits: 600–1000 слов

EVIDENCE:
{evidence}
""".strip()
    return llm_json(llm, system, user)