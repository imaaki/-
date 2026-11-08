import streamlit as st
import sqlite3, uuid, hashlib
from pathlib import Path
from datetime import date, datetime, timedelta
from PIL import Image

st.set_page_config(page_title="Smart Closet", page_icon="", layout="wide")

DB_PATH = Path("smart_closet.db")
UPLOAD_DIR = Path("uploads"); UPLOAD_DIR.mkdir(exist_ok=True)

CREAM, PLUM, CHERRY, MUTED = "#F5EFE5", "#552D43", "#742D40", "#826A73"
BLUE, GREEN = "#2E5AAC", "#2E7D5B"

st.markdown(f"""
<style>
.stApp {{ background: {CREAM}; color: #3A2230; }}
h1, h2, h3 {{ color: {PLUM} !important; }}
p, label, .stMarkdown, .stCaption, .stText {{ color: #3A2230 !important; }}

[data-testid="stSidebar"] {{ background: #E9DED2; }}
[data-testid="stSidebar"] * {{ color: {PLUM} !important; }}

/* Кнопки по умолчанию: белый фон, сливовый текст */
.stButton > button,
.stFormSubmitButton > button,
.stDownloadButton > button {{
    background: #FFFFFF !important;
    color: {PLUM} !important;
    border: 1px solid {PLUM} !important;
    border-radius: 12px;
}}
.stButton > button:hover,
.stFormSubmitButton > button:hover,
.stDownloadButton > button:hover {{
    background: #F0E6DA !important;
    color: {PLUM} !important;
}}

/* Primary: сливовый фон, кремовый текст */
.stButton > button[kind="primary"],
.stFormSubmitButton > button[kind="primary"] {{
    background: {PLUM} !important;
    color: {CREAM} !important;
    border: 0 !important;
}}
.stButton > button[kind="primary"]:hover,
.stFormSubmitButton > button[kind="primary"]:hover {{
    background: {CHERRY} !important;
    color: {CREAM} !important;
}}

/* Синяя кнопка: синий фон, кремовый текст */
.stButton > button[kind="secondary"][data-color="blue"] {{
    background: {BLUE} !important; color: {CREAM} !important; border: 0 !important;
}}
/* Зелёная кнопка: зелёный фон, кремовый текст */
.stButton > button[kind="secondary"][data-color="green"] {{
    background: {GREEN} !important; color: {CREAM} !important; border: 0 !important;
}}

/* Метрики */
div[data-testid="stMetric"] {{ background: {PLUM}; padding: 14px; border-radius: 14px; }}
div[data-testid="stMetric"] * {{ color: {CREAM} !important; }}

/* Уведомления */
.stAlert, div[data-testid="stNotification"] {{ background: #FFFFFF !important; border-radius: 12px; }}
.stAlert *, div[data-testid="stNotification"] * {{ color: {PLUM} !important; }}

/* Expander */
[data-testid="stExpander"] {{ background: #FFFFFF; border-radius: 12px; }}
[data-testid="stExpander"] summary {{ color: {PLUM} !important; }}

/* Кнопки внутри expander: сливовый фон, кремовый текст */
[data-testid="stExpander"] .stButton > button,
[data-testid="stExpander"] .stFormSubmitButton > button,
[data-testid="stExpander"] .stDownloadButton > button {{
    background: {PLUM} !important;
    color: {CREAM} !important;
    border: 1px solid {PLUM} !important;
}}
[data-testid="stExpander"] .stButton > button:hover,
[data-testid="stExpander"] .stFormSubmitButton > button:hover,
[data-testid="stExpander"] .stDownloadButton > button:hover {{
    background: {CHERRY} !important;
    color: {CREAM} !important;
    border: 1px solid {CHERRY} !important;
}}
[data-testid="stExpander"] .stButton > button *,
[data-testid="stExpander"] .stFormSubmitButton > button * {{
    color: {CREAM} !important;
}}

/* Поля ввода */
input, textarea, select,
[data-baseweb="input"] input,
[data-baseweb="select"] *,
[data-baseweb="textarea"] * {{
    background: #FFFFFF !important;
    color: {PLUM} !important;
}}
</style>
""", unsafe_allow_html=True)

# ---------- БД ----------
def db():
    conn = sqlite3.connect(DB_PATH); conn.row_factory = sqlite3.Row; return conn

def init_db():
    with db() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS items (id TEXT PRIMARY KEY, user_id TEXT, name TEXT, category TEXT,
            subcategory TEXT, occasion TEXT, color TEXT, season TEXT, notes TEXT, image_path TEXT, last_worn TEXT, created_at TEXT)""")
        con.execute("""CREATE TABLE IF NOT EXISTS outfits (id TEXT PRIMARY KEY, user_id TEXT, name TEXT, occasion TEXT,
            item_ids TEXT, item_images TEXT, notes TEXT, image_path TEXT, created_at TEXT)""")
        con.execute("""CREATE TABLE IF NOT EXISTS purchases (id TEXT PRIMARY KEY, user_id TEXT, name TEXT, category TEXT,
            subcategory TEXT, color TEXT, price REAL, reason TEXT, decision TEXT, created_at TEXT)""")
        

def rows(q, p=()):
    with db() as con: return con.execute(q, p).fetchall()

def execute(q, p=()):
    with db() as con: con.execute(q, p)

init_db()
def migrate_db():
    with db() as con:
        cols_items = [r["name"] for r in con.execute("PRAGMA table_info(items)").fetchall()]
        if "subcategory" not in cols_items:
            con.execute("ALTER TABLE items ADD COLUMN subcategory TEXT DEFAULT 'Другое'")
        cols_purch = [r["name"] for r in con.execute("PRAGMA table_info(purchases)").fetchall()]
        if "subcategory" not in cols_purch:
            con.execute("ALTER TABLE purchases ADD COLUMN subcategory TEXT DEFAULT 'Другое'")
        if "color" not in cols_purch:
            con.execute("ALTER TABLE purchases ADD COLUMN color TEXT DEFAULT ''")
        cols_outf = [r["name"] for r in con.execute("PRAGMA table_info(outfits)").fetchall()]
        if "item_images" not in cols_outf:
            con.execute("ALTER TABLE outfits ADD COLUMN item_images TEXT DEFAULT ''")

init_db()
migrate_db()

# ---------- ВХОД ----------
def login_screen():
    st.title("smart closet"); st.caption("YOUR PERSONAL WARDROBE")
    st.write("Войди через Google, чтобы открыть свой личный гардероб.")
    st.info("Для входа настрой Google OAuth в файле `.streamlit/secrets.toml` (инструкция в README).")
    if st.button("Продолжить через Google", use_container_width=True): st.login()

if not st.user.is_logged_in:
    login_screen(); st.stop()

user_email = str(st.user.get("email", ""))
user_id = hashlib.sha256(user_email.lower().encode()).hexdigest()[:24]
user_dir = UPLOAD_DIR / user_id; user_dir.mkdir(parents=True, exist_ok=True)
display_name = st.user.get("name", "Пользователь")

# ---------- КАТЕГОРИИ С ПОДКАТЕГОРИЯМИ ----------
CATEGORY_TREE = {
    "Верх": ["Футболка", "Лонгслив", "Рубашка", "Блузка", "Свитер", "Кардиган", "Топ", "Худи", "Другое"],
    "Низ": ["Брюки", "Джинсы", "Шорты", "Спортивные штаны", "Юбка", "Леггинсы", "Другое"],
    "Платья и комбинезоны": ["Платье", "Сарафан", "Комбинезон", "Другое"],
    "Обувь": ["Кроссовки", "Ботинки", "Туфли", "Сандалии", "Балетки", "Сапоги", "Другое"],
    "Верхняя одежда": ["Куртка", "Пальто", "Плащ", "Пуховик", "Пиджак", "Другое"],
    "Сумки": ["Рюкзак", "Сумка через плечо", "Клатч", "Шоппер", "Другое"],
    "Аксессуары": ["Шарф", "Шапка", "Перчатки", "Ремень", "Украшения", "Другое"],
    "Другое": ["Другое"],
}
CATEGORIES = list(CATEGORY_TREE.keys())
OCCASIONS = ["Учёба", "Прогулка", "Во двор", "Праздник", "Спорт", "Повседневное", "Другое"]

def save_image(uploaded):
    if uploaded is None: return None
    image = Image.open(uploaded).convert("RGBA")
    path = user_dir / f"{uuid.uuid4().hex}.png"; image.save(path, format="PNG"); return str(path)

def show_image(path, width=220):
    if path and Path(path).exists(): st.image(path, width=width)

def get_items(): return rows("SELECT * FROM items WHERE user_id=? ORDER BY created_at DESC", (user_id,))
def get_outfits(): return rows("SELECT * FROM outfits WHERE user_id=? ORDER BY created_at DESC", (user_id,))
def item_name(i):
    f = rows("SELECT name FROM items WHERE id=? AND user_id=?", (i, user_id)); return f[0]["name"] if f else "Удалённая вещь"
def item_image(i):
    f = rows("SELECT image_path FROM items WHERE id=? AND user_id=?", (i, user_id)); return f[0]["image_path"] if f else None

def stylist_tip(sel):
    if not sel: return "Добавь вещи в гардероб — и я помогу собрать сочетание."
    colors = [x["color"].lower() for x in sel if x["color"]]
    if len(set(colors)) == 1 and len(colors) > 1: return "В комплекте много одного цвета. Попробуй добавить нейтральный оттенок."
    if len(sel) == 1: return "Добавь ещё одну вещь или аксессуар, чтобы завершить комплект."
    return "Попробуй повторить один цвет в двух элементах образа — так комплект будет выглядеть цельнее."

# ---------- НАВИГАЦИЯ ----------
st.sidebar.title("smart closet"); st.sidebar.caption(f"Привет, {display_name}!")
page = st.sidebar.radio("Меню", ["Главная", "Мой гардероб", "Мои образы", "Перед покупкой", "Стилист"])
if st.sidebar.button("Выйти из аккаунта"): st.logout()

items, outfits = get_items(), get_outfits()

# ---------- ГЛАВНАЯ ----------
if page == "Главная":
    st.title("Твой умный шкаф")
    st.write("Всё, что ты носишь, любишь и планируешь купить — в одном месте.")
    a, b, c = st.columns(3)
    a.metric("Вещей в гардеробе", len(items)); b.metric("Сохранённых образов", len(outfits))
    c.metric("Покупок на рассмотрении", len(rows("SELECT id FROM purchases WHERE user_id=? AND decision='Думаю'", (user_id,))))
    st.subheader("Совет стилиста")
    st.success("Необязательно покупать новое: иногда новый образ получается из уже знакомых вещей.")
    st.subheader("Пора вспомнить")
    cutoff = (date.today() - timedelta(days=30)).isoformat()
    old = [x for x in items if not x["last_worn"] or x["last_worn"] < cutoff]
    if old:
        st.write("Эти вещи давно не отмечались как надетые:")
        for x in old[:8]: st.write(f"• **{x['name']}** — {x['last_worn'] or 'ещё не отмечали'}")
    else: st.write("Пока все вещи в актуальном использовании. Так держать!")
    st.caption("Напоминания отображаются внутри приложения при следующем входе.")

# ---------- ГАРДЕРОБ ----------
elif page == "Мой гардероб":
    st.title("Мой гардероб")

    if "show_add_form" not in st.session_state:
        st.session_state.show_add_form = False
    if st.button("➕ Добавить вещь", type="primary"):
        st.session_state.show_add_form = not st.session_state.show_add_form

    if st.session_state.show_add_form:
        with st.form("add_item_inline"):
            st.markdown("**Новая вещь**")
            name = st.text_input("Название вещи", placeholder="Например, сливовый кардиган")
            category = st.selectbox("Категория", CATEGORIES)
            subcategory = st.selectbox("Тип", CATEGORY_TREE[category])
            occasion = st.selectbox("Для чего?", OCCASIONS)
            color = st.text_input("Цвет")
            season = st.selectbox("Сезон", ["Весна","Лето","Осень","Зима","Любой"])
            notes = st.text_area("Заметки")
            photo = st.file_uploader("Фотография вещи", type=["png","jpg","jpeg"])
            if st.form_submit_button("Сохранить вещь"):
                if not name.strip():
                    st.error("Введи название вещи.")
                else:
                    path = save_image(photo)
                    execute("INSERT INTO items VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                            (uuid.uuid4().hex, user_id, name.strip(), category, subcategory, occasion, color, season, notes, path, None, datetime.now().isoformat()))
                    st.success("Вещь добавлена в гардероб!")
                    st.session_state.show_add_form = False
                    st.rerun()

    f1, f2 = st.columns(2)
    cf = f1.selectbox("Категория", ["Все"] + CATEGORIES)
    of = f2.selectbox("Для чего", ["Все"] + OCCASIONS)
    filtered = [x for x in items if (cf == "Все" or x["category"] == cf) and (of == "Все" or x["occasion"] == of)]
    if not filtered:
        st.info("Пока здесь пусто. Добавь первую вещь!")
    for x in filtered:
        with st.expander(f"{x['name']} · {x['category']} / {x['subcategory']}"):
            c1, c2 = st.columns([1, 2])
            with c1: show_image(x["image_path"])
            with c2:
                st.write(f"**Категория:** {x['category']} / {x['subcategory']}")
                st.write(f"**Ситуация:** {x['occasion']}")
                st.write(f"**Цвет:** {x['color'] or 'Не указан'}")
                st.write(f"**Сезон:** {x['season'] or 'Любой'}")
                st.write(f"**Заметки:** {x['notes'] or 'Нет'}")
                st.write(f"**Последний раз надевала:** {x['last_worn'] or 'Не отмечено'}")
            with st.form(f"edit_{x['id']}"):
                st.markdown("**Изменить вещь**")
                nn = st.text_input("Название", x["name"])
                nc = st.selectbox("Категория", CATEGORIES, index=CATEGORIES.index(x["category"]) if x["category"] in CATEGORIES else 0)
                nsubs = CATEGORY_TREE.get(nc, ["Другое"])
                nsub = st.selectbox("Тип", nsubs, index=nsubs.index(x["subcategory"]) if x["subcategory"] in nsubs else 0)
                no = st.selectbox("Для чего", OCCASIONS, index=OCCASIONS.index(x["occasion"]) if x["occasion"] in OCCASIONS else 0)
                ncol = st.text_input("Цвет", x["color"] or "")
                ns = st.text_input("Сезон", x["season"] or "")
                nnt = st.text_area("Заметки", x["notes"] or "")
                nd = st.date_input("Последний раз надевала", value=date.fromisoformat(x["last_worn"]) if x["last_worn"] else date.today())
                rep = st.file_uploader("Заменить фото", type=["png","jpg","jpeg"], key=f"r_{x['id']}")
                if st.form_submit_button("Сохранить изменения"):
                    path = save_image(rep) if rep else x["image_path"]
                    execute("UPDATE items SET name=?, category=?, subcategory=?, occasion=?, color=?, season=?, notes=?, last_worn=?, image_path=? WHERE id=? AND user_id=?",
                            (nn, nc, nsub, no, ncol, ns, nnt, nd.isoformat(), path, x["id"], user_id))
                    st.success("Вещь обновлена."); st.rerun()
            if st.button("Удалить вещь", key=f"d_{x['id']}"):
                execute("DELETE FROM items WHERE id=? AND user_id=?", (x["id"], user_id))
                if x["image_path"] and Path(x["image_path"]).exists(): Path(x["image_path"]).unlink()
                st.rerun()
            if st.button("Отметить как надетую сегодня", key=f"w_{x['id']}"):
                execute("UPDATE items SET last_worn=? WHERE id=? AND user_id=?", (date.today().isoformat(), x["id"], user_id)); st.rerun()

# ---------- МОИ ОБРАЗЫ ----------
elif page == "Мои образы":
    st.title("Мои образы")

    if "show_outfit_form" not in st.session_state:
        st.session_state.show_outfit_form = False
    if st.button("➕ Создать образ", type="primary"):
        st.session_state.show_outfit_form = not st.session_state.show_outfit_form

    if st.session_state.show_outfit_form:
        if not items:
            st.info("Сначала добавь хотя бы одну вещь в гардероб.")
        else:
            avail = {x["id"]: f"{x['name']} ({x['category']}/{x['subcategory']})" for x in items}
            with st.form("new_outfit_inline"):
                st.markdown("**Новый образ**")
                on = st.text_input("Название образа", placeholder="Например, уютный образ на учёбу")
                occ = st.selectbox("Куда собираемся?", OCCASIONS)
                chosen = st.multiselect("Выбери вещи", list(avail.keys()), format_func=lambda k: avail[k])
                notes = st.text_area("Комментарий или идея")
                photo = st.file_uploader("Фото готового образа (необязательно)", type=["png","jpg","jpeg"])
                if st.form_submit_button("Сохранить образ"):
                    if not on.strip():
                        st.error("Дай образу название.")
                    elif not chosen:
                        st.error("Выбери хотя бы одну вещь.")
                    else:
                        path = save_image(photo)
                        chosen_images = ",".join([item_image(i) or "" for i in chosen])
                        execute("INSERT INTO outfits VALUES (?,?,?,?,?,?,?,?,?)",
                                (uuid.uuid4().hex, user_id, on, occ, ",".join(chosen), chosen_images, notes, path, datetime.now().isoformat()))
                        st.success("Образ сохранён!")
                        st.session_state.show_outfit_form = False
                        st.rerun()

    if not outfits:
        st.info("Пока нет сохранённых образов. Нажми «➕ Создать образ», чтобы добавить первый.")
    for o in outfits:
        with st.expander(o["name"]):
            if o["image_path"]:
                show_image(o["image_path"], 300)
            st.write(f"**Ситуация:** {o['occasion']}")
            ids = o["item_ids"].split(",") if o["item_ids"] else []
            st.write("**Вещи:** " + ", ".join(item_name(i) for i in ids))
            if ids:
                st.write("**Фото вещей в образе:**")
                cols = st.columns(min(len(ids), 4))
                for idx, iid in enumerate(ids):
                    with cols[idx % 4]:
                        img = item_image(iid)
                        if img and Path(img).exists(): st.image(img, width=120)
                        st.caption(item_name(iid))
            st.write(o["notes"] or "")
            with st.form(f"eo_{o['id']}"):
                nn = st.text_input("Название образа", o["name"])
                no = st.selectbox("Ситуация", OCCASIONS, index=OCCASIONS.index(o["occasion"]) if o["occasion"] in OCCASIONS else 0)
                avail = {x["id"]: f"{x['name']} ({x['category']}/{x['subcategory']})" for x in items}
                valid = [i for i in ids if i in avail]
                nids = st.multiselect("Вещи", list(avail.keys()), default=valid, format_func=lambda k: avail[k])
                nnt = st.text_area("Комментарий", o["notes"] or "")
                np = st.file_uploader("Заменить фото образа", type=["png","jpg","jpeg"], key=f"op_{o['id']}")
                if st.form_submit_button("Сохранить изменения"):
                    path = save_image(np) if np else o["image_path"]
                    chosen_images = ",".join([item_image(i) or "" for i in nids])
                    execute("UPDATE outfits SET name=?, occasion=?, item_ids=?, item_images=?, notes=?, image_path=? WHERE id=? AND user_id=?",
                            (nn, no, ",".join(nids), chosen_images, nnt, path, o["id"], user_id))
                    st.success("Образ обновлён."); st.rerun()
            if st.button("Удалить образ", key=f"do_{o['id']}"):
                execute("DELETE FROM outfits WHERE id=? AND user_id=?", (o["id"], user_id))
                if o["image_path"] and Path(o["image_path"]).exists(): Path(o["image_path"]).unlink()
                st.rerun()

# ---------- ПЕРЕД ПОКУПКОЙ ----------
elif page == "Перед покупкой":
    st.title("Стоит ли покупать?")
    st.write("Проверь, действительно ли новая вещь нужна твоему гардеробу.")
    with st.form("purchase"):
        name = st.text_input("Что хочешь купить?")
        category = st.selectbox("Категория", CATEGORIES)
        subcategory = st.selectbox("Тип", CATEGORY_TREE[category])
        color = st.text_input("Цвет покупки")
        price = st.number_input("Цена в рублях", min_value=0.0, step=100.0)
        reason = st.text_area("Зачем тебе эта вещь? С чем будешь носить?")
        if st.form_submit_button("Оценить покупку"):
            similar_cat = [x for x in items if x["category"] == category and x["subcategory"] == subcategory]
            similar_color = [x for x in items if x["color"] and color and x["color"].strip().lower() == color.strip().lower()]
            st.session_state["purchase_review"] = {
                "name": name, "category": category, "subcategory": subcategory,
                "color": color, "price": price, "reason": reason,
                "similar_cat": [x["name"] for x in similar_cat],
                "similar_color": [x["name"] for x in similar_color],
            }
            execute("INSERT INTO purchases VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (uuid.uuid4().hex, user_id, name, category, subcategory, color, price, reason, "Думаю", datetime.now().isoformat()))
    review = st.session_state.get("purchase_review")
    if review:
        st.subheader("Мнение помощника")
        st.metric("Стоимость", f"{review['price']:,.0f} ₽".replace(",", " "))

        if review["similar_cat"]:
            st.warning(f"У тебя уже есть похожие вещи ({review['category']} / {review['subcategory']}): " + ", ".join(review["similar_cat"]))
            st.write("Подумай, отличается ли новая вещь по назначению, цвету или сочетаниям.")
        else:
            st.success(f"В категории «{review['category']} / {review['subcategory']}» пока нет вещей. Возможно, покупка заполнит пробел.")

        if review["color"] and review["similar_color"]:
            st.warning(f"Вещи того же цвета уже есть: " + ", ".join(review["similar_color"]))
            st.write("Если это базовый цвет — возможно, дубликат не нужен. Если акцентный — проверь, с чем будешь носить.")
        elif review["color"]:
            st.info(f"Вещей цвета «{review['color']}» в гардеробе пока нет — это может быть хорошим акцентом.")

        if not review["reason"].strip():
            st.info("Попробуй сформулировать минимум два образа, с которыми будешь носить покупку.")
        elif len(review["reason"].strip()) > 20:
            st.success("Ты уже продумала назначение вещи. Проверь, подходит ли она к нескольким комплектам.")
        st.write("Это подсказка, а не обязательное решение — выбор остаётся за тобой.")
        purchases = rows("SELECT * FROM purchases WHERE user_id=? ORDER BY created_at DESC", (user_id,))
    if purchases:
        st.subheader("История решений")
        for p in purchases:
            try:
                price_val = float(p["price"]) if p["price"] not in (None, "") else 0.0
            except (ValueError, TypeError):
                price_val = 0.0
            color_val = p["color"] or "цвет не указан"
            sub_val = p["subcategory"] or "Другое"
            st.write(f"• {p['name']} — {p['category']}/{sub_val} — {color_val} — {price_val:,.0f} ₽ — {p['decision']}".replace(",", " "))
        if st.button("🗑 Очистить историю покупок", key="clear_purchases"):
            execute("DELETE FROM purchases WHERE user_id=?", (user_id,))
            st.success("История покупок очищена.")
            st.rerun()
    else:
        st.info("История покупок пока пуста.")
# ---------- СТИЛИСТ ----------
elif page == "Стилист":
    st.title("Твой персональный стилист")
    st.write("Выбери ситуацию — посмотрим, что уже есть в твоём шкафу.")
    occ = st.selectbox("Куда нужен образ?", OCCASIONS)
    matching = [x for x in items if x["occasion"] == occ]
    if matching:
        st.subheader(f"Вещи для ситуации «{occ.lower()}»")
        cols = st.columns(3)
        for i, x in enumerate(matching):
            with cols[i % 3]:
                show_image(x["image_path"], 150)
                st.write(f"**{x['name']}**")
                st.caption(f"{x['category']} / {x['subcategory']} · {x['color'] or 'цвет не указан'}")
        st.info(stylist_tip(matching[:3]))
    else:
        st.info("Пока нет вещей с такой отметкой. Добавь вещь и выбери эту ситуацию.")
    st.subheader("Маленькое правило стилиста")
    st.write("Для начала выбери одну главную вещь, затем подбери к ней базовые элементы и один акцент. Не обязательно следовать трендам — важнее, чтобы тебе было удобно.")
