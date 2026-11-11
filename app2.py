import streamlit as st
import sqlite3, uuid, hashlib, random
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

.stButton > button[kind="secondary"][data-color="blue"] {{
    background: {BLUE} !important; color: {CREAM} !important; border: 0 !important;
}}
.stButton > button[kind="secondary"][data-color="green"] {{
    background: {GREEN} !important; color: {CREAM} !important; border: 0 !important;
}}

div[data-testid="stMetric"] {{ background: {PLUM}; padding: 14px; border-radius: 14px; }}
div[data-testid="stMetric"] * {{ color: {CREAM} !important; }}

.stAlert, div[data-testid="stNotification"] {{ background: #FFFFFF !important; border-radius: 12px; }}
.stAlert *, div[data-testid="stNotification"] * {{ color: {PLUM} !important; }}

[data-testid="stExpander"] {{ background: #FFFFFF; border-radius: 12px; }}
[data-testid="stExpander"] summary {{ color: {PLUM} !important; }}

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
        con.execute("""CREATE TABLE IF NOT EXISTS custom_categories (
            id TEXT PRIMARY KEY, user_id TEXT, name TEXT, parent_category TEXT)""")

def rows(q, p=()):
    with db() as con: return con.execute(q, p).fetchall()

def execute(q, p=()):
    with db() as con: con.execute(q, p)

def execute_and_clear(q, p=()):
    execute(q, p)
    st.cache_data.clear()

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

# ---------- БАЗОВЫЕ КАТЕГОРИИ ----------
BASE_CATEGORY_TREE = {
    "Верх": ["Футболка", "Кофта", "Лонгслив", "Рубашка", "Блузка", "Свитер", "Кардиган", "Топ", "Худи", "Другое"],
    "Низ": ["Брюки", "Джинсы", "Шорты", "Спортивные штаны", "Юбка", "Леггинсы", "Бриджи", "Другое"],
    "Платья и комбинезоны": ["Платье", "Сарафан", "Комбинезон", "Другое"],
    "Обувь": ["Кроссовки", "Ботинки", "Туфли", "Кеды", "Сандали", "Балетки", "Сапоги", "Босоножки", "Другое"],
    "Верхняя одежда": ["Куртка", "Жилет", "Безрукавка", "Пальто", "Плащ", "Пуховик", "Пиджак", "Другое"],
    "Сумки": ["Рюкзак", "Сумка через плечо", "Клатч", "Шоппер", "Другое"],
    "Аксессуары": ["Кольцо", "Серьги", "Цепочка", "Браслет", "Шарф", "Шапка", "Перчатки", "Ремень", "Очки", "Другое"],
    "Другое": ["Другое"],
}
OCCASIONS = ["Учёба", "Прогулка", "Во двор", "Праздник", "Спорт", "Повседневное", "Другое"]
NEW_OPTION = "➕ Создать новую…"

@st.cache_data(ttl=30, show_spinner=False)
def get_custom_categories(uid):
    return [dict(r) for r in rows("SELECT * FROM custom_categories WHERE user_id=?", (uid,))]

def build_category_tree(uid):
    tree = {k: list(v) for k, v in BASE_CATEGORY_TREE.items()}
    customs = get_custom_categories(uid)
    for c in customs:
        if not c["parent_category"]:
            name = c["name"]
            if name not in tree:
                tree[name] = ["Другое"]
    for c in customs:
        if c["parent_category"]:
            parent = c["parent_category"]
            if parent in tree and c["name"] not in tree[parent]:
                tree[parent].append(c["name"])
            elif parent not in tree:
                tree[parent] = [c["name"]]
    return tree

def add_custom_category(uid, name, parent_category=""):
    name = name.strip()
    if not name:
        return False
    customs = get_custom_categories(uid)
    for c in customs:
        if c["name"].lower() == name.lower() and (c["parent_category"] or "") == (parent_category or ""):
            return False
    execute_and_clear("INSERT INTO custom_categories VALUES (?,?,?,?)",
                      (uuid.uuid4().hex, uid, name, parent_category or ""))
    return True

CATEGORY_TREE = build_category_tree(user_id)
CATEGORIES = list(CATEGORY_TREE.keys())

# ---------- КАРТИНКИ ----------
def save_image(uploaded):
    if uploaded is None: return None
    image = Image.open(uploaded).convert("RGB")
    image.thumbnail((800, 800))
    path = user_dir / f"{uuid.uuid4().hex}.jpg"
    image.save(path, format="JPEG", quality=82, optimize=True)
    return str(path)

def show_image(path, width=220):
    if path and Path(path).exists(): st.image(path, width=width)

# ---------- КЭШИРУЕМОЕ ЧТЕНИЕ ----------
@st.cache_data(ttl=30, show_spinner=False)
def get_items_cached(uid):
    return [dict(r) for r in rows("SELECT * FROM items WHERE user_id=? ORDER BY created_at DESC", (uid,))]

@st.cache_data(ttl=30, show_spinner=False)
def get_outfits_cached(uid):
    return [dict(r) for r in rows("SELECT * FROM outfits WHERE user_id=? ORDER BY created_at DESC", (uid,))]

@st.cache_data(ttl=30, show_spinner=False)
def items_map(uid):
    return {r["id"]: {"name": r["name"], "image_path": r["image_path"]}
            for r in rows("SELECT id, name, image_path FROM items WHERE user_id=?", (uid,))}

def get_items(): return get_items_cached(user_id)
def get_outfits(): return get_outfits_cached(user_id)

def item_name(i):
    m = items_map(user_id)
    return m.get(i, {}).get("name", "Удалённая вещь")

def item_image(i):
    m = items_map(user_id)
    return m.get(i, {}).get("image_path")

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
        st.markdown("**Новая вещь**")

        cat_options = CATEGORIES + [NEW_OPTION]
        category_choice = st.selectbox("Категория", cat_options, key="add_cat")

        if category_choice == NEW_OPTION:
            new_cat = st.text_input("Название новой категории", key="add_new_cat")
            if st.button("Создать категорию", key="btn_new_cat"):
                if add_custom_category(user_id, new_cat, ""):
                    st.success(f"Категория «{new_cat.strip()}» создана.")
                    st.rerun()
                else:
                    st.error("Введите название или такая категория уже есть.")
            st.stop()

        category = category_choice
        sub_options = CATEGORY_TREE.get(category, ["Другое"]) + [NEW_OPTION]
        subcategory_choice = st.selectbox("Тип", sub_options, key="add_sub")

        if subcategory_choice == NEW_OPTION:
            new_sub = st.text_input("Название нового типа", key="add_new_sub")
            if st.button("Создать тип", key="btn_new_sub"):
                if add_custom_category(user_id, new_sub, category):
                    st.success(f"Тип «{new_sub.strip()}» создан в категории «{category}».")
                    st.rerun()
                else:
                    st.error("Введите название или такой тип уже есть.")
            st.stop()

        subcategory = subcategory_choice

        with st.form("add_item_inline"):
            name = st.text_input("Название вещи (необязательно)", placeholder="Например, сливовый кардиган")
            occasion = st.selectbox("Для чего?", OCCASIONS)
            color = st.text_input("Цвет")
            season = st.selectbox("Сезон", ["Весна","Лето","Осень","Зима","Любой"])
            notes = st.text_area("Заметки")
            photo = st.file_uploader("Фотография вещи", type=["png","jpg","jpeg"])
            submitted = st.form_submit_button("Сохранить вещь")

        if submitted:
            final_name = name.strip() or (subcategory + (f" · {color.strip()}" if color.strip() else ""))
            path = save_image(photo)
            execute_and_clear("INSERT INTO items VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    (uuid.uuid4().hex, user_id, final_name, category, subcategory, occasion,
                     color, season, notes, path, None, datetime.now().isoformat()))
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
            if st.checkbox("✏️ Редактировать", key=f"ed_{x['id']}"):
                cat_options = CATEGORIES + [NEW_OPTION]
                idx_cat = cat_options.index(x["category"]) if x["category"] in cat_options else 0
                nc_choice = st.selectbox("Категория", cat_options, index=idx_cat, key=f"ec_{x['id']}")

                if nc_choice == NEW_OPTION:
                    new_cat = st.text_input("Название новой категории", key=f"newcat_{x['id']}")
                    if st.button("Создать категорию", key=f"btncat_{x['id']}"):
                        if add_custom_category(user_id, new_cat, ""):
                            st.success(f"Категория «{new_cat.strip()}» создана.")
                            st.rerun()
                        else:
                            st.error("Введите название или такая категория уже есть.")
                    st.stop()

                nc = nc_choice
                subs = CATEGORY_TREE.get(nc, ["Другое"]) + [NEW_OPTION]
                idx_sub = subs.index(x["subcategory"]) if x["subcategory"] in subs else 0
                nsub_choice = st.selectbox("Тип", subs, index=idx_sub, key=f"es_{x['id']}")

                if nsub_choice == NEW_OPTION:
                    new_sub = st.text_input("Название нового типа", key=f"newsub_{x['id']}")
                    if st.button("Создать тип", key=f"btnsub_{x['id']}"):
                        if add_custom_category(user_id, new_sub, nc):
                            st.success(f"Тип «{new_sub.strip()}» создан в категории «{nc}».")
                            st.rerun()
                        else:
                            st.error("Введите название или такой тип уже есть.")
                    st.stop()

                nsub = nsub_choice

                with st.form(f"edit_{x['id']}"):
                    st.markdown("**Изменить вещь**")
                    nn = st.text_input("Название (необязательно)", x["name"])
                    no = st.selectbox("Для чего", OCCASIONS, index=OCCASIONS.index(x["occasion"]) if x["occasion"] in OCCASIONS else 0)
                    ncol = st.text_input("Цвет", x["color"] or "")
                    ns = st.text_input("Сезон", x["season"] or "")
                    nnt = st.text_area("Заметки", x["notes"] or "")
                    nd = st.date_input("Последний раз надевала", value=date.fromisoformat(x["last_worn"]) if x["last_worn"] else date.today())
                    rep = st.file_uploader("Заменить фото", type=["png","jpg","jpeg"], key=f"r_{x['id']}")
                    if st.form_submit_button("Сохранить изменения"):
                        final_name = nn.strip() or (nsub + (f" · {ncol.strip()}" if ncol.strip() else ""))
                        path = save_image(rep) if rep else x["image_path"]
                        execute_and_clear("UPDATE items SET name=?, category=?, subcategory=?, occasion=?, color=?, season=?, notes=?, last_worn=?, image_path=? WHERE id=? AND user_id=?",
                                (final_name, nc, nsub, no, ncol, ns, nnt, nd.isoformat(), path, x["id"], user_id))
                        st.success("Вещь обновлена."); st.rerun()
            col_a, col_b = st.columns(2)
            if col_a.button("Удалить вещь", key=f"d_{x['id']}"):
                execute_and_clear("DELETE FROM items WHERE id=? AND user_id=?", (x["id"], user_id))
                if x["image_path"] and Path(x["image_path"]).exists(): Path(x["image_path"]).unlink()
                st.rerun()
            if col_b.button("Отметить как надетую сегодня", key=f"w_{x['id']}"):
                execute_and_clear("UPDATE items SET last_worn=? WHERE id=? AND user_id=?", (date.today().isoformat(), x["id"], user_id)); st.rerun()

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
                        execute_and_clear("INSERT INTO outfits VALUES (?,?,?,?,?,?,?,?,?)",
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
            if st.checkbox("✏️ Редактировать образ", key=f"edo_{o['id']}"):
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
                        execute_and_clear("UPDATE outfits SET name=?, occasion=?, item_ids=?, item_images=?, notes=?, image_path=? WHERE id=? AND user_id=?",
                                (nn, no, ",".join(nids), chosen_images, nnt, path, o["id"], user_id))
                        st.success("Образ обновлён."); st.rerun()
            if st.button("Удалить образ", key=f"do_{o['id']}"):
                execute_and_clear("DELETE FROM outfits WHERE id=? AND user_id=?", (o["id"], user_id))
                if o["image_path"] and Path(o["image_path"]).exists(): Path(o["image_path"]).unlink()
                st.rerun()

# ---------- ПЕРЕД ПОКУПКОЙ ----------
elif page == "Перед покупкой":
    st.title("Стоит ли покупать?")
    st.write("Проверь, действительно ли новая вещь нужна твоему гардеробу.")

    cat_options = CATEGORIES + [NEW_OPTION]
    category_choice = st.selectbox("Категория", cat_options, key="pur_cat")

    if category_choice == NEW_OPTION:
        new_cat = st.text_input("Название новой категории", key="pur_new_cat")
        if st.button("Создать категорию", key="pur_btn_cat"):
            if add_custom_category(user_id, new_cat, ""):
                st.success(f"Категория «{new_cat.strip()}» создана.")
                st.rerun()
            else:
                st.error("Введите название или такая категория уже есть.")
        st.stop()

    category = category_choice
    sub_options = CATEGORY_TREE.get(category, ["Другое"]) + [NEW_OPTION]
    sub_choice = st.selectbox("Тип", sub_options, key="pur_sub")

    if sub_choice == NEW_OPTION:
        new_sub = st.text_input("Название нового типа", key="pur_new_sub")
        if st.button("Создать тип", key="pur_btn_sub"):
            if add_custom_category(user_id, new_sub, category):
                st.success(f"Тип «{new_sub.strip()}» создан в категории «{category}».")
                st.rerun()
            else:
                st.error("Введите название или такой тип уже есть.")
        st.stop()

    subcategory = sub_choice

    with st.form("purchase"):
        name = st.text_input("Что хочешь купить?")
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
            execute_and_clear("INSERT INTO purchases VALUES (?,?,?,?,?,?,?,?,?,?)",
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
                execute_and_clear("DELETE FROM purchases WHERE user_id=?", (user_id,))
                st.success("История покупок очищена.")
                st.rerun()
        else:
            st.info("История покупок пока пуста.")

# ---------- СТИЛИСТ ----------
elif page == "Стилист":
    st.title("Твой персональный стилист")
    st.write("Выбери ситуацию — я сам соберу несколько готовых образов из твоих вещей.")

    occ = st.selectbox("Куда нужен образ?", OCCASIONS)
    pool = [x for x in items if x["occasion"] == occ or x["occasion"] == "Другое"]

    if not pool:
        st.info("Пока нет вещей с такой отметкой. Добавь вещь и выбери эту ситуацию.")
        st.stop()

        def by_cat(cat):
        return [x for x in pool if x["category"] == cat]

    tops = by_cat("Верх")
    bottoms = by_cat("Низ")
    dresses = by_cat("Платья и комбинезоны")
    shoes = by_cat("Обувь")
    outer = by_cat("Верхняя одежда")
    bags = by_cat("Сумки")
    accs = by_cat("Аксессуары")

    can_basic = bool(tops and bottoms) or bool(dresses)
    if not can_basic:
        st.warning("Чтобы собрать образ, нужно хотя бы: верх + низ, либо платье/комбинезон.")
        st.write("Сейчас в гардеробе под эту ситуацию есть:")
        for label, arr in [("Верх", tops), ("Низ", bottoms), ("Платья", dresses),
                           ("Обувь", shoes), ("Верхняя одежда", outer),
                           ("Сумки", bags), ("Аксессуары", accs)]:
            st.write(f"• {label}: {len(arr)}")
        st.stop()

    def color_key(x):
        return (x["color"] or "").strip().lower()

    def pick_accent(base_items):
        base_colors = {color_key(i) for i in base_items if color_key(i)}
        candidates = [a for a in accs if color_key(a) and color_key(a) not in base_colors]
        return random.choice(candidates) if candidates else (random.choice(accs) if accs else None)

    def pick_bag(base_items):
        base_colors = {color_key(i) for i in base_items if color_key(i)}
        candidates = [b for b in bags if color_key(b) and color_key(b) not in base_colors]
        return random.choice(candidates) if candidates else (random.choice(bags) if bags else None)

    def build_outfit():
        base = []
        if dresses and random.random() < 0.5:
            base.append(random.choice(dresses))
        elif tops and bottoms:
            base.append(random.choice(tops))
            base.append(random.choice(bottoms))
        elif dresses:
            base.append(random.choice(dresses))
        else:
            return None

        if shoes:
            base.append(random.choice(shoes))
        if outer and random.random() < 0.6:
            base.append(random.choice(outer))

        bag = pick_bag(base)
        if bag:
            base.append(bag)
        acc = pick_accent(base)
        if acc:
            base.append(acc)

        seen, result = set(), []
        for it in base:
            if it["id"] not in seen:
                seen.add(it["id"])
                result.append(it)
        return result

    def outfit_signature(outfit):
        return tuple(sorted(i["id"] for i in outfit))

    if "stylist_variants" not in st.session_state or st.session_state.get("stylist_occ") != occ:
        st.session_state.stylist_occ = occ
        st.session_state.stylist_variants = []

    if st.button("Собрать образы", type="primary") or not st.session_state.stylist_variants:
        variants, signatures = [], set()
        attempts = 0
        while len(variants) < 3 and attempts < 60:
            attempts += 1
            o = build_outfit()
            if not o:
                break
            sig = outfit_signature(o)
            if sig in signatures:
                continue
            signatures.add(sig)
            variants.append(o)
        st.session_state.stylist_variants = variants

    variants = st.session_state.stylist_variants

    if not variants:
        st.warning("Не удалось собрать ни одного образа. Проверь, что есть верх и низ (или платье).")
        st.stop()

    st.subheader(f"Готовые образы для ситуации «{occ.lower()}»")

    for idx, outfit in enumerate(variants, start=1):
        with st.container(border=True):
            st.markdown(f"### Образ {idx}")
            cols = st.columns(min(len(outfit), 4))
            for j, it in enumerate(outfit):
                with cols[j % 4]:
                    show_image(it["image_path"], 140)
                    st.caption(f"**{it['name']}**")
                    st.caption(f"{it['category']} / {it['subcategory']}")
                    if it["color"]:
                        st.caption(f"Цвет: {it['color']}")

            names = [it["name"] for it in outfit]
            st.write("**Состав:** " + ", ".join(names))

            colors_in_outfit = [color_key(it) for it in outfit if color_key(it)]
            unique_colors = set(colors_in_outfit)
            if len(unique_colors) >= 3:
                st.info("В образе 3+ цвета — следи, чтобы они сочетались. Один из них лучше сделать нейтральным.")
            elif len(unique_colors) == 1:
                st.info("Образ в одном цвете — выглядит цельно. Можно добавить аксессуар-акцент другого оттенка.")
            else:
                st.success("Хорошее сочетание: 2 цвета — базовый и поддерживающий.")

    if st.button("Собрать другие варианты"):
        st.session_state.stylist_variants = []
        st.rerun()

    st.caption(
        "Стилист подбирает образы по правилам: база (верх+низ или платье), "
        "обувь, при необходимости верхняя одежда, сумка и аксессуар-акцент. "
        "Цвета старается не повторять."
    )
