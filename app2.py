import sqlite3
import uuid
from datetime import date
from itertools import product
from pathlib import Path

import streamlit  as st

# ---------- Настройки проекта ----------
APP_DIR = Path(__file__).parent
DB_PATH = APP_DIR / "wardrobe.db"
UPLOAD_DIR = APP_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

CATEGORIES = [
    "Верх",
    "Низ",
    "Платье / комбинезон",
    "Обувь",
    "Верхняя одежда",
    "Аксессуар",
    "Другое",
]
SEASONS = ["Всесезонная", "Весна", "Лето", "Осень", "Зима"]
OCCASIONS = ["Повседневный", "Учёба / работа", "Праздник", "Спорт", "Прогулка"]

# Сливовая палитра с контрастным тёмным текстом и светлыми полями
CREAM = "#F7F3F7"       # фон приложения
PLUM = "#4B3152"        # основные сливовые элементы
CHERRY = "#963B55"      # кнопки при наведении и акцент
BUTTER = "#F2DE93"      # небольшие выделения
INK = "#2D2430"         # основной текст — тёмный
SIDEBAR = "#E9E1EB"     # фон бокового меню
SURFACE = "#FFFFFF"     # фон форм и полей
BORDER = "#D8CBDC"      # границы

st.markdown(
    f"""
    <style>
      .stApp,
      [data-testid="stAppViewContainer"] {{
        background: {CREAM};
        color: {INK};
      }}

      [data-testid="stSidebar"] {{
        background: {SIDEBAR};
      }}

      h1, h2, h3, h4,
      [data-testid="stMarkdownContainer"],
      [data-testid="stCaptionContainer"] {{
        color: {INK};
      }}

      /* Поля ввода — светлый фон, тёмный текст */
      input, textarea,
      [data-baseweb="select"] > div {{
        background: {SURFACE} !important;
        color: {INK} !important;
        border-color: {BORDER} !important;
      }}

      input::placeholder,
      textarea::placeholder {{
        color: #716676 !important;
        opacity: 1;
      }}

      /* Кнопки */
      div.stButton > button,
      div.stFormSubmitButton > button {{
        background: {PLUM};
        color: #FFFFFF;
        border: 0;
        border-radius: 10px;
        padding: 0.55rem 1rem;
        font-weight: 600;
      }}

      div.stButton > button:hover,
      div.stFormSubmitButton > button:hover {{
        background: {CHERRY};
        color: #FFFFFF;
      }}

      /* Формы и карточки */
      div[data-testid="stForm"],
      [data-testid="stVerticalBlockBorderWrapper"] {{
        background: {SURFACE};
        border: 1px solid {BORDER};
        border-radius: 14px;
      }}

      .hero {{
        background: {PLUM};
        color: #FFFFFF;
        padding: 1.5rem 1.7rem;
        border-radius: 18px;
        margin-bottom: 1rem;
      }}

      .hero h1, .hero p {{
        color: #FFFFFF;
      }}

      .tag {{
        display: inline-block;
        background: {BUTTER};
        color: {INK};
        padding: 0.2rem 0.6rem;
        border-radius: 99px;
        font-size: 0.85rem;
      }}
    </style>
    """,
    unsafe_allow_html=True,
)
# ---------- База данных ----------
def connect_db():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def init_db():
    with connect_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS clothes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                color TEXT NOT NULL,
                season TEXT NOT NULL,
                notes TEXT DEFAULT '',
                photo_path TEXT DEFAULT '',
                date_added TEXT NOT NULL,
                last_worn TEXT,
                occasions TEXT DEFAULT ''
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS outfits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                item_ids TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )

        # Добавляет новое поле в уже созданную базу, не удаляя старые вещи.
        columns = {
            row[1] for row in conn.execute("PRAGMA table_info(clothes)").fetchall()
        }
        if "occasions" not in columns:
            conn.execute(
                "ALTER TABLE clothes ADD COLUMN occasions TEXT DEFAULT ''"
            )


def get_clothes():
    with connect_db() as conn:
        conn.row_factory = sqlite3.Row
        return conn.execute("SELECT * FROM clothes ORDER BY id DESC").fetchall()


def get_outfits():
    with connect_db() as conn:
        conn.row_factory = sqlite3.Row
        return conn.execute("SELECT * FROM outfits ORDER BY id DESC").fetchall()


def save_photo(uploaded_file):
    if uploaded_file is None:
        return ""

    suffix = Path(uploaded_file.name).suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png", ".webp"}:
        suffix = ".jpg"

    filename = f"{uuid.uuid4().hex}{suffix}"
    path = UPLOAD_DIR / filename
    path.write_bytes(uploaded_file.getvalue())
    return str(path)


def add_clothing(name, category, color, season, notes, photo_path, occasions):
    with connect_db() as conn:
        conn.execute(
            """
            INSERT INTO clothes
            (name, category, color, season, notes, photo_path,
             date_added, last_worn, occasions)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                name.strip(),
                category,
                color.strip(),
                season,
                notes.strip(),
                photo_path,
                date.today().isoformat(),
                None,
                ", ".join(occasions),
            ),
        )


def mark_worn(item_id):
    with connect_db() as conn:
        conn.execute(
            "UPDATE clothes SET last_worn = ? WHERE id = ?",
            (date.today().isoformat(), item_id),
        )


def delete_clothing(item_id):
    with connect_db() as conn:
        row = conn.execute(
            "SELECT photo_path FROM clothes WHERE id = ?", (item_id,)
        ).fetchone()
        conn.execute("DELETE FROM clothes WHERE id = ?", (item_id,))

    if row and row[0]:
        try:
            Path(row[0]).unlink(missing_ok=True)
        except OSError:
            pass


def save_outfit(name, item_ids):
    with connect_db() as conn:
        conn.execute(
            "INSERT INTO outfits (name, item_ids, created_at) VALUES (?, ?, ?)",
            (
                name.strip(),
                ",".join(map(str, item_ids)),
                date.today().isoformat(),
            ),
        )
def update_clothing(
    item_id, name, category, color, season, notes, occasions, new_photo_path=None
):
    """Обновляет вещь. Если новое фото не загружено, старое остаётся."""
    with connect_db() as conn:
        old_photo = conn.execute(
            "SELECT photo_path FROM clothes WHERE id = ?", (item_id,)
        ).fetchone()

        if new_photo_path is None:
            conn.execute(
                """
                UPDATE clothes
                SET name = ?, category = ?, color = ?, season = ?,
                    notes = ?, occasions = ?
                WHERE id = ?
                """,
                (
                    name.strip(), category, color.strip(), season,
                    notes.strip(), ", ".join(occasions), item_id,
                ),
            )
        else:
            conn.execute(
                """
                UPDATE clothes
                SET name = ?, category = ?, color = ?, season = ?,
                    notes = ?, occasions = ?, photo_path = ?
                WHERE id = ?
                """,
                (
                    name.strip(), category, color.strip(), season,
                    notes.strip(), ", ".join(occasions),
                    new_photo_path, item_id,
                ),
            )

    # Удаляем старый файл фотографии только после замены.
    if new_photo_path and old_photo and old_photo[0]:
        try:
            Path(old_photo[0]).unlink(missing_ok=True)
        except OSError:
            pass


def update_outfit(outfit_id, name, item_ids):
    with connect_db() as conn:
        conn.execute(
            "UPDATE outfits SET name = ?, item_ids = ? WHERE id = ?",
            (
                name.strip(),
                ",".join(map(str, item_ids)),
                outfit_id,
            ),
        )


def delete_outfit(outfit_id):
    with connect_db() as conn:
        conn.execute("DELETE FROM outfits WHERE id = ?", (outfit_id,))
    with connect_db() as conn:
        conn.execute(
            "INSERT INTO outfits (name, item_ids, created_at) VALUES (?, ?, ?)",
            (
                name.strip(),
                ",".join(map(str, item_ids)),
                date.today().isoformat(),
            ),
        )

# ---------- Подбор по цветам ----------
COLOR_GROUPS = {
    "нейтральный": [
        "бел", "чёрн", "черн", "сер", "беж", "крем",
        "молоч", "коричнев", "коричн",
    ],
    "синий": ["син", "голуб", "джинс", "деним"],
    "зелёный": ["зелён", "зелен", "олив", "хаки", "мят"],
    "красный": ["красн", "бордов", "вишн", "марсал"],
    "розовый": ["розов", "пудров"],
    "жёлтый": ["жёлт", "желт", "горчич"],
    "фиолетовый": ["фиолет", "лилов", "сливов"],
}


def color_group(color):
    value = color.casefold().strip()
    for group, words in COLOR_GROUPS.items():
        if any(word in value for word in words):
            return group
    return value


def colors_compatible(color_a, color_b):
    """Простая эвристика, а не автоматическая оценка стиля."""
    group_a = color_group(color_a)
    group_b = color_group(color_b)

    if group_a == group_b:
        return True

    if group_a == "нейтральный" or group_b == "нейтральный":
        return True

    friendly_pairs = {
        frozenset(("синий", "коричневый")),
        frozenset(("синий", "жёлтый")),
        frozenset(("зелёный", "коричневый")),
        frozenset(("зелёный", "жёлтый")),
        frozenset(("красный", "синий")),
        frozenset(("розовый", "фиолетовый")),
    }
    return frozenset((group_a, group_b)) in friendly_pairs


def same_color_family(color_a, color_b):
    return color_group(color_a) == color_group(color_b)
# ---------- Подбор комплектов ----------
def fits_occasion(item, occasion):
    """Вещи без указанного повода считаются подходящими для любого повода."""
    item_occasions = [
        value.strip()
        for value in (item["occasions"] or "").split(",")
        if value.strip()
    ]
    return not item_occasions or occasion in item_occasions


def suggest_outfits(clothes, occasion, target_item=None, limit=3):
    """
    Собирает простые варианты:
    верх + низ (+ обувь) или платье (+ обувь).
    Для напоминания старается включить выбранную забытую вещь.
    """
    candidates = [
        item for item in clothes
        if fits_occasion(item, occasion)
    ]

    if target_item is not None:
        candidates = [
            item for item in candidates
            if item["id"] != target_item["id"]
        ]

    tops = [item for item in candidates if item["category"] == "Верх"]
    bottoms = [item for item in candidates if item["category"] == "Низ"]
    dresses = [
        item for item in candidates
        if item["category"] == "Платье / комбинезон"
    ]
    shoes = [item for item in candidates if item["category"] == "Обувь"]

    results = []

    if target_item is not None:
        if target_item["category"] == "Верх":
            tops = [target_item]
        elif target_item["category"] == "Низ":
            bottoms = [target_item]
        elif target_item["category"] == "Платье / комбинезон":
            dresses = [target_item]
        elif target_item["category"] == "Обувь":
            shoes = [target_item]
        else:
            # Для куртки или аксессуара показываем сочетающиеся вещи.
            candidates = [
                item for item in candidates
                if item["category"] in {"Верх", "Низ", "Обувь",
                                        "Платье / комбинезон"}
            ]

    for top, bottom in product(tops, bottoms):
        if top["id"] == bottom["id"]:
            continue
        if not colors_compatible(top["color"], bottom["color"]):
            continue

        outfit = [top, bottom]
        matching_shoes = [
            shoe for shoe in shoes
            if colors_compatible(shoe["color"], top["color"])
            and colors_compatible(shoe["color"], bottom["color"])
        ]
        if matching_shoes:
            outfit.append(matching_shoes[0])

        if target_item is not None and target_item["id"] not in {
            item["id"] for item in outfit
        }:
            if colors_compatible(target_item["color"], top["color"]):
                outfit.append(target_item)
            elif colors_compatible(target_item["color"], bottom["color"]):
                outfit.append(target_item)
            else:
                continue

        results.append(outfit)

    for dress in dresses:
        outfit = [dress]
        matching_shoes = [
            shoe for shoe in shoes
            if colors_compatible(shoe["color"], dress["color"])
        ]
        if matching_shoes:
            outfit.append(matching_shoes[0])

        if target_item is not None and target_item["id"] not in {
            item["id"] for item in outfit
        }:
            if colors_compatible(target_item["color"], dress["color"]):
                outfit.append(target_item)
            else:
                continue

        results.append(outfit)
        # Убираем повторяющиеся комплекты и возвращаем первые несколько.
    unique_results = []
    seen = set()
    for outfit in results:
        key = tuple(sorted(item["id"] for item in outfit))
        if key not in seen:
            seen.add(key)
            unique_results.append(outfit)

    return unique_results[:limit]


def days_since_last_worn(item):
    last_worn = item["last_worn"] or item["date_added"]
    return (date.today() - date.fromisoformat(last_worn)).days


def show_photo(path, width=220):
    if path and Path(path).exists():
        st.image(path, width=width)
    else:
        st.caption(" Фото не добавлено")


def show_outfit(outfit):
    """Показывает комплект карточками с фотографиями и подписями."""
    if not outfit:
        st.caption("В этом образе пока нет вещей.")
        return

    # Не больше трёх вещей в одном ряду — так удобнее смотреть с телефона.
    for start in range(0, len(outfit), 3):
        row_items = outfit[start:start + 3]
        cols = st.columns(len(row_items))

        for col, item in zip(cols, row_items):
            with col:
                photo_path = item["photo_path"]

                if photo_path and Path(photo_path).exists():
                    st.image(photo_path, width=220)
                else:
                    st.info("Для этой вещи пока нет фото")

                st.caption(
                    f"**{item['name']}**\n\n"
                    f"{item['category']} · {item['color']}"
                )


# ---------- Запуск ----------
init_db()
clothes = get_clothes()

st.sidebar.markdown("## Умный шкаф")
st.sidebar.caption("Твой гардероб — с умом")
page = st.sidebar.radio(
    "Раздел",
    [
        "Главная",
        "Мой гардероб",
        "Подобрать образ",
        "Перед покупкой",
        "Пора надеть",
        "Мои образы",
    ],
)
st.sidebar.markdown("---")
st.sidebar.markdown(
    f"<span class='tag'>Plum · Cherry · Butter</span>",
    unsafe_allow_html=True,
)
st.sidebar.caption("Данные хранятся в локальной базе wardrobe.db")


# ---------- Главная ----------
if page == "Главная":
    st.markdown(
        """
        <div class="hero">
          <h1>Твой гардероб. Твои решения.</h1>
          <p>Собирай образы, возвращай забытые вещи и покупай осознанно.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    forgotten = [item for item in clothes if days_since_last_worn(item) >= 30]
    c1, c2, c3 = st.columns(3)
    c1.metric("Вещей в гардеробе", len(clothes))
    c2.metric("Давно не надевались", len(forgotten))
    c3.metric("Сохранённых образов", len(get_outfits()))

    st.subheader("Что умеет приложение")
    col1, col2 = st.columns(2)
    col1.info(
        "**Мой гардероб**\n\n"
        "Добавляй фотографии, категории, цвета, сезоны и поводы."
    )
    col2.info(
        "**Подбор образа**\n\n"
        "Получай простые варианты сочетаний из уже добавленных вещей."
    )
    col3, col4 = st.columns(2)
    col3.info(
        "**Пора надеть**\n\n"
        "Находи вещи, которые давно не отмечались как надетые."
    )
    col4.info(
        "**Перед покупкой**\n\n"
        "Проверяй, есть ли похожая вещь и с чем сочетать обновку."
    )

    if forgotten:
        st.subheader("Можно вернуть в образы")
        for item in forgotten[:3]:
            st.write(
                f"• **{item['name']}** — "
                f"{days_since_last_worn(item)} дн. без отметки о носке"
            )


# ---------- Гардероб ----------
elif page == "Мой гардероб":
    st.title("Мой гардероб")
    st.caption("Добавляй вещи — так подсказки приложения станут полезнее.")

    with st.expander("＋ Добавить вещь", expanded=(len(clothes) == 0)):
        with st.form("add_clothing_form", clear_on_submit=True):
            name = st.text_input(
                "Название вещи *",
                placeholder="Например, белая рубашка",
            )
            col1, col2 = st.columns(2)

            with col1:
                category = st.selectbox("Категория", CATEGORIES)
                color = st.text_input(
                    "Основной цвет *",
                    placeholder="Например, белый",
                )
                season = st.selectbox("Сезон", SEASONS)

            with col2:
                photo = st.file_uploader(
                    "Фотография",
                    type=["jpg", "jpeg", "png", "webp"],
                )
                occasions = st.multiselect(
                    "Для каких поводов подходит",
                    OCCASIONS,
                )
                notes = st.text_area(
                    "Заметки",
                    placeholder="Материал, стиль, с чем сочетается…",
                )

            submitted = st.form_submit_button("Сохранить вещь")

            if submitted:
                if not name.strip() or not color.strip():
                    st.error("Заполни название и цвет вещи.")
                else:
                    photo_path = save_photo(photo)
                    add_clothing(
                        name, category, color, season, notes,
                        photo_path, occasions,
                    )
                    st.success("Вещь добавлена!")
                    st.rerun()

    if not clothes:
        st.info("Пока гардероб пуст. Добавь первую вещь выше.")
    else:
        f1, f2 = st.columns(2)
        with f1:
            category_filter = st.selectbox(
                "Фильтр по категории",
                ["Все"] + sorted({item["category"] for item in clothes}),
            )
        with f2:
            search = st.text_input("Поиск по названию или цвету")

        filtered = [
            item for item in clothes
            if (category_filter == "Все"
                or item["category"] == category_filter)
            and search.casefold() in (
                item["name"] + " " + item["color"]
            ).casefold()
        ]

        st.caption(f"Показано вещей: {len(filtered)}")
        cols = st.columns(3)

        for index, item in enumerate(filtered):
            with cols[index % 3]:
                with st.container(border=True):
                    show_photo(item["photo_path"], 240)
                    st.subheader(item["name"])
                    st.caption(
                        f"{item['category']} · {item['color']} · "
                        f"{item['season']}"
                    )

                    if item["occasions"]:
                        st.caption(f"Поводы: {item['occasions']}")
                    if item["notes"]:
                        st.write(item["notes"])
                        with st.expander("Редактировать вещь"):
                            with st.form(f"edit_clothing_{item['id']}"):
                                edited_name = st.text_input(
                                    "Название",
                                    value=item["name"],
                                    key=f"edit_name_{item['id']}",)
                                category_index = (
                                    CATEGORIES.index(item["category"])
                                    if item["category"] in CATEGORIES else 0
                                )
                                edited_category = st.selectbox(
                                    "Категория",
                                    CATEGORIES,
                                    index=category_index,
                                    key=f"edit_category_{item['id']}",
                                )
                                edited_color = st.text_input(
                                    "Цвет",
                                    value=item["color"],
                                    key=f"edit_color_{item['id']}",
                                )
                                season_index = (
                                    SEASONS.index(item["season"])
                                    if item["season"] in SEASONS else 0
                                )
                                edited_season = st.selectbox(
                                    "Сезон",
                                    SEASONS,
                                    index=season_index,
                                    key=f"edit_season_{item['id']}",
                                )
                                old_occasions = [
                                    value.strip()
                                    for value in (item["occasions"] or "").split(",")
                                    if value.strip()
                                ]
                                edited_occasions = st.multiselect(
                                    "Для каких поводов подходит",
                                    OCCASIONS,
                                    default=[x for x in old_occasions if x in OCCASIONS],
                                    key=f"edit_occasions_{item['id']}",
                                )
                                edited_notes = st.text_area(
                                    "Заметки",
                                    value=item["notes"] or "",
                                    key=f"edit_notes_{item['id']}",
                                )
                                replacement_photo = st.file_uploader(
                                    "Новое фото (необязательно)",
                                    type=["jpg", "jpeg", "png", "webp"],
                                    key=f"edit_photo_{item['id']}",
                                )
                                save_edit = st.form_submit_button("Сохранить изменения")
                                if save_edit:
                                    if not edited_name.strip() or not edited_color.strip():
                                        st.error("Название и цвет не должны быть пустыми.")
                                    else:
                                        new_photo_path = (
                                            save_photo(replacement_photo)
                                            if replacement_photo is not None
                                            else None
                                        )
                                        update_clothing(
                                            item["id"]
                                            edited_name,
                                            edited_category,
                                            edited_color,
                                            edited_season,
                                            edited_notes,
                                            edited_occasions,
                                            new_photo_path,
                                        )
                                        st.success("Изменения сохранены.")
                                        st.rerun()
                                        last_text = item["last_worn"] or "Пока не отмечено"
                                        st.caption(f"Последняя носка: {last_text}")
                                        if st.button(
                                            "Надела сегодня",
                                            key=f"worn_{item['id']}",
                                            use_container_width=True,
                                        ):
                                            mark_worn(item["id"])
                                            st.rerun()
                                        if st.button
                                            "Удалить вещь",
                                            key=f"delete_{item['id']}",
                                            use_container_width=True,
                                        ):
                                            delete_clothing(item["id"])
                                            st.rerun()


# ---------- Подбор образа ----------
elif page == "Подобрать образ":
    st.title("Подобрать образ")
    st.write(
        "Приложение предлагает сочетания по категориям, цветам и выбранному поводу."
    )

    if len(clothes) < 2:
        st.info("Добавь в гардероб хотя бы две вещи.")
    else:
        occasion = st.selectbox("Повод", OCCASIONS)
        suggestions = suggest_outfits(clothes, occasion)

        if not suggestions:
            st.warning(
                "Пока не удалось собрать комплект. Добавь вещи разных "
                "категорий — например, верх и низ."
            )
        else:
            st.subheader("Варианты из твоего гардероба")
            for index, outfit in enumerate(suggestions, start=1):
                with st.container(border=True):
                    st.markdown(f"**Вариант {index}**")
                    show_outfit(outfit)

                    outfit_name = st.text_input(
                        "Название комплекта",
                        value=f"{occasion}: вариант {index}",
                        key=f"outfit_name_{index}",
                    )
                    if st.button(
                        "Сохранить этот образ",
                        key=f"save_suggested_{index}",
                    ):
                        save_outfit(
                            outfit_name,
                            [item["id"] for item in outfit],
                        )
                        st.success("Образ сохранён!")
                        st.rerun()


# ---------- Перед покупкой ----------
elif page == "Перед покупкой":
    st.title("Перед покупкой")
    st.write(
        "Проверь, нет ли похожей вещи и с чем покупка может сочетаться. "
        "Это ориентир, а не гарантия идеального выбора."
    )

    with st.form("purchase_form"):
        purchase_name = st.text_input(
            "Что хочешь купить?",
            placeholder="Например, бежевый кардиган",
        )
        col1, col2 = st.columns(2)

        with col1:
            purchase_category = st.selectbox(
                "Категория",
                CATEGORIES,
                key="purchase_category",
            )
            purchase_color = st.text_input(
                "Цвет",
                placeholder="Например, бежевый",
            )
            price = st.number_input(
                "Цена покупки, ₽",
                min_value=0,
                value=3500,
                step=500,
                )

        with col2:
            budget = st.number_input(
                "Бюджет на покупку, ₽",
                min_value=0,
                value=5000,
                step=500,
            )
            occasion = st.selectbox(
                "Для какого повода нужна вещь?",
                OCCASIONS,
                key="purchase_occasion",
            )

        reason = st.text_area(
            "Зачем тебе эта вещь?",
            placeholder="Например, нужна одежда для учёбы.",
        )
        purchase_submitted = st.form_submit_button("Проверить покупку")

    if purchase_submitted:
        if not purchase_name.strip():
            st.error("Напиши название вещи.")
        else:
            # Вещи той же категории показываются как возможные дубли.
            same_category = [
                item for item in clothes
                if item["category"] == purchase_category
            ]

            if purchase_color.strip():
                same_category.sort(
                    key=lambda item: not same_color_family(
                        item["color"], purchase_color
                    )
                )

            st.subheader("Рекомендация")
            score = 0

            if price <= budget:
                st.success("Цена укладывается в указанный бюджет.")
                score += 1
            else:
                st.warning("Цена выше указанного бюджета.")

            if same_category:
                st.warning(
                    f"В гардеробе есть {len(same_category)} вещ. "
                    "той же категории — проверь, не будет ли это дублем."
                )
                st.markdown("**Что уже есть:**")
                for item in same_category[:5]:
                    st.write(
                        f"• {item['name']} — {item['color']} "
                        f"({item['category']})"
                    )
            else:
                st.success("Вещей этой категории в гардеробе пока нет.")
                score += 1

            # Показываем, какие имеющиеся вещи могут сочетаться с покупкой.
            compatible_items = [
                item for item in clothes
                if item["category"] != purchase_category
                and colors_compatible(item["color"], purchase_color)
                and fits_occasion(item, occasion)
            ] if purchase_color.strip() else []

            if compatible_items:
                st.markdown(
                    f"**Из гардероба может подойти к покупке "
                    f"для повода «{occasion}»:**"
                )
                for item in compatible_items[:5]:
                    st.write(f"• {item['name']} — {item['color']}")

            if reason.strip():
                st.info(
                    "Ты указала цель покупки. Проверь, действительно ли "
                    "эта вещь решает нужную задачу."
                )

            if score == 2:
                st.success("Покупку можно рассмотреть.")
            elif score == 0:
                st.info("Сравни плюсы и минусы перед решением.")

            st.caption(
                "Приложение сравнивает введённые категории и названия цветов. "
                "Фотографии автоматически не распознаются."
            )


# ---------- Напоминания ----------
elif page == "Пора надеть":
    st.title("Пора надеть")
    st.write(
        "Здесь собраны вещи, которые не отмечались как надетые "
        "30 дней или дольше."
    )

    forgotten = [
        item for item in clothes
        if days_since_last_worn(item) >= 30
    ]
    forgotten.sort(key=days_since_last_worn, reverse=True)

    if not forgotten:
        st.success(
            "Пока нет вещей для напоминания. Отмечай вещи после носки, "
            "чтобы напоминания были точнее."
        )
    else:
        occasion = st.selectbox(
            "Подобрать сочетания для повода",
            OCCASIONS,
            key="reminder_occasion",
        )

        for item in forgotten:
            with st.container(border=True):
                col1, col2 = st.columns([1, 2])

                with col1:
                    show_photo(item["photo_path"], 180)

                with col2:
                    st.subheader(item["name"])
                    st.caption(
                        f"{item['category']} · {item['color']} · "
                        f"{item['season']}"
                    )
                    st.write(
                        f"Не отмечалась как надетая "
                        f"**{days_since_last_worn(item)} дней**."
                    )

                    ideas = suggest_outfits(
                        clothes,
                        occasion,
                        target_item=item,
                        limit=3,
                    )

                    if ideas:
                        st.markdown("**Идеи сочетаний:**")
                        for outfit in ideas:
                            show_outfit(outfit)
                    else:
                        st.write(
                            "Пока нет подходящего готового сочетания. "
                            "Попробуй добавить вещи других категорий."
                        )

                    if st.button(
                        "Отметить как надетую сегодня",
                        key=f"reminder_worn_{item['id']}",
                    ):
                        mark_worn(item["id"])
                        st.rerun()


# ---------- Сохранённые образы ----------
elif page == "Мои образы":
    st.title("Мои образы")

    outfits = get_outfits()
    if not outfits:
        st.info(
            "Сохранённых образов пока нет. Создай их в разделе "
            "«Подобрать образ»."
        )
    else:
        clothes_by_id = {item["id"]: item for item in clothes}

       labels = {
    f"{item['name']} — {item['color']} ({item['category']}) · ID {item['id']}":
    item["id"]
    for item in clothes
}
for outfit in outfits:
    with st.container(border=True):
        st.subheader(outfit["name"])
        st.caption(f"Создан: {outfit['created_at']}")

        item_ids = [
            int(value)
            for value in outfit["item_ids"].split(",")
            if value
        ]
        saved_items = [
            clothes_by_id[item_id]
            for item_id in item_ids
            if item_id in clothes_by_id
        ]

        if saved_items:
            show_outfit(saved_items)
        else:
            st.write("Вещи из этого образа уже удалены из гардероба.")

        with st.expander("Редактировать образ"):
            with st.form(f"edit_outfit_{outfit['id']}"):
                edited_outfit_name = st.text_input(
                    "Название образа",
                    value=outfit["name"],
                    key=f"edit_outfit_name_{outfit['id']}",
                )

                current_labels = [
                    label
                    for label, clothing_id in labels.items()
                    if clothing_id in item_ids
                ]

                selected_labels = st.multiselect(
                    "Вещи в образе",
                    options=list(labels.keys()),
                    default=current_labels,
                    key=f"edit_outfit_items_{outfit['id']}",
                )

                save_outfit_edit = st.form_submit_button(
                    "Сохранить образ"
                )

                if save_outfit_edit:
                    selected_ids = [
                        labels[label] for label in selected_labels
                    ]

                    if not edited_outfit_name.strip():
                        st.error("Укажи название образа.")
                    elif len(selected_ids) < 2:
                        st.error("Выбери минимум две вещи.")
                    else:
                        update_outfit(
                            outfit["id"],
                            edited_outfit_name,
                            selected_ids,
                        )
                        st.success("Образ обновлён.")
                        st.rerun()

        if st.button(
            "Удалить образ",
            key=f"delete_outfit_{outfit['id']}",
        ):
            delete_outfit(outfit["id"])
            st.rerun()
