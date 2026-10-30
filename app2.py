import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import hashlib
from datetime import datetime

# ---------- ЦВЕТОВАЯ ПАЛИТРА ----------
PLUM = "#5B2C4F"        # сливовый
CHERRY = "#8B1E3F"      # вишнёвый
BUTTER = "#F5E6A8"      # светло-жёлтый (масло)
CREAM = "#FFF8E7"
TEXT_DARK = "#2B1B26"

FONT_TITLE = ("Georgia", 20, "bold")
FONT_HEAD = ("Georgia", 14, "bold")
FONT_BODY = ("Georgia", 11)
FONT_BTN = ("Georgia", 11, "bold")


# ---------- БАЗА ДАННЫХ ----------
class DB:
    def __init__(self, path="wardrobe.db"):
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self._create()

    def _create(self):
        c = self.conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            style TEXT DEFAULT '',
            season TEXT DEFAULT '',
            color_pref TEXT DEFAULT ''
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS clothes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            category TEXT,
            color TEXT,
            season TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS wishlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            item TEXT NOT NULL,
            price TEXT,
            note TEXT
        )""")
        self.conn.commit()

    @staticmethod
    def hash_pw(pw):
        return hashlib.sha256(pw.encode()).hexdigest()

    def register(self, username, password, style, season, color_pref):
        try:
            self.conn.execute(
                "INSERT INTO users(username,password,style,season,color_pref) VALUES(?,?,?,?,?)",
                (username, self.hash_pw(password), style, season, color_pref),
            )
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def login(self, username, password):
        row = self.conn.execute(
            "SELECT * FROM users WHERE username=? AND password=?",
            (username, self.hash_pw(password)),
        ).fetchone()
        return dict(row) if row else None

    def add_cloth(self, user_id, name, category, color, season):
        self.conn.execute(
            "INSERT INTO clothes(user_id,name,category,color,season) VALUES(?,?,?,?,?)",
            (user_id, name, category, color, season),
        )
        self.conn.commit()

    def list_clothes(self, user_id):
        return self.conn.execute(
            "SELECT * FROM clothes WHERE user_id=? ORDER BY category, name", (user_id,)
        ).fetchall()

    def delete_cloth(self, cloth_id):
        self.conn.execute("DELETE FROM clothes WHERE id=?", (cloth_id,))
        self.conn.commit()

    def add_wish(self, user_id, item, price, note):
        self.conn.execute(
            "INSERT INTO wishlist(user_id,item,price,note) VALUES(?,?,?,?)",
            (user_id, item, price, note),
        )
        self.conn.commit()

    def list_wishes(self, user_id):
        return self.conn.execute(
            "SELECT * FROM wishlist WHERE user_id=? ORDER BY id DESC", (user_id,)
        ).fetchall()

    def delete_wish(self, wish_id):
        self.conn.execute("DELETE FROM wishlist WHERE id=?", (wish_id,))
        self.conn.commit()


db = DB()


# ---------- ВСПОМОГАТЕЛЬНЫЕ ----------
def styled_button(parent, text, command, bg=CHERRY, fg=BUTTER):
    return tk.Button(
        parent, text=text, command=command,
        bg=bg, fg=fg, activebackground=PLUM, activeforeground=BUTTER,
        font=FONT_BTN, relief="flat", bd=0, padx=14, pady=8, cursor="hand2",
    )


def styled_entry(parent, show=None):
    e = tk.Entry(
        parent, font=FONT_BODY, bg=CREAM, fg=TEXT_DARK,
        insertbackground=TEXT_DARK, relief="flat", bd=4, show=show,
    )
    return e


def clear_frame(frame):
    for w in frame.winfo_children():
        w.destroy()


# ---------- ЭКРАН ВХОДА ----------
class AuthScreen(tk.Frame):
    def __init__(self, app):
        super().__init__(app, bg=BUTTER)
        self.app = app
        self.build()

    def build(self):
        clear_frame(self)
        tk.Label(self, text="🌸 Умный шкаф", font=("Georgia", 30, "bold"),
                 bg=BUTTER, fg=PLUM).pack(pady=(60, 10))
        tk.Label(self, text="Твой персональный стилист",
                 font=("Georgia", 13, "italic"), bg=BUTTER, fg=CHERRY).pack(pady=(0, 30))

        card = tk.Frame(self, bg=CREAM, bd=0, highlightthickness=2,
                        highlightbackground=PLUM)
        card.pack(padx=40, pady=10, fill="x")

        tk.Label(card, text="Имя пользователя", font=FONT_BODY,
                 bg=CREAM, fg=TEXT_DARK).pack(anchor="w", padx=20, pady=(18, 4))
        self.e_user = styled_entry(card)
        self.e_user.pack(padx=20, fill="x")

        tk.Label(card, text="Пароль", font=FONT_BODY,
                 bg=CREAM, fg=TEXT_DARK).pack(anchor="w", padx=20, pady=(12, 4))
        self.e_pw = styled_entry(card, show="•")
        self.e_pw.pack(padx=20, fill="x")

        btns = tk.Frame(card, bg=CREAM)
        btns.pack(pady=20)
        styled_button(btns, "Войти", self.on_login).pack(side="left", padx=6)
        styled_button(btns, "Регистрация", self.on_register, bg=PLUM).pack(side="left", padx=6)

    def on_login(self):
        u = self.e_user.get().strip()
        p = self.e_pw.get()
        if not u or not p:
            messagebox.showwarning("Внимание", "Заполни все поля")
            return
        user = db.login(u, p)
        if user:
            self.app.current_user = user
            self.app.show_main()
        else:
            messagebox.showerror("Ошибка", "Неверное имя или пароль")

    def on_register(self):
        reg = RegisterWindow(self.app)
        reg.grab_set()


class RegisterWindow(tk.Toplevel):
    def __init__(self, app):
        super().__init__(app, bg=BUTTER)
        self.app = app
        self.title("Регистрация")
        self.geometry("420x560")
        self.build()

    def build(self):
        tk.Label(self, text="Создать профиль", font=FONT_TITLE,
                 bg=BUTTER, fg=PLUM).pack(pady=16)

        fields = [
            ("Имя пользователя", "user"),
            ("Пароль", "pw"),
            ("Твой стиль (напр.: casual, business)", "style"),
            ("Любимый сезон (весна/лето/осень/зима)", "season"),
            ("Любимые цвета", "colors"),
        ]
        self.entries = {}
        for label, key in fields:
            tk.Label(self, text=label, font=FONT_BODY,
                     bg=BUTTER, fg=TEXT_DARK).pack(anchor="w", padx=30)
            e = styled_entry(self, show="•" if key == "pw" else None)
            e.pack(padx=30, pady=(2, 12), fill="x")
            self.entries[key] = e

        styled_button(self, "Готово", self.submit, bg=CHERRY).pack(pady=10)

    def submit(self):
        u = self.entries["user"].get().strip()
        p = self.entries["pw"].get()
        if not u or not p:
            messagebox.showwarning("Внимание", "Имя и пароль обязательны")
            return
        ok = db.register(
            u, p,
            self.entries["style"].get().strip(),
            self.entries["season"].get().strip(),
            self.entries["colors"].get().strip(),
        )
        if ok:
            messagebox.showinfo("Успех", "Профиль создан! Теперь войди.")
            self.destroy()
        else:
            messagebox.showerror("Ошибка", "Такое имя уже существует")


# ---------- ГЛАВНЫЙ ЭКРАН ----------
class MainScreen(tk.Frame):
    def __init__(self, app):
        super().__init__(app, bg=BUTTER)
        self.app = app
        self.build()

    def build(self):
        clear_frame(self)
        user = self.app.current_user

        # Шапка
        head = tk.Frame(self, bg=PLUM)
        head.pack(fill="x")
        tk.Label(head, text=f"👗 {user['username']}", font=FONT_TITLE,
                 bg=PLUM, fg=BUTTER).pack(side="left", padx=20, pady=12)
        styled_button(head, "Выйти", self.logout, bg=CHERRY).pack(side="right", padx=15, pady=10)

        # Приветствие с персональными данными
        info = tk.Frame(self, bg=CREAM, highlightthickness=1, highlightbackground=PLUM)
        info.pack(fill="x", padx=20, pady=15)
        tk.Label(info, text="Твой профиль", font=FONT_HEAD,
                 bg=CREAM, fg=CHERRY).pack(anchor="w", padx=15, pady=(10, 4))
        style = user.get("style") or "не указан"
        season = user.get("season") or "не указан"
        colors = user.get("color_pref") or "не указаны"
        tk.Label(info, text=f"Стиль: {style}   •   Сезон: {season}   •   Цвета: {colors}",
                 font=FONT_BODY, bg=CREAM, fg=TEXT_DARK).pack(anchor="w", padx=15, pady=(0, 12))

        # Меню кнопок
        menu = tk.Frame(self, bg=BUTTER)
        menu.pack(pady=20)
        buttons = [
            ("🧺  Мой гардероб", self.open_wardrobe),
            ("✨  Подбор образа", self.open_outfit),
            ("🛍  Помощь перед покупкой", self.open_shopping),
        ]
        for i, (txt, cmd) in enumerate(buttons):
            b = styled_button(menu, txt, cmd, bg=CHERRY)
            b.config(font=("Georgia", 13, "bold"), width=26, pady=18)
            b.grid(row=0, column=i, padx=12)

        # Декор снизу
        tk.Label(self, text="С любовью к твоему стилю 💐",
                 font=("Georgia", 12, "italic"), bg=BUTTER, fg=PLUM).pack(side="bottom", pady=20)

    def logout(self):
        self.app.current_user = None
        self.app.show_auth()

    def open_wardrobe(self):
        self.app.show(WardrobeScreen(self.app))

    def open_outfit(self):
        self.app.show(OutfitScreen(self.app))

    def open_shopping(self):
        self.app.show(ShoppingScreen(self.app))


# ---------- ГАРДЕРОБ ----------
class WardrobeScreen(tk.Frame):
    def __init__(self, app):
        super().__init__(app, bg=BUTTER)
        self.app = app
        self.build()

    def build(self):
        clear_frame(self)
        user = self.app.current_user

        head = tk.Frame(self, bg=PLUM)
        head.pack(fill="x")
        styled_button(head, "← Назад", self.app.show_main, bg=CHERRY).pack(side="left", padx=15, pady=10)
        tk.Label(head, text="Мой гардероб", font=FONT_TITLE,
                 bg=PLUM, fg=BUTTER).pack(side="left", padx=10)

        # Форма добавления
        form = tk.Frame(self, bg=CREAM, highlightthickness=1, highlightbackground=PLUM)
        form.pack(fill="x", padx=20, pady=12)

        tk.Label(form, text="Добавить вещь", font=FONT_HEAD,
                 bg=CREAM, fg=CHERRY).grid(row=0, column=0, columnspan=6,
                                           sticky="w", padx=12, pady=8)

        self.e_name = styled_entry(form); self.e_name.grid(row=1, column=0, padx=6, pady=6, sticky="ew")
        self.e_name.insert(0, "Название")

        self.cb_cat = ttk.Combobox(form, values=["Верх", "Низ", "Обувь", "Аксессуар", "Верхняя одежда", "Платье"],
                                    font=FONT_BODY)
        self.cb_cat.set("Верх"); self.cb_cat.grid(row=1, column=1, padx=6, pady=6, sticky="ew")

        self.e_color = styled_entry(form); self.e_color.grid(row=1, column=2, padx=6, pady=6, sticky="ew")
        self.e_color.insert(0, "Цвет")

        self.cb_season = ttk.Combobox(form, values=["Весна", "Лето", "Осень", "Зима", "Всесезон"],
                                       font=FONT_BODY)
        self.cb_season.set("Всесезон"); self.cb_season.grid(row=1, column=3, padx=6, pady=6, sticky="ew")

        styled_button(form, "+", self.add_item).grid(row=1, column=4, padx=8, pady=6)
        for i in range(5):
            form.columnconfigure(i, weight=1)

        # Таблица вещей
        self.tree = ttk.Treeview(self, columns=("name", "cat", "color", "season"),
                                  show="headings", height=12)
        self.tree.heading("name", text="Название")
        self.tree.heading("cat", text="Категория")
        self.tree.heading("color", text="Цвет")
        self.tree.heading("season", text="Сезон")
        self.tree.column("name", width=220)
        self.tree.column("cat", width=140)
        self.tree.column("color", width=120)
        self.tree.column("season", width=120)
        self.tree.pack(fill="both", expand=True, padx=20, pady=(0, 8))

        bottom = tk.Frame(self, bg=BUTTER)
        bottom.pack(fill="x", padx=20, pady=(0, 15))
        styled_button(bottom, "Удалить выбранное", self.delete_item, bg=PLUM).pack(side="right")

        self.refresh()

    def add_item(self):
        name = self.e_name.get().strip()
        color = self.e_color.get().strip()
        if not name or name == "Название":
            messagebox.showwarning("Внимание", "Введите название вещи")
            return
        if not color or color == "Цвет":
            color = "—"
        db.add_cloth(self.app.current_user["id"], name, self.cb_cat.get(),
                     color, self.cb_season.get())
        self.e_name.delete(0, "end"); self.e_name.insert(0, "Название")
        self.e_color.delete(0, "end"); self.e_color.insert(0, "Цвет")
        self.refresh()

    def delete_item(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Подсказка", "Выберите вещь")
            return
        db.delete_cloth(sel[0])
        self.refresh()

    def refresh(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        for r in db.list_clothes(self.app.current_user["id"]):
            self.tree.insert("", "end", iid=r["id"],
                             values=(r["name"], r["category"], r["color"], r["season"]))


# ---------- ПОДБОР ОБРАЗА ----------
class OutfitScreen(tk.Frame):
    def __init__(self, app):
        super().__init__(app, bg=BUTTER)
        self.app = app
        self.build()

    def build(self):
        clear_frame(self)
        head = tk.Frame(self, bg=PLUM)
        head.pack(fill="x")
        styled_button(head, "← Назад", self.app.show_main, bg=CHERRY).pack(side="left", padx=15, pady=10)
        tk.Label(head, text="Подбор образа", font=FONT_TITLE,
                 bg=PLUM, fg=BUTTER).pack(side="left", padx=10)

        info = tk.Frame(self, bg=CREAM, highlightthickness=1, highlightbackground=PLUM)
        info.pack(fill="x", padx=20, pady=12)
        tk.Label(info, text="Выбери сезон и повод — я соберу образ из твоих вещей.",
                 font=FONT_BODY, bg=CREAM, fg=TEXT_DARK).pack(pady=10, padx=15, anchor="w")

        controls = tk.Frame(self, bg=BUTTER)
        controls.pack(pady=10)

        tk.Label(controls, text="Сезон:", font=FONT_BODY, bg=BUTTER).grid(row=0, column=0, padx=6)
        self.cb_season = ttk.Combobox(controls, values=["Весна", "Лето", "Осень", "Зима", "Всесезон"],
                                       font=FONT_BODY, width=12)
        self.cb_season.set("Всесезон"); self.cb_season.grid(row=0, column=1, padx=6)

        tk.Label(controls, text="Повод:", font=FONT_BODY, bg=BUTTER).grid(row=0, column=2, padx=6)
        self.cb_occasion = ttk.Combobox(controls, values=["Повседневный", "Работа", "Вечер", "Прогулка"],
                                         font=FONT_BODY, width=14)
        self.cb_occasion.set("Повседневный"); self.cb_occasion.grid(row=0, column=3, padx=6)

        styled_button(controls, "Собрать образ ✨", self.make_outfit).grid(row=0, column=4, padx=15)

        self.result = tk.Text(self, height=14, font=FONT_BODY, bg=CREAM, fg=TEXT_DARK,
                              relief="flat", bd=8, wrap="word")
        self.result.pack(fill="both", expand=True, padx=20, pady=15)
        self.result.insert("end", "Здесь появится твой образ...")
        self.result.config(state="disabled")

    def make_outfit(self):
        user_id = self.app.current_user["id"]
        season = self.cb_season.get()
        occasion = self.cb_occasion.get()
        items = db.list_clothes(user_id)

        if not items:
            self.show_text("Гардероб пуст. Добавь вещи в разделе «Мой гардероб».")
            return

        # фильтр по сезону
        def match_season(it):
            return it["season"] in (season, "Всесезон", "")

        tops = [i for i in items if i["category"] in ("Верх", "Платье") and match_season(i)]
        bottoms = [i for i in items if i["category"] == "Низ" and match_season(i)]
        shoes = [i for i in items if i["category"] == "Обувь" and match_season(i)]
        acc = [i for i in items if i["category"] == "Аксессуар"]
        outer = [i for i in items if i["category"] == "Верхняя одежда" and match_season(i)]

        def pick(lst):
            return lst[0] if lst else None

        top = pick(tops); bottom = pick(bottoms)
        shoe = pick(shoes); accessory = pick(acc); outerwear = pick(outer)

        lines = [f"🌿 Образ на повод «{occasion}» ({season})\n"]
        if outerwear: lines.append(f"• Верхняя одежда: {outerwear['name']} ({outerwear['color']})")
        if top: lines.append(f"• Верх: {top['name']} ({top['color']})")
        else: lines.append("• Верх: не найдено подходящей вещи")
        if top and top["category"] == "Платье":
            lines.append("• Низ: платье — дополнять не нужно")
        else:
            if bottom: lines.append(f"• Низ: {bottom['name']} ({bottom['color']})")
            else: lines.append("• Низ: не найдено")
        if shoe: lines.append(f"• Обувь: {shoe['name']} ({shoe['color']})")
        if accessory: lines.append(f"• Аксессуар: {accessory['name']} ({accessory['color']})")

        lines.append("\n💡 Совет: если хочешь добавить яркости — используй вещи в вишнёвом "
                     "или сливовом оттенке, они хорошо сочетаются с масляно-жёлтым.")
        self.show_text("\n".join(lines))

    def show_text(self, text):
        self.result.config(state="normal")
        self.result.delete("1.0", "end")
        self.result.insert("end", text)
        self.result.config(state="disabled")


# ---------- ПОМОЩЬ ПЕРЕД ПОКУПКОЙ ----------
class ShoppingScreen(tk.Frame):
    def __init__(self, app):
        super().__init__(app, bg=BUTTER)
        self.app = app
        self.build()

    def build(self):
        clear_frame(self)
        head = tk.Frame(self, bg=PLUM)
        head.pack(fill="x")
        styled_button(head, "← Назад", self.app.show_main, bg=CHERRY).pack(side="left", padx=15, pady=10)
        tk.Label(head, text="Помощь перед покупкой", font=FONT_TITLE,
                 bg=PLUM, fg=BUTTER).pack(side="left", padx=10)

        # Список желаний
        form = tk.Frame(self, bg=CREAM, highlightthickness=1, highlightbackground=PLUM)
        form.pack(fill="x", padx=20, pady=12)
        tk.Label(form, text="Вещь, которую хочу купить", font=FONT_HEAD,
                 bg=CREAM, fg=CHERRY).grid(row=0, column=0, columnspan=4, sticky="w", padx=12, pady=8)

        self.e_item = styled_entry(form); self.e_item.grid(row=1, column=0, padx=6, pady=6, sticky="ew")
        self.e_item.insert(0, "Что это?")
        self.e_price = styled_entry(form); self.e_price.grid(row=1, column=1, padx=6, pady=6, sticky="ew")
        self.e_price.insert(0, "Цена")
        self.e_note = styled_entry(form); self.e_note.grid(row=1, column=2, padx=6, pady=6, sticky="ew")
        self.e_note.insert(0, "Зачем мне это?")

        styled_button(form, "+", self.add_wish).grid(row=1, column=3, padx=8, pady=6)
        for i in range(4): form.columnconfigure(i, weight=1)

        self.tree = ttk.Treeview(self, columns=("item", "price", "note"),
                                  show="headings", height=10)
        self.tree.heading("item", text="Вещь")
        self.tree.heading("price", text="Цена")
        self.tree.heading("note", text="Комментарий")
        self.tree.column("item", width=220)
        self.tree.column("price", width=120)
        self.tree.column("note", width=320)
        self.tree.pack(fill="both", expand=True, padx=20, pady=(0, 8))

        # Кнопки-советы
        bottom = tk.Frame(self, bg=BUTTER)
        bottom.pack(fill="x", padx=20, pady=(0, 15))
        styled_button(bottom, "Спросить совет", self.ask_advice, bg=CHERRY).pack(side="left", padx=4)
        styled_button(bottom, "Удалить выбранное", self.delete_wish, bg=PLUM).pack(side="right", padx=4)

        self.advice = tk.Text(self, height=5, font=FONT_BODY, bg=CREAM, fg=TEXT_DARK,
                              relief="flat", bd=8, wrap="word")
        self.advice.pack(fill="x", padx=20, pady=(0, 15))
        self.advice.insert("end", "Нажми «Спросить совет» — я помогу решить, нужна ли покупка.")
        self.advice.config(state="disabled")

        self.refresh()

    def add_wish(self):
        item = self.e_item.get().strip()
        price = self.e_price.get().strip()
        note = self.e_note.get().strip()
        if not item or item == "Что это?":
            messagebox.showwarning("Внимание", "Введите название вещи")
            return
        db.add_wish(self.app.current_user["id"], item,
                    price if price != "Цена" else "", note if note != "Зачем мне это?" else "")
        for e, ph in [(self.e_item, "Что это?"), (self.e_price, "Цена"), (self.e_note, "Зачем мне это?")]:
            e.delete(0, "end"); e.insert(0, ph)
        self.refresh()

    def delete_wish(self):
        sel = self.tree.selection()
        if not sel: return
        db.delete_wish(sel[0]); self.refresh()

    def refresh(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        for r in db.list_wishes(self.app.current_user["id"]):
            self.tree.insert("", "end", iid=r["id"],
                             values=(r["item"], r["price"], r["note"]))

    def ask_advice(self):
        wishes = db.list_wishes(self.app.current_user["id"])
        clothes = db.list_clothes(self.app.current_user["id"])
        if not wishes:
            msg = ("Список желаний пуст. Добавь то, что присматриваешь — "
                   "и я помогу оценить, насколько вещь тебе нужна.")
        else:
            w = wishes[0]
            item = w["item"]
            same_color = [c for c in clothes if w["note"] and c["color"].lower() in w["note"].lower()]
            msg = f"💭 Анализ покупки «{item}»:\n"
            msg += "1. Проверь, сочетается ли вещь с твоими любимыми цветами и базовым гардеробом.\n"
            msg += "2. Спроси себя: смогу ли я составить минимум 3 образа с этой вещью?\n"
            if same_color:
                msg += f"3. У тебя уже есть похожие вещи: {', '.join(c['name'] for c in same_color)}. Возможно, дубль не нужен.\n"
            else:
                msg += "3. Похожих вещей в гардеробе нет — это плюс к разнообразию.\n"
            msg += "4. Если вещь не носится минимум 30 раз за сезон — лучше подождать."
        self.advice.config(state="normal")
        self.advice.delete("1.0", "end")
        self.advice.insert("end", msg)
        self.advice.config(state="disabled")


# ---------- ПРИЛОЖЕНИЕ ----------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("🌸 Умный шкаф")
        self.geometry("900x650")
        self.configure(bg=BUTTER)
        self.current_user = None
        self.container = tk.Frame(self, bg=BUTTER)
        self.container.pack(fill="both", expand=True)
        self.show_auth()

    def show(self, frame):
        clear_frame(self.container)
        frame.pack(fill="both", expand=True)

    def show_auth(self):
        self.show(AuthScreen(self))

    def show_main(self):
        self.show(MainScreen(self))


if __name__ == "__main__":
    App().mainloop()
