import streamlit as st
import sqlite3
import uuid
import hashlib
from pathlib import Path
from datetime import date, datetime, timedelta
from PIL import Image
from io import BytesIO

# -------------------- НАСТРОЙКИ --------------------
st.set_page_config(page_title="Smart Closet", page_icon="👗", layout="wide")

DB_PATH = Path("smart_closet.db")
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

CREAM = "#F5EFE5"
PLUM = "#552D43"
CHERRY = "#742D40"
MUTED = "#826A73"

st.markdown(f"""
<style>
.stApp {{ background: {CREAM}; color: #30252A; }}
h1, h2, h3 {{ color: {PLUM} !important; }}
p, label, .stMarkdown {{ color: #30252A; }}
[data-testid="stSidebar"] {{ background: #E9DED2; }}
.stButton > button {{ background: {PLUM}; color: white; border: 0; border-radius: 12px; }}
.stButton > button:hover {{ background: {CHERRY}; color: white; border: 0; }}
div[data-testid="stMetric"] {{ background: #E9DED2; padding: 14px; border-radius: 14px; }}
</style>
""", unsafe_allow_html=True)

# -------------------- БАЗА ДАННЫХ --------------------
def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with db() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS items (
            id TEXT PRIMARY KEY, user_id TEXT, name TEXT, category TEXT,
            occasion TEXT, color TEXT, season TEXT, notes TEXT,
            image_path TEXT, last_worn TEXT, created_at TEXT
        )""")
        con.execute("""CREATE TABLE IF NOT EXISTS outfits (
            id TEXT PRIMARY KEY, user_id TEXT, name TEXT, occasion TEXT,
            item_ids TEXT, notes TEXT, image_path TEXT, created_at TEXT
        )""")
        con.execute("""CREATE TABLE IF NOT EXISTS purchases (
            id TEXT PRIMARY KEY, user_id TEXT, name TEXT, category TEXT,
            price REAL, reason TEXT, decision TEXT, created_at TEXT
        )""")

def rows(query, params=()):
    with db() as con:
        return con.execute(query, params).fetchall()

def execute(query, params=()):
    with db() as con:
        con.execute(query, params)

init_db()

# -------------------- ВХОД GOOGLE --------------------
def login_screen():
    st.title("smart closet")
    st.caption("YOUR PERSONAL WARDROBE")
    st.write("Войди через Google, чтобы открыть свой личный гардероб.")
    st.info("Для входа настрой Google OAuth в файле `.streamlit/secrets.toml` (инструкция в README).")
    if st.button("Продолжить через Google", use_container_width=True):
        st.login()

if not st.user.is_logged_in:
    login_screen()
    st.stop()

# У каждого аккаунта собственный идентификатор и папка с фотографиями.
user_email = str(st.user.get("email", ""))
user_id = hashlib.sha256(user_email.lower().encode("utf-8")).hexdigest()[:24]
user_dir = UPLOAD_DIR / user_id
user_dir.mkdir(parents=True, exist_ok=True)
display_name = st.user.get("name", "Пользователь")

# -------------------- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ --------------------
CATEGORIES = ["Верх", "Низ", "Платья и комбинезоны", "Обувь", "Верхняя одежда",
              "Сумки", "Аксессуары", "Другое"]
OCCASIONS = ["Учёба", "Прогулка", "Во двор", "Праздник", "Спорт", "Повседневное", "Другое"]

def save_image(uploaded, remove_bg=False):
    if uploaded is None:
        return None
    image = Image.open(uploaded).convert("RGBA")
    if remove_bg:
        try:
            from rembg import remove
            image = remove(image)
        except Exception:
            st.warning("Удаление фона недоступно. Установи rembg и повтори попытку.")
    filename = f"{uuid.uuid4().hex}.png"
    path = user_dir / filename
    image.save(path, format="PNG")
    return str(path)

def show_image(path, width=220):
    if path and Path(path).exists():
        st.image(path, width=width)

def get_items():
    return rows("SELECT * FROM items WHERE user_id=? ORDER BY created_at DESC", (user_id,))

def get_outfits():
    return rows("SELECT * FROM outfits WHERE user_id=? ORDER BY created_at DESC", (user_id,))

def item_name(item_id):
    found = rows("SELECT name FROM items WHERE id=? AND user_id=?", (item_id, user_id))
    return found[0]["name"] if found else "Удалённая вещь"

def stylist_tip(selected_items):
    if not selected_items:
        return "Добавь вещи в гардероб — и я помогу собрать сочетание."
    colors = [x["color"].lower() for x in selected_items if x["color"]]
    if len(set(colors)) == 1 and len(colors) > 1:
        return "В комплекте много одного цвета. Попробуй добавить нейтральный оттенок."
    if len(selected_items) == 1:
        return "Добавь ещё одну вещь или аксессуар, чтобы завершить комплект."
    return "Попробуй повторить один цвет в двух элементах образа — так комплект будет выглядеть цельнее."

# -------------------- НАВИГАЦИЯ --------------------
st.sidebar.title("smart closet")
st.sidebar.caption(f"Привет, {display_name}!")
page = st.sidebar.radio("Меню", [
    "Главная", "Мой гардероб", "Добавить вещь", "Мои образы",
    "Создать образ", "Перед покупкой", "Стилист"
])
if st.sidebar.button("Выйти из аккаунта"):
    st.logout()

items = get_items()
outfits = get_outfits()

# -------------------- ГЛАВНАЯ --------------------
if page == "Главная":
    st.title("Твой умный шкаф")
    st.write("Всё, что ты носишь, любишь и планируешь купить — в одном месте.")
    a, b, c = st.columns(3)
    a.metric("Вещей в гардеробе", len(items))
    b.metric("Сохранённых образов", len(outfits))
    c.metric("Покупок на рассмотрении", len(rows(
        "SELECT id FROM purchases WHERE user_id=? AND decision='Думаю'", (user_id,))))
    st.subheader("Совет стилиста")
    st.success("Необязательно покупать новое: иногда новый образ получается из уже знакомых вещей.")
    st.subheader("Пора вспомнить")
    cutoff = (date.today() - timedelta(days=30)).isoformat()
    old_items = [x for x in items if not x["last_worn"] or x["last_worn"] < cutoff]
    if old_items:
        st.write("Эти вещи давно не отмечались как надетые:")
        for x in old_items[:8]:
            st.write(f"• **{x['name']}** — {x['last_worn'] or 'ещё не отмечали'}")
    else:
        st.write("Пока все вещи в актуальном использовании. Так держать!")
    st.caption("Напоминания отображаются внутри приложения при следующем входе.")

# -------------------- ГАРДЕРОБ --------------------
elif page == "Мой гардероб":
    st.title("Мой гардероб")
    f1, f2 = st.columns(2)
    category_filter = f1.selectbox("Категория", ["Все"] + CATEGORIES)
    occasion_filter = f2.selectbox("Для чего", ["Все"] + OCCASIONS)
    filtered = [x for x in items
                if (category_filter == "Все" or x["category"] == category_filter)
                and (occasion_filter == "Все" or x["occasion"] == occasion_filter)]
    if not filtered:
        st.info("Пока здесь пусто. Добавь первую вещь!")
    for x in filtered:
        with st.expander(f"{x['name']} · {x['category']}"):
            col1, col2 = st.columns([1, 2])
            with col1:
                show_image(x["image_path"])
            with col2:
                st.write(f"**Ситуация:** {x['occasion']}")
                st.write(f"**Цвет:** {x['color'] or 'Не указан'}")
                st.write(f"**Сезон:** {x['season'] or 'Любой'}")
                st.write(f"**Заметки:** {x['notes'] or 'Нет'}")
                st.write(f"**Последний раз надевала:** {x['last_worn'] or 'Не отмечено'}")
            with st.form(f"edit_item_{x['id']}"):
                st.markdown("**Изменить вещь**")
                new_name = st.text_input("Название", x["name"])
                new_category = st.selectbox("Категория", CATEGORIES,
                    index=CATEGORIES.index(x["category"]) if x["category"] in CATEGORIES else 0)
                new_occasion = st.selectbox("Для чего", OCCASIONS,
                    index=OCCASIONS.index(x["occasion"]) if x["occasion"] in OCCASIONS else 0)
                new_color = st.text_input("Цвет", x["color"] or "")
                new_season = st.text_input("Сезон", x["season"] or "")
                new_notes = st.text_area("Заметки", x["notes"] or "")
                new_date = st.date_input("Последний раз надевала",
                    value=date.fromisoformat(x["last_worn"]) if x["last_worn"] else date.today())
                replacement = st.file_uploader("Заменить фото (необязательно)", type=["png", "jpg", "jpeg"],
                                               key=f"replace_{x['id']}")
                remove_bg = st.checkbox("Убрать фон у нового фото", key=f"bg_edit_{x['id']}")
                save = st.form_submit_button("Сохранить изменения")
                if save:
                    path = save_image(replacement, remove_bg) if replacement else x["image_path"]
                    execute("""UPDATE items SET name=?, category=?, occasion=?, color=?, season=?,
                               notes=?, last_worn=?, image_path=? WHERE id=? AND user_id=?""",
                            (new_name, new_category, new_occasion, new_color, new_season,
                             new_notes, new_date.isoformat(), path, x["id"], user_id))
                    st.success("Вещь обновлена.")
                    st.rerun()
            if st.button("Удалить вещь", key=f"delete_item_{x['id']}"):
                execute("DELETE FROM items WHERE id=? AND user_id=?", (x["id"], user_id))
                if x["image_path"] and Path(x["image_path"]).exists():
                    Path(x["image_path"]).unlink()
                st.rerun()
            if st.button("Отметить как надетую сегодня", key=f"worn_{x['id']}"):
                execute("UPDATE items SET last_worn=? WHERE id=? AND user_id=?",
                        (date.today().isoformat(), x["id"], user_id))
                st.rerun()

# -------------------- ДОБАВИТЬ ВЕЩЬ --------------------
elif page == "Добавить вещь":
    st.title("Добавить новую вещь")
    with st.form("add_item_form"):
        name = st.text_input("Название вещи", placeholder="Например, сливовый кардиган")
        category = st.selectbox("Категория", CATEGORIES)
        occasion = st.selectbox("Для чего?", OCCASIONS)
        color = st.text_input("Цвет")
        season = st.selectbox("Сезон", ["Весна", "Лето", "Осень", "Зима", "Любой"])
        notes = st.text_area("Заметки")
        photo = st.file_uploader("Фотография вещи", type=["png", "jpg", "jpeg"])
        remove_bg = st.checkbox("Попробовать убрать фон с фотографии")
        submitted = st.form_submit_button("Сохранить вещь")
        if submitted:
            if not name.strip():
                st.error("Введи название вещи.")
            else:
                path = save_image(photo, remove_bg)
                execute("""INSERT INTO items VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (uuid.uuid4().hex, user_id, name.strip(), category, occasion,
                         color, season, notes, path, None, datetime.now().isoformat()))
                st.success("Вещь добавлена в гардероб!")
                st.rerun()

# -------------------- ОБРАЗЫ --------------------
elif page == "Мои образы":
    st.title("Мои образы")
    if not outfits:
        st.info("Сохрани свой первый образ на странице «Создать образ».")
    for o in outfits:
        with st.expander(o["name"]):
            show_image(o["image_path"], 300)
            st.write(f"**Ситуация:** {o['occasion']}")
            selected_ids = o["item_ids"].split(",") if o["item_ids"] else []
            st.write("**Вещи:** " + ", ".join(item_name(i) for i in selected_ids))
            st.write(o["notes"] or "")
            with st.form(f"edit_outfit_{o['id']}"):
                new_name = st.text_input("Название образа", o["name"])
                new_occasion = st.selectbox("Ситуация", OCCASIONS,
                    index=OCCASIONS.index(o["occasion"]) if o["occasion"] in OCCASIONS else 0)
                available = {x["id"]: x["name"] for x in items}
                valid_old = [i for i in selected_ids if i in available]
                new_ids = st.multiselect("Вещи", list(available.keys()), default=valid_old,
                    format_func=lambda k: available[k])
                new_notes = st.text_area("Комментарий", o["notes"] or "")
                new_photo = st.file_uploader("Заменить фото образа", type=["png", "jpg", "jpeg"],
                                             key=f"outfit_photo_{o['id']}")
                new_bg = st.checkbox("Убрать фон у нового фото", key=f"outfit_bg_{o['id']}")
                save_outfit = st.form_submit_button("Сохранить изменения")
                if save_outfit:
                    path = save_image(new_photo, new_bg) if new_photo else o["image_path"]
                    execute("""UPDATE outfits SET name=?, occasion=?, item_ids=?, notes=?, image_path=?
                               WHERE id=? AND user_id=?""",
                            (new_name, new_occasion, ",".join(new_ids), new_notes, path, o["id"], user_id))
                    st.success("Образ обновлён.")
                    st.rerun()
            if st.button("Удалить образ", key=f"delete_outfit_{o['id']}"):
                execute("DELETE FROM outfits WHERE id=? AND user_id=?", (o["id"], user_id))
                if o["image_path"] and Path(o["image_path"]).exists():
                    Path(o["image_path"]).unlink()
                st.rerun()

elif page == "Создать образ":
    st.title("Создать образ")
    if not items:
        st.info("Сначала добавь хотя бы одну вещь в гардероб.")
    else:
        available = {x["id"]: x["name"] for x in items}
        with st.form("new_outfit_form"):
            outfit_name = st.text_input("Название образа", placeholder="Например, уютный образ на учёбу")
            occasion = st.selectbox("Куда собираемся?", OCCASIONS)
            chosen = st.multiselect("Выбери вещи", list(available.keys()),
                                    format_func=lambda k: available[k])
            notes = st.text_area("Комментарий или идея")
            photo = st.file_uploader("Фото готового образа (необязательно)",
                                     type=["png", "jpg", "jpeg"])
            remove_bg = st.checkbox("Попробовать убрать фон с фото")
            submitted = st.form_submit_button("Сохранить образ")
            if submitted:
                if not outfit_name.strip():
                    st.error("Дай образу название.")
                else:
                    path = save_image(photo, remove_bg)
                    execute("INSERT INTO outfits VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                            (uuid.uuid4().hex, user_id, outfit_name, occasion,
                             ",".join(chosen), notes, path, datetime.now().isoformat()))
                    st.success("Образ сохранён!")
                    st.rerun()
        st.subheader("Подсказка стилиста")
        chosen_items = [x for x in items if x["id"] in st.session_state.get("chosen_preview", [])]
        st.write(stylist_tip(chosen_items))

# -------------------- ПЕРЕД ПОКУПКОЙ --------------------
elif page == "Перед покупкой":
    st.title("Стоит ли покупать?")
    st.write("Проверь, действительно ли новая вещь нужна твоему гардеробу.")
    with st.form("purchase_form"):
        name = st.text_input("Что хочешь купить?")
        category = st.selectbox("Категория", CATEGORIES)
        price = st.number_input("Цена в рублях", min_value=0.0, step=100.0)
        reason = st.text_area("Зачем тебе эта вещь? С чем будешь носить?")
        submitted = st.form_submit_button("Оценить покупку")
        if submitted:
            similar = [x for x in items if x["category"] == category]
            st.session_state["purchase_review"] = {
                "name": name, "category": category, "price": price,
                "reason": reason, "similar": [x["name"] for x in similar]
            }
            decision = "Думаю"
            execute("INSERT INTO purchases VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (uuid.uuid4().hex, user_id, name, category, price, reason,
                     decision, datetime.now().isoformat()))
    review = st.session_state.get("purchase_review")
    if review:
        st.subheader("Мнение помощника")
        st.metric("Стоимость", f"{review['price']:,.0f} ₽".replace(",", " "))
        if review["similar"]:
            st.warning("В гардеробе уже есть вещи этой категории: " + ", ".join(review["similar"]))
            st.write("Подумай, отличается ли новая вещь по назначению, цвету или сочетаниям.")
        else:
            st.success("В этой категории пока нет вещей. Возможно, покупка заполнит пробел.")
        if not review["reason"].strip():
            st.info("Попробуй сформулировать минимум два образа, с которыми будешь носить покупку.")
        elif len(review["reason"].strip()) > 20:
            st.success("Ты уже продумала назначение вещи. Проверь, подходит ли она к нескольким комплектам.")
        st.write("Это подсказка, а не обязательное решение — выбор остаётся за тобой.")
    purchases = rows("SELECT * FROM purchases WHERE user_id=? ORDER BY created_at DESC", (user_id,))
    if purchases:
        st.subheader("История решений")
        for p in purchases:
            st.write(f"• {p['name']} — {p['price']:,.0f} ₽ — {p['decision']}".replace(",", " "))

# -------------------- СТИЛИСТ --------------------
elif page == "Стилист":
    st.title("Твой персональный стилист")
    st.write("Выбери ситуацию — посмотрим, что уже есть в твоём шкафу.")
    occasion = st.selectbox("Куда нужен образ?", OCCASIONS)
    matching = [x for x in items if x["occasion"] == occasion]
    if matching:
        st.subheader(f"Вещи для ситуации «{occasion.lower()}»")
        cols = st.columns(3)
        for i, x in enumerate(matching):
            with cols[i % 3]:
                show_image(x["image_path"], 150)
                st.write(f"**{x['name']}**")
                st.caption(f"{x['category']} · {x['color'] or 'цвет не указан'}")
        st.info(stylist_tip(matching[:3]))
    else:
        st.info("Пока нет вещей с такой отметкой. Добавь вещь и выбери эту ситуацию.")
    st.subheader("Маленькое правило стилиста")
    st.write("Для начала выбери одну главную вещь, затем подбери к ней базовые элементы и один акцент. Не обязательно следовать трендам — важнее, чтобы тебе было удобно.")
