import hashlib
import sqlite3
import uuid
from datetime import date
from io import BytesIO
from pathlib import Path

import streamlit as st
from PIL import Image


# ---------- Пути и настройки ----------
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

OCCASIONS = [
    "Повседневный",
    "Учёба / работа",
    "Праздник",
    "Спорт",
    "Прогулка",
]


# ---------- База данных ----------
def connect_db():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def init_db():
    """Создаёт таблицы и добавляет поля, если база уже существовала."""
    with connect_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS clothes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                color TEXT NOT NULL,
                season TEXT NOT NULL,
                notes TEXT DEFAULT '',
                photo_path TEXT DEFAULT '',
                date_added TEXT NOT NULL,
                occasions TEXT DEFAULT '',
                last_worn TEXT
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS outfits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                name TEXT NOT NULL,
                item_ids TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )

        # Добавляем колонки в старую базу, если их ещё нет.
        for table, column, definition in [
            ("clothes", "user_id", "TEXT"),
            ("clothes", "occasions", "TEXT DEFAULT ''"),
            ("clothes", "last_worn", "TEXT"),
            ("outfits", "user_id", "TEXT"),
        ]:
            columns = {
                row[1]
                for row in conn.execute(
                    f"PRAGMA table_info({table})"
                ).fetchall()
            }

            if column not in columns:
                conn.execute(
                    f"ALTER TABLE {table} ADD COLUMN {column} {definition}"
                )


def get_clothes(user_id):
    with connect_db() as conn:
        conn.row_factory = sqlite3.Row
        return conn.execute(
            """
            SELECT * FROM clothes
            WHERE user_id = ?
            ORDER BY id DESC
            """,
            (user_id,),
        ).fetchall()


def get_outfits(user_id):
    with connect_db() as conn:
        conn.row_factory = sqlite3.Row
        return conn.execute(
            """
            SELECT * FROM outfits
            WHERE user_id = ?
            ORDER BY id DESC
            """,
            (user_id,),
        ).fetchall()


# ---------- Фотографии ----------
def user_upload_dir(user_id):
    """Создаёт отдельную папку фотографий для пользователя."""
    user_hash = hashlib.sha256(user_id.encode("utf-8")).hexdigest()[:20]
    folder = UPLOAD_DIR / user_hash
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def save_photo(uploaded_file, user_id, remove_background=True):
    """
    Сохраняет загруженную фотографию в PNG.
    Если remove_background=True, пытается удалить фон через rembg.
    """
    if uploaded_file is None:
        return ""

    image_bytes = uploaded_file.getvalue()

    if remove_background:
        from rembg import remove

        image_bytes = remove(image_bytes)

    image = Image.open(BytesIO(image_bytes)).convert("RGBA")

    filename = f"{uuid.uuid4().hex}.png"
    path = user_upload_dir(user_id) / filename

    image.save(path, format="PNG")
    return str(path)


def delete_photo_file(path):
    if not path:
        return

    try:
        Path(path).unlink(missing_ok=True)
    except OSError:
        pass


# ---------- Вещи ----------
def add_clothing(
    user_id,
    name,
    category,
    color,
    season,
    notes,
    occasions,
    photo_path,
):
    with connect_db() as conn:
        conn.execute(
            """
            INSERT INTO clothes
            (user_id, name, category, color, season, notes,
             photo_path, date_added, occasions)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                name.strip(),
                category,
                color.strip(),
                season,
                notes.strip(),
                photo_path,
                date.today().isoformat(),
                ", ".join(occasions),
            ),
        )


def update_clothing(
    user_id,
    item_id,
    name,
    category,
    color,
    season,
    notes,
    occasions,
    new_photo_path=None,
):
    with connect_db() as conn:
        old_row = conn.execute(
            """
            SELECT photo_path FROM clothes
            WHERE id = ? AND user_id = ?
            """,
            (item_id, user_id),
        ).fetchone()

        if not old_row:
            return False

        if new_photo_path is None:
            conn.execute(
                """
                UPDATE clothes
                SET name = ?, category = ?, color = ?, season = ?,
                    notes = ?, occasions = ?
                WHERE id = ? AND user_id = ?
                """,
                (
                    name.strip(),
                    category,
                    color.strip(),
                    season,
                    notes.strip(),
                    ", ".join(occasions),
                    item_id,
                    user_id,
                ),
            )
        else:
            conn.execute(
                """
                UPDATE clothes
                SET name = ?, category = ?, color = ?, season = ?,
                    notes = ?, occasions = ?, photo_path = ?
                WHERE id = ? AND user_id = ?
                """,
                (
                    name.strip(),
                    category,
                    color.strip(),
                    season,
                    notes.strip(),
                    ", ".join(occasions),
                    new_photo_path,
                    item_id,
                    user_id,
                ),
            )

    # Старое фото удаляем только после успешной замены.
    if new_photo_path and old_row[0]:
        delete_photo_file(old_row[0])

    return True


def delete_clothing(user_id, item_id):
    with connect_db() as conn:
        row = conn.execute(
            """
            SELECT photo_path FROM clothes
            WHERE id = ? AND user_id = ?
            """,
            (item_id, user_id),
        ).fetchone()

        conn.execute(
            "DELETE FROM clothes WHERE id = ? AND user_id = ?",
            (item_id, user_id),
        )

    if row:
        delete_photo_file(row[0])


# ---------- Образы ----------
def parse_item_ids(value):
    if not value:
        return []

    result = []
    for part in value.split(","):
        part = part.strip()
        if part.isdigit():
            result.append(int(part))
    return result


def user_owns_items(user_id, item_ids):
    if not item_ids:
        return False

    placeholders = ",".join("?" for _ in item_ids)

    with connect_db() as conn:
        rows = conn.execute(
            f"""
            SELECT id FROM clothes
            WHERE user_id = ? AND id IN ({placeholders})
            """,
            [user_id, *item_ids],
        ).fetchall()

    return len(rows) == len(set(item_ids))


def save_outfit(user_id, name, item_ids):
    item_ids = list(dict.fromkeys(item_ids))

    if len(item_ids) < 2:
        raise ValueError("Для образа выбери хотя бы две вещи.")

    if not user_owns_items(user_id, item_ids):
        raise ValueError("Некоторые вещи не найдены в твоём гардеробе.")

    with connect_db() as conn:
        conn.execute(
            """
            INSERT INTO outfits (user_id, name, item_ids, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                user_id,
                name.strip(),
                ",".join(map(str, item_ids)),
                date.today().isoformat(),
            ),
        )


def update_outfit(user_id, outfit_id, name, item_ids):
    item_ids = list(dict.fromkeys(item_ids))

    if len(item_ids) < 2:
        raise ValueError("Для образа выбери хотя бы две вещи.")

    if not user_owns_items(user_id, item_ids):
        raise ValueError("Некоторые вещи не найдены в твоём гардеробе.")

    with connect_db() as conn:
        conn.execute(
            """
            UPDATE outfits
            SET name = ?, item_ids = ?
            WHERE id = ? AND user_id = ?
            """,
            (
                name.strip(),
                ",".join(map(str, item_ids)),
                outfit_id,
                user_id,
            ),
        )


def delete_outfit(user_id, outfit_id):
    with connect_db() as conn:
        conn.execute(
            "DELETE FROM outfits WHERE id = ? AND user_id = ?",
            (outfit_id, user_id),
        )


# ---------- Авторизация ----------
init_db()

if not st.user.is_logged_in:
    st.title("Умный шкаф")
    st.write("Войди, чтобы открыть свой гардероб.")
    st.button("Войти через Google", on_click=st.login)
    st.stop()

user_id = str(st.user.sub)
user_email = st.user.get("email", "пользователь")

st.sidebar.title("Умный шкаф")
st.sidebar.caption(f"Вошли как: {user_email}")

if st.sidebar.button("Выйти"):
    st.logout()

page = st.sidebar.radio(
    "Раздел",
    ["Мой гардероб", "Создать образ", "Мои образы"],
)

clothes = get_clothes(user_id)
outfits = get_outfits(user_id)


# ---------- Мой гардероб ----------
if page == "Мой гардероб":
    st.title("Мой гардероб")

    with st.expander("Добавить вещь", expanded=(len(clothes) == 0)):
        with st.form("add_clothing_form", clear_on_submit=True):
            name = st.text_input("Название вещи")
            category = st.selectbox("Категория", CATEGORIES)
            color = st.text_input("Цвет")
            season = st.selectbox("Сезон", SEASONS)
            occasions = st.multiselect("Подходящие поводы", OCCASIONS)
            notes = st.text_area("Заметки")

            photo = st.file_uploader(
                "Фото вещи",
                type=["jpg", "jpeg", "png", "webp"],
            )
            remove_bg = st.checkbox("Удалить фон у фото", value=True)

            submitted = st.form_submit_button("Добавить вещь")

        if submitted:
            if not name.strip() or not color.strip():
                st.error("Укажи название и цвет вещи.")
            else:
                try:
                    photo_path = save_photo(
                        photo,
                        user_id,
                        remove_background=remove_bg,
                    )
                    add_clothing(
                        user_id,
                        name,
                        category,
                        color,
                        season,
                        notes,
                        occasions,
                        photo_path,
                    )
                    st.success("Вещь добавлена.")
                    st.rerun()
                except Exception as error:
                    st.error(f"Не удалось обработать фото: {error}")

    if not clothes:
        st.info("Гардероб пока пуст. Добавь первую вещь выше.")
    else:
        st.write(f"Вещей в гардеробе: **{len(clothes)}**")

        for item in clothes:
            with st.container(border=True):
                if item["photo_path"] and Path(item["photo_path"]).exists():
                    st.image(item["photo_path"], width=220)

                st.subheader(item["name"])
                st.caption(
                    f"{item['category']} · {item['color']} · {item['season']}"
                )

                if item["occasions"]:
                    st.write(f"Поводы: {item['occasions']}")
                if item["notes"]:
                    st.write(item["notes"])

                with st.expander("Изменить вещь"):
                    with st.form(f"edit_clothing_{item['id']}"):
                        new_name = st.text_input(
                            "Название",
                            value=item["name"],
                        )

                        old_category = item["category"]
                        category_index = (
                            CATEGORIES.index(old_category)
                            if old_category in CATEGORIES
                            else 0
                        )
                        new_category = st.selectbox(
                            "Категория",
                            CATEGORIES,
                            index=category_index,
                        )

                        new_color = st.text_input(
                            "Цвет",
                            value=item["color"],
                        )

                        old_season = item["season"]
                        season_index = (
                            SEASONS.index(old_season)
                            if old_season in SEASONS
                            else 0
                        )
                        new_season = st.selectbox(
                            "Сезон",
                            SEASONS,
                            index=season_index,
                        )

                        old_occasions = [
                            value.strip()
                            for value in (item["occasions"] or "").split(",")
                            if value.strip()
                        ]
                        new_occasions = st.multiselect(
                            "Подходящие поводы",
                            OCCASIONS,
                            default=[
                                value
                                for value in old_occasions
                                if value in OCCASIONS
                            ],
                        )

                        new_notes = st.text_area(
                            "Заметки",
                            value=item["notes"] or "",
                        )

                        new_photo = st.file_uploader(
                            "Заменить фото (необязательно)",
                            type=["jpg", "jpeg", "png", "webp"],
                            key=f"photo_{item['id']}",
                        )
                        remove_new_bg = st.checkbox(
                            "Удалить фон у нового фото",
                            value=True,
                            key=f"remove_bg_{item['id']}",
                        )

                        save_changes = st.form_submit_button("Сохранить")

                    if save_changes:
                        if not new_name.strip() or not new_color.strip():
                            st.error("Название и цвет не должны быть пустыми.")
                        else:
                            try:
                                new_photo_path = None

                                if new_photo is not None:
                                    new_photo_path = save_photo(
                                        new_photo,
                                        user_id,
                                        remove_background=remove_new_bg,
                                    )

                                update_clothing(
                                    user_id,
                                    item["id"],
                                    new_name,
                                    new_category,
                                    new_color,
                                    new_season,
                                    new_notes,
                                    new_occasions,
                                    new_photo_path,
                                )
                                st.success("Изменения сохранены.")
                                st.rerun()
                            except Exception as error:
                                st.error(f"Не удалось сохранить изменения: {error}")

                if st.button(
                    "Удалить вещь",
                    key=f"delete_clothing_{item['id']}",
                ):
                    delete_clothing(user_id, item["id"])
                    st.rerun()


# ---------- Создать образ ----------
elif page == "Создать образ":
    st.title("Создать образ")

    if len(clothes) < 2:
        st.info("Сначала добавь в гардероб хотя бы две вещи.")
    else:
        label_to_id = {
            f"{item['name']} — {item['color']} ({item['category']}) · ID {item['id']}":
            item["id"]
            for item in clothes
        }

        with st.form("create_outfit_form"):
            outfit_name = st.text_input("Название образа")
            selected_labels = st.multiselect(
                "Выбери вещи",
                options=list(label_to_id.keys()),
            )
            submitted = st.form_submit_button("Сохранить образ")

        if submitted:
            if not outfit_name.strip():
                st.error("Укажи название образа.")
            else:
                selected_ids = [
                    label_to_id[label] for label in selected_labels
                ]

                try:
                    save_outfit(user_id, outfit_name, selected_ids)
                    st.success("Образ сохранён.")
                    st.rerun()
                except ValueError as error:
                    st.error(str(error))


# ---------- Мои образы ----------
elif page == "Мои образы":
    st.title("Мои образы")

    if not outfits:
        st.info("Сохранённых образов пока нет.")
    else:
        clothes_by_id = {
            item["id"]: item
            for item in clothes
        }

        label_to_id = {
            f"{item['name']} — {item['color']} ({item['category']}) · ID {item['id']}":
            item["id"]
            for item in clothes
        }

        id_to_label = {
            item_id: label
            for label, item_id in label_to_id.items()
        }

        for outfit in outfits:
            with st.container(border=True):
                st.subheader(outfit["name"])
                st.caption(f"Создан: {outfit['created_at']}")

                item_ids = parse_item_ids(outfit["item_ids"])
                saved_items = [
                    clothes_by_id[item_id]
                    for item_id in item_ids
                    if item_id in clothes_by_id
                ]

                if saved_items:
                    cols = st.columns(min(len(saved_items), 3))
                    for index, item in enumerate(saved_items):
                        with cols[index % len(cols)]:
                            if (
                                item["photo_path"]
                                and Path(item["photo_path"]).exists()
                            ):
                                st.image(item["photo_path"], width=180)
                            st.caption(
                                f"{item['name']} — "
                                f"{item['category']}, {item['color']}"
                            )
                else:
                    st.write("Вещи из этого образа уже удалены.")

                with st.expander("Изменить образ"):
                    with st.form(f"edit_outfit_{outfit['id']}"):
                        edited_name = st.text_input(
                            "Название образа",
                            value=outfit["name"],
                        )

                        current_labels = [
                            id_to_label[item_id]
                            for item_id in item_ids
                            if item_id in id_to_label
                        ]

                        selected_labels = st.multiselect(
                            "Вещи в образе",
                            options=list(label_to_id.keys()),
                            default=current_labels,
                        )

                        save_changes = st.form_submit_button("Сохранить образ")

                    if save_changes:
                        if not edited_name.strip():
                            st.error("Укажи название образа.")
                        else:
                            selected_ids = [
                                label_to_id[label]
                                for label in selected_labels
                            ]

                            try:
                                update_outfit(
                                    user_id,
                                    outfit["id"],
                                    edited_name,
                                    selected_ids,
                                )
                                st.success("Образ обновлён.")
                                st.rerun()
                            except ValueError as error:
                                st.error(str(error))

                if st.button(
                    "Удалить образ",
                    key=f"delete_outfit_{outfit['id']}",
                ):
                    delete_outfit(user_id, outfit["id"])
                    st.rerun()
