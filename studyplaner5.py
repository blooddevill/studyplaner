import customtkinter as ctk
import sqlite3
import hashlib
import os
import shutil
import re
import tkinter as tk
import calendar
import math
import random
from tkinter import messagebox, filedialog
from datetime import datetime, timedelta
from PIL import Image, ImageTk, ImageDraw, ImageFont

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from fpdf import FPDF

try:
    from plyer import notification
    PLYER_OK = True
except ImportError:
    PLYER_OK = False

try:
    import qrcode
    QR_OK = True
except ImportError:
    QR_OK = False

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("green")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "planner.db")
AVATAR_DIR = os.path.join(BASE_DIR, "avatars")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
QR_DIR = os.path.join(BASE_DIR, "qrcodes")
BADWORDS_FILE = os.path.join(BASE_DIR, "badwords.txt")

os.makedirs(AVATAR_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(QR_DIR, exist_ok=True)

TEACHER_CODE = "TEACHER2026"
MAX_FILE_SIZE_MB = 20

SPECIALTIES = [
    "Разработка и управление программным обеспечением",
    "Техническая эксплуатация и сопровождение информационных систем",
    "Сестринское дело",
    "Лечебное дело",
    "Ветеринария",
    "Операционная деятельность в логистике",
    "Банковское дело",
    "Правоохранительная деятельность",
    "Юриспруденция",
    "Преподавание в начальных классах",
    "Дошкольное образование",
    "Дизайн (по отраслям)",
]

DAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб"]
WEEK_TYPES = ["Каждую неделю", "Только чётные", "Только нечётные"]
EMOJIS = ["", "📚", "📝", "🧪", "💻", "📐", "🌍", "🎨", "🔬", "📊", "✏️", "🔥", "⭐", "🎯"]

SUBJECT_COLORS = {
    "Зелёный": "#2E7D32", "Синий": "#1976D2", "Красный": "#C62828",
    "Оранжевый": "#EF6C00", "Фиолетовый": "#7B1FA2", "Бирюзовый": "#00838F",
    "Коричневый": "#5D4037", "Серый": "#616161",
}

DEFAULT_BAD_WORDS = [
    "хуй", "пизд", "ебан", "ебал", "ебат", "бляд", "мудак", "гандон", "сука",
    "шлюх", "долбоеб", "пидор", "нахуй", "залуп", "манда", "fuck", "shit"
]


def load_bad_words():
    """Читает запрещённые слова из badwords.txt. Создаёт файл при отсутствии."""
    if os.path.exists(BADWORDS_FILE):
        try:
            with open(BADWORDS_FILE, "r", encoding="utf-8") as f:
                words = [line.strip().lower() for line in f
                         if line.strip() and not line.strip().startswith("#")]
            if words:
                return words
        except Exception:
            pass
        return DEFAULT_BAD_WORDS
    try:
        with open(BADWORDS_FILE, "w", encoding="utf-8") as f:
            f.write("# Запрещённые слова для ников (по одному на строку)\n")
            f.write("# Строки, начинающиеся с # — игнорируются\n\n")
            f.write("\n".join(DEFAULT_BAD_WORDS))
    except Exception:
        pass
    return DEFAULT_BAD_WORDS


BAD_WORDS = load_bad_words()

GREEN = ("#2E7D32", "#4CAF50")
GREEN_LIGHT = ("#4CAF50", "#66BB6A")
GREEN_SOFT = ("#E8F5E9", "#1B3D1D")
GRAY_DARK = ("#424242", "#CCCCCC")
GRAY_MED = ("#9E9E9E", "#888888")
GRAY_LIGHT = ("#EEEEEE", "#3A3A3A")
GRAY_BG = ("#F0F2F5", "#121212")
WHITE = ("#FFFFFF", "#1E1E1E")
BLACK = ("#1A1A1A", "#FFFFFF")
RED = ("#C62828", "#EF5350")
RED_SOFT = ("#FFEBEE", "#3D1F1F")
ORANGE = ("#EF6C00", "#FFB74D")
GOLD = ("#FBC02D", "#FDD835")
DUO_ORANGE = "#FF9600"
DUO_GRAY = "#4B4B4B"


def safe_color(value, default="#2E7D32"):
    if isinstance(value, str):
        v = value.strip()
        if re.match(r"^#[0-9A-Fa-f]{6}$", v):
            return v
    return default


def current_week_parity():
    week = datetime.now().isocalendar()[1]
    return "odd" if week % 2 == 1 else "even"


def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT UNIQUE NOT NULL,
        nickname TEXT NOT NULL, password TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'student',
        avatar TEXT DEFAULT '', created_at TEXT, specialty TEXT DEFAULT '',
        group_name TEXT DEFAULT '', xp INTEGER DEFAULT 0, level INTEGER DEFAULT 1,
        streak INTEGER DEFAULT 0, last_login TEXT DEFAULT ''
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS schedule (
        id INTEGER PRIMARY KEY AUTOINCREMENT, subject TEXT, teacher TEXT, day TEXT, time TEXT, room TEXT,
        specialty TEXT DEFAULT '', group_name TEXT DEFAULT '', color TEXT DEFAULT '#2E7D32', week_type INTEGER DEFAULT 0
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS homework (
        id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, subject TEXT, deadline TEXT, priority TEXT,
        file_path TEXT DEFAULT '', specialty TEXT DEFAULT '', group_name TEXT DEFAULT '', emoji TEXT DEFAULT ''
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT, subject TEXT, date TEXT, info TEXT,
        specialty TEXT DEFAULT '', group_name TEXT DEFAULT ''
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS homework_done (
        user_email TEXT NOT NULL, homework_id INTEGER NOT NULL, done_at TEXT,
        PRIMARY KEY (user_email, homework_id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_email TEXT NOT NULL, title TEXT, content TEXT,
        subject TEXT, color TEXT DEFAULT '#2E7D32', created_at TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS user_achievements (
        user_email TEXT NOT NULL, achievement_id TEXT NOT NULL, unlocked_at TEXT,
        PRIMARY KEY (user_email, achievement_id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS grades (
        id INTEGER PRIMARY KEY AUTOINCREMENT, student_email TEXT NOT NULL, subject TEXT NOT NULL,
        grade INTEGER NOT NULL, date TEXT NOT NULL, teacher_email TEXT NOT NULL
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS settings (
        id INTEGER PRIMARY KEY CHECK (id = 1), theme TEXT DEFAULT 'light',
        font_size INTEGER DEFAULT 14, reminder_days INTEGER DEFAULT 3
    )""")
    c.execute("INSERT OR IGNORE INTO settings (id, theme, font_size, reminder_days) VALUES (1, 'light', 14, 3)")

    existing = [row[1] for row in c.execute("PRAGMA table_info(users)").fetchall()]
    if "xp" not in existing: c.execute("ALTER TABLE users ADD COLUMN xp INTEGER DEFAULT 0")
    if "level" not in existing: c.execute("ALTER TABLE users ADD COLUMN level INTEGER DEFAULT 1")
    if "streak" not in existing: c.execute("ALTER TABLE users ADD COLUMN streak INTEGER DEFAULT 0")
    if "last_login" not in existing: c.execute("ALTER TABLE users ADD COLUMN last_login TEXT DEFAULT ''")

    existing = [row[1] for row in c.execute("PRAGMA table_info(homework)").fetchall()]
    if "emoji" not in existing: c.execute("ALTER TABLE homework ADD COLUMN emoji TEXT DEFAULT ''")

    existing = [row[1] for row in c.execute("PRAGMA table_info(settings)").fetchall()]
    if "reminder_days" not in existing:
        c.execute("ALTER TABLE settings ADD COLUMN reminder_days INTEGER DEFAULT 3")

    conn.commit()
    conn.close()


def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()


def db():
    return sqlite3.connect(DB_PATH)


def get_setting(key):
    conn = db()
    try:
        row = conn.execute(f"SELECT {key} FROM settings WHERE id=1").fetchone()
        return row[0] if row else None
    finally:
        conn.close()


def set_setting(key, value):
    conn = db()
    conn.execute(f"UPDATE settings SET {key}=? WHERE id=1", (value,))
    conn.commit()
    conn.close()


def parse_deadline(s):
    if not s:
        return None
    for fmt in ("%d.%m.%Y", "%d.%m.%y", "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(s.strip(), fmt)
        except ValueError:
            continue
    return None


def notify(title, message):
    if PLYER_OK:
        try:
            notification.notify(title=title, message=message, app_name="Study Planner", timeout=10)
        except Exception:
            pass


def get_all_groups():
    conn = db()
    rows = conn.execute("""SELECT DISTINCT specialty, group_name FROM users
                           WHERE role='student' AND group_name != ''
                           ORDER BY specialty, group_name""").fetchall()
    conn.close()
    return rows


def get_groups_for_specialty(specialty):
    conn = db()
    rows = conn.execute("""SELECT DISTINCT group_name FROM users
                           WHERE role='student' AND specialty=? AND group_name != ''
                           ORDER BY group_name""", (specialty,)).fetchall()
    conn.close()
    return [r[0] for r in rows]


def validate_nickname(nick):
    nick = nick.strip()
    if len(nick) < 3:
        return False, "Ник должен быть не короче 3 символов"
    if len(nick) > 20:
        return False, "Ник должен быть не длиннее 20 символов"
    if not re.match(r"^[A-Za-zА-Яа-я0-9_]+$", nick):
        return False, "Разрешены только буквы, цифры и _"
    if nick.isdigit():
        return False, "Ник не может состоять только из цифр"
    if re.fullmatch(r"[_]+", nick):
        return False, "Ник не может состоять только из спецсимволов"
    low = nick.lower()
    for w in BAD_WORDS:
        if w in low:
            return False, "Ник содержит запрещённые слова"
    return True, ""


class StudyPlannerApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Study Planner v5.1")
        self.state('zoomed')
        self.configure(fg_color=GRAY_BG)

        self.user_email = None
        self.nickname = None
        self.role = None
        self.is_teacher = False
        self.specialty = ""
        self.group_name = ""
        self.avatar_path = ""
        self.created_at = ""
        self.xp = 0
        self.level = 1
        self.streak = 0
        self.sound_playing = False

        self.filter_specialty = ""
        self.filter_group = ""
        self.schedule_day = "Все"
        self.hw_filter = "all"
        self.schedule_view = "list"
        self.search_var = ctk.StringVar()

        self.pomo_time = 25 * 60
        self.pomo_running = False
        self.pomo_job = None
        self.anim_job = None
        self.sparks = []

        self.current_tab = "dashboard"
        self.content = None
        self.scroll_frame = None
        self.nav_indicators = {}
        self.nav_buttons = {}

        self.show_login()

    def clear_window(self):
        if self.pomo_job:
            try: self.after_cancel(self.pomo_job)
            except: pass
            self.pomo_job = None
        if self.anim_job:
            try: self.after_cancel(self.anim_job)
            except: pass
            self.anim_job = None
        self.sparks.clear()

        if self.sound_playing:
            try:
                import winsound
                winsound.PlaySound(None, winsound.SND_PURGE)
            except: pass
            self.sound_playing = False

        for widget in self.winfo_children():
            widget.destroy()

    # ==================== ЭКРАН ВХОДА ====================
    def show_login(self):
        self.clear_window()

        left_frame = ctk.CTkFrame(self, fg_color=GREEN, corner_radius=0)
        left_frame.pack(side="left", fill="both", expand=True)

        right_frame = ctk.CTkFrame(self, fg_color=WHITE, corner_radius=0, width=500)
        right_frame.pack(side="right", fill="y")
        right_frame.pack_propagate(False)

        ctk.CTkLabel(left_frame, text="Study Planner", font=("Segoe UI", 52, "bold"), text_color=WHITE).place(relx=0.5, rely=0.4, anchor="center")
        ctk.CTkLabel(left_frame, text="Твой личный помощник в учёбе", font=("Segoe UI", 20), text_color=WHITE).place(relx=0.5, rely=0.5, anchor="center")

        scroll_right = ctk.CTkScrollableFrame(right_frame, fg_color="transparent")
        scroll_right.pack(fill="both", expand=True, padx=30, pady=50)

        inner = ctk.CTkFrame(scroll_right, fg_color="transparent")
        inner.pack(fill="x")

        ctk.CTkLabel(inner, text="С возвращением!", font=("Segoe UI", 28, "bold"), text_color=BLACK).pack(pady=(20, 40))

        ctk.CTkLabel(inner, text="Email", font=("Segoe UI", 13), text_color=GRAY_DARK).pack(anchor="w", pady=(0, 5))
        self.email_entry = ctk.CTkEntry(inner, placeholder_text="example@mail.com", height=50, fg_color=GRAY_BG, border_color=GRAY_LIGHT, text_color=BLACK, corner_radius=8)
        self.email_entry.pack(fill="x", pady=(0, 15))

        ctk.CTkLabel(inner, text="Пароль", font=("Segoe UI", 13), text_color=GRAY_DARK).pack(anchor="w", pady=(0, 5))
        self.pass_entry = ctk.CTkEntry(inner, placeholder_text="••••••••", show="*", height=50, fg_color=GRAY_BG, border_color=GRAY_LIGHT, text_color=BLACK, corner_radius=8)
        self.pass_entry.pack(fill="x", pady=(0, 30))

        self.email_entry.bind("<Return>", lambda e: self.attempt_login())
        self.pass_entry.bind("<Return>", lambda e: self.attempt_login())

        ctk.CTkButton(inner, text="Войти", height=50, fg_color=GREEN, hover_color=GREEN_LIGHT, text_color=WHITE, font=("Segoe UI", 16, "bold"), corner_radius=8, command=self.attempt_login).pack(fill="x", pady=(0, 20))
        ctk.CTkButton(inner, text="Создать аккаунт", height=50, fg_color=GREEN_SOFT, hover_color=GRAY_LIGHT, text_color=GREEN, font=("Segoe UI", 14, "bold"), corner_radius=8, command=self.show_register).pack(fill="x")

    def attempt_login(self):
        email = self.email_entry.get().strip()
        pw = self.pass_entry.get()
        if not email or not pw:
            messagebox.showerror("Ошибка", "Заполни все поля", parent=self)
            return
        conn = db()
        row = conn.execute("SELECT role FROM users WHERE email=? AND password=?", (email, hash_pw(pw))).fetchone()
        conn.close()

        if not row:
            messagebox.showerror("Ошибка", "Неверный email или пароль", parent=self)
            return

        self.user_email = email
        self.role = row[0]
        self.is_teacher = (self.role == "teacher")

        conn = db()
        user_row = conn.execute("SELECT nickname, avatar, created_at, specialty, group_name, xp, level, streak FROM users WHERE email=?", (email,)).fetchone()
        conn.close()

        self.nickname = user_row[0] if user_row else email
        self.avatar_path = user_row[1] if user_row else ""
        self.created_at = user_row[2] if user_row else ""
        self.specialty = user_row[3] if user_row else ""
        self.group_name = user_row[4] if user_row else ""
        self.xp = user_row[5] if user_row else 0
        self.level = user_row[6] if user_row else 1
        self.streak = user_row[7] if user_row else 0

        self.update_streak_on_login()
        self.check_and_unlock_achievements()

        if self.is_teacher:
            self.filter_specialty = self.specialty
            self.filter_group = self.group_name
            groups = get_all_groups()
            if groups:
                self.filter_specialty = groups[0][0]
                self.filter_group = groups[0][1]

        self.show_main_app()
        self.after(1000, self.check_deadlines)
        self.after(2000, self.update_theme_auto)

    def update_streak_on_login(self):
        conn = db()
        row = conn.execute("SELECT streak, last_login FROM users WHERE email=?", (self.user_email,)).fetchone()
        conn.close()
        if not row: return
        streak, last_login = row
        today = datetime.now().date()

        new_streak = streak
        if last_login:
            try:
                last = datetime.strptime(last_login, "%d.%m.%Y").date()
                delta = (today - last).days
                if delta == 0: return
                elif delta == 1: new_streak = streak + 1
                else: new_streak = 1
            except: new_streak = 1
        else:
            new_streak = 1

        conn = db()
        conn.execute("UPDATE users SET streak=?, last_login=? WHERE email=?", (new_streak, today.strftime("%d.%m.%Y"), self.user_email))
        conn.commit()
        conn.close()
        self.streak = new_streak

    def update_theme_auto(self):
        theme = get_setting("theme")
        if theme == "auto":
            hour = datetime.now().hour
            ctk.set_appearance_mode("light" if 8 <= hour < 20 else "dark")
        self.after(600000, self.update_theme_auto)

    def show_register(self):
        self.clear_window()

        left_frame = ctk.CTkFrame(self, fg_color=GREEN, corner_radius=0)
        left_frame.pack(side="left", fill="both", expand=True)

        right_frame = ctk.CTkFrame(self, fg_color=WHITE, corner_radius=0, width=500)
        right_frame.pack(side="right", fill="y")
        right_frame.pack_propagate(False)

        ctk.CTkLabel(left_frame, text="Study Planner", font=("Segoe UI", 52, "bold"), text_color=WHITE).place(relx=0.5, rely=0.4, anchor="center")
        ctk.CTkLabel(left_frame, text="Присоединяйся к нам", font=("Segoe UI", 20), text_color=WHITE).place(relx=0.5, rely=0.5, anchor="center")

        scroll_right = ctk.CTkScrollableFrame(right_frame, fg_color="transparent")
        scroll_right.pack(fill="both", expand=True, padx=30, pady=30)

        inner = ctk.CTkFrame(scroll_right, fg_color="transparent")
        inner.pack(fill="x")

        ctk.CTkLabel(inner, text="Регистрация", font=("Segoe UI", 28, "bold"), text_color=BLACK).pack(pady=(10, 30))

        ctk.CTkLabel(inner, text="Email", font=("Segoe UI", 13), text_color=GRAY_DARK).pack(anchor="w", pady=(0, 5))
        self.reg_email = ctk.CTkEntry(inner, placeholder_text="example@mail.com", height=45, fg_color=GRAY_BG, border_color=GRAY_LIGHT, corner_radius=8)
        self.reg_email.pack(fill="x", pady=(0, 15))

        ctk.CTkLabel(inner, text="Ник (3-20 символов)", font=("Segoe UI", 13), text_color=GRAY_DARK).pack(anchor="w", pady=(0, 5))
        self.reg_nick = ctk.CTkEntry(inner, placeholder_text="SuperStudent", height=45, fg_color=GRAY_BG, border_color=GRAY_LIGHT, corner_radius=8)
        self.reg_nick.pack(fill="x", pady=(0, 15))

        ctk.CTkLabel(inner, text="Пароль (от 4 символов)", font=("Segoe UI", 13), text_color=GRAY_DARK).pack(anchor="w", pady=(0, 5))
        self.reg_pass = ctk.CTkEntry(inner, placeholder_text="••••••••", show="*", height=45, fg_color=GRAY_BG, border_color=GRAY_LIGHT, corner_radius=8)
        self.reg_pass.pack(fill="x", pady=(0, 20))

        ctk.CTkLabel(inner, text="Кто вы?", font=("Segoe UI", 13), text_color=GRAY_DARK).pack(anchor="w", pady=(0, 5))
        self.reg_role_var = ctk.StringVar(value="student")
        role_frame = ctk.CTkFrame(inner, fg_color="transparent")
        role_frame.pack(fill="x", pady=(0, 15))

        ctk.CTkRadioButton(role_frame, text="Студент", variable=self.reg_role_var, value="student", text_color=BLACK, fg_color=GREEN, command=self.toggle_reg_role).pack(side="left", padx=(0, 30))
        ctk.CTkRadioButton(role_frame, text="Преподаватель", variable=self.reg_role_var, value="teacher", text_color=BLACK, fg_color=GREEN, command=self.toggle_reg_role).pack(side="left")

        self.reg_student_frame = ctk.CTkFrame(inner, fg_color="transparent")
        self.reg_student_frame.pack(fill="x")

        ctk.CTkLabel(self.reg_student_frame, text="Специальность", font=("Segoe UI", 13), text_color=GRAY_DARK).pack(anchor="w", pady=(0, 5))
        self.reg_spec_var = ctk.StringVar(value=SPECIALTIES[0])
        ctk.CTkOptionMenu(self.reg_student_frame, values=SPECIALTIES, variable=self.reg_spec_var, fg_color=GREEN, button_color=GREEN_LIGHT, dropdown_fg_color=WHITE, dropdown_text_color=BLACK, height=40).pack(fill="x", pady=(0, 15))

        ctk.CTkLabel(self.reg_student_frame, text="Группа", font=("Segoe UI", 13), text_color=GRAY_DARK).pack(anchor="w", pady=(0, 5))
        self.reg_group = ctk.CTkEntry(self.reg_student_frame, placeholder_text="например: ИС-21", height=45, fg_color=GRAY_BG, border_color=GRAY_LIGHT, corner_radius=8)
        self.reg_group.pack(fill="x", pady=(0, 15))

        self.reg_teacher_frame = ctk.CTkFrame(inner, fg_color="transparent")
        ctk.CTkLabel(self.reg_teacher_frame, text="Код преподавателя", font=("Segoe UI", 13), text_color=GRAY_DARK).pack(anchor="w", pady=(0, 5))
        self.reg_tcode = ctk.CTkEntry(self.reg_teacher_frame, placeholder_text="TEACHER2026", height=45, fg_color=GRAY_BG, border_color=GRAY_LIGHT, corner_radius=8)
        self.reg_tcode.pack(fill="x", pady=(0, 15))

        ctk.CTkButton(inner, text="Зарегистрироваться", height=50, fg_color=GREEN, hover_color=GREEN_LIGHT, text_color=WHITE, font=("Segoe UI", 16, "bold"), command=self.do_register).pack(fill="x", pady=(10, 15))
        ctk.CTkButton(inner, text="Уже есть аккаунт? Войти", height=45, fg_color="transparent", text_color=GRAY_DARK, hover_color=GRAY_LIGHT, command=self.show_login).pack(fill="x")

    def toggle_reg_role(self):
        if self.reg_role_var.get() == "teacher":
            self.reg_student_frame.pack_forget()
            self.reg_teacher_frame.pack(fill="x")
        else:
            self.reg_teacher_frame.pack_forget()
            self.reg_student_frame.pack(fill="x")

    def do_register(self):
        email = self.reg_email.get().strip()
        nick = self.reg_nick.get().strip()
        pw = self.reg_pass.get()
        role = self.reg_role_var.get()

        if not email or not pw or len(pw) < 4:
            messagebox.showerror("Ошибка", "Email обязателен, пароль от 4 символов", parent=self)
            return
        ok, err = validate_nickname(nick)
        if not ok:
            messagebox.showerror("Ошибка", err, parent=self)
            return

        spec, group = "", ""
        if role == "student":
            spec = self.reg_spec_var.get()
            group = self.reg_group.get().strip().upper()
            if not group:
                messagebox.showerror("Ошибка", "Введите группу", parent=self)
                return
        else:
            if self.reg_tcode.get().strip() != TEACHER_CODE:
                messagebox.showerror("Ошибка", "Неверный код преподавателя", parent=self)
                return

        conn = db()
        try:
            conn.execute("INSERT INTO users (email, nickname, password, role, created_at, specialty, group_name) VALUES (?,?,?,?,?,?,?)",
                         (email, nick, hash_pw(pw), role, datetime.now().strftime("%d.%m.%Y"), spec, group))
            conn.commit()
            messagebox.showinfo("Готово", "Аккаунт создан!", parent=self)
            self.show_login()
        except sqlite3.IntegrityError:
            messagebox.showerror("Ошибка", "Email уже занят", parent=self)
        finally:
            conn.close()

    # ==================== ГЛАВНЫЙ ЭКРАН ====================
    def refresh_profile_btn(self):
        """Обновляет надпись/аватарку в верхней панели."""
        if not hasattr(self, "profile_btn") or not self.profile_btn.winfo_exists():
            return
        role_text = "Преподаватель" if self.is_teacher else "Студент"
        lvl_text = f" [Lvl {self.level}]" if not self.is_teacher else ""
        text = f"{self.nickname}{lvl_text} · {role_text}"
        if self.avatar_path and os.path.exists(self.avatar_path):
            try:
                pil_img = Image.open(self.avatar_path).resize((32, 32), Image.Resampling.LANCZOS)
                self.topbar_avatar_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(32, 32))
                self.profile_btn.configure(text=text, image=self.topbar_avatar_img, compound="left")
                return
            except Exception:
                pass
        self.profile_btn.configure(text=text + "  👤", image=None)

    def show_main_app(self):
        self.clear_window()

        top = ctk.CTkFrame(self, fg_color=GREEN, corner_radius=0, height=70)
        top.pack(fill="x")
        top.pack_propagate(False)

        ctk.CTkLabel(top, text="🎓  Study Planner v5.1", font=("Segoe UI", 22, "bold"), text_color=WHITE).pack(side="left", padx=30)

        right_top = ctk.CTkFrame(top, fg_color="transparent")
        right_top.pack(side="right", padx=30)

        self.profile_btn = ctk.CTkButton(right_top, text="", font=("Segoe UI", 14, "bold"),
                                         fg_color="transparent", hover_color=GREEN_LIGHT,
                                         text_color=WHITE, command=self.show_profile)
        self.profile_btn.pack(side="left")
        self.refresh_profile_btn()

        self.main_container = ctk.CTkFrame(self, fg_color=GRAY_BG, corner_radius=0)
        self.main_container.pack(fill="both", expand=True)

        self.sidebar = ctk.CTkFrame(self.main_container, fg_color=WHITE, width=250, corner_radius=0)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        ctk.CTkLabel(self.sidebar, text="МЕНЮ", font=("Segoe UI", 12, "bold"), text_color=GRAY_MED).pack(pady=(30, 15), padx=25, anchor="w")

        items = [
            ("🏠 Главная", "dashboard"), ("📅 Расписание", "schedule"),
            ("📝 Задания", "homework"), ("📖 Сессии", "sessions"),
            ("📊 Журнал", "grades"), ("⏱️ Фокус", "pomodoro"),
            ("📆 Календарь", "calendar"), ("📌 Заметки", "notes"),
            ("🏅 Достижения", "achievements")
        ]
        if self.is_teacher:
            items.append(("👥 Студенты", "students"))

        for name, key in items:
            row = ctk.CTkFrame(self.sidebar, fg_color="transparent", height=42)
            row.pack(fill="x", padx=15, pady=3)
            row.pack_propagate(False)

            indicator = ctk.CTkFrame(row, fg_color="transparent", width=4, corner_radius=2)
            indicator.pack(side="left", fill="y", pady=8)

            btn = ctk.CTkButton(row, text=name, anchor="w", height=42, fg_color="transparent",
                                hover_color=GREEN_SOFT, text_color=GRAY_DARK, font=("Segoe UI", 14),
                                corner_radius=8, command=lambda k=key: self.switch_tab(k))
            btn.pack(side="left", fill="both", expand=True, padx=(5, 0))

            self.nav_indicators[key] = indicator
            self.nav_buttons[key] = btn

        ctk.CTkButton(self.sidebar, text="🚪 Выйти", anchor="w", height=45, fg_color="transparent",
                      hover_color=RED_SOFT, text_color=RED, font=("Segoe UI", 15), corner_radius=8,
                      command=self.logout).pack(side="bottom", padx=15, pady=20, fill="x")

        self.content = ctk.CTkFrame(self.main_container, fg_color=GRAY_BG, corner_radius=0)
        self.content.pack(side="left", fill="both", expand=True)

        self.switch_tab("dashboard")

    def switch_tab(self, key):
        self.current_tab = key
        self.search_var.set("")

        if self.anim_job:
            try: self.after_cancel(self.anim_job)
            except: pass
            self.anim_job = None
        self.sparks.clear()

        for k, ind in self.nav_indicators.items():
            if k == key:
                ind.configure(fg_color=GREEN)
                self.nav_buttons[k].configure(fg_color=GREEN_SOFT, text_color=GREEN)
            else:
                ind.configure(fg_color="transparent")
                self.nav_buttons[k].configure(fg_color="transparent", text_color=GRAY_DARK)

        for w in self.content.winfo_children():
            w.destroy()

        titles = {
            "dashboard": f"Привет, {self.nickname}!" if not self.is_teacher else f"Панель управления",
            "schedule": "Расписание", "homework": "Задания", "sessions": "Сессии",
            "grades": "Электронный журнал", "pomodoro": "Помидорный таймер",
            "calendar": "Календарь дедлайнов", "notes": "Заметки",
            "achievements": "Достижения", "students": "Студенты"
        }

        header = ctk.CTkFrame(self.content, fg_color="transparent")
        header.pack(fill="x", padx=40, pady=(30, 10))

        ctk.CTkLabel(header, text=titles[key], font=("Segoe UI", 32, "bold"), text_color=BLACK).pack(side="left")

        today_str = datetime.now().strftime("%d %B %Y")
        ctk.CTkLabel(header, text=today_str, font=("Segoe UI", 14), text_color=GRAY_MED).pack(side="right", pady=(10, 0))

        if key == "dashboard": self.render_dashboard()
        elif key == "schedule": self.render_schedule()
        elif key == "homework": self.render_homework()
        elif key == "sessions": self.render_sessions()
        elif key == "grades": self.render_grades()
        elif key == "pomodoro": self.render_pomodoro()
        elif key == "calendar": self.render_calendar()
        elif key == "notes": self.render_notes()
        elif key == "achievements": self.render_achievements()
        elif key == "students": self.render_students()

    # ==================== ДАШБОРД ====================
    def get_tree_info(self):
        conn = db()
        total_done = conn.execute("SELECT COUNT(*) FROM homework_done WHERE user_email=?", (self.user_email,)).fetchone()[0]
        conn.close()
        if total_done < 3: return "🌱", "Росток", f"Выполни {3-total_done} заданий, чтобы дерево проросло"
        elif total_done < 10: return "🌿", "Молодое растение", f"До цветения: {10-total_done} заданий"
        elif total_done < 30: return "🌳", "Дерево", f"До могучего: {30-total_done} заданий"
        elif total_done < 70: return "🌳✨", "Цветущее дерево", f"До легендарного: {70-total_done} заданий"
        else: return "🌴👑", "Легендарное древо", "Ты настоящий герой учёбы!"

    def get_week_tracker(self):
        today = datetime.now().date()
        monday = today - timedelta(days=today.weekday())
        week_days = [(monday + timedelta(days=i)) for i in range(7)]

        conn = db()
        row = conn.execute("SELECT streak, last_login FROM users WHERE email=?", (self.user_email,)).fetchone()
        conn.close()

        streak, last_login_str = row if row else (0, "")
        if not last_login_str:
            return week_days, [False]*7

        last_login = datetime.strptime(last_login_str, "%d.%m.%Y").date()

        active_dates = []
        for i in range(streak):
            active_dates.append(last_login - timedelta(days=i))

        checks = [d in active_dates for d in week_days]
        return week_days, checks

    def start_fire_animation(self, label, text_val):
        self.sparks = []
        S = 4

        def update_frame(t=0):
            if not label.winfo_exists():
                return

            W, H = 160, 200
            img = Image.new("RGBA", (W*S, H*S), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            cx, cy = (W * S) // 2, (H * S) // 2 - 10 * S

            COLOR_BASE = (255, 242, 219)
            COLOR_FLAME_OUT = (255, 75, 0)
            COLOR_FLAME_IN = (255, 196, 0)
            COLOR_TEXT = (255, 150, 0)

            base_radius = 80 * S
            draw.ellipse((cx - base_radius, cy + 20*S - base_radius, cx + base_radius, cy + 20*S + base_radius), fill=COLOR_BASE)
            draw.rectangle((cx - base_radius, cy + 20*S, cx + base_radius, cy + 20*S + base_radius), fill=(0,0,0,0))

            glow = Image.new("RGBA", (W*S, H*S), (0,0,0,0))
            glow_draw = ImageDraw.Draw(glow)
            glow_draw.ellipse((cx - 70*S, cy + 30*S - 70*S, cx + 70*S, cy + 30*S + 70*S), fill=(255, 75, 0, 100))
            img = Image.alpha_composite(img, glow)
            draw = ImageDraw.Draw(img)

            sway = math.sin(t * 0.1) * 8 * S
            pulse = math.cos(t * 0.15) * 4 * S

            def get_flame_points(cx, cy, w, h):
                points = []
                for pt in range(0, 101, 5):
                    x = cx + (w / 2) * math.sin(math.radians(pt * 1.8)) + sway
                    y = cy + (h / 2) * math.cos(math.radians(pt * 1.8)) + pulse
                    if y < cy:
                        x = cx + (w / 2) * (1 - (cy - y) / (h / 2)) * math.sin(math.radians(pt * 1.8)) + sway
                    points.append((x, y))
                for pt in range(100, -1, -5):
                    x = cx - (w / 2) * math.sin(math.radians(pt * 1.8)) + sway
                    y = cy + (h / 2) * math.cos(math.radians(pt * 1.8)) + pulse
                    if y < cy:
                        x = cx - (w / 2) * (1 - (cy - y) / (h / 2)) * math.sin(math.radians(pt * 1.8)) + sway
                    points.append((x, y))
                return points

            draw.polygon(get_flame_points(cx, cy + 15*S, 100*S, 140*S), fill=COLOR_FLAME_OUT)
            draw.polygon(get_flame_points(cx, cy + 35*S, 60*S, 85*S), fill=COLOR_FLAME_IN)

            if random.random() < 0.3:
                self.sparks.append({
                    'x': cx + random.uniform(-15, 15) * S, 'y': cy - 20*S,
                    'vx': random.uniform(-2, 2) * S, 'vy': random.uniform(-6, -3) * S,
                    'r': random.uniform(2, 4) * S, 'color': random.choice([COLOR_FLAME_OUT, COLOR_FLAME_IN])
                })

            alive = []
            for sp in self.sparks:
                sp['x'] += sp['vx']; sp['y'] += sp['vy']; sp['vy'] += 0.15 * S; sp['r'] -= 0.03 * S
                if sp['r'] > 0.5 * S and sp['y'] > cy - 100*S:
                    alive.append(sp)
                    draw.ellipse((sp['x']-sp['r'], sp['y']-sp['r'], sp['x']+sp['r'], sp['y']+sp['r']), fill=sp['color'])
            self.sparks = alive

            try:
                font_main = ImageFont.truetype("segoeui.ttf", 90*S)
                font_sub = ImageFont.truetype("segoeui.ttf", 22*S)
            except:
                font_main = ImageFont.load_default()
                font_sub = ImageFont.load_default()

            draw.text((cx, cy + 110*S), str(text_val), font=font_main, fill=COLOR_TEXT, anchor="mm")
            draw.text((cx, cy + 160*S), "дн. подряд", font=font_sub, fill=COLOR_TEXT, anchor="mm")

            final_img = img.resize((W, H), Image.Resampling.LANCZOS)
            ctk_img = ctk.CTkImage(light_image=final_img, dark_image=final_img, size=(W, H))
            label.configure(image=ctk_img)
            label.image = ctk_img

            self.anim_job = self.after(30, lambda: update_frame(t + 1))

        update_frame()

    def render_dashboard(self):
        scroll = ctk.CTkScrollableFrame(self.content, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=30, pady=(0, 20))

        where = " WHERE specialty=? AND group_name=?"
        p1, p2 = (self.specialty, self.group_name) if not self.is_teacher else (self.filter_specialty, self.filter_group)
        reminder_days = int(get_setting("reminder_days") or 3)

        conn = db()
        total_hw = conn.execute(f"SELECT COUNT(*) FROM homework{where}", (p1, p2)).fetchone()[0]

        today_idx = datetime.now().weekday()
        total_today_pairs = 0
        if today_idx < 6:
            today_name = DAYS[today_idx]
            total_today_pairs = conn.execute(f"SELECT COUNT(*) FROM schedule{where} AND day=?", (p1, p2, today_name)).fetchone()[0]

        students_count = 0
        if self.is_teacher:
            students_count = conn.execute("SELECT COUNT(*) FROM users WHERE role='student' AND specialty=? AND group_name=?", (p1, p2)).fetchone()[0]
        conn.close()

        stats_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        stats_frame.pack(fill="x", pady=(0, 20))

        c1 = ctk.CTkFrame(stats_frame, fg_color=WHITE, corner_radius=16, border_width=1, border_color=GRAY_LIGHT)
        c1.pack(side="left", fill="x", expand=True, padx=(0, 10))
        ctk.CTkLabel(c1, text="📚 Всего заданий", font=("Segoe UI", 14, "bold"), text_color=GRAY_DARK).pack(pady=(15, 0))
        ctk.CTkLabel(c1, text=str(total_hw), font=("Segoe UI", 32, "bold"), text_color=BLACK).pack(pady=(0, 15))

        c2 = ctk.CTkFrame(stats_frame, fg_color=WHITE, corner_radius=16, border_width=1, border_color=GRAY_LIGHT)
        c2.pack(side="left", fill="x", expand=True, padx=(0 if self.is_teacher else 10, 10 if self.is_teacher else 0))
        ctk.CTkLabel(c2, text="📅 Пар сегодня", font=("Segoe UI", 14, "bold"), text_color=GRAY_DARK).pack(pady=(15, 0))
        ctk.CTkLabel(c2, text=str(total_today_pairs), font=("Segoe UI", 32, "bold"), text_color=BLACK).pack(pady=(0, 15))

        if self.is_teacher:
            c3 = ctk.CTkFrame(stats_frame, fg_color=WHITE, corner_radius=16, border_width=1, border_color=GRAY_LIGHT)
            c3.pack(side="left", fill="x", expand=True, padx=(10, 0))
            ctk.CTkLabel(c3, text="👥 Студентов", font=("Segoe UI", 14, "bold"), text_color=GRAY_DARK).pack(pady=(15, 0))
            ctk.CTkLabel(c3, text=str(students_count), font=("Segoe UI", 32, "bold"), text_color=BLACK).pack(pady=(0, 15))

        if not self.is_teacher:
            mid_frame = ctk.CTkFrame(scroll, fg_color="transparent")
            mid_frame.pack(fill="x", pady=(0, 20))
            mid_frame.columnconfigure(0, weight=1)
            mid_frame.columnconfigure(1, weight=1)

            tree_card = ctk.CTkFrame(mid_frame, fg_color=WHITE, corner_radius=16, border_width=1, border_color=GRAY_LIGHT)
            tree_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
            tree_inner = ctk.CTkFrame(tree_card, fg_color="transparent")
            tree_inner.pack(padx=25, pady=30, fill="x")

            emoji, title, desc = self.get_tree_info()
            ctk.CTkLabel(tree_inner, text=emoji, font=("Segoe UI Emoji", 80)).pack()
            ctk.CTkLabel(tree_inner, text=title, font=("Segoe UI", 16, "bold"), text_color=GREEN).pack(pady=(5, 0))
            ctk.CTkLabel(tree_inner, text=desc, font=("Segoe UI", 12), text_color=GRAY_DARK, wraplength=250).pack(pady=(5, 0))

            streak_card = ctk.CTkFrame(mid_frame, fg_color=WHITE, corner_radius=16, border_width=1, border_color=GRAY_LIGHT)
            streak_card.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
            streak_inner = ctk.CTkFrame(streak_card, fg_color="transparent")
            streak_inner.pack(padx=25, pady=20, fill="x")

            self.fire_label = ctk.CTkLabel(streak_inner, text="")
            self.fire_label.pack(pady=(0, 10))

            if self.anim_job:
                try: self.after_cancel(self.anim_job)
                except: pass
            self.start_fire_animation(self.fire_label, self.streak)

            days_frame = ctk.CTkFrame(streak_inner, fg_color="transparent")
            days_frame.pack(fill="x")

            week_days, checks = self.get_week_tracker()
            day_names = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]

            for i in range(7):
                col = ctk.CTkFrame(days_frame, fg_color="transparent")
                col.pack(side="left", expand=True, fill="x")
                is_today = (week_days[i] == datetime.now().date())
                ctk.CTkLabel(col, text=day_names[i], font=("Segoe UI", 11, "bold"), text_color=GRAY_DARK).pack()

                circle_color = DUO_ORANGE if checks[i] else DUO_GRAY
                if is_today:
                    circle = ctk.CTkFrame(col, fg_color=circle_color, width=30, height=30, corner_radius=15, border_width=2, border_color="#1CB0F6")
                else:
                    circle = ctk.CTkFrame(col, fg_color=circle_color, width=30, height=30, corner_radius=15)
                circle.pack(pady=5)
                circle.pack_propagate(False)
                if checks[i]:
                    ctk.CTkLabel(circle, text="✓", font=("Segoe UI", 16, "bold"), text_color="white").place(relx=0.5, rely=0.5, anchor="center")

        if today_idx < 6 and total_today_pairs > 0:
            today_name = DAYS[today_idx]
            conn = db()
            rows = conn.execute(f"SELECT subject, time, room FROM schedule{where} AND day=?", (p1, p2, today_name)).fetchall()
            conn.close()

            card = ctk.CTkFrame(scroll, fg_color=WHITE, corner_radius=16, border_width=1, border_color=GRAY_LIGHT)
            card.pack(fill="x", pady=(0, 20))
            inner = ctk.CTkFrame(card, fg_color="transparent")
            inner.pack(padx=25, pady=20, fill="x")

            ctk.CTkLabel(inner, text=f"📅 Сегодня по расписанию ({today_name})", font=("Segoe UI", 16, "bold"), text_color=BLACK).pack(anchor="w", pady=(0, 10))
            for r in rows:
                ctk.CTkLabel(inner, text=f"• {r[1]} — {r[0]} (ауд. {r[2]})", font=("Segoe UI", 14), text_color=GRAY_DARK).pack(anchor="w", pady=2)

        if not self.is_teacher:
            conn = db()
            hw_rows = conn.execute(f"SELECT id, title, deadline FROM homework{where} ORDER BY deadline ASC", (p1, p2)).fetchall()
            conn.close()

            urgent = []
            for hwid, title, dl_s in hw_rows:
                conn = db()
                done = conn.execute("SELECT 1 FROM homework_done WHERE user_email=? AND homework_id=?", (self.user_email, hwid)).fetchone()
                conn.close()
                if done: continue
                dl = parse_deadline(dl_s)
                if dl and dl.date() <= (datetime.now() + timedelta(days=reminder_days)).date():
                    urgent.append((title, dl_s))

            if urgent:
                card = ctk.CTkFrame(scroll, fg_color=WHITE, corner_radius=16, border_width=1, border_color=RED_SOFT)
                card.pack(fill="x", pady=(0, 20))
                inner = ctk.CTkFrame(card, fg_color="transparent")
                inner.pack(padx=25, pady=20, fill="x")

                ctk.CTkLabel(inner, text=f"🔥 Срочно сдать (в ближайшие {reminder_days} дн.)", font=("Segoe UI", 16, "bold"), text_color=RED).pack(anchor="w", pady=(0, 10))
                for u in urgent[:5]:
                    ctk.CTkLabel(inner, text=f"• {u[0]} (до {u[1]})", font=("Segoe UI", 14), text_color=GRAY_DARK).pack(anchor="w", pady=2)

    # ==================== ЖУРНАЛ ОЦЕНОК ====================
    def render_grades(self):
        scroll = ctk.CTkScrollableFrame(self.content, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=30, pady=(0, 20))

        if self.is_teacher:
            ctk.CTkLabel(scroll, text="Выставить оценку", font=("Segoe UI", 18, "bold"), text_color=BLACK).pack(anchor="w", pady=(10, 10))

            card = ctk.CTkFrame(scroll, fg_color=WHITE, corner_radius=16, border_width=1, border_color=GRAY_LIGHT)
            card.pack(fill="x", pady=(0, 20))
            inner = ctk.CTkFrame(card, fg_color="transparent")
            inner.pack(padx=25, pady=20, fill="x")

            ctk.CTkLabel(inner, text="Студент (Email)", text_color=GRAY_DARK).pack(anchor="w")
            students = []
            if self.filter_group and self.filter_group not in ("— нет групп —", "📋 Все группы"):
                conn = db()
                students = conn.execute("SELECT email, nickname FROM users WHERE role='student' AND specialty=? AND group_name=?", (self.filter_specialty, self.filter_group)).fetchall()
                conn.close()

            student_var = ctk.StringVar(value=students[0][1] if students else "Нет студентов")
            student_opts = [f"{s[1]} ({s[0]})" for s in students]
            student_menu = ctk.CTkOptionMenu(inner, values=student_opts if student_opts else ["Нет студентов"], variable=student_var, fg_color=GREEN, height=40)
            student_menu.pack(fill="x", pady=(5, 15))

            ctk.CTkLabel(inner, text="Предмет", text_color=GRAY_DARK).pack(anchor="w")
            subject_entry = ctk.CTkEntry(inner, height=40, placeholder_text="Математика")
            subject_entry.pack(fill="x", pady=(5, 15))

            ctk.CTkLabel(inner, text="Оценка (от 1 до 5)", text_color=GRAY_DARK).pack(anchor="w")
            grade_entry = ctk.CTkEntry(inner, height=40, placeholder_text="5")
            grade_entry.pack(fill="x", pady=(5, 15))

            def save_grade():
                if not student_opts: return messagebox.showerror("Ошибка", "В группе нет студентов", parent=self)
                st_email = students[student_opts.index(student_var.get())][0]
                subj = subject_entry.get().strip()
                gr = grade_entry.get().strip()

                if not subj or not gr.isdigit() or not (1 <= int(gr) <= 5):
                    messagebox.showerror("Ошибка", "Заполните предмет и поставьте оценку от 1 до 5", parent=self)
                    return

                conn = db()
                conn.execute("INSERT INTO grades (student_email, subject, grade, date, teacher_email) VALUES (?,?,?,?,?)",
                             (st_email, subj, int(gr), datetime.now().strftime("%d.%m.%Y"), self.user_email))
                conn.commit()
                conn.close()
                messagebox.showinfo("Успех", "Оценка выставлена!", parent=self)
                self.switch_tab("grades")

            ctk.CTkButton(inner, text="Выставить", height=45, fg_color=GREEN, command=save_grade).pack(fill="x", pady=10)

            ctk.CTkLabel(scroll, text="Последние оценки в группе", font=("Segoe UI", 18, "bold"), text_color=BLACK).pack(anchor="w", pady=(10, 10))
            if not self.filter_group or self.filter_group in ("— нет групп —", "📋 Все группы"):
                ctk.CTkLabel(scroll, text="Выберите группу для отображения", text_color=GRAY_MED).pack(pady=20)
                return

            conn = db()
            g_rows = conn.execute("""SELECT u.nickname, g.subject, g.grade, g.date FROM grades g
                                     JOIN users u ON u.email = g.student_email
                                     WHERE u.specialty=? AND u.group_name=?
                                     ORDER BY g.id DESC LIMIT 20""", (self.filter_specialty, self.filter_group)).fetchall()
            conn.close()

            for r in g_rows:
                gc = ctk.CTkFrame(scroll, fg_color=WHITE, corner_radius=12, border_width=1, border_color=GRAY_LIGHT)
                gc.pack(fill="x", pady=5)
                gci = ctk.CTkFrame(gc, fg_color="transparent")
                gci.pack(padx=15, pady=10, fill="x")

                col = GREEN if r[2] >= 4 else (ORANGE if r[2] == 3 else RED)
                ctk.CTkLabel(gci, text=f"{r[2]}", font=("Segoe UI", 24, "bold"), text_color=col, width=40).pack(side="left")
                ctk.CTkLabel(gci, text=f"{r[0]} — {r[1]}", font=("Segoe UI", 14, "bold"), text_color=BLACK).pack(side="left", padx=10)
                ctk.CTkLabel(gci, text=r[3], font=("Segoe UI", 12), text_color=GRAY_MED).pack(side="right")

        else:
            conn = db()
            g_rows = conn.execute("SELECT subject, grade, date FROM grades WHERE student_email=? ORDER BY id DESC", (self.user_email,)).fetchall()
            conn.close()

            if not g_rows:
                ctk.CTkLabel(scroll, text="У вас пока нет оценок", text_color=GRAY_MED, font=("Segoe UI", 16)).pack(pady=40)
                return

            avg = sum(r[1] for r in g_rows) / len(g_rows)
            ctk.CTkLabel(scroll, text=f"Ваш средний балл: {avg:.2f}", font=("Segoe UI", 24, "bold"), text_color=GOLD).pack(pady=(10, 20))

            for r in g_rows:
                gc = ctk.CTkFrame(scroll, fg_color=WHITE, corner_radius=12, border_width=1, border_color=GRAY_LIGHT)
                gc.pack(fill="x", pady=5)
                gci = ctk.CTkFrame(gc, fg_color="transparent")
                gci.pack(padx=20, pady=12, fill="x")

                col = GREEN if r[1] >= 4 else (ORANGE if r[1] == 3 else RED)
                ctk.CTkLabel(gci, text=f"{r[1]}", font=("Segoe UI", 28, "bold"), text_color=col, width=50).pack(side="left")
                ctk.CTkLabel(gci, text=r[0], font=("Segoe UI", 16, "bold"), text_color=BLACK).pack(side="left", padx=10)
                ctk.CTkLabel(gci, text=r[2], font=("Segoe UI", 13), text_color=GRAY_MED).pack(side="right")

            ctk.CTkButton(scroll, text="📊 Показать график успеваемости", fg_color=GREEN_SOFT, text_color=GREEN, height=45,
                          command=self.show_grade_chart).pack(fill="x", pady=20)

    def show_grade_chart(self):
        win = ctk.CTkToplevel(self)
        win.title("График успеваемости")
        win.geometry("600x400")
        win.transient(self)

        conn = db()
        rows = conn.execute("SELECT subject, AVG(grade) FROM grades WHERE student_email=? GROUP BY subject", (self.user_email,)).fetchall()
        conn.close()

        if not rows:
            return

        subjects = [r[0] for r in rows]
        grades = [r[1] for r in rows]

        fig = Figure(figsize=(6, 4), dpi=100)
        ax = fig.add_subplot(111)
        ax.bar(subjects, grades, color='#4CAF50')
        ax.set_ylim(0, 5.5)
        ax.set_ylabel('Средняя оценка')
        ax.set_title('Успеваемость по предметам')

        canvas = FigureCanvasTkAgg(fig, master=win)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=20, pady=20)

    # ==================== ПОМОДОРО ====================
    def render_pomodoro(self):
        frame = ctk.CTkFrame(self.content, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=40, pady=20)

        card = ctk.CTkFrame(frame, fg_color=WHITE, corner_radius=16, border_width=1, border_color=GRAY_LIGHT)
        card.pack(expand=True, fill="both", padx=100, pady=50)

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.place(relx=0.5, rely=0.5, anchor="center")

        self.timer_lbl = ctk.CTkLabel(inner, text="25:00", font=("Segoe UI", 80, "bold"), text_color=BLACK)
        self.timer_lbl.pack(pady=(0, 20))

        ctk.CTkLabel(inner, text="Сконцентрируйся на учебе. 25 минут работы, 5 минут отдыха.", font=("Segoe UI", 14), text_color=GRAY_MED).pack(pady=(0, 30))

        btn_frame = ctk.CTkFrame(inner, fg_color="transparent")
        btn_frame.pack()

        self.btn_start = ctk.CTkButton(btn_frame, text="▶ Старт", height=50, width=150, fg_color=GREEN, font=("Segoe UI", 16, "bold"), command=self.toggle_pomodoro)
        self.btn_start.pack(side="left", padx=10)

        ctk.CTkButton(btn_frame, text="🔄 Сброс", height=50, width=150, fg_color=GRAY_LIGHT, text_color=GRAY_DARK, font=("Segoe UI", 16, "bold"), command=self.reset_pomodoro).pack(side="left", padx=10)

        self.btn_sound = ctk.CTkButton(inner, text="🔇 Включить дождь", fg_color=GRAY_LIGHT, text_color=GRAY_DARK, command=self.toggle_sound)
        self.btn_sound.pack(pady=20)

        self.update_pomo_label()

    def toggle_sound(self):
        try:
            import winsound
        except ImportError:
            return

        sound_file = os.path.join(BASE_DIR, "rain.wav")

        if not os.path.exists(sound_file):
            messagebox.showinfo("Инфо", "Положите файл rain.wav в папку с программой.", parent=self)
            return

        if self.sound_playing:
            winsound.PlaySound(None, winsound.SND_PURGE)
            self.sound_playing = False
            self.btn_sound.configure(text="🔇 Включить дождь")
        else:
            winsound.PlaySound(sound_file, winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_LOOP)
            self.sound_playing = True
            self.btn_sound.configure(text="🔊 Выключить дождь")

    def toggle_pomodoro(self):
        if self.pomo_running:
            self.pomo_running = False
            self.btn_start.configure(text="▶ Продолжить")
            if self.pomo_job:
                self.after_cancel(self.pomo_job)
                self.pomo_job = None
        else:
            self.pomo_running = True
            self.btn_start.configure(text="⏸ Пауза")
            self.run_pomodoro()

    def reset_pomodoro(self):
        if self.pomo_job:
            self.after_cancel(self.pomo_job)
            self.pomo_job = None
        self.pomo_running = False
        self.pomo_time = 25 * 60
        self.update_pomo_label()
        self.btn_start.configure(text="▶ Старт")

    def run_pomodoro(self):
        if self.pomo_running and self.pomo_time > 0:
            self.pomo_time -= 1
            self.update_pomo_label()
            self.pomo_job = self.after(1000, self.run_pomodoro)
        elif self.pomo_time == 0:
            self.pomo_running = False
            self.btn_start.configure(text="▶ Старт")
            self.pomo_time = 25 * 60
            self.update_pomo_label()
            notify("Pomodoro", "Время вышло! Пора отдохнуть.")
            messagebox.showinfo("Помидор", "25 минут прошло! Сделай перерыв на 5 минут.", parent=self)

    def update_pomo_label(self):
        if hasattr(self, 'timer_lbl') and self.timer_lbl.winfo_exists():
            m = self.pomo_time // 60
            s = self.pomo_time % 60
            self.timer_lbl.configure(text=f"{m:02d}:{s:02d}")

    # ==================== РАСПИСАНИЕ ====================
    def render_schedule(self):
        top_bar = ctk.CTkFrame(self.content, fg_color="transparent")
        top_bar.pack(fill="x", padx=40, pady=(0, 20))

        if self.is_teacher:
            self.render_group_selector(top_bar)
            ctk.CTkButton(top_bar, text="+ Добавить", height=40, fg_color=GREEN, hover_color=GREEN_LIGHT, text_color=WHITE, font=("Segoe UI", 14, "bold"), width=140, corner_radius=8, command=lambda: self.show_add_form("schedule")).pack(side="left", padx=(15, 0))

        view_frame = ctk.CTkFrame(top_bar, fg_color="transparent")
        view_frame.pack(side="right")
        ctk.CTkButton(view_frame, text="📋 Список", width=100, height=36, fg_color=GREEN if self.schedule_view == "list" else WHITE, text_color=WHITE if self.schedule_view == "list" else GRAY_DARK, font=("Segoe UI", 12, "bold"), command=lambda: self.set_schedule_view("list")).pack(side="left", padx=2)
        ctk.CTkButton(view_frame, text="📊 Таймлайн", width=110, height=36, fg_color=GREEN if self.schedule_view == "timeline" else WHITE, text_color=WHITE if self.schedule_view == "timeline" else GRAY_DARK, font=("Segoe UI", 12, "bold"), command=lambda: self.set_schedule_view("timeline")).pack(side="left", padx=2)
        ctk.CTkButton(view_frame, text="📄 PDF", width=80, height=36, fg_color=RED_SOFT, text_color=RED, font=("Segoe UI", 12, "bold"), command=self.export_schedule_pdf).pack(side="left", padx=(10, 0))
        ctk.CTkButton(view_frame, text="📄 TXT", width=80, height=36, fg_color=GREEN_SOFT, text_color=GREEN, font=("Segoe UI", 12, "bold"), command=self.export_schedule_txt).pack(side="left", padx=2)

        if self.schedule_view == "list":
            days_frame = ctk.CTkFrame(self.content, fg_color="transparent")
            days_frame.pack(fill="x", padx=40, pady=(0, 20))

            options = ["Все"] + DAYS
            for d in options:
                is_active = (self.schedule_day == d)
                ctk.CTkButton(days_frame, text=d, width=60, height=36, fg_color=GREEN if is_active else WHITE, text_color=WHITE if is_active else GRAY_DARK, font=("Segoe UI", 13, "bold"), corner_radius=18, command=lambda x=d: self.set_day(x)).pack(side="left", padx=(0, 10))

            self.render_search_bar()

            self.scroll_frame = ctk.CTkScrollableFrame(self.content, fg_color="transparent")
            self.scroll_frame.pack(fill="both", expand=True, padx=30, pady=(0, 20))
            self.refresh_items("schedule")
        else:
            self.render_timeline()

    def export_schedule_pdf(self):
        where, params = self.get_filter_sql()
        conn = db()
        rows = conn.execute(f"SELECT * FROM schedule{where} ORDER BY day, time", params).fetchall()
        conn.close()

        if not rows:
            messagebox.showwarning("Экспорт", "Расписание пустое.", parent=self)
            return

        p = filedialog.asksaveasfilename(parent=self, defaultextension=".pdf", filetypes=[("PDF файл", "*.pdf")], initialfile=f"raspisanie_{self.group_name or 'all'}.pdf")
        if not p: return

        pdf = FPDF()
        pdf.add_page()

        try:
            pdf.add_font('DejaVu', '', 'DejaVuSans.ttf', uni=True)
            pdf.set_font("DejaVu", size=16)
        except:
            messagebox.showerror("Ошибка", "Для PDF нужен файл DejaVuSans.ttf в папке с программой.", parent=self)
            return

        pdf.cell(200, 10, txt="РАСПИСАНИЕ ЗАНЯТИЙ", ln=True, align='C')
        pdf.set_font("DejaVu", size=10)
        pdf.cell(200, 10, txt=f"Группа: {self.filter_group or self.group_name}", ln=True, align='L')

        by_day = {d: [] for d in DAYS}
        for r in rows:
            day, time_str, subject, teacher, room = r[3], r[4], r[1], r[2], r[5]
            if day in by_day:
                by_day[day].append(f"  {time_str} — {subject} ({teacher}, ауд. {room})")

        for day in DAYS:
            if by_day[day]:
                pdf.ln(5)
                pdf.set_font("DejaVu", size=12)
                pdf.cell(200, 8, txt=day, ln=True)
                pdf.set_font("DejaVu", size=10)
                for line in by_day[day]:
                    pdf.cell(200, 6, txt=line, ln=True)

        pdf.output(p)
        messagebox.showinfo("Готово", f"PDF сохранен в:\n{p}", parent=self)

    def export_schedule_txt(self):
        where, params = self.get_filter_sql()
        conn = db()
        rows = conn.execute(f"SELECT * FROM schedule{where} ORDER BY day, time", params).fetchall()
        conn.close()

        if not rows:
            messagebox.showwarning("Экспорт", "Расписание пустое.", parent=self)
            return

        by_day = {d: [] for d in DAYS}
        for r in rows:
            day, time_str, subject, teacher, room = r[3], r[4], r[1], r[2], r[5]
            if day in by_day:
                by_day[day].append(f"  {time_str} — {subject} ({teacher}, ауд. {room})")

        text = "РАСПИСАНИЕ ЗАНЯТИЙ\n"
        text += f"Группа: {self.filter_group or self.group_name}\n"
        text += f"Дата экспорта: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"

        for day in DAYS:
            if by_day[day]:
                text += f"{day}:\n"
                for line in by_day[day]:
                    text += line + "\n"
                text += "\n"

        p = filedialog.asksaveasfilename(parent=self, defaultextension=".txt", filetypes=[("Текстовый файл", "*.txt")], initialfile=f"raspisanie_{self.group_name or 'all'}.txt")
        if not p: return

        try:
            with open(p, "w", encoding="utf-8") as f:
                f.write(text)
            messagebox.showinfo("Готово", f"Сохранено в:\n{p}", parent=self)
        except Exception as e:
            messagebox.showerror("Ошибка", str(e), parent=self)

    def set_schedule_view(self, view):
        self.schedule_view = view
        self.switch_tab("schedule")

    def render_timeline(self):
        where, params = self.get_filter_sql()
        conn = db()
        rows = conn.execute(f"SELECT * FROM schedule{where}", params).fetchall()
        conn.close()

        parity = current_week_parity()
        filtered = []
        for r in rows:
            wt = r[9] if len(r) > 9 else 0
            if wt == 1 and parity != "even": continue
            if wt == 2 and parity != "odd": continue
            filtered.append(r)

        bg_color = "#FFFFFF" if ctk.get_appearance_mode() == "Light" else "#1E1E1E"
        line_color = "#EEEEEE" if ctk.get_appearance_mode() == "Light" else "#444444"
        text_color = "#000000" if ctk.get_appearance_mode() == "Light" else "#FFFFFF"

        canvas = tk.Canvas(self.content, bg=bg_color, highlightthickness=0)
        canvas.pack(fill="both", expand=True, padx=40, pady=20)

        HOUR_HEIGHT = 50
        START_HOUR = 8
        END_HOUR = 22
        DAY_WIDTH = 130
        LEFT_MARGIN = 70
        TOP_MARGIN = 40

        for i, day in enumerate(DAYS):
            x = LEFT_MARGIN + i * DAY_WIDTH + DAY_WIDTH // 2
            canvas.create_text(x, 20, text=day, font=("Segoe UI", 13, "bold"), fill=text_color)

        for h in range(START_HOUR, END_HOUR + 1):
            y = TOP_MARGIN + (h - START_HOUR) * HOUR_HEIGHT
            canvas.create_text(LEFT_MARGIN - 10, y, text=f"{h:02d}:00", font=("Segoe UI", 10), anchor="e", fill=text_color)
            canvas.create_line(LEFT_MARGIN, y, LEFT_MARGIN + 6 * DAY_WIDTH, y, fill=line_color)

        for r in filtered:
            day, time_str = r[3], r[4]
            if day not in DAYS: continue
            day_idx = DAYS.index(day)

            try:
                t = time_str.replace("—", "-").replace("–", "-").replace(" ", "")
                start_str, end_str = t.split("-")
                sh, sm = map(int, start_str.split(":")[:2])
                eh, em = map(int, end_str.split(":")[:2])
            except:
                sh, sm, eh, em = 9, 0, 10, 30

            y1 = TOP_MARGIN + (sh - START_HOUR) * HOUR_HEIGHT + sm * HOUR_HEIGHT // 60
            y2 = TOP_MARGIN + (eh - START_HOUR) * HOUR_HEIGHT + em * HOUR_HEIGHT // 60
            x1 = LEFT_MARGIN + day_idx * DAY_WIDTH + 5
            x2 = x1 + DAY_WIDTH - 10

            color = safe_color(r[8])
            canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="")
            name = r[1] if len(r[1]) < 15 else r[1][:13] + "..."
            canvas.create_text((x1 + x2) // 2, (y1 + y2) // 2, text=name, fill="white", font=("Segoe UI", 10, "bold"), width=DAY_WIDTH - 15)
            canvas.create_text((x1 + x2) // 2, (y1 + y2) // 2 + 15, text=f"ауд. {r[5]}", fill="white", font=("Segoe UI", 9), width=DAY_WIDTH - 15)

    def set_day(self, day):
        self.schedule_day = day
        self.switch_tab("schedule")

    # ==================== ЗАДАНИЯ ====================
    def render_homework(self):
        top_bar = ctk.CTkFrame(self.content, fg_color="transparent")
        top_bar.pack(fill="x", padx=40, pady=(0, 20))

        if self.is_teacher:
            self.render_group_selector(top_bar)
            ctk.CTkButton(top_bar, text="+ Добавить", height=40, fg_color=GREEN, hover_color=GREEN_LIGHT, text_color=WHITE, font=("Segoe UI", 14, "bold"), width=140, corner_radius=8, command=lambda: self.show_add_form("homework")).pack(side="left", padx=(15, 0))

        filters_frame = ctk.CTkFrame(self.content, fg_color="transparent")
        filters_frame.pack(fill="x", padx=40, pady=(0, 20))

        options = [("Все", "all"), ("Активные", "active"), ("Выполненные", "done"), ("Просроченные", "overdue")]
        for label, val in options:
            is_active = (self.hw_filter == val)
            ctk.CTkButton(filters_frame, text=label, height=36, fg_color=GREEN if is_active else WHITE, text_color=WHITE if is_active else GRAY_DARK, font=("Segoe UI", 13, "bold"), corner_radius=18, command=lambda x=val: self.set_hw_filter(x)).pack(side="left", padx=(0, 10))

        self.render_search_bar()

        self.scroll_frame = ctk.CTkScrollableFrame(self.content, fg_color="transparent")
        self.scroll_frame.pack(fill="both", expand=True, padx=30, pady=(0, 20))
        self.refresh_items("homework")

    def set_hw_filter(self, val):
        self.hw_filter = val
        self.switch_tab("homework")

    # ==================== СЕССИИ (НОВЫЙ РАЗДЕЛ) ====================
    def render_sessions(self):
        top_bar = ctk.CTkFrame(self.content, fg_color="transparent")
        top_bar.pack(fill="x", padx=40, pady=(0, 20))

        if self.is_teacher:
            self.render_group_selector(top_bar)
            ctk.CTkButton(top_bar, text="+ Добавить", height=40, fg_color=GREEN, hover_color=GREEN_LIGHT,
                          text_color=WHITE, font=("Segoe UI", 14, "bold"), width=140, corner_radius=8,
                          command=lambda: self.show_add_form("sessions")).pack(side="left", padx=(15, 0))

        self.render_search_bar()

        self.scroll_frame = ctk.CTkScrollableFrame(self.content, fg_color="transparent")
        self.scroll_frame.pack(fill="both", expand=True, padx=30, pady=(0, 20))
        self.refresh_items("sessions")

    # ==================== ЗАМЕТКИ ====================
    def render_notes(self):
        if not self.is_teacher:
            ctk.CTkButton(self.content, text="+ Новая заметка", height=40, fg_color=GREEN, hover_color=GREEN_LIGHT, text_color=WHITE, font=("Segoe UI", 14, "bold"), width=180, corner_radius=8, command=self.show_add_form_note).pack(anchor="w", padx=40, pady=(0, 20))

        self.render_search_bar()

        self.scroll_frame = ctk.CTkScrollableFrame(self.content, fg_color="transparent")
        self.scroll_frame.pack(fill="both", expand=True, padx=30, pady=(0, 20))
        self.refresh_notes()

    # ==================== СТУДЕНТЫ (преподаватель) ====================
    def render_students(self):
        top_bar = ctk.CTkFrame(self.content, fg_color="transparent")
        top_bar.pack(fill="x", padx=40, pady=(0, 20))
        self.render_group_selector(top_bar)

        if not self.filter_group or self.filter_group in ("— нет групп —", "📋 Все группы"):
            ctk.CTkLabel(self.content, text="Выберите конкретную группу", text_color=GRAY_MED, font=("Segoe UI", 16)).pack(pady=40)
            return

        conn = db()
        students = conn.execute("SELECT email, nickname, level FROM users WHERE role='student' AND specialty=? AND group_name=? ORDER BY level DESC", (self.filter_specialty, self.filter_group)).fetchall()
        total_hw = conn.execute("SELECT COUNT(*) FROM homework WHERE specialty=? AND group_name=?", (self.filter_specialty, self.filter_group)).fetchone()[0]
        conn.close()

        summary = ctk.CTkFrame(self.content, fg_color=WHITE, corner_radius=16, border_width=1, border_color=GRAY_LIGHT)
        summary.pack(fill="x", padx=40, pady=(0, 20))
        inner = ctk.CTkFrame(summary, fg_color="transparent")
        inner.pack(padx=25, pady=20, fill="x")
        ctk.CTkLabel(inner, text=f"👥 Студентов: {len(students)}", text_color=BLACK, font=("Segoe UI", 15, "bold")).pack(side="left")
        ctk.CTkLabel(inner, text=f"📚 Заданий: {total_hw}", text_color=BLACK, font=("Segoe UI", 15, "bold")).pack(side="left", padx=30)

        self.scroll_frame = ctk.CTkScrollableFrame(self.content, fg_color="transparent")
        self.scroll_frame.pack(fill="both", expand=True, padx=30, pady=(0, 20))

        for email, nick, lvl in students:
            conn = db()
            done = conn.execute("SELECT COUNT(*) FROM homework_done WHERE user_email=? AND homework_id IN (SELECT id FROM homework WHERE specialty=? AND group_name=?)", (email, self.filter_specialty, self.filter_group)).fetchone()[0]
            conn.close()

            card = ctk.CTkFrame(self.scroll_frame, fg_color=WHITE, corner_radius=16, height=90, border_width=1, border_color=GRAY_LIGHT)
            card.pack(fill="x", pady=8, padx=10)
            card.pack_propagate(False)

            ctk.CTkFrame(card, fg_color=GOLD if lvl > 5 else GREEN, width=6, corner_radius=3).pack(side="left", fill="y", padx=(15, 0), pady=15)
            info = ctk.CTkFrame(card, fg_color="transparent")
            info.pack(side="left", fill="both", expand=True, padx=20, pady=15)
            ctk.CTkLabel(info, text=f"{nick or email}  (Lvl {lvl})", font=("Segoe UI", 16, "bold"), text_color=BLACK).pack(anchor="w")
            ctk.CTkLabel(info, text=email, font=("Segoe UI", 12), text_color=GRAY_MED).pack(anchor="w", pady=(2, 0))

            right = ctk.CTkFrame(card, fg_color="transparent")
            right.pack(side="right", padx=25)
            if total_hw > 0:
                bar = ctk.CTkProgressBar(right, width=200, height=10, progress_color=GREEN, fg_color=GRAY_LIGHT)
                bar.pack(pady=(0, 5))
                bar.set(done / total_hw)
                ctk.CTkLabel(right, text=f"{done} / {total_hw} ({int(done/total_hw*100)}%)", font=("Segoe UI", 12, "bold"), text_color=GRAY_DARK).pack()
            else:
                ctk.CTkLabel(right, text="Заданий нет", text_color=GRAY_MED).pack()

    def render_group_selector(self, parent):
        ctk.CTkLabel(parent, text="Группа:", font=("Segoe UI", 14, "bold"), text_color=GRAY_DARK).pack(side="left", padx=(0, 10))
        groups = get_groups_for_specialty(self.filter_specialty)
        if not groups:
            groups = ["— нет групп —"]
        options = groups + ["📋 Все группы"]

        var = ctk.StringVar(value=self.filter_group if self.filter_group in groups else options[0])
        def on_change(val):
            self.filter_group = val
            self.switch_tab(self.current_tab)

        ctk.CTkOptionMenu(parent, values=options, variable=var, width=160, height=40, fg_color=GREEN, button_color=GREEN_LIGHT, font=("Segoe UI", 13), corner_radius=8, command=on_change).pack(side="left", padx=(0, 15))

        ctk.CTkButton(parent, text="📱 QR-код", width=100, height=40, fg_color=WHITE, text_color=GREEN, font=("Segoe UI", 13, "bold"), corner_radius=8, border_width=1, border_color=GREEN, command=self.show_qr).pack(side="left")

    def render_search_bar(self):
        bar = ctk.CTkFrame(self.content, fg_color=WHITE, corner_radius=12, border_width=1, border_color=GRAY_LIGHT)
        bar.pack(fill="x", padx=40, pady=(0, 20))
        inner = ctk.CTkFrame(bar, fg_color="transparent")
        inner.pack(padx=20, pady=12, fill="x")

        ctk.CTkLabel(inner, text="🔍", text_color=GRAY_MED, font=("Segoe UI", 18)).pack(side="left", padx=(0, 15))

        self.search_var.set("")
        entry = ctk.CTkEntry(inner, textvariable=self.search_var, height=38, fg_color=GRAY_BG, border_color=GRAY_LIGHT, placeholder_text="Поиск...", font=("Segoe UI", 14))
        entry.pack(side="left", fill="x", expand=True)

        self.search_var.trace_add("write", lambda *a: self.refresh_items(self.current_tab) if self.current_tab not in ("notes", "dashboard", "pomodoro", "calendar", "achievements", "grades") else (self.refresh_notes() if self.current_tab == "notes" else None))

    def get_filter_sql(self):
        if self.is_teacher:
            if self.filter_group == "📋 Все группы":
                return " WHERE specialty=?", (self.filter_specialty,)
            elif self.filter_group and self.filter_group != "— нет групп —":
                return " WHERE specialty=? AND group_name=?", (self.filter_specialty, self.filter_group)
            return " WHERE specialty=?", (self.filter_specialty,)
        return " WHERE specialty=? AND group_name=?", (self.specialty, self.group_name)

    def refresh_items(self, key):
        if not self.scroll_frame or not self.scroll_frame.winfo_exists(): return
        for w in self.scroll_frame.winfo_children(): w.destroy()

        where, params = self.get_filter_sql()
        conn = db()
        rows = conn.execute(f"SELECT * FROM {key}{where}", params).fetchall()
        conn.close()

        q = self.search_var.get().strip().lower()
        today = datetime.now()

        filtered = []
        for row in rows:
            if q and q not in " ".join(str(x) for x in row if x).lower(): continue

            if key == "schedule":
                if self.schedule_day != "Все" and row[3] != self.schedule_day: continue
                wt = row[9] if len(row) > 9 else 0
                parity = current_week_parity()
                if wt == 1 and parity != "even": continue
                if wt == 2 and parity != "odd": continue
            elif key == "homework":
                hw_id = row[0]
                conn = db()
                is_done = conn.execute("SELECT 1 FROM homework_done WHERE user_email=? AND homework_id=?", (self.user_email, hw_id)).fetchone()
                conn.close()
                dl = parse_deadline(row[3])
                overdue = (not is_done) and dl is not None and dl.date() < today.date()

                if self.hw_filter == "active" and (is_done or overdue): continue
                if self.hw_filter == "done" and not is_done: continue
                if self.hw_filter == "overdue" and not overdue: continue
            filtered.append(row)

        if not filtered:
            ctk.CTkLabel(self.scroll_frame, text="Ничего не найдено", text_color=GRAY_MED, font=("Segoe UI", 16)).pack(pady=50)
            return

        for r in filtered:
            self.create_card(self.scroll_frame, key, r)

    def create_card(self, parent, key, row):
        card = ctk.CTkFrame(parent, fg_color=WHITE, corner_radius=16, height=100, border_width=1, border_color=GRAY_LIGHT)
        card.pack(fill="x", pady=8, padx=10)
        card.pack_propagate(False)

        strip_color = GREEN[0]
        is_done = False
        is_overdue = False

        if key == "schedule": strip_color = safe_color(row[8])
        elif key == "homework":
            hw_id = row[0]
            conn = db()
            is_done = conn.execute("SELECT 1 FROM homework_done WHERE user_email=? AND homework_id=?", (self.user_email, hw_id)).fetchone()
            conn.close()
            dl = parse_deadline(row[3])
            if not is_done and dl and dl.date() < datetime.now().date():
                is_overdue = True
                strip_color = RED[0]

        ctk.CTkFrame(card, fg_color=strip_color, width=6, corner_radius=3).pack(side="left", fill="y", padx=(15, 0), pady=15)

        info = ctk.CTkFrame(card, fg_color="transparent")
        info.pack(side="left", fill="both", expand=True, padx=20, pady=15)

        emoji = ""
        if key == "homework" and len(row) > 8 and row[8]:
            emoji = f"{row[8]} "

        if key == "schedule":
            title = row[1]
            sub = f"{row[2]} · {row[3]} · ауд. {row[5]}"
        elif key == "homework":
            title = ("✅ " if is_done else "") + emoji + row[1]
            sub = f"{row[2]} · до {row[3]} · {row[4]}"
            if is_overdue: sub += " · ПРОСРОЧЕНО"
        else:
            title = row[1]
            sub = f"{row[2]} · {row[3]}"

        title_frame = ctk.CTkFrame(info, fg_color="transparent")
        title_frame.pack(fill="x", anchor="w")

        ctk.CTkLabel(title_frame, text=title, font=("Segoe UI", 17, "bold"), text_color=GRAY_MED if is_done else (RED if is_overdue else BLACK)).pack(side="left")

        if key == "homework" and row[4]:
            pr = row[4].lower()
            b_col = RED if "сроч" in pr else (ORANGE if "сред" in pr else GREEN)
            ctk.CTkLabel(title_frame, text=row[4], font=("Segoe UI", 11, "bold"), text_color=WHITE, fg_color=b_col, corner_radius=10, padx=8, pady=2).pack(side="left", padx=10)

        ctk.CTkLabel(info, text=sub, font=("Segoe UI", 13), text_color=GRAY_DARK).pack(anchor="w", pady=(4, 0))

        btns = ctk.CTkFrame(card, fg_color="transparent")
        btns.pack(side="right", padx=20)

        if key == "homework":
            ctk.CTkButton(btns, text="Отменить" if is_done else "Выполнено (+10 XP)", width=140, height=36, fg_color=GRAY_LIGHT if is_done else GREEN_SOFT, text_color=GRAY_DARK if is_done else GREEN, font=("Segoe UI", 12, "bold"), corner_radius=8, command=lambda: self.toggle_hw(row[0])).pack(side="left", padx=5)
        if key == "homework" and row[5]:
            ctk.CTkButton(btns, text="📎 Файл", width=90, height=36, fg_color=WHITE, border_width=1, border_color=GRAY_LIGHT, text_color=GRAY_DARK, font=("Segoe UI", 12), corner_radius=8, command=lambda: os.startfile(row[5])).pack(side="left", padx=5)
        if self.is_teacher:
            ctk.CTkButton(btns, text="Удалить", width=90, height=36, fg_color=RED_SOFT, hover_color=RED, text_color=RED, font=("Segoe UI", 12), corner_radius=8, command=lambda: self.delete_item(key, row[0])).pack(side="left", padx=5)

    def toggle_hw(self, hw_id):
        conn = db()
        exists = conn.execute("SELECT 1 FROM homework_done WHERE user_email=? AND homework_id=?", (self.user_email, hw_id)).fetchone()

        if exists:
            conn.execute("DELETE FROM homework_done WHERE user_email=? AND homework_id=?", (self.user_email, hw_id))
            self.add_xp(-10)
        else:
            conn.execute("INSERT INTO homework_done (user_email, homework_id) VALUES (?,?)", (self.user_email, hw_id))
            self.add_xp(10)

        conn.commit()
        conn.close()
        self.check_and_unlock_achievements()
        self.refresh_items("homework")

    def add_xp(self, amount):
        if self.is_teacher: return
        self.xp += amount
        if self.xp < 0: self.xp = 0

        next_lvl_xp = self.level * 100
        if self.xp >= next_lvl_xp:
            self.level += 1
            self.xp -= next_lvl_xp
            messagebox.showinfo("🎉 Новый уровень!", f"Поздравляю! Вы достигли {self.level} уровня!", parent=self)
            notify("Новый уровень!", f"Вы достигли {self.level} уровня!")
            self.check_and_unlock_achievements()

        conn = db()
        conn.execute("UPDATE users SET xp=?, level=? WHERE email=?", (self.xp, self.level, self.user_email))
        conn.commit()
        conn.close()

        self.refresh_profile_btn()

    def delete_item(self, key, row_id):
        if not messagebox.askyesno("Удалить", "Точно удалить?", parent=self): return
        conn = db()
        conn.execute(f"DELETE FROM {key} WHERE id=?", (row_id,))
        if key == "homework": conn.execute("DELETE FROM homework_done WHERE homework_id=?", (row_id,))
        conn.commit()
        conn.close()
        self.switch_tab(self.current_tab)

    def refresh_notes(self):
        if not self.scroll_frame or not self.scroll_frame.winfo_exists(): return
        for w in self.scroll_frame.winfo_children(): w.destroy()

        q = self.search_var.get().strip().lower()
        conn = db()
        rows = conn.execute("SELECT id, title, content, subject, color, created_at FROM notes WHERE user_email=?", (self.user_email,)).fetchall()
        conn.close()

        if q: rows = [r for r in rows if q in " ".join(str(x) for x in r if x).lower()]

        if not rows:
            ctk.CTkLabel(self.scroll_frame, text="У вас пока нет заметок", text_color=GRAY_MED, font=("Segoe UI", 16)).pack(pady=50)
            return

        for r in rows:
            card = ctk.CTkFrame(self.scroll_frame, fg_color=WHITE, corner_radius=16, border_width=1, border_color=GRAY_LIGHT)
            card.pack(fill="x", pady=8, padx=10)

            ctk.CTkFrame(card, fg_color=safe_color(r[4]), width=6, corner_radius=3).pack(side="left", fill="y", padx=(15, 0), pady=15)

            info = ctk.CTkFrame(card, fg_color="transparent")
            info.pack(side="left", fill="both", expand=True, padx=20, pady=15)
            ctk.CTkLabel(info, text=r[1] or "(без названия)", font=("Segoe UI", 16, "bold"), text_color=BLACK).pack(anchor="w")
            if r[3]: ctk.CTkLabel(info, text=r[3], text_color=GREEN, font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(2, 0))
            ctk.CTkLabel(info, text=r[2], font=("Segoe UI", 13), text_color=GRAY_DARK, wraplength=800, justify="left").pack(anchor="w", pady=6)
            ctk.CTkLabel(info, text=r[5], font=("Segoe UI", 11), text_color=GRAY_MED).pack(anchor="w")

            ctk.CTkButton(card, text="Удалить", width=90, height=36, fg_color=RED_SOFT, hover_color=RED, text_color=RED, font=("Segoe UI", 12), corner_radius=8, command=lambda i=r[0]: self.delete_note(i)).pack(side="right", padx=20)

    def delete_note(self, nid):
        if not messagebox.askyesno("Удалить", "Удалить заметку?", parent=self): return
        conn = db()
        conn.execute("DELETE FROM notes WHERE id=? AND user_email=?", (nid, self.user_email))
        conn.commit()
        conn.close()
        self.switch_tab("notes")

    def show_add_form(self, key):
        for w in self.content.winfo_children(): w.destroy()

        header = ctk.CTkFrame(self.content, fg_color="transparent")
        header.pack(fill="x", padx=40, pady=(30, 20))

        ctk.CTkButton(header, text="← Назад", fg_color=WHITE, text_color=GRAY_DARK, font=("Segoe UI", 14, "bold"), corner_radius=8, command=lambda: self.switch_tab(key)).pack(side="left")
        ctk.CTkLabel(header, text="Новая запись", font=("Segoe UI", 28, "bold"), text_color=BLACK).pack(side="left", padx=20)

        scroll = ctk.CTkScrollableFrame(self.content, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=40)

        form_card = ctk.CTkFrame(scroll, fg_color=WHITE, corner_radius=16, border_width=1, border_color=GRAY_LIGHT)
        form_card.pack(fill="x", pady=10)

        inner = ctk.CTkFrame(form_card, fg_color="transparent")
        inner.pack(padx=30, pady=30, fill="x")

        spec_var = ctk.StringVar(value=self.filter_specialty or SPECIALTIES[0])
        group_var = ctk.StringVar(value=self.filter_group if self.filter_group not in ("📋 Все группы", "— нет групп —") else "")

        if self.is_teacher:
            ctk.CTkLabel(inner, text="Специальность", text_color=GRAY_DARK, font=("Segoe UI", 13)).pack(anchor="w")
            ctk.CTkOptionMenu(inner, values=SPECIALTIES, variable=spec_var, fg_color=GREEN, height=40).pack(fill="x", pady=(5, 15))
            ctk.CTkLabel(inner, text="Группа", text_color=GRAY_DARK, font=("Segoe UI", 13)).pack(anchor="w")
            ctk.CTkEntry(inner, textvariable=group_var, height=40).pack(fill="x", pady=(5, 15))

        fields = []
        labels = []
        if key == "schedule": labels = ["Предмет", "Преподаватель", "День (Пн/Вт/...)", "Время", "Аудитория"]
        elif key == "homework": labels = ["Название", "Предмет", "Дедлайн (15.10.2026)", "Приоритет"]
        else: labels = ["Предмет", "Дата (20.12.2026)", "Инфо (препод · ауд.)"]

        for lbl in labels:
            ctk.CTkLabel(inner, text=lbl, text_color=GRAY_DARK, font=("Segoe UI", 13)).pack(anchor="w")
            e = ctk.CTkEntry(inner, height=40, fg_color=GRAY_BG, border_color=GRAY_LIGHT)
            e.pack(fill="x", pady=(5, 15))
            fields.append(e)

        color_var = ctk.StringVar(value="Зелёный")
        week_var = ctk.StringVar(value=WEEK_TYPES[0])
        emoji_var = ctk.StringVar(value="")
        if key == "schedule":
            ctk.CTkLabel(inner, text="Цвет", text_color=GRAY_DARK, font=("Segoe UI", 13)).pack(anchor="w")
            ctk.CTkOptionMenu(inner, values=list(SUBJECT_COLORS.keys()), variable=color_var, fg_color=GREEN).pack(fill="x", pady=(5, 15))
            ctk.CTkLabel(inner, text="Повторение", text_color=GRAY_DARK, font=("Segoe UI", 13)).pack(anchor="w")
            ctk.CTkOptionMenu(inner, values=WEEK_TYPES, variable=week_var, fg_color=GREEN).pack(fill="x", pady=(5, 15))
        elif key == "homework":
            ctk.CTkLabel(inner, text="Эмодзи (стикер)", text_color=GRAY_DARK, font=("Segoe UI", 13)).pack(anchor="w")
            ctk.CTkOptionMenu(inner, values=EMOJIS, variable=emoji_var, fg_color=GREEN).pack(fill="x", pady=(5, 15))

        attached_file = {"path": ""}
        if key == "homework":
            file_status_lbl = ctk.CTkLabel(inner, text=f"Файл не прикреплён (макс. {MAX_FILE_SIZE_MB} МБ)", text_color=GRAY_MED)
            file_status_lbl.pack(pady=10)

            def pick():
                p = filedialog.askopenfilename(parent=self)
                if not p:
                    return
                try:
                    size_bytes = os.path.getsize(p)
                except OSError:
                    messagebox.showerror("Ошибка", "Не удалось прочитать размер файла", parent=self)
                    return
                if size_bytes > MAX_FILE_SIZE_MB * 1024 * 1024:
                    messagebox.showerror(
                        "Ошибка",
                        f"Файл слишком большой ({size_bytes / (1024*1024):.1f} МБ). "
                        f"Максимум {MAX_FILE_SIZE_MB} МБ.",
                        parent=self,
                    )
                    return
                attached_file["path"] = p
                file_status_lbl.configure(text=f"📎 {os.path.basename(p)} ({size_bytes // 1024} КБ)", text_color=GREEN)

            ctk.CTkButton(inner, text="📎 Прикрепить файл", fg_color=GRAY_BG, text_color=GRAY_DARK, command=pick).pack(fill="x")

        def save():
            spec = spec_var.get() if self.is_teacher else self.specialty
            grp = group_var.get().upper() if self.is_teacher else self.group_name
            vals = [f.get().strip() for f in fields]
            if not spec or not grp or any(not v for v in vals):
                messagebox.showerror("Ошибка", "Заполните все поля", parent=self)
                return

            saved_path = ""
            if key == "homework" and attached_file["path"]:
                fname = f"{int(datetime.now().timestamp())}_{os.path.basename(attached_file['path'])}"
                saved_path = os.path.join(UPLOAD_DIR, fname)
                shutil.copy2(attached_file["path"], saved_path)

            conn = db()
            if key == "schedule":
                conn.execute("INSERT INTO schedule (subject, teacher, day, time, room, specialty, group_name, color, week_type) VALUES (?,?,?,?,?,?,?,?,?)",
                             vals + [spec, grp, SUBJECT_COLORS[color_var.get()], WEEK_TYPES.index(week_var.get())])
            elif key == "homework":
                conn.execute("INSERT INTO homework (title, subject, deadline, priority, file_path, specialty, group_name, emoji) VALUES (?,?,?,?,?,?,?,?)",
                             vals + [saved_path, spec, grp, emoji_var.get()])
            else:
                conn.execute("INSERT INTO sessions (subject, date, info, specialty, group_name) VALUES (?,?,?,?,?)",
                             vals + [spec, grp])
            conn.commit()
            conn.close()

            if self.is_teacher:
                self.filter_specialty = spec
                self.filter_group = grp
            self.switch_tab(key)

        ctk.CTkButton(inner, text="Сохранить", height=50, fg_color=GREEN, text_color=WHITE, font=("Segoe UI", 16, "bold"), corner_radius=8, command=save).pack(fill="x", pady=(30, 0))

    def show_add_form_note(self):
        for w in self.content.winfo_children(): w.destroy()

        header = ctk.CTkFrame(self.content, fg_color="transparent")
        header.pack(fill="x", padx=40, pady=(30, 20))
        ctk.CTkButton(header, text="← Назад", fg_color=WHITE, text_color=GRAY_DARK, font=("Segoe UI", 14, "bold"), corner_radius=8, command=lambda: self.switch_tab("notes")).pack(side="left")
        ctk.CTkLabel(header, text="Новая заметка", font=("Segoe UI", 28, "bold"), text_color=BLACK).pack(side="left", padx=20)

        scroll = ctk.CTkScrollableFrame(self.content, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=40)

        form_card = ctk.CTkFrame(scroll, fg_color=WHITE, corner_radius=16, border_width=1, border_color=GRAY_LIGHT)
        form_card.pack(fill="x", pady=10)

        inner = ctk.CTkFrame(form_card, fg_color="transparent")
        inner.pack(padx=30, pady=30, fill="x")

        ctk.CTkLabel(inner, text="Заголовок", text_color=GRAY_DARK, font=("Segoe UI", 13)).pack(anchor="w")
        t_entry = ctk.CTkEntry(inner, height=40, fg_color=GRAY_BG, border_color=GRAY_LIGHT)
        t_entry.pack(fill="x", pady=(5, 15))

        ctk.CTkLabel(inner, text="Предмет", text_color=GRAY_DARK, font=("Segoe UI", 13)).pack(anchor="w")
        s_entry = ctk.CTkEntry(inner, height=40, fg_color=GRAY_BG, border_color=GRAY_LIGHT)
        s_entry.pack(fill="x", pady=(5, 15))

        ctk.CTkLabel(inner, text="Текст", text_color=GRAY_DARK, font=("Segoe UI", 13)).pack(anchor="w")
        c_box = ctk.CTkTextbox(inner, height=200, fg_color=GRAY_BG, border_color=GRAY_LIGHT, border_width=1)
        c_box.pack(fill="x", pady=(5, 15))

        ctk.CTkLabel(inner, text="Цвет", text_color=GRAY_DARK, font=("Segoe UI", 13)).pack(anchor="w")
        col_var = ctk.StringVar(value="Зелёный")
        ctk.CTkOptionMenu(inner, values=list(SUBJECT_COLORS.keys()), variable=col_var, fg_color=GREEN).pack(fill="x", pady=(5, 15))

        def save():
            t = t_entry.get().strip()
            c = c_box.get("1.0", "end").strip()
            s = s_entry.get().strip()
            if not t and not c:
                messagebox.showerror("Ошибка", "Заполните текст", parent=self)
                return
            conn = db()
            conn.execute("INSERT INTO notes (user_email, title, content, subject, color, created_at) VALUES (?,?,?,?,?,?)",
                         (self.user_email, t, c, s, SUBJECT_COLORS[col_var.get()], datetime.now().strftime("%d.%m.%Y %H:%M")))
            conn.commit()
            conn.close()
            self.check_and_unlock_achievements()
            self.switch_tab("notes")

        ctk.CTkButton(inner, text="Сохранить", height=50, fg_color=GREEN, text_color=WHITE, font=("Segoe UI", 16, "bold"), corner_radius=8, command=save).pack(fill="x", pady=(20, 0))

    # ==================== ПРОФИЛЬ ====================
    def show_profile(self):
        for w in self.content.winfo_children(): w.destroy()

        header = ctk.CTkFrame(self.content, fg_color="transparent")
        header.pack(fill="x", padx=40, pady=(30, 20))
        ctk.CTkButton(header, text="← Назад", fg_color=WHITE, text_color=GRAY_DARK, font=("Segoe UI", 14, "bold"), corner_radius=8, command=lambda: self.switch_tab(self.current_tab)).pack(side="left")
        ctk.CTkLabel(header, text="Профиль и настройки", font=("Segoe UI", 28, "bold"), text_color=BLACK).pack(side="left", padx=20)

        scroll = ctk.CTkScrollableFrame(self.content, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=40, pady=(0, 20))

        card = ctk.CTkFrame(scroll, fg_color=WHITE, corner_radius=16, border_width=1, border_color=GRAY_LIGHT)
        card.pack(fill="x", pady=10)

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(padx=30, pady=30, fill="x")

        avatar_frame = tk.Frame(inner, width=120, height=120, bg="#2E7D32")
        avatar_frame.pack(side="left", padx=(0, 30))
        avatar_frame.pack_propagate(False)

        self.avatar_label = tk.Label(avatar_frame, text="👤", font=("Segoe UI", 50), bg="#2E7D32", fg="white")
        self.avatar_label.place(relx=0.5, rely=0.5, anchor="center")

        if self.avatar_path and os.path.exists(self.avatar_path):
            try:
                img = Image.open(self.avatar_path).resize((120, 120))
                photo = ImageTk.PhotoImage(img)
                self.avatar_label.configure(image=photo, text="")
                self.avatar_label.image = photo
            except: pass

        info = ctk.CTkFrame(inner, fg_color="transparent")
        info.pack(side="left", fill="both", expand=True)
        ctk.CTkLabel(info, text=self.nickname, font=("Segoe UI", 26, "bold"), text_color=BLACK).pack(anchor="w")
        ctk.CTkLabel(info, text=self.user_email, font=("Segoe UI", 15), text_color=GRAY_DARK).pack(anchor="w", pady=(2, 0))
        ctk.CTkLabel(info, text=f"Роль: {'Преподаватель' if self.is_teacher else 'Студент'}", font=("Segoe UI", 14, "bold"), text_color=GREEN).pack(anchor="w", pady=(10, 0))

        if not self.is_teacher:
            ctk.CTkLabel(info, text=f"Группа: {self.group_name}", font=("Segoe UI", 14), text_color=GRAY_DARK).pack(anchor="w", pady=2)
            ctk.CTkLabel(info, text=f"🔥 Стрик: {self.streak} дн.", font=("Segoe UI", 13, "bold"), text_color=ORANGE).pack(anchor="w", pady=(5, 0))

            xp_frame = ctk.CTkFrame(info, fg_color="transparent")
            xp_frame.pack(fill="x", pady=(10, 0))
            ctk.CTkLabel(xp_frame, text=f"Lvl {self.level}  ({self.xp}/{self.level * 100} XP)", font=("Segoe UI", 12, "bold"), text_color=GOLD).pack(anchor="w")
            prog = ctk.CTkProgressBar(xp_frame, height=10, progress_color=GOLD, fg_color=GRAY_LIGHT)
            prog.pack(fill="x", pady=(5, 0))
            prog.set(min(1.0, self.xp / (self.level * 100)))

        ctk.CTkLabel(info, text=f"Дата регистрации: {self.created_at}", font=("Segoe UI", 12), text_color=GRAY_MED).pack(anchor="w", pady=(10, 0))

        btn_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        btn_frame.pack(fill="x", pady=10)

        ctk.CTkButton(btn_frame, text="Изменить ник", height=45, fg_color=GREEN, font=("Segoe UI", 14, "bold"), command=self.change_nickname_ui).pack(side="left", padx=(0, 10), expand=True, fill="x")
        ctk.CTkButton(btn_frame, text="Сменить аватарку", height=45, fg_color=GREEN_SOFT, text_color=GREEN, font=("Segoe UI", 14, "bold"), command=lambda: self.change_avatar_ui(self.avatar_label)).pack(side="left", padx=10, expand=True, fill="x")
        ctk.CTkButton(btn_frame, text="Сменить пароль", height=45, fg_color=GREEN_SOFT, text_color=GREEN, font=("Segoe UI", 14, "bold"), command=self.show_change_password).pack(side="left", padx=(10, 0), expand=True, fill="x")

        settings_card = ctk.CTkFrame(scroll, fg_color=WHITE, corner_radius=16, border_width=1, border_color=GRAY_LIGHT)
        settings_card.pack(fill="x", pady=10)
        sett_inner = ctk.CTkFrame(settings_card, fg_color="transparent")
        sett_inner.pack(padx=30, pady=25, fill="x")

        ctk.CTkLabel(sett_inner, text="Настройки приложения", font=("Segoe UI", 18, "bold"), text_color=BLACK).pack(anchor="w", pady=(0, 15))

        # Тема
        row = ctk.CTkFrame(sett_inner, fg_color="transparent")
        row.pack(fill="x", pady=5)
        ctk.CTkLabel(row, text="Тема:", font=("Segoe UI", 14), width=220, anchor="w").pack(side="left")
        theme_var = ctk.StringVar(value=get_setting("theme") or "light")
        ctk.CTkOptionMenu(row, values=["light", "dark", "auto"], variable=theme_var, fg_color=GREEN, height=36,
                          command=lambda v: self.apply_theme(v)).pack(side="left", padx=15)

        # Размер шрифта
        row_font = ctk.CTkFrame(sett_inner, fg_color="transparent")
        row_font.pack(fill="x", pady=5)
        ctk.CTkLabel(row_font, text="Размер шрифта (для слабовидящих):", font=("Segoe UI", 14), width=220, anchor="w").pack(side="left")
        cur_font = str(int(get_setting("font_size") or 14))
        font_var = ctk.StringVar(value=cur_font)
        ctk.CTkOptionMenu(row_font, values=["12", "14", "16", "18", "20", "22"], variable=font_var, fg_color=GREEN, height=36,
                          command=lambda v: self.apply_font_size(v)).pack(side="left", padx=15)

        # Напоминания
        row_rem = ctk.CTkFrame(sett_inner, fg_color="transparent")
        row_rem.pack(fill="x", pady=5)
        ctk.CTkLabel(row_rem, text="Напоминать о дедлайнах за (дней):", font=("Segoe UI", 14), width=220, anchor="w").pack(side="left")
        cur_rem = str(int(get_setting("reminder_days") or 3))
        rem_var = ctk.StringVar(value=cur_rem)
        ctk.CTkOptionMenu(row_rem, values=["1", "2", "3", "5", "7", "14"], variable=rem_var, fg_color=GREEN, height=36,
                          command=lambda v: self.apply_reminder_days(v)).pack(side="left", padx=15)

    def apply_font_size(self, value):
        try:
            sz = int(value)
        except (TypeError, ValueError):
            return
        set_setting("font_size", sz)
        try:
            ctk.set_widget_scaling(sz / 14.0)
        except Exception:
            pass
        messagebox.showinfo(
            "Готово",
            "Размер шрифта сохранён.\n\n"
            "Новые вкладки применят его сразу.\n"
            "Для полного эффекта (включая меню и верхнюю панель) перезапустите приложение.",
            parent=self,
        )
        self.switch_tab(self.current_tab if self.current_tab != "dashboard" else "dashboard")

    def apply_reminder_days(self, value):
        try:
            d = int(value)
        except (TypeError, ValueError):
            return
        set_setting("reminder_days", d)
        messagebox.showinfo("Готово", f"Напоминания будут за {d} дн. до дедлайна.", parent=self)

    def change_nickname_ui(self):
        for w in self.content.winfo_children(): w.destroy()

        header = ctk.CTkFrame(self.content, fg_color="transparent")
        header.pack(fill="x", padx=40, pady=(30, 20))
        ctk.CTkButton(header, text="← Назад", fg_color=WHITE, text_color=GRAY_DARK, font=("Segoe UI", 14, "bold"), corner_radius=8, command=self.show_profile).pack(side="left")
        ctk.CTkLabel(header, text="Изменить ник", font=("Segoe UI", 28, "bold"), text_color=BLACK).pack(side="left", padx=20)

        scroll = ctk.CTkFrame(self.content, fg_color=WHITE, corner_radius=16, border_width=1, border_color=GRAY_LIGHT)
        scroll.pack(padx=40, pady=20, fill="x")

        inner = ctk.CTkFrame(scroll, fg_color="transparent")
        inner.pack(padx=30, pady=30, fill="x")

        ctk.CTkLabel(inner, text="Новый ник (3-20 символов)", font=("Segoe UI", 13)).pack(anchor="w")
        nick_entry = ctk.CTkEntry(inner, height=40, fg_color=GRAY_BG, border_color=GRAY_LIGHT)
        nick_entry.pack(fill="x", pady=(5, 20))

        def save():
            new_nick = nick_entry.get().strip()
            ok, err = validate_nickname(new_nick)
            if not ok:
                messagebox.showerror("Ошибка", err, parent=self)
                return
            conn = db()
            conn.execute("UPDATE users SET nickname=? WHERE email=?", (new_nick, self.user_email))
            conn.commit()
            conn.close()
            self.nickname = new_nick
            self.refresh_profile_btn()
            messagebox.showinfo("Готово", "Ник изменён!")
            self.show_profile()

        ctk.CTkButton(inner, text="Сохранить", height=45, fg_color=GREEN, font=("Segoe UI", 14, "bold"), command=save).pack(fill="x")

    def show_change_password(self):
        for w in self.content.winfo_children(): w.destroy()

        header = ctk.CTkFrame(self.content, fg_color="transparent")
        header.pack(fill="x", padx=40, pady=(30, 20))
        ctk.CTkButton(header, text="← Назад", fg_color=WHITE, text_color=GRAY_DARK, font=("Segoe UI", 14, "bold"), corner_radius=8, command=self.show_profile).pack(side="left")
        ctk.CTkLabel(header, text="Смена пароля", font=("Segoe UI", 28, "bold"), text_color=BLACK).pack(side="left", padx=20)

        scroll = ctk.CTkFrame(self.content, fg_color=WHITE, corner_radius=16, border_width=1, border_color=GRAY_LIGHT)
        scroll.pack(padx=40, pady=20, fill="x")

        inner = ctk.CTkFrame(scroll, fg_color="transparent")
        inner.pack(padx=30, pady=30, fill="x")

        ctk.CTkLabel(inner, text="Текущий пароль", font=("Segoe UI", 13)).pack(anchor="w")
        old_e = ctk.CTkEntry(inner, show="*", height=40, fg_color=GRAY_BG, border_color=GRAY_LIGHT)
        old_e.pack(fill="x", pady=(5, 15))

        ctk.CTkLabel(inner, text="Новый пароль", font=("Segoe UI", 13)).pack(anchor="w")
        n1_e = ctk.CTkEntry(inner, show="*", height=40, fg_color=GRAY_BG, border_color=GRAY_LIGHT)
        n1_e.pack(fill="x", pady=(5, 15))

        ctk.CTkLabel(inner, text="Повтор пароля", font=("Segoe UI", 13)).pack(anchor="w")
        n2_e = ctk.CTkEntry(inner, show="*", height=40, fg_color=GRAY_BG, border_color=GRAY_LIGHT)
        n2_e.pack(fill="x", pady=(5, 15))

        def save():
            if len(n1_e.get()) < 4: return messagebox.showerror("Ошибка", "Пароль от 4 символов")
            if n1_e.get() != n2_e.get(): return messagebox.showerror("Ошибка", "Пароли не совпадают")
            conn = db()
            row = conn.execute("SELECT id FROM users WHERE email=? AND password=?", (self.user_email, hash_pw(old_e.get()))).fetchone()
            if not row:
                conn.close()
                return messagebox.showerror("Ошибка", "Текущий пароль неверный")
            conn.execute("UPDATE users SET password=? WHERE email=?", (hash_pw(n1_e.get()), self.user_email))
            conn.commit()
            conn.close()
            messagebox.showinfo("Готово", "Пароль изменён")
            self.show_profile()

        ctk.CTkButton(inner, text="Сохранить", height=45, fg_color=GREEN, font=("Segoe UI", 14, "bold"), command=save).pack(fill="x", pady=20)

    def change_avatar_ui(self, label_widget):
        p = filedialog.askopenfilename(filetypes=[("Images", "*.png;*.jpg;*.jpeg")])
        if not p: return
        fname = f"{hashlib.md5(self.user_email.encode()).hexdigest()}_{os.path.basename(p)}"
        dst = os.path.join(AVATAR_DIR, fname)
        shutil.copy2(p, dst)
        self.avatar_path = dst

        conn = db()
        conn.execute("UPDATE users SET avatar=? WHERE email=?", (dst, self.user_email))
        conn.commit()
        conn.close()

        img = Image.open(dst).resize((120, 120))
        photo = ImageTk.PhotoImage(img)
        label_widget.configure(image=photo, text="")
        label_widget.image = photo

        # Обновить аватар в верхней панели
        self.refresh_profile_btn()

    def apply_theme(self, theme):
        set_setting("theme", theme)
        if theme == "auto":
            hour = datetime.now().hour
            ctk.set_appearance_mode("light" if 8 <= hour < 20 else "dark")
        else:
            ctk.set_appearance_mode(theme)

    def show_qr(self):
        if not QR_OK:
            return messagebox.showerror("Ошибка", "Библиотека qrcode не установлена")
        if self.filter_group in ("— нет групп —", "📋 Все группы", ""):
            return messagebox.showerror("Ошибка", "Выберите конкретную группу")

        for w in self.content.winfo_children(): w.destroy()

        header = ctk.CTkFrame(self.content, fg_color="transparent")
        header.pack(fill="x", padx=40, pady=(30, 20))
        ctk.CTkButton(header, text="← Назад", fg_color=WHITE, text_color=GRAY_DARK, font=("Segoe UI", 14, "bold"), corner_radius=8, command=lambda: self.switch_tab(self.current_tab)).pack(side="left")
        ctk.CTkLabel(header, text=f"QR-код группы {self.filter_group}", font=("Segoe UI", 28, "bold"), text_color=BLACK).pack(side="left", padx=20)

        card = ctk.CTkFrame(self.content, fg_color=WHITE, corner_radius=16, border_width=1, border_color=GRAY_LIGHT)
        card.pack(padx=40, pady=20, fill="x")

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(padx=30, pady=30)

        data = f"StudyPlanner|{self.filter_specialty}|{self.filter_group}"
        qr = qrcode.QRCode(version=1, box_size=10, border=2)
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white").convert("RGB")

        photo = ImageTk.PhotoImage(img)
        lbl_img = tk.Label(inner, image=photo, bg="#1E1E1E", bd=0)
        lbl_img.image = photo
        lbl_img.pack(pady=10)

        def save():
            p = filedialog.asksaveasfilename(defaultextension=".png")
            if p: img.save(p); messagebox.showinfo("Готово", "Сохранено")

        ctk.CTkButton(inner, text="Сохранить как PNG", fg_color=GREEN, height=45, font=("Segoe UI", 14, "bold"), command=save).pack(fill="x", pady=(20, 0))

    def logout(self):
        if messagebox.askyesno("Выход", "Выйти?", parent=self):
            self.user_email = None
            self.show_login()

    def check_deadlines(self):
        if self.is_teacher or not self.specialty: return
        try:
            reminder_days = int(get_setting("reminder_days") or 3)
            conn = db()
            rows = conn.execute("SELECT id, title, deadline FROM homework WHERE specialty=? AND group_name=?", (self.specialty, self.group_name)).fetchall()
            conn.close()

            today = datetime.now().date()
            urgent = []
            for hw_id, title, dl_str in rows:
                conn = db()
                is_done = conn.execute("SELECT 1 FROM homework_done WHERE user_email=? AND homework_id=?", (self.user_email, hw_id)).fetchone()
                conn.close()
                if is_done: continue
                dl = parse_deadline(dl_str)
                if not dl: continue
                delta = (dl.date() - today).days
                if delta < 0: urgent.append(("ПРОСРОЧЕНО", title))
                elif delta == 0: urgent.append(("СЕГОДНЯ", title))
                elif delta == 1: urgent.append(("завтра", title))
                elif delta <= reminder_days: urgent.append((f"через {delta} дн.", title))

            if urgent:
                for tag, title in urgent[:5]:
                    notify(f"Дедлайн {tag}", title)
                text = "\n".join(f"• [{tag}] {t}" for tag, t in urgent)
                messagebox.showwarning("Срочные задания", text, parent=self)
        except:
            pass

    def check_and_unlock_achievements(self):
        if self.is_teacher: return
        conn = db()
        total_done = conn.execute("SELECT COUNT(*) FROM homework_done WHERE user_email=?", (self.user_email,)).fetchone()[0]
        notes_count = conn.execute("SELECT COUNT(*) FROM notes WHERE user_email=?", (self.user_email,)).fetchone()[0]
        conn.close()

        is_night = datetime.now().hour >= 23 or datetime.now().hour < 6

        conditions = {
            "first_step": total_done >= 1, "hardworker": total_done >= 10,
            "excellent": total_done >= 30, "marathon": self.streak >= 7,
            "night_watch": is_night, "note_taker": notes_count >= 10, "guru": self.level >= 10,
        }

        conn = db()
        for ach_id, unlocked in conditions.items():
            if unlocked:
                try:
                    conn.execute("INSERT OR IGNORE INTO user_achievements (user_email, achievement_id, unlocked_at) VALUES (?, ?, ?)",
                                 (self.user_email, ach_id, datetime.now().strftime("%d.%m.%Y %H:%M")))
                except Exception:
                    pass
        conn.commit()
        conn.close()

    def render_achievements(self):
        self.check_and_unlock_achievements()
        scroll = ctk.CTkScrollableFrame(self.content, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=30, pady=(0, 20))

        conn = db()
        unlocked_rows = conn.execute("SELECT achievement_id FROM user_achievements WHERE user_email=?", (self.user_email,)).fetchall()
        conn.close()
        unlocked_set = {r[0] for r in unlocked_rows}

        achievements = [
            ("first_step", "🥇", "Первый шаг", "Выполни первое задание"),
            ("hardworker", "📝", "Трудяга", "Выполни 10 заданий"),
            ("excellent", "⭐", "Отличник", "Выполни 30 заданий"),
            ("marathon", "🔥", "Марафонец", "Заходи 7 дней подряд"),
            ("night_watch", "🌙", "Ночной страж", "Заходи после 23:00"),
            ("note_taker", "📌", "Заметливый", "Создай 10 заметок"),
            ("guru", "🏆", "Гуру", "Достигни 10 уровня"),
        ]

        for ach_id, emoji, name, desc in achievements:
            is_unlocked = ach_id in unlocked_set
            card = ctk.CTkFrame(scroll, fg_color=WHITE if is_unlocked else GRAY_LIGHT, corner_radius=16, border_width=1, border_color=GOLD if is_unlocked else GRAY_LIGHT)
            card.pack(fill="x", pady=8, padx=10)
            inner = ctk.CTkFrame(card, fg_color="transparent")
            inner.pack(padx=20, pady=15, fill="x")

            ctk.CTkLabel(inner, text=emoji if is_unlocked else "🔒", font=("Segoe UI Emoji", 40)).pack(side="left", padx=(0, 20))

            info = ctk.CTkFrame(inner, fg_color="transparent")
            info.pack(side="left", fill="both", expand=True)
            ctk.CTkLabel(info, text=name, font=("Segoe UI", 16, "bold"), text_color=BLACK if is_unlocked else GRAY_MED).pack(anchor="w")
            ctk.CTkLabel(info, text=desc, font=("Segoe UI", 13), text_color=GRAY_DARK if is_unlocked else GRAY_MED).pack(anchor="w")

            status = "✅ Открыто" if is_unlocked else "Не открыто"
            ctk.CTkLabel(inner, text=status, font=("Segoe UI", 13, "bold"), text_color=GREEN if is_unlocked else GRAY_MED).pack(side="right")

    def render_calendar(self):
        scroll = ctk.CTkScrollableFrame(self.content, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=30, pady=(0, 20))

        card = ctk.CTkFrame(scroll, fg_color=WHITE, corner_radius=16, border_width=1, border_color=GRAY_LIGHT)
        card.pack(fill="x", pady=10)
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(padx=25, pady=25, fill="x")

        now = datetime.now()
        month_names = ["", "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь", "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]
        ctk.CTkLabel(inner, text=f"{month_names[now.month]} {now.year}", font=("Segoe UI", 24, "bold"), text_color=BLACK).pack(pady=(0, 20))

        days_bar = ctk.CTkFrame(inner, fg_color="transparent")
        days_bar.pack(fill="x", pady=(0, 5))
        for d in ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]:
            ctk.CTkLabel(days_bar, text=d, font=("Segoe UI", 13, "bold"), text_color=GRAY_DARK, width=100).pack(side="left", padx=2)

        where, params = self.get_filter_sql()
        conn = db()
        hw = conn.execute(f"SELECT id, title, deadline FROM homework{where}", params).fetchall()
        conn.close()

        deadlines_by_day = {}
        for hwid, title, dl_s in hw:
            dl = parse_deadline(dl_s)
            if dl and dl.year == now.year and dl.month == now.month:
                deadlines_by_day[dl.day] = deadlines_by_day.get(dl.day, []) + [title]

        cal = calendar.monthcalendar(now.year, now.month)
        for week in cal:
            row = ctk.CTkFrame(inner, fg_color="transparent")
            row.pack(fill="x", pady=2)
            for day in week:
                if day == 0:
                    ctk.CTkLabel(row, text="", width=100, height=70).pack(side="left", padx=2)
                else:
                    has_deadline = day in deadlines_by_day
                    btn_color = RED_SOFT if has_deadline else WHITE
                    txt_color = RED if has_deadline else BLACK
                    btn = ctk.CTkButton(row, text=str(day), width=100, height=70,
                                        fg_color=btn_color, border_width=1, border_color=GRAY_LIGHT,
                                        text_color=txt_color, font=("Segoe UI", 14, "bold"),
                                        hover_color=GREEN_SOFT,
                                        command=lambda d=day: self.show_day_deadlines(d, deadlines_by_day))
                    btn.pack(side="left", padx=2)

        ctk.CTkLabel(inner, text="* Красные дни — есть дедлайны. Клик на день — показать список.", font=("Segoe UI", 12), text_color=GRAY_MED).pack(pady=(15, 0))

    def show_day_deadlines(self, day, deadlines):
        now = datetime.now()
        date_str = f"{day:02d}.{now.month:02d}.{now.year}"
        titles = deadlines.get(day, [])
        if not titles:
            messagebox.showinfo(f"Дедлайны на {date_str}", "В этот день дедлайнов нет.", parent=self)
        else:
            text = "\n".join(f"• {t}" for t in titles)
            messagebox.showinfo(f"Дедлайны на {date_str}", text, parent=self)


if __name__ == "__main__":
    init_db()
    try:
        _fs = int(get_setting("font_size") or 14)
        ctk.set_widget_scaling(_fs / 14.0)
    except Exception:
        pass
    ctk.set_appearance_mode(get_setting("theme") or "light")
    app = StudyPlannerApp()
    app.mainloop()