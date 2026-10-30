import sqlite3
import uuid
from datetime import date
from itertools import product
from pathlib import Path

import streamlit  as st

# ---------- РќР°СЃС‚СЂРѕР№РєРё РїСЂРѕРµРєС‚Р° ----------
APP_DIR = Path(__file__).parent
DB_PATH = APP_DIR / "wardrobe.db"
UPLOAD_DIR = APP_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

CATEGORIES = [
    "Р’РµСЂС…",
    "РќРёР·",
    "РџР»Р°С‚СЊРµ / РєРѕРјР±РёРЅРµР·РѕРЅ",
    "РћР±СѓРІСЊ",
    "Р’РµСЂС…РЅСЏСЏ РѕРґРµР¶РґР°",
    "РђРєСЃРµСЃСЃСѓР°СЂ",
    "Р”СЂСѓРіРѕРµ",
]
SEASONS = ["Р’СЃРµСЃРµР·РѕРЅРЅР°СЏ", "Р’РµСЃРЅР°", "Р›РµС‚Рѕ", "РћСЃРµРЅСЊ", "Р—РёРјР°"]
OCCASIONS = ["РџРѕРІСЃРµРґРЅРµРІРЅС‹Р№", "РЈС‡С‘Р±Р° / СЂР°Р±РѕС‚Р°", "РџСЂР°Р·РґРЅРёРє", "РЎРїРѕСЂС‚", "РџСЂРѕРіСѓР»РєР°"]


CREAM = "#F7F3F7"       
PLUM = "#4B3152"        
CHERRY = "#963B55"      
BUTTER = "#F2DE93"     
INK = "#2D2430"         
SIDEBAR = "#E9E1EB"    
SURFACE = "#FFFFFF"    
BORDER = "#D8CBDC"     

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

      /* РџРѕР»СЏ РІРІРѕРґР° вЂ” СЃРІРµС‚Р»С‹Р№ С„РѕРЅ, С‚С‘РјРЅС‹Р№ С‚РµРєСЃС‚ */
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

      /* РљРЅРѕРїРєРё */
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

      /* Р¤РѕСЂРјС‹ Рё РєР°СЂС‚РѕС‡РєРё */
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
# ---------- Р‘Р°Р·Р° РґР°РЅРЅС‹С… ----------
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
        return conn.execute(
            "SELECT * FROM outfits ORDER BY id DESC"
        ).fetchall()


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
    """РћР±РЅРѕРІР»СЏРµС‚ РІРµС‰СЊ. Р•СЃР»Рё РЅРѕРІРѕРµ С„РѕС‚Рѕ РЅРµ Р·Р°РіСЂСѓР¶РµРЅРѕ, СЃС‚Р°СЂРѕРµ РѕСЃС‚Р°С‘С‚СЃСЏ."""
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
        conn.execute(
            "DELETE FROM outfits WHERE id = ?",
            (outfit_id,),
        )

# ---------- РџРѕРґР±РѕСЂ РїРѕ С†РІРµС‚Р°Рј ----------
COLOR_GROUPS = {
    "РЅРµР№С‚СЂР°Р»СЊРЅС‹Р№": [
        "Р±РµР»", "С‡С‘СЂРЅ", "С‡РµСЂРЅ", "СЃРµСЂ", "Р±РµР¶", "РєСЂРµРј",
        "РјРѕР»РѕС‡", "РєРѕСЂРёС‡РЅРµРІ", "РєРѕСЂРёС‡РЅ",
    ],
    "СЃРёРЅРёР№": ["СЃРёРЅ", "РіРѕР»СѓР±", "РґР¶РёРЅСЃ", "РґРµРЅРёРј"],
    "Р·РµР»С‘РЅС‹Р№": ["Р·РµР»С‘РЅ", "Р·РµР»РµРЅ", "РѕР»РёРІ", "С…Р°РєРё", "РјСЏС‚"],
    "РєСЂР°СЃРЅС‹Р№": ["РєСЂР°СЃРЅ", "Р±РѕСЂРґРѕРІ", "РІРёС€РЅ", "РјР°СЂСЃР°Р»"],
    "СЂРѕР·РѕРІС‹Р№": ["СЂРѕР·РѕРІ", "РїСѓРґСЂРѕРІ"],
    "Р¶С‘Р»С‚С‹Р№": ["Р¶С‘Р»С‚", "Р¶РµР»С‚", "РіРѕСЂС‡РёС‡"],
    "С„РёРѕР»РµС‚РѕРІС‹Р№": ["С„РёРѕР»РµС‚", "Р»РёР»РѕРІ", "СЃР»РёРІРѕРІ"],
}


def color_group(color):
    value = color.casefold().strip()
    for group, words in COLOR_GROUPS.items():
        if any(word in value for word in words):
            return group
    return value


def colors_compatible(color_a, color_b):
    """РџСЂРѕСЃС‚Р°СЏ СЌРІСЂРёСЃС‚РёРєР°, Р° РЅРµ Р°РІС‚РѕРјР°С‚РёС‡РµСЃРєР°СЏ РѕС†РµРЅРєР° СЃС‚РёР»СЏ."""
    group_a = color_group(color_a)
    group_b = color_group(color_b)

    if group_a == group_b:
        return True

    if group_a == "РЅРµР№С‚СЂР°Р»СЊРЅС‹Р№" or group_b == "РЅРµР№С‚СЂР°Р»СЊРЅС‹Р№":
        return True

    friendly_pairs = {
        frozenset(("СЃРёРЅРёР№", "РєРѕСЂРёС‡РЅРµРІС‹Р№")),
        frozenset(("СЃРёРЅРёР№", "Р¶С‘Р»С‚С‹Р№")),
        frozenset(("Р·РµР»С‘РЅС‹Р№", "РєРѕСЂРёС‡РЅРµРІС‹Р№")),
        frozenset(("Р·РµР»С‘РЅС‹Р№", "Р¶С‘Р»С‚С‹Р№")),
        frozenset(("РєСЂР°СЃРЅС‹Р№", "СЃРёРЅРёР№")),
        frozenset(("СЂРѕР·РѕРІС‹Р№", "С„РёРѕР»РµС‚РѕРІС‹Р№")),
    }
    return frozenset((group_a, group_b)) in friendly_pairs


def same_color_family(color_a, color_b):
    return color_group(color_a) == color_group(color_b)
def fits_occasion(item, occasion):
    """Р’РµС‰Рё Р±РµР· СѓРєР°Р·Р°РЅРЅРѕРіРѕ РїРѕРІРѕРґР° СЃС‡РёС‚Р°СЋС‚СЃСЏ РїРѕРґС…РѕРґСЏС‰РёРјРё РґР»СЏ Р»СЋР±РѕРіРѕ РїРѕРІРѕРґР°."""
    item_occasions = [
        value.strip()
        for value in (item["occasions"] or "").split(",")
        if value.strip()
    ]
    return not item_occasions or occasion in item_occasions


def suggest_outfits(clothes, occasion, target_item=None, limit=3):
    """
    РЎРѕР±РёСЂР°РµС‚ РїСЂРѕСЃС‚С‹Рµ РІР°СЂРёР°РЅС‚С‹:
    РІРµСЂС… + РЅРёР· (+ РѕР±СѓРІСЊ) РёР»Рё РїР»Р°С‚СЊРµ (+ РѕР±СѓРІСЊ).
    Р”Р»СЏ РЅР°РїРѕРјРёРЅР°РЅРёСЏ СЃС‚Р°СЂР°РµС‚СЃСЏ РІРєР»СЋС‡РёС‚СЊ РІС‹Р±СЂР°РЅРЅСѓСЋ Р·Р°Р±С‹С‚СѓСЋ РІРµС‰СЊ.
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

    tops = [item for item in candidates if item["category"] == "Р’РµСЂС…"]
    bottoms = [item for item in candidates if item["category"] == "РќРёР·"]
    dresses = [
        item for item in candidates
        if item["category"] == "РџР»Р°С‚СЊРµ / РєРѕРјР±РёРЅРµР·РѕРЅ"
    ]
    shoes = [item for item in candidates if item["category"] == "РћР±СѓРІСЊ"]

    results = []

    if target_item is not None:
        if target_item["category"] == "Р’РµСЂС…":
            tops = [target_item]
        elif target_item["category"] == "РќРёР·":
            bottoms = [target_item]
        elif target_item["category"] == "РџР»Р°С‚СЊРµ / РєРѕРјР±РёРЅРµР·РѕРЅ":
            dresses = [target_item]
        elif target_item["category"] == "РћР±СѓРІСЊ":
            shoes = [target_item]
        else:

            candidates = [
                item for item in candidates
                if item["category"] in {"Р’РµСЂС…", "РќРёР·", "РћР±СѓРІСЊ",
                                        "РџР»Р°С‚СЊРµ / РєРѕРјР±РёРЅРµР·РѕРЅ"}
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
        st.caption(" Р¤РѕС‚Рѕ РЅРµ РґРѕР±Р°РІР»РµРЅРѕ")


def show_outfit(outfit):
    """РџРѕРєР°Р·С‹РІР°РµС‚ РєРѕРјРїР»РµРєС‚ РєР°СЂС‚РѕС‡РєР°РјРё СЃ С„РѕС‚РѕРіСЂР°С„РёСЏРјРё Рё РїРѕРґРїРёСЃСЏРјРё."""
    if not outfit:
        st.caption("Р’ СЌС‚РѕРј РѕР±СЂР°Р·Рµ РїРѕРєР° РЅРµС‚ РІРµС‰РµР№.")
        return


    for start in range(0, len(outfit), 3):
        row_items = outfit[start:start + 3]
        cols = st.columns(len(row_items))

        for col, item in zip(cols, row_items):
            with col:
                photo_path = item["photo_path"]

                if photo_path and Path(photo_path).exists():
                    st.image(photo_path, width=220)
                else:
                    st.info("Р”Р»СЏ СЌС‚РѕР№ РІРµС‰Рё РїРѕРєР° РЅРµС‚ С„РѕС‚Рѕ")

                st.caption(
                    f"**{item['name']}**\n\n"
                    f"{item['category']} В· {item['color']}"
                )



init_db()
clothes = get_clothes()

st.sidebar.markdown("## РЈРјРЅС‹Р№ С€РєР°С„")
st.sidebar.caption("РўРІРѕР№ РіР°СЂРґРµСЂРѕР± вЂ” СЃ СѓРјРѕРј")
page = st.sidebar.radio(
    "Р Р°Р·РґРµР»",
    [
        "Р“Р»Р°РІРЅР°СЏ",
        "РњРѕР№ РіР°СЂРґРµСЂРѕР±",
        "РџРѕРґРѕР±СЂР°С‚СЊ РѕР±СЂР°Р·",
        "РџРµСЂРµРґ РїРѕРєСѓРїРєРѕР№",
        "РџРѕСЂР° РЅР°РґРµС‚СЊ",
        "РњРѕРё РѕР±СЂР°Р·С‹",
    ],
)
st.sidebar.markdown("---")
st.sidebar.markdown(
    f"<span class='tag'>Plum В· Cherry В· Butter</span>",
    unsafe_allow_html=True,
)
st.sidebar.caption("Р”Р°РЅРЅС‹Рµ С…СЂР°РЅСЏС‚СЃСЏ РІ Р»РѕРєР°Р»СЊРЅРѕР№ Р±Р°Р·Рµ wardrobe.db")



if page == "Р“Р»Р°РІРЅР°СЏ":
    st.markdown(
        """
        <div class="hero">
          <h1>РўРІРѕР№ РіР°СЂРґРµСЂРѕР±. РўРІРѕРё СЂРµС€РµРЅРёСЏ.</h1>
          <p>РЎРѕР±РёСЂР°Р№ РѕР±СЂР°Р·С‹, РІРѕР·РІСЂР°С‰Р°Р№ Р·Р°Р±С‹С‚С‹Рµ РІРµС‰Рё Рё РїРѕРєСѓРїР°Р№ РѕСЃРѕР·РЅР°РЅРЅРѕ.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    forgotten = [item for item in clothes if days_since_last_worn(item) >= 30]
    c1, c2, c3 = st.columns(3)
    c1.metric("Р’РµС‰РµР№ РІ РіР°СЂРґРµСЂРѕР±Рµ", len(clothes))
    c2.metric("Р”Р°РІРЅРѕ РЅРµ РЅР°РґРµРІР°Р»РёСЃСЊ", len(forgotten))
    c3.metric("РЎРѕС…СЂР°РЅС‘РЅРЅС‹С… РѕР±СЂР°Р·РѕРІ", len(get_outfits()))

    st.subheader("Р§С‚Рѕ СѓРјРµРµС‚ РїСЂРёР»РѕР¶РµРЅРёРµ")
    col1, col2 = st.columns(2)
    col1.info(
        "**РњРѕР№ РіР°СЂРґРµСЂРѕР±**\n\n"
        "Р”РѕР±Р°РІР»СЏР№ С„РѕС‚РѕРіСЂР°С„РёРё, РєР°С‚РµРіРѕСЂРёРё, С†РІРµС‚Р°, СЃРµР·РѕРЅС‹ Рё РїРѕРІРѕРґС‹."
    )
    col2.info(
        "**РџРѕРґР±РѕСЂ РѕР±СЂР°Р·Р°**\n\n"
        "РџРѕР»СѓС‡Р°Р№ РїСЂРѕСЃС‚С‹Рµ РІР°СЂРёР°РЅС‚С‹ СЃРѕС‡РµС‚Р°РЅРёР№ РёР· СѓР¶Рµ РґРѕР±Р°РІР»РµРЅРЅС‹С… РІРµС‰РµР№."
    )
    col3, col4 = st.columns(2)
    col3.info(
        "**РџРѕСЂР° РЅР°РґРµС‚СЊ**\n\n"
        "РќР°С…РѕРґРё РІРµС‰Рё, РєРѕС‚РѕСЂС‹Рµ РґР°РІРЅРѕ РЅРµ РѕС‚РјРµС‡Р°Р»РёСЃСЊ РєР°Рє РЅР°РґРµС‚С‹Рµ."
    )
    col4.info(
        "**РџРµСЂРµРґ РїРѕРєСѓРїРєРѕР№**\n\n"
        "РџСЂРѕРІРµСЂСЏР№, РµСЃС‚СЊ Р»Рё РїРѕС…РѕР¶Р°СЏ РІРµС‰СЊ Рё СЃ С‡РµРј СЃРѕС‡РµС‚Р°С‚СЊ РѕР±РЅРѕРІРєСѓ."
    )

    if forgotten:
        st.subheader("РњРѕР¶РЅРѕ РІРµСЂРЅСѓС‚СЊ РІ РѕР±СЂР°Р·С‹")
        for item in forgotten[:3]:
            st.write(
                f"вЂў **{item['name']}** вЂ” "
                f"{days_since_last_worn(item)} РґРЅ. Р±РµР· РѕС‚РјРµС‚РєРё Рѕ РЅРѕСЃРєРµ"
            )



elif page == "РњРѕР№ РіР°СЂРґРµСЂРѕР±":
    st.title("РњРѕР№ РіР°СЂРґРµСЂРѕР±")
    st.caption("Р”РѕР±Р°РІР»СЏР№ РІРµС‰Рё вЂ” С‚Р°Рє РїРѕРґСЃРєР°Р·РєРё РїСЂРёР»РѕР¶РµРЅРёСЏ СЃС‚Р°РЅСѓС‚ РїРѕР»РµР·РЅРµРµ.")

    with st.expander("пј‹ Р”РѕР±Р°РІРёС‚СЊ РІРµС‰СЊ", expanded=(len(clothes) == 0)):
        with st.form("add_clothing_form", clear_on_submit=True):
            name = st.text_input(
                "РќР°Р·РІР°РЅРёРµ РІРµС‰Рё *",
                placeholder="РќР°РїСЂРёРјРµСЂ, Р±РµР»Р°СЏ СЂСѓР±Р°С€РєР°",
            )
            col1, col2 = st.columns(2)

            with col1:
                category = st.selectbox("РљР°С‚РµРіРѕСЂРёСЏ", CATEGORIES)
                color = st.text_input(
                    "РћСЃРЅРѕРІРЅРѕР№ С†РІРµС‚ *",
                    placeholder="РќР°РїСЂРёРјРµСЂ, Р±РµР»С‹Р№",
                )
                season = st.selectbox("РЎРµР·РѕРЅ", SEASONS)

            with col2:
                photo = st.file_uploader(
                    "Р¤РѕС‚РѕРіСЂР°С„РёСЏ",
                    type=["jpg", "jpeg", "png", "webp"],
                )
                occasions = st.multiselect(
                    "Р”Р»СЏ РєР°РєРёС… РїРѕРІРѕРґРѕРІ РїРѕРґС…РѕРґРёС‚",
                    OCCASIONS,
                )
                notes = st.text_area(
                    "Р—Р°РјРµС‚РєРё",
                    placeholder="РњР°С‚РµСЂРёР°Р», СЃС‚РёР»СЊ, СЃ С‡РµРј СЃРѕС‡РµС‚Р°РµС‚СЃСЏвЂ¦",
                )

            submitted = st.form_submit_button("РЎРѕС…СЂР°РЅРёС‚СЊ РІРµС‰СЊ")

            if submitted:
                if not name.strip() or not color.strip():
                    st.error("Р—Р°РїРѕР»РЅРё РЅР°Р·РІР°РЅРёРµ Рё С†РІРµС‚ РІРµС‰Рё.")
                else:
                    photo_path = save_photo(photo)
                    add_clothing(
                        name, category, color, season, notes,
                        photo_path, occasions,
                    )
                    st.success("Р’РµС‰СЊ РґРѕР±Р°РІР»РµРЅР°!")
                    st.rerun()

    if not clothes:
        st.info("РџРѕРєР° РіР°СЂРґРµСЂРѕР± РїСѓСЃС‚. Р”РѕР±Р°РІСЊ РїРµСЂРІСѓСЋ РІРµС‰СЊ РІС‹С€Рµ.")
    else:
        f1, f2 = st.columns(2)
        with f1:
            category_filter = st.selectbox(
                "Р¤РёР»СЊС‚СЂ РїРѕ РєР°С‚РµРіРѕСЂРёРё",
                ["Р’СЃРµ"] + sorted({item["category"] for item in clothes}),
            )
        with f2:
            search = st.text_input("РџРѕРёСЃРє РїРѕ РЅР°Р·РІР°РЅРёСЋ РёР»Рё С†РІРµС‚Сѓ")

        filtered = [
            item for item in clothes
            if (category_filter == "Р’СЃРµ"
                or item["category"] == category_filter)
            and search.casefold() in (
                item["name"] + " " + item["color"]
            ).casefold()
        ]

        st.caption(f"РџРѕРєР°Р·Р°РЅРѕ РІРµС‰РµР№: {len(filtered)}")
        cols = st.columns(3)

        for index, item in enumerate(filtered):
            with cols[index % 3]:
                with st.container(border=True):
                    show_photo(item["photo_path"], 240)
                    st.subheader(item["name"])
                    st.caption(
                        f"{item['category']} В· {item['color']} В· "
                        f"{item['season']}"
                    )

                    if item["occasions"]:
                        st.caption(f"РџРѕРІРѕРґС‹: {item['occasions']}")
                    if item["notes"]:
                        st.write(item["notes"])
                        with st.expander("Р РµРґР°РєС‚РёСЂРѕРІР°С‚СЊ РІРµС‰СЊ"):
                            with st.form(f"edit_clothing_{item['id']}"):
                                edited_name = st.text_input(
                                    "РќР°Р·РІР°РЅРёРµ",
                                    value=item["name"],
                                    key=f"edit_name_{item['id']}",)
                                category_index = (
                                    CATEGORIES.index(item["category"])
                                    if item["category"] in CATEGORIES else 0
                                )
                                edited_category = st.selectbox(
                                    "РљР°С‚РµРіРѕСЂРёСЏ",
                                    CATEGORIES,
                                    index=category_index,
                                    key=f"edit_category_{item['id']}",
                                )
                                edited_color = st.text_input(
                                    "Р¦РІРµС‚",
                                    value=item["color"],
                                    key=f"edit_color_{item['id']}",
                                )
                                season_index = (
                                    SEASONS.index(item["season"])
                                    if item["season"] in SEASONS else 0
                                )
                                edited_season = st.selectbox(
                                    "РЎРµР·РѕРЅ",
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
                                    "Р”Р»СЏ РєР°РєРёС… РїРѕРІРѕРґРѕРІ РїРѕРґС…РѕРґРёС‚",
                                    OCCASIONS,
                                    default=[x for x in old_occasions if x in OCCASIONS],
                                    key=f"edit_occasions_{item['id']}",
                                )
                                edited_notes = st.text_area(
                                    "Р—Р°РјРµС‚РєРё",
                                    value=item["notes"] or "",
                                    key=f"edit_notes_{item['id']}",
                                )
                                replacement_photo = st.file_uploader(
                                    "РќРѕРІРѕРµ С„РѕС‚Рѕ (РЅРµРѕР±СЏР·Р°С‚РµР»СЊРЅРѕ)",
                                    type=["jpg", "jpeg", "png", "webp"],
                                    key=f"edit_photo_{item['id']}",
                                )
                                save_edit = st.form_submit_button("РЎРѕС…СЂР°РЅРёС‚СЊ РёР·РјРµРЅРµРЅРёСЏ")
                                if save_edit:
                                    if not edited_name.strip() or not edited_color.strip():
                                        st.error("РќР°Р·РІР°РЅРёРµ Рё С†РІРµС‚ РЅРµ РґРѕР»Р¶РЅС‹ Р±С‹С‚СЊ РїСѓСЃС‚С‹РјРё.")
                                    else:
                                        new_photo_path = (
                                            save_photo(replacement_photo)
                                            if replacement_photo is not None
                                            else None
                                        )
                                        update_clothing(
                                            item["id"],
                                            edited_name,
                                            edited_category,
                                            edited_color,
                                            edited_season,
                                            edited_notes,
                                            edited_occasions,
                                            new_photo_path,
                                        )
                                        st.success("РР·РјРµРЅРµРЅРёСЏ СЃРѕС…СЂР°РЅРµРЅС‹.")
                                        st.rerun()
                                        last_text = item["last_worn"] or "РџРѕРєР° РЅРµ РѕС‚РјРµС‡РµРЅРѕ"
                                        st.caption(f"РџРѕСЃР»РµРґРЅСЏСЏ РЅРѕСЃРєР°: {last_text}")
                                        if st.button(
                                            "РќР°РґРµР»Р° СЃРµРіРѕРґРЅСЏ",
                                            key=f"worn_{item['id']}",
                                            use_container_width=True,
                                        ):
                                            mark_worn(item["id"])
                                            st.rerun()
                                        if st.button(
                                            "РЈРґР°Р»РёС‚СЊ РІРµС‰СЊ",
                                            key=f"delete_{item['id']}",
                                            use_container_width=True,
                                        ):
                                            delete_clothing(item["id"])
                                            st.rerun()



elif page == "РџРѕРґРѕР±СЂР°С‚СЊ РѕР±СЂР°Р·":
    st.title("РџРѕРґРѕР±СЂР°С‚СЊ РѕР±СЂР°Р·")
    st.write(
        "РџСЂРёР»РѕР¶РµРЅРёРµ РїСЂРµРґР»Р°РіР°РµС‚ СЃРѕС‡РµС‚Р°РЅРёСЏ РїРѕ РєР°С‚РµРіРѕСЂРёСЏРј, С†РІРµС‚Р°Рј Рё РІС‹Р±СЂР°РЅРЅРѕРјСѓ РїРѕРІРѕРґСѓ."
    )

    if len(clothes) < 2:
        st.info("Р”РѕР±Р°РІСЊ РІ РіР°СЂРґРµСЂРѕР± С…РѕС‚СЏ Р±С‹ РґРІРµ РІРµС‰Рё.")
    else:
        occasion = st.selectbox("РџРѕРІРѕРґ", OCCASIONS)
        suggestions = suggest_outfits(clothes, occasion)

        if not suggestions:
            st.warning(
                "РџРѕРєР° РЅРµ СѓРґР°Р»РѕСЃСЊ СЃРѕР±СЂР°С‚СЊ РєРѕРјРїР»РµРєС‚. Р”РѕР±Р°РІСЊ РІРµС‰Рё СЂР°Р·РЅС‹С… "
                "РєР°С‚РµРіРѕСЂРёР№ вЂ” РЅР°РїСЂРёРјРµСЂ, РІРµСЂС… Рё РЅРёР·."
            )
        else:
            st.subheader("Р’Р°СЂРёР°РЅС‚С‹ РёР· С‚РІРѕРµРіРѕ РіР°СЂРґРµСЂРѕР±Р°")
            for index, outfit in enumerate(suggestions, start=1):
                with st.container(border=True):
                    st.markdown(f"**Р’Р°СЂРёР°РЅС‚ {index}**")
                    show_outfit(outfit)

                    outfit_name = st.text_input(
                        "РќР°Р·РІР°РЅРёРµ РєРѕРјРїР»РµРєС‚Р°",
                        value=f"{occasion}: РІР°СЂРёР°РЅС‚ {index}",
                        key=f"outfit_name_{index}",
                    )
                    if st.button(
                        "РЎРѕС…СЂР°РЅРёС‚СЊ СЌС‚РѕС‚ РѕР±СЂР°Р·",
                        key=f"save_suggested_{index}",
                    ):
                        save_outfit(
                            outfit_name,
                            [item["id"] for item in outfit],
                        )
                        st.success("РћР±СЂР°Р· СЃРѕС…СЂР°РЅС‘РЅ!")
                        st.rerun()



elif page == "РџРµСЂРµРґ РїРѕРєСѓРїРєРѕР№":
    st.title("РџРµСЂРµРґ РїРѕРєСѓРїРєРѕР№")
    st.write(
        "РџСЂРѕРІРµСЂСЊ, РЅРµС‚ Р»Рё РїРѕС…РѕР¶РµР№ РІРµС‰Рё Рё СЃ С‡РµРј РїРѕРєСѓРїРєР° РјРѕР¶РµС‚ СЃРѕС‡РµС‚Р°С‚СЊСЃСЏ. "
        "Р­С‚Рѕ РѕСЂРёРµРЅС‚РёСЂ, Р° РЅРµ РіР°СЂР°РЅС‚РёСЏ РёРґРµР°Р»СЊРЅРѕРіРѕ РІС‹Р±РѕСЂР°."
    )

    with st.form("purchase_form"):
        purchase_name = st.text_input(
            "Р§С‚Рѕ С…РѕС‡РµС€СЊ РєСѓРїРёС‚СЊ?",
            placeholder="РќР°РїСЂРёРјРµСЂ, Р±РµР¶РµРІС‹Р№ РєР°СЂРґРёРіР°РЅ",
        )
        col1, col2 = st.columns(2)

        with col1:
            purchase_category = st.selectbox(
                "РљР°С‚РµРіРѕСЂРёСЏ",
                CATEGORIES,
                key="purchase_category",
            )
            purchase_color = st.text_input(
                "Р¦РІРµС‚",
                placeholder="РќР°РїСЂРёРјРµСЂ, Р±РµР¶РµРІС‹Р№",
            )
            price = st.number_input(
                "Р¦РµРЅР° РїРѕРєСѓРїРєРё, в‚Ѕ",
                min_value=0,
                value=3500,
                step=500,
                )

        with col2:
            budget = st.number_input(
                "Р‘СЋРґР¶РµС‚ РЅР° РїРѕРєСѓРїРєСѓ, в‚Ѕ",
                min_value=0,
                value=5000,
                step=500,
            )
            occasion = st.selectbox(
                "Р”Р»СЏ РєР°РєРѕРіРѕ РїРѕРІРѕРґР° РЅСѓР¶РЅР° РІРµС‰СЊ?",
                OCCASIONS,
                key="purchase_occasion",
            )

        reason = st.text_area(
            "Р—Р°С‡РµРј С‚РµР±Рµ СЌС‚Р° РІРµС‰СЊ?",
            placeholder="РќР°РїСЂРёРјРµСЂ, РЅСѓР¶РЅР° РѕРґРµР¶РґР° РґР»СЏ СѓС‡С‘Р±С‹.",
        )
        purchase_submitted = st.form_submit_button("РџСЂРѕРІРµСЂРёС‚СЊ РїРѕРєСѓРїРєСѓ")

    if purchase_submitted:
        if not purchase_name.strip():
            st.error("РќР°РїРёС€Рё РЅР°Р·РІР°РЅРёРµ РІРµС‰Рё.")
        else:
            # Р’РµС‰Рё С‚РѕР№ Р¶Рµ РєР°С‚РµРіРѕСЂРёРё РїРѕРєР°Р·С‹РІР°СЋС‚СЃСЏ РєР°Рє РІРѕР·РјРѕР¶РЅС‹Рµ РґСѓР±Р»Рё.
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

            st.subheader("Р РµРєРѕРјРµРЅРґР°С†РёСЏ")
            score = 0

            if price <= budget:
                st.success("Р¦РµРЅР° СѓРєР»Р°РґС‹РІР°РµС‚СЃСЏ РІ СѓРєР°Р·Р°РЅРЅС‹Р№ Р±СЋРґР¶РµС‚.")
                score += 1
            else:
                st.warning("Р¦РµРЅР° РІС‹С€Рµ СѓРєР°Р·Р°РЅРЅРѕРіРѕ Р±СЋРґР¶РµС‚Р°.")

            if same_category:
                st.warning(
                    f"Р’ РіР°СЂРґРµСЂРѕР±Рµ РµСЃС‚СЊ {len(same_category)} РІРµС‰. "
                    "С‚РѕР№ Р¶Рµ РєР°С‚РµРіРѕСЂРёРё вЂ” РїСЂРѕРІРµСЂСЊ, РЅРµ Р±СѓРґРµС‚ Р»Рё СЌС‚Рѕ РґСѓР±Р»РµРј."
                )
                st.markdown("**Р§С‚Рѕ СѓР¶Рµ РµСЃС‚СЊ:**")
                for item in same_category[:5]:
                    st.write(
                        f"вЂў {item['name']} вЂ” {item['color']} "
                        f"({item['category']})"
                    )
            else:
                st.success("Р’РµС‰РµР№ СЌС‚РѕР№ РєР°С‚РµРіРѕСЂРёРё РІ РіР°СЂРґРµСЂРѕР±Рµ РїРѕРєР° РЅРµС‚.")
                score += 1

            
            compatible_items = [
                item for item in clothes
                if item["category"] != purchase_category
                and colors_compatible(item["color"], purchase_color)
                and fits_occasion(item, occasion)
            ] if purchase_color.strip() else []

            if compatible_items:
                st.markdown(
                    f"**РР· РіР°СЂРґРµСЂРѕР±Р° РјРѕР¶РµС‚ РїРѕРґРѕР№С‚Рё Рє РїРѕРєСѓРїРєРµ "
                    f"РґР»СЏ РїРѕРІРѕРґР° В«{occasion}В»:**"
                )
                for item in compatible_items[:5]:
                    st.write(f"вЂў {item['name']} вЂ” {item['color']}")

            if reason.strip():
                st.info(
                    "РўС‹ СѓРєР°Р·Р°Р»Р° С†РµР»СЊ РїРѕРєСѓРїРєРё. РџСЂРѕРІРµСЂСЊ, РґРµР№СЃС‚РІРёС‚РµР»СЊРЅРѕ Р»Рё "
                    "СЌС‚Р° РІРµС‰СЊ СЂРµС€Р°РµС‚ РЅСѓР¶РЅСѓСЋ Р·Р°РґР°С‡Сѓ."
                )

            if score == 2:
                st.success("РџРѕРєСѓРїРєСѓ РјРѕР¶РЅРѕ СЂР°СЃСЃРјРѕС‚СЂРµС‚СЊ.")
            elif score == 0:
                st.info("РЎСЂР°РІРЅРё РїР»СЋСЃС‹ Рё РјРёРЅСѓСЃС‹ РїРµСЂРµРґ СЂРµС€РµРЅРёРµРј.")

            st.caption(
                "РџСЂРёР»РѕР¶РµРЅРёРµ СЃСЂР°РІРЅРёРІР°РµС‚ РІРІРµРґС‘РЅРЅС‹Рµ РєР°С‚РµРіРѕСЂРёРё Рё РЅР°Р·РІР°РЅРёСЏ С†РІРµС‚РѕРІ. "
                "Р¤РѕС‚РѕРіСЂР°С„РёРё Р°РІС‚РѕРјР°С‚РёС‡РµСЃРєРё РЅРµ СЂР°СЃРїРѕР·РЅР°СЋС‚СЃСЏ."
            )



elif page == "РџРѕСЂР° РЅР°РґРµС‚СЊ":
    st.title("РџРѕСЂР° РЅР°РґРµС‚СЊ")
    st.write(
        "Р—РґРµСЃСЊ СЃРѕР±СЂР°РЅС‹ РІРµС‰Рё, РєРѕС‚РѕСЂС‹Рµ РЅРµ РѕС‚РјРµС‡Р°Р»РёСЃСЊ РєР°Рє РЅР°РґРµС‚С‹Рµ "
        "30 РґРЅРµР№ РёР»Рё РґРѕР»СЊС€Рµ."
    )

    forgotten = [
        item for item in clothes
        if days_since_last_worn(item) >= 30
    ]
    forgotten.sort(key=days_since_last_worn, reverse=True)

    if not forgotten:
        st.success(
            "РџРѕРєР° РЅРµС‚ РІРµС‰РµР№ РґР»СЏ РЅР°РїРѕРјРёРЅР°РЅРёСЏ. РћС‚РјРµС‡Р°Р№ РІРµС‰Рё РїРѕСЃР»Рµ РЅРѕСЃРєРё, "
            "С‡С‚РѕР±С‹ РЅР°РїРѕРјРёРЅР°РЅРёСЏ Р±С‹Р»Рё С‚РѕС‡РЅРµРµ."
        )
    else:
        occasion = st.selectbox(
            "РџРѕРґРѕР±СЂР°С‚СЊ СЃРѕС‡РµС‚Р°РЅРёСЏ РґР»СЏ РїРѕРІРѕРґР°",
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
                        f"{item['category']} В· {item['color']} В· "
                        f"{item['season']}"
                    )
                    st.write(
                        f"РќРµ РѕС‚РјРµС‡Р°Р»Р°СЃСЊ РєР°Рє РЅР°РґРµС‚Р°СЏ "
                        f"**{days_since_last_worn(item)} РґРЅРµР№**."
                    )

                    ideas = suggest_outfits(
                        clothes,
                        occasion,
                        target_item=item,
                        limit=3,
                    )

                    if ideas:
                        st.markdown("**РРґРµРё СЃРѕС‡РµС‚Р°РЅРёР№:**")
                        for outfit in ideas:
                            show_outfit(outfit)
                    else:
                        st.write(
                            "РџРѕРєР° РЅРµС‚ РїРѕРґС…РѕРґСЏС‰РµРіРѕ РіРѕС‚РѕРІРѕРіРѕ СЃРѕС‡РµС‚Р°РЅРёСЏ. "
                            "РџРѕРїСЂРѕР±СѓР№ РґРѕР±Р°РІРёС‚СЊ РІРµС‰Рё РґСЂСѓРіРёС… РєР°С‚РµРіРѕСЂРёР№."
                        )

                    if st.button(
                        "РћС‚РјРµС‚РёС‚СЊ РєР°Рє РЅР°РґРµС‚СѓСЋ СЃРµРіРѕРґРЅСЏ",
                        key=f"reminder_worn_{item['id']}",
                    ):
                        mark_worn(item["id"])
                        st.rerun()



elif page == "РњРѕРё РѕР±СЂР°Р·С‹":
    st.title("РњРѕРё РѕР±СЂР°Р·С‹")
    outfits = get_outfits()

    if not outfits:
        st.info(
            "РЎРѕС…СЂР°РЅС‘РЅРЅС‹С… РѕР±СЂР°Р·РѕРІ РїРѕРєР° РЅРµС‚. РЎРѕР·РґР°Р№ РёС… РІ СЂР°Р·РґРµР»Рµ "
            "В«РџРѕРґРѕР±СЂР°С‚СЊ РѕР±СЂР°Р·В»."
        )
    else:
        clothes_by_id = {item["id"]: item for item in clothes}

        labels = {
            f"{item['name']} вЂ” {item['color']} "
            f"({item['category']}) В· ID {item['id']}": item["id"]
            for item in clothes
        }

        for outfit in outfits:
            with st.container(border=True):
                st.subheader(outfit["name"])
                st.caption(f"РЎРѕР·РґР°РЅ: {outfit['created_at']}")

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
                    st.write(
                        "Р’РµС‰Рё РёР· СЌС‚РѕРіРѕ РѕР±СЂР°Р·Р° СѓР¶Рµ СѓРґР°Р»РµРЅС‹ РёР· РіР°СЂРґРµСЂРѕР±Р°."
                    )

                with st.expander("Р РµРґР°РєС‚РёСЂРѕРІР°С‚СЊ РѕР±СЂР°Р·"):
                    with st.form(f"edit_outfit_{outfit['id']}"):
                        edited_outfit_name = st.text_input(
                            "РќР°Р·РІР°РЅРёРµ РѕР±СЂР°Р·Р°",
                            value=outfit["name"],
                            key=f"edit_outfit_name_{outfit['id']}",
                        )

                        current_labels = [
                            label
                            for label, clothing_id in labels.items()
                            if clothing_id in item_ids
                        ]

                        selected_labels = st.multiselect(
                            "Р’РµС‰Рё РІ РѕР±СЂР°Р·Рµ",
                            options=list(labels.keys()),
                            default=current_labels,
                            key=f"edit_outfit_items_{outfit['id']}",
                        )

                        save_outfit_edit = st.form_submit_button(
                            "РЎРѕС…СЂР°РЅРёС‚СЊ РѕР±СЂР°Р·"
                        )

                        if save_outfit_edit:
                            selected_ids = [
                                labels[label] for label in selected_labels
                            ]

                            if not edited_outfit_name.strip():
                                st.error("РЈРєР°Р¶Рё РЅР°Р·РІР°РЅРёРµ РѕР±СЂР°Р·Р°.")
                            elif len(selected_ids) < 2:
                                st.error("Р’С‹Р±РµСЂРё РјРёРЅРёРјСѓРј РґРІРµ РІРµС‰Рё.")
                            else:
                                update_outfit(
                                    outfit["id"],
                                    edited_outfit_name,
                                    selected_ids,
                                )
                                st.success("РћР±СЂР°Р· РѕР±РЅРѕРІР»С‘РЅ.")
                                st.rerun()

                if st.button(
                    "РЈРґР°Р»РёС‚СЊ РѕР±СЂР°Р·",
                    key=f"delete_outfit_{outfit['id']}",
                ):
                    delete_outfit(outfit["id"])
                    st.rerun()
