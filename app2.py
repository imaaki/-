import streamlit as st
import uuid, hashlib, random
from pathlib import Path
from datetime import date, datetime, timedelta
from PIL import Image
from supabase import create_client

st.set_page_config(page_title="Smart Closet", page_icon="", layout="wide")

UPLOAD_DIR = Path("uploads"); UPLOAD_DIR.mkdir(exist_ok=True)

CREAM, PLUM, CHERRY, MUTED = "#F5EFE5", "#552D43", "#742D40", "#826A73"
BLUE, GREEN = "#2E5AAC", "#2E7D5B"

# ---------- ПОДКЛЮЧЕНИЕ К SUPABASE ----------
@st.cache_resource
def init_supabase():
    url = st.secrets["connections"]["supabase"]["SUPABASE_URL"]
    key = st.secrets["connections"]["supabase"]["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_supabase()

st.markdown(f"""
<style>
.stApp {{ background: {CREAM}; color: #3A2230; }}
h1, h2, h3 {{ color: {PLUM} !important; }}
p, label, .stMarkdown, .stCaption, .stText {{ color: #3A2230 !important; }}
[data-testid="stSidebar"] {{ background: #E9DED2; }}
[data-testid="stSidebar"] * {{ color: {PLUM} !important; }}
.stButton > button, .stFormSubmitButton > button, .stDownloadButton > button {{
    background: #FFFFFF !important; color: {PLUM} !important;
    border: 1px solid {PLUM} !important; border-radius: 12px;
}}
.stButton > button:hover, .stFormSubmitButton > button:hover, .stDownloadButton > button:hover {{
    background: #F0E6DA !important; color: {PLUM} !important;
}}
.stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] {{
    background: {PLUM} !important; color: {CREAM} !important; border: 0 !important;
}}
.stButton > button[kind="primary"]:hover, .stFormSubmitButton > button[kind="primary"]:hover {{
    background: {CHERRY} !important; color: {CREAM} !important;
}}
div[data-testid="stMetric"] {{ background: {PLUM}; padding: 14px; border-radius: 14px; }}
div[data-testid="stMetric"] * {{ color: {CREAM} !important; }}
.stAlert, div[data-testid="stNotification"] {{ background: #FFFFFF !important; border-radius: 12px; }}
.stAlert *, div[data-testid="stNotification"] * {{ color: {PLUM} !important; }}
[data-testid="stExpander"] {{ background: #FFFFFF; border-radius: 12px; }}
[data-testid="stExpander"] summary {{ color: {PLUM} !important; }}
input, textarea, select, [data-baseweb="input"] input,
[data-baseweb="select"] *, [data-baseweb="textarea"] * {{
    background: #FFFFFF !important; color: {PLUM} !important;
}}
</style>
""", unsafe_allow_html=True)

# ---------- ФУНКЦИИ РАБОТЫ С БД ----------
def rows(table, filters=None):
    q = supabase.table(table).select("*")
    if filters:
        for k, v in filters.items():
            q = q.eq(k, v)
    res = q.execute()
    return res.data

def execute_insert(table, data):
    supabase.table(table).insert(data).execute()
    st.cache_data.clear()

def execute_update(table, filters, data):
    q = supabase.table(table)
    for k, v in filters.items():
        q = q.eq(k, v)
    q.update(data).execute()
    st.cache_data.clear()

def execute_delete(table, filters):
    q = supabase.table(table)
    for k, v in filters.items():
        q = q.eq(k, v)
    q.delete().execute()
    st.cache_data.clear()

# ---------- ВХОД ----------
def login_screen():
    st.title("smart closet"); st.caption("YOUR PERSONAL WARDROBE")
    st.write("Войди через Google, чтобы открыть свой личный гардероб.")
    st.info("Для входа настрой Google OAuth в файле `.streamlit/secrets.toml`.")
    if st.button("Продолжить через Google", use_container_width=True): st.login()

if not st.user.is_logged_in:
    login_screen(); st.stop()

user_email = str(st.user.get("email", ""))
user_id = hashlib.sha256(user_email.lower().encode()).hexdigest()[:24]
user_dir = UPLOAD_DIR / user_id; user_dir.mkdir(parents=True, exist_ok=True)
display_name = st.user.get("name", "Пользователь")

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
NEW_OPTION = "Создать новую..."

@st.cache_data(ttl=30, show_spinner=False)
def get_custom_categories(uid):
    return rows("custom_categories", {"user_id": uid})

def build_category_tree(uid):
    tree = {k: list(v) for k, v in BASE_CATEGORY_TREE.items()}
    customs = get_custom_categories(uid)
    for c in customs:
        if not c["parent_category"]:
            if c["name"] not in tree: tree[c["name"]] = ["Другое"]
    for c in customs:
        if c["parent_category"]:
            p = c["parent_category"]
            if p in tree and c["name"] not in tree[p]: tree[p].append(c["name"])
            elif p not in tree: tree[p] = [c["name"]]
    return tree

def add_custom_category(uid, name, parent_category=""):
    name = name.strip()
    if not name: return False
    customs = get_custom_categories(uid)
    for c in customs:
        if c["name"].lower() == name.lower() and (c["parent_category"] or "") == (parent_category or ""):
            return False
    execute_insert("custom_categories", {"id": uuid.uuid4().hex, "user_id": uid, "name": name, "parent_category": parent_category or ""})
    return True

CATEGORY_TREE = build_category_tree(user_id)
CATEGORIES = list(CATEGORY_TREE.keys())

def save_image(uploaded):
    if uploaded is None: return None
    image = Image.open(uploaded).convert("RGB")
    image.thumbnail((800, 800))
    path = user_dir / f"{uuid.uuid4().hex}.jpg"
    image.save(path, format="JPEG", quality=82, optimize=True)
    return str(path)

def show_image(path, width=220):
    if path and Path(path).exists(): st.image(path, width=width)

@st.cache_data(ttl=30, show_spinner=False)
def get_items_cached(uid): return rows("items", {"user_id": uid})

@st.cache_data(ttl=30, show_spinner=False)
def get_outfits_cached(uid): return rows("outfits", {"user_id": uid})

def get_items(): return get_items_cached(user_id)
def get_outfits(): return get_outfits_cached(user_id)

def item_name(i):
    m = {r["id"]: r["name"] for r in get_items()}
    return m.get(i, "Удалённая вещь")

def item_image(i):
    m = {r["id"]: r["image_path"] for r in get_items()}
    return m.get(i)

def stylist_tip(sel):
    if not sel: return "Добавь вещи в гардероб — и я помогу собрать сочетание."
    colors = [x["color"].lower() for x in sel if x["color"]]
    if len(set(colors)) == 1 and len(colors) > 1: return "В комплекте много одного цвета. Попробуй добавить нейтральный оттенок."
    if len(sel) == 1: return "Добавь ещё одну вещь или аксессуар, чтобы завершить комплект."
    return "Попробуй повторить один цвет в двух элементах образа — так комплект будет выглядеть цельнее."

st.sidebar.title("smart closet"); st.sidebar.caption(f"Привет, {display_name}!")
page = st.sidebar.radio("Меню", ["Главная", "Мой гардероб", "Мои образы", "Перед покупкой", "Стилист"])
if st.sidebar.button("Выйти из аккаунта"): st.logout()

items, outfits = get_items(), get_outfits()
if page == "Главная":
    st.title("Твой умный шкаф")
    st.write("Всё, что ты носишь, любишь и планируешь купить — в одном месте.")
    a, b, c = st.columns(3)
    a.metric("Вещей в гардеробе", len(items)); b.metric("Сохранённых образов", len(outfits))
    c.metric("Покупок на рассмотрении", len([p for p in rows("purchases", {"user_id": user_id, "decision": "Думаю"})]))
    st.subheader("Совет стилиста")
    st.success("Необязательно покупать новое: иногда новый образ получается из уже знакомых вещей.")
    st.subheader("Пора вспомнить")
    cutoff = (date.today() - timedelta(days=30)).isoformat()
    old = [x for x in items if not x["last_worn"] or x["last_worn"] < cutoff]
    if old:
        st.write("Эти вещи давно не отмечались как надетые:")
        for x in old[:8]: st.write(f"• **{x['name']}** — {x['last_worn'] or 'ещё не отмечали'}")
    else: st.write("Пока все вещи в актуальном использовании. Так держать!")

elif page == "Мой гардероб":
    st.title("Мой гардероб")
    if "show_add_form" not in st.session_state: st.session_state.show_add_form = False
    if st.button("Добавить вещь", type="primary"): st.session_state.show_add_form = not st.session_state.show_add_form

    if st.session_state.show_add_form:
        st.markdown("**Новая вещь**")
        cat_options = CATEGORIES + [NEW_OPTION]
        category_choice = st.selectbox("Категория", cat_options, key="add_cat")
        if category_choice == NEW_OPTION:
            new_cat = st.text_input("Название новой категории", key="add_new_cat")
            if st.button("Создать категорию", key="btn_new_cat"):
                if add_custom_category(user_id, new_cat, ""):
                    st.success(f"Категория «{new_cat.strip()}» создана."); st.rerun()
                else: st.error("Введите название или такая категория уже есть.")
            st.stop()
        category = category_choice
        sub_options = CATEGORY_TREE.get(category, ["Другое"]) + [NEW_OPTION]
        subcategory_choice = st.selectbox("Тип", sub_options, key="add_sub")
        if subcategory_choice == NEW_OPTION:
            new_sub = st.text_input("Название нового типа", key="add_new_sub")
            if st.button("Создать тип", key="btn_new_sub"):
                if add_custom_category(user_id, new_sub, category):
                    st.success(f"Тип «{new_sub.strip()}» создан в категории «{category}»."); st.rerun()
                else: st.error("Введите название или такой тип уже есть.")
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
            execute_insert("items", {"id": uuid.uuid4().hex, "user_id": user_id, "name": final_name, "category": category, "subcategory": subcategory, "occasion": occasion, "color": color, "season": season, "notes": notes, "image_path": path, "last_worn": None, "created_at": datetime.now().isoformat()})
            st.success("Вещь добавлена!"); st.session_state.show_add_form = False; st.rerun()

    f1, f2 = st.columns(2)
    cf = f1.selectbox("Категория", ["Все"] + CATEGORIES)
    of = f2.selectbox("Для чего", ["Все"] + OCCASIONS)
    filtered = [x for x in items if (cf == "Все" or x["category"] == cf) and (of == "Все" or x["occasion"] == of)]
    if not filtered: st.info("Пока здесь пусто. Добавь первую вещь!")
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
            if st.checkbox("Редактировать", key=f"ed_{x['id']}"):
                cat_options = CATEGORIES + [NEW_OPTION]
                idx_cat = cat_options.index(x["category"]) if x["category"] in cat_options else 0
                nc_choice = st.selectbox("Категория", cat_options, index=idx_cat, key=f"ec_{x['id']}")
                if nc_choice == NEW_OPTION:
                    new_cat = st.text_input("Название новой категории", key=f"newcat_{x['id']}")
                    if st.button("Создать категорию", key=f"btncat_{x['id']}"):
                        if add_custom_category(user_id, new_cat, ""):
                            st.success(f"Категория «{new_cat.strip()}» создана."); st.rerun()
                        else: st.error("Введите название или такая категория уже есть.")
                    st.stop()
                nc = nc_choice
                subs = CATEGORY_TREE.get(nc, ["Другое"]) + [NEW_OPTION]
                idx_sub = subs.index(x["subcategory"]) if x["subcategory"] in subs else 0
                nsub_choice = st.selectbox("Тип", subs, index=idx_sub, key=f"es_{x['id']}")
                if nsub_choice == NEW_OPTION:
                    new_sub = st.text_input("Название нового типа", key=f"newsub_{x['id']}")
                    if st.button("Создать тип", key=f"btnsub_{x['id']}"):
                        if add_custom_category(user_id, new_sub, nc):
                            st.success(f"Тип «{new_sub.strip()}» создан."); st.rerun()
                        else: st.error("Введите название или такой тип уже есть.")
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
                        execute_update("items", {"id": x["id"], "user_id": user_id}, {"name": final_name, "category": nc, "subcategory": nsub, "occasion": no, "color": ncol, "season": ns, "notes": nnt, "last_worn": nd.isoformat(), "image_path": path})
                        st.success("Вещь обновлена."); st.rerun()
            col_a, col_b = st.columns(2)
            if col_a.button("Удалить вещь", key=f"d_{x['id']}"):
                execute_delete("items", {"id": x["id"], "user_id": user_id})
                if x["image_path"] and Path(x["image_path"]).exists(): Path(x["image_path"]).unlink()
                st.rerun()
            if col_b.button("Отметить как надетую сегодня", key=f"w_{x['id']}"):
                execute_update("items", {"id": x["id"], "user_id": user_id}, {"last_worn": date.today().isoformat()}); st.rerun()

elif page == "Мои образы":
    st.title("Мои образы")
    if "show_outfit_form" not in st.session_state: st.session_state.show_outfit_form = False
    if st.button("Создать образ", type="primary"): st.session_state.show_outfit_form = not st.session_state.show_outfit_form
    if st.session_state.show_outfit_form:
        if not items: st.info("Сначала добавь хотя бы одну вещь.")
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
                    if not on.strip(): st.error("Дай образу название.")
                    elif not chosen: st.error("Выбери хотя бы одну вещь.")
                    else:
                        path = save_image(photo)
                        chosen_images = ",".join([item_image(i) or "" for i in chosen])
                        execute_insert("outfits", {"id": uuid.uuid4().hex, "user_id": user_id, "name": on, "occasion": occ, "item_ids": ",".join(chosen), "item_images": chosen_images, "notes": notes, "image_path": path, "created_at": datetime.now().isoformat()})
                        st.success("Образ сохранён!"); st.session_state.show_outfit_form = False; st.rerun()
    if not outfits: st.info("Пока нет сохранённых образов.")
    for o in outfits:
        with st.expander(o["name"]):
            if o["image_path"]: show_image(o["image_path"], 300)
            st.write(f"**Ситуация:** {o['occasion']}")
            ids = o["item_ids"].split(",") if o["item_ids"] else []
            st.write("**Вещи:** " + ", ".join(item_name(i) for i in ids))
            if ids:
                cols = st.columns(min(len(ids), 4))
                for idx, iid in enumerate(ids):
                    with cols[idx % 4]:
                        img = item_image(iid)
                        if img and Path(img).exists(): st.image(img, width=120)
                        st.caption(item_name(iid))
            st.write(o["notes"] or "")
            if st.checkbox("Редактировать образ", key=f"edo_{o['id']}"):
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
                        execute_update("outfits", {"id": o["id"], "user_id": user_id}, {"name": nn, "occasion": no, "item_ids": ",".join(nids), "item_images": chosen_images, "notes": nnt, "image_path": path})
                        st.success("Образ обновлён."); st.rerun()
            if st.button("Удалить образ", key=f"do_{o['id']}"):
                execute_delete("outfits", {"id": o["id"], "user_id": user_id})
                if o["image_path"] and Path(o["image_path"]).exists(): Path(o["image_path"]).unlink()
                st.rerun()

elif page == "Перед покупкой":
    st.title("Стоит ли покупать?")
    st.write("Проверь, действительно ли новая вещь нужна твоему гардеробу.")
    cat_options = CATEGORIES + [NEW_OPTION]
    category_choice = st.selectbox("Категория", cat_options, key="pur_cat")
    if category_choice == NEW_OPTION:
        new_cat = st.text_input("Название новой категории", key="pur_new_cat")
        if st.button("Создать категорию", key="pur_btn_cat"):
            if add_custom_category(user_id, new_cat, ""): st.success(f"Категория «{new_cat.strip()}» создана."); st.rerun()
            else: st.error("Введите название или такая категория уже есть.")
        st.stop()
    category = category_choice
    sub_options = CATEGORY_TREE.get(category, ["Другое"]) + [NEW_OPTION]
    sub_choice = st.selectbox("Тип", sub_options, key="pur_sub")
    if sub_choice == NEW_OPTION:
        new_sub = st.text_input("Название нового типа", key="pur_new_sub")
        if st.button("Создать тип", key="pur_btn_sub"):
            if add_custom_category(user_id, new_sub, category): st.success(f"Тип «{new_sub.strip()}» создан."); st.rerun()
            else: st.error("Введите название или такой тип уже есть.")
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
            st.session_state["purchase_review"] = {"name": name, "category": category, "subcategory": subcategory, "color": color, "price": price, "reason": reason, "similar_cat": [x["name"] for x in similar_cat], "similar_color": [x["name"] for x in similar_color]}
            execute_insert("purchases", {"id": uuid.uuid4().hex, "user_id": user_id, "name": name, "category": category, "subcategory": subcategory, "color": color, "price": price, "reason": reason, "decision": "Думаю", "created_at": datetime.now().isoformat()})
    review = st.session_state.get("purchase_review")
    if review:
        st.subheader("Мнение помощника")
        st.metric("Стоимость", f"{review['price']:,.0f} ₽".replace(",", " "))
        if review["similar_cat"]: st.warning(f"У тебя уже есть похожие вещи ({review['category']} / {review['subcategory']}): " + ", ".join(review["similar_cat"]))
        else: st.success(f"В категории «{review['category']} / {review['subcategory']}» пока нет вещей.")
        if review["color"] and review["similar_color"]: st.warning(f"Вещи того же цвета уже есть: " + ", ".join(review["similar_color"]))
        elif review["color"]: st.info(f"Вещей цвета «{review['color']}» пока нет — это может быть акцентом.")
        if not review["reason"].strip(): st.info("Попробуй сформулировать минимум два образа с покупкой.")
        elif len(review["reason"].strip()) > 20: st.success("Ты уже продумала назначение вещи.")
        st.write("Это подсказка, а не обязательное решение.")
        purchases = rows("purchases", {"user_id": user_id})
        if purchases:
            st.subheader("История решений")
            for p in purchases:
                price_val = float(p["price"]) if p["price"] not in (None, "") else 0.0
                st.write(f"• {p['name']} — {p['category']}/{p['subcategory'] or 'Другое'} — {p['color'] or 'цвет не указан'} — {price_val:,.0f} ₽ — {p['decision']}".replace(",", " "))
            if st.button("Очистить историю покупок", key="clear_purchases"):
                execute_delete("purchases", {"user_id": user_id}); st.success("История очищена."); st.rerun()
        else: st.info("История покупок пока пуста.")

elif page == "Стилист":
    st.title("Твой персональный стилист")
    st.write("Выбери ситуацию — я сам соберу несколько готовых образов.")
    occ = st.selectbox("Куда нужен образ?", OCCASIONS)
    pool = [x for x in items if x["occasion"] == occ or x["occasion"] == "Другое"]
    if not pool: st.info("Пока нет вещей с такой отметкой."); st.stop()
    def by_cat(cat): return [x for x in pool if x["category"] == cat]
    tops, bottoms = by_cat("Верх"), by_cat("Низ")
    dresses, shoes = by_cat("Платья и комбинезоны"), by_cat("Обувь")
    outer, bags, accs = by_cat("Верхняя одежда"), by_cat("Сумки"), by_cat("Аксессуары")
    if not (bool(tops and bottoms) or bool(dresses)):
        st.warning("Чтобы собрать образ, нужно хотя бы: верх + низ, либо платье."); st.stop()
    def color_key(x): return (x["color"] or "").strip().lower()
    def pick_accent(base):
        bc = {color_key(i) for i in base if color_key(i)}
        c = [a for a in accs if color_key(a) and color_key(a) not in bc]
        return random.choice(c) if c else (random.choice(accs) if accs else None)
    def pick_bag(base):
        bc = {color_key(i) for i in base if color_key(i)}
        c = [b for b in bags if color_key(b) and color_key(b) not in bc]
        return random.choice(c) if c else (random.choice(bags) if bags else None)
    def build_outfit():
        base = []
        if dresses and random.random() < 0.5: base.append(random.choice(dresses))
        elif tops and bottoms: base.append(random.choice(tops)); base.append(random.choice(bottoms))
        elif dresses: base.append(random.choice(dresses))
        else: return None
        if shoes: base.append(random.choice(shoes))
        if outer and random.random() < 0.6: base.append(random.choice(outer))
        bag = pick_bag(base)
        if bag: base.append(bag)
        acc = pick_accent(base)
        if acc: base.append(acc)
        seen, res = set(), []
        for it in base:
            if it["id"] not in seen: seen.add(it["id"]); res.append(it)
        return res
    if "stylist_variants" not in st.session_state or st.session_state.get("stylist_occ") != occ:
        st.session_state.stylist_occ = occ; st.session_state.stylist_variants = []
    if st.button("Собрать образы", type="primary") or not st.session_state.stylist_variants:
        variants, sigs = [], set()
        for _ in range(60):
            if len(variants) >= 3: break
            o = build_outfit()
            if not o: break
            sig = tuple(sorted(i["id"] for i in o))
            if sig in sigs: continue
            sigs.add(sig); variants.append(o)
        st.session_state.stylist_variants = variants
    variants = st.session_state.stylist_variants
    if not variants: st.warning("Не удалось собрать образ. Проверь наличие верха и низа."); st.stop()
    st.subheader(f"Готовые образы для «{occ.lower()}»")
    for idx, outfit in enumerate(variants, 1):
        with st.container(border=True):
            st.markdown(f"### Образ {idx}")
            cols = st.columns(min(len(outfit), 4))
            for j, it in enumerate(outfit):
                with cols[j % 4]:
                    show_image(it["image_path"], 140)
                    st.caption(f"**{it['name']}**"); st.caption(f"{it['category']} / {it['subcategory']}")
                    if it["color"]: st.caption(f"Цвет: {it['color']}")
            st.write("**Состав:** " + ", ".join(it["name"] for it in outfit))
            uc = set(color_key(it) for it in outfit if color_key(it))
            if len(uc) >= 3: st.info("3+ цвета — следи за сочетанием.")
            elif len(uc) == 1: st.info("Один цвет — можно добавить акцент.")
            else: st.success("2 цвета — базовый и поддерживающий.")
    if st.button("Собрать другие варианты"): st.session_state.stylist_variants = []; st.rerun()
