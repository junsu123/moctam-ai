"""Lớp lưu trữ SQLite cho công ty Agent AI."""
import json
import os
import sqlite3
import threading
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Giờ Việt Nam cho lịch họp và nhật ký
os.environ["TZ"] = os.getenv("APP_TZ", "Asia/Ho_Chi_Minh")
if hasattr(time, "tzset"):
    time.tzset()

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "company.db"
_lock = threading.RLock()


def now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


_conn = None


def conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        _conn = connect()
    return _conn


def q(sql: str, params=()) -> list[dict]:
    with _lock:
        cur = conn().execute(sql, params)
        return [dict(r) for r in cur.fetchall()]


def one(sql: str, params=()):
    rows = q(sql, params)
    return rows[0] if rows else None


def run(sql: str, params=()) -> int:
    with _lock:
        cur = conn().execute(sql, params)
        conn().commit()
        return cur.lastrowid


SCHEMA = """
CREATE TABLE IF NOT EXISTS products (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL, category TEXT, description TEXT,
  wholesale_price TEXT, retail_price TEXT, moq TEXT, selling_points TEXT,
  created_at TEXT
);
CREATE TABLE IF NOT EXISTS groups (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL, url TEXT, topic TEXT, members INTEGER DEFAULT 0,
  rules TEXT, min_days_between_posts INTEGER DEFAULT 3,
  last_posted_at TEXT, leads_count INTEGER DEFAULT 0, note TEXT, created_at TEXT
);
CREATE TABLE IF NOT EXISTS posts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  agent_id TEXT, product_id INTEGER, target_type TEXT DEFAULT 'group',
  group_id INTEGER, angle TEXT, title TEXT, content TEXT, hashtags TEXT,
  image_idea TEXT, status TEXT DEFAULT 'draft', scheduled_for TEXT,
  posted_at TEXT, posted_url TEXT, fb_post_id TEXT, poster TEXT,
  comments INTEGER DEFAULT 0, leads INTEGER DEFAULT 0, created_at TEXT
);
CREATE TABLE IF NOT EXISTS leads (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT, contact TEXT, channel TEXT, source TEXT, business_type TEXT,
  need TEXT, score INTEGER DEFAULT 0, status TEXT DEFAULT 'new',
  note TEXT, last_contact_at TEXT, created_at TEXT, updated_at TEXT
);
CREATE TABLE IF NOT EXISTS meetings (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  date TEXT, topic TEXT, status TEXT DEFAULT 'running', summary TEXT,
  action_items TEXT, created_at TEXT, ended_at TEXT
);
CREATE TABLE IF NOT EXISTS meeting_messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  meeting_id INTEGER, agent_id TEXT, phase TEXT, content TEXT, created_at TEXT
);
CREATE TABLE IF NOT EXISTS tasks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  agent_id TEXT, title TEXT, status TEXT DEFAULT 'todo', meeting_id INTEGER,
  due TEXT, created_at TEXT
);
CREATE TABLE IF NOT EXISTS activity (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  agent_id TEXT, action TEXT, detail TEXT, created_at TEXT
);
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS usage (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  task TEXT, model TEXT, input_tokens INTEGER, output_tokens INTEGER, cost_usd REAL,
  batch INTEGER DEFAULT 0, created_at TEXT
);
CREATE TABLE IF NOT EXISTS ai_batches (
  id TEXT PRIMARY KEY, task TEXT, meta TEXT, status TEXT DEFAULT 'in_progress', created_at TEXT, ended_at TEXT
);
CREATE TABLE IF NOT EXISTS bumps (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  post_id INTEGER, sale_id INTEGER, image TEXT, text TEXT, status TEXT DEFAULT 'scheduled',
  scheduled_for TEXT, done_at TEXT, error TEXT, screenshot TEXT, created_at TEXT
);
CREATE TABLE IF NOT EXISTS lessons (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  agent_id TEXT, text TEXT, evidence TEXT, source TEXT DEFAULT 'auto', rule_key TEXT,
  confidence REAL DEFAULT 0.6, pinned INTEGER DEFAULT 0, status TEXT DEFAULT 'active',
  created_at TEXT, updated_at TEXT
);
CREATE TABLE IF NOT EXISTS feedback (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  post_id INTEGER, kind TEXT, before TEXT, after TEXT, reason TEXT, created_at TEXT
);
CREATE TABLE IF NOT EXISTS replies (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  lead_id INTEGER, text TEXT, sent INTEGER DEFAULT 0, outcome TEXT, created_at TEXT, sent_at TEXT
);
CREATE TABLE IF NOT EXISTS agent_progress (
  agent_id TEXT PRIMARY KEY, xp INTEGER DEFAULT 0, level INTEGER DEFAULT 1, goal TEXT, updated_at TEXT
);
CREATE TABLE IF NOT EXISTS kpi_daily (
  date TEXT PRIMARY KEY, target_min INTEGER, target_max INTEGER, leads_phone INTEGER, leads_total INTEGER,
  posts INTEGER, bumps INTEGER, escalated INTEGER, achieved INTEGER, detail TEXT, created_at TEXT
);
CREATE TABLE IF NOT EXISTS comment_seen (
  id INTEGER PRIMARY KEY AUTOINCREMENT, post_id INTEGER, author TEXT, text_hash TEXT, lead_id INTEGER,
  replied INTEGER DEFAULT 0, sale_id INTEGER, created_at TEXT, UNIQUE(post_id, author, text_hash)
);
CREATE TABLE IF NOT EXISTS sales (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL, fb_name TEXT, profile_dir TEXT, look TEXT,
  login_status TEXT DEFAULT 'not_logged_in',
  auto_post INTEGER DEFAULT 1, max_posts_per_day INTEGER DEFAULT 5,
  min_gap_minutes INTEGER DEFAULT 40, active_from TEXT DEFAULT '08:00', active_to TEXT DEFAULT '22:00',
  last_check_at TEXT, last_post_at TEXT, last_error TEXT, created_at TEXT
);
"""

# Cột thêm cho cơ sở dữ liệu tạo từ phiên bản trước
MIGRATIONS = [
    ("posts", "sale_id", "INTEGER"), ("posts", "error", "TEXT"), ("posts", "screenshot", "TEXT"),
    ("groups", "member_sale_ids", "TEXT DEFAULT ''"), ("products", "images", "TEXT DEFAULT '[]'"),
    ("posts", "permalink_status", "TEXT"), ("posts", "bump_enabled", "INTEGER DEFAULT 1"),
    ("posts", "bump_count", "INTEGER DEFAULT 0"), ("posts", "last_bump_at", "TEXT"),
    ("leads", "post_id", "INTEGER"),
    ("leads", "phone", "TEXT"), ("leads", "origin", "TEXT DEFAULT 'manual'"), ("leads", "fb_author", "TEXT"),
    ("leads", "escalated_at", "TEXT"), ("leads", "escalate_reason", "TEXT"), ("leads", "consult_note", "TEXT"),
    ("posts", "last_scan_at", "TEXT"),
    ("leads", "phone_at", "TEXT"), ("leads", "boss_status", "TEXT"), ("leads", "remind_at", "TEXT"),
]

DEFAULT_SETTINGS = {
    "company_name": "Xưởng Trà & Bột Thiên Nhiên",
    "meeting_time": "08:30",
    "auto_meeting": "1",
    "auto_daily_work": "1",
    "posts_per_day": "4",
    "fb_page_id": "",
    "fb_page_token": "",
    "brand_voice": "Thân thiện, chân thật, nói chuyện như người làm xưởng; nhấn mạnh nguồn hàng tận gốc, giá sỉ tốt, hỗ trợ người bán online.",
    "contact_info": "Inbox trang hoặc Zalo 09xx.xxx.xxx",
    "browser_headless": "0",
    "cost_preset": "can_bang",
    "model_posts": "claude-sonnet-5-5",
    "model_replies": "claude-haiku-5-5",
    "model_meeting": "claude-haiku-5-5",
    "use_batch": "1",
    "monthly_budget_usd": "10",
    "meeting_weekdays": "1,2,3,4,5,6,7",
    "debate_rounds": "2",
    "bump_enabled": "1",
    "bump_time": "19:30",
    "bump_folder": "",
    "bump_max_age_days": "7",
    "bump_max_per_nick": "8",
    "bump_gap_minutes": "6",
    "bump_texts": "Còn hàng sỉ nhé cả nhà\nAi cần báo giá sỉ cứ inbox mình nha\nHàng mới về, ảnh thật tại xưởng\n",
    "bump_planned_date": "",
    "learn_enabled": "1",
    "learn_time": "23:15",
    "learn_last_date": "",
    "learn_explore": "0.25",
    "model_learning": "claude-haiku-5-5",
    "kpi_min": "5",
    "kpi_max": "10",
    "kpi_check_time": "15:00",
    "escalate_all_phone": "1",
    "escalate_complex": "1",
    "escalate_after_hours": "2",
    "scan_enabled": "1",
    "scan_times": "11:30,16:30,20:45",
    "scan_max_age_days": "7",
    "auto_reply_comments": "1",
    "reply_max_per_nick": "10",
    "reply_texts": "Dạ anh/chị để lại SĐT hoặc Zalo giúp em, bên em gọi tư vấn giá sỉ ngay ạ\nEm cảm ơn ạ, anh/chị cho em xin SĐT/Zalo để em gửi bảng giá sỉ và tư vấn kỹ hơn nhé\nDạ có hàng sẵn ạ, anh/chị để lại số điện thoại giúp em, xưởng gọi báo giá liền ạ",
    "scan_last": "",
    "tg_token": "",
    "tg_chat_ids": "",
    "tg_pair_code": "",
    "tg_morning": "09:00",
    "tg_evening": "21:30",
    "tg_alert_leads": "1",
    "tg_alert_nick": "1",
    "tg_alert_kpi": "1",
    "tg_sent_log": "{}",
    "attach_images": "1",
}

DATA_DIR = DB_PATH.parent
MEDIA_DIR = DATA_DIR / "media"
SHOTS_DIR = DATA_DIR / "shots"
PROFILES_DIR = DATA_DIR / "profiles"
for _d in (MEDIA_DIR, SHOTS_DIR, PROFILES_DIR):
    _d.mkdir(parents=True, exist_ok=True)

SEED_PRODUCTS = [
    ("Trà gừng mật ong túi lọc", "Trà túi lọc", "Gừng sẻ sấy lạnh phối mật ong, hộp 20 túi x 2g.",
     "38.000đ/hộp", "65.000đ", "50 hộp", "Ấm bụng, dễ uống, bán chạy mùa lạnh; in nhãn riêng (OEM) được"),
    ("Trà hoa đậu biếc - cỏ ngọt", "Trà túi lọc", "Hoa đậu biếc sấy khô phối cỏ ngọt, hộp 25 túi.",
     "35.000đ/hộp", "60.000đ", "50 hộp", "Màu xanh đẹp lên video, hợp livestream pha chế"),
    ("Bột ngũ cốc dinh dưỡng 25 loại hạt", "Bột ngũ cốc", "Hũ 500g, không đường hóa học, rang xay tại xưởng.",
     "85.000đ/hũ", "150.000đ", "30 hũ", "Biên lợi nhuận cao, khách mua lặp lại, hợp bán sàn"),
    ("Bột cần tây sấy lạnh", "Bột thiên nhiên", "Túi 100g, sấy lạnh giữ màu xanh tự nhiên.",
     "75.000đ/túi", "135.000đ", "30 túi", "Trend giữ dáng, nội dung TikTok/Reels dễ làm"),
    ("Bột diếp cá - rau má", "Bột thiên nhiên", "Túi 100g, nguyên chất 100%.",
     "60.000đ/túi", "110.000đ", "30 túi", "Hợp tệp mẹ bỉm, chị em quan tâm làn da"),
    ("Cà phê hòa tan 3in1 vị đậm", "Cà phê hòa tan", "Hộp 18 gói x 17g, vị đậm kiểu phố.",
     "42.000đ/hộp", "75.000đ", "50 hộp", "Giá dễ chốt, combo quà tặng, bán quanh năm"),
]

SEED_GROUPS = [
    ("Cộng đồng bán hàng online toàn quốc", "", "Bán hàng online", 520000,
     "Chỉ đăng bài bán hàng vào thứ 3, 5, 7. Không để số điện thoại trong bài.", 4),
    ("Hội chạy quảng cáo Facebook Ads", "", "Quảng cáo", 180000,
     "Ưu tiên bài chia sẻ kinh nghiệm, bài bán hàng phải mang giá trị.", 5),
    ("Tìm nguồn hàng sỉ - Đầu mối tận xưởng", "", "Nguồn hàng", 310000,
     "Được đăng nguồn hàng mỗi ngày 1 bài.", 2),
    ("Hội Livestream bán hàng", "", "Livestream", 95000,
     "Không spam link. Đăng kèm video/ảnh thật.", 3),
    ("Bán hàng Shopee - TikTok Shop", "", "Sàn TMĐT", 240000,
     "Bài nguồn hàng đăng trong chủ đề 'Tìm nguồn hàng'.", 3),
    ("Hội mẹ bỉm kinh doanh online", "", "Bán hàng online", 150000,
     "Bài bán hàng cần duyệt, nội dung nhẹ nhàng.", 4),
]

SEED_LEADS = [
    ("Thu Trang", "fb.com/thutrang.shop", "Facebook", "Hội Livestream bán hàng", "Livestream",
     "Muốn lấy sỉ trà đậu biếc để live pha chế", 80, "contacted"),
    ("Shop Mộc An", "Zalo 09xx", "Zalo", "Tìm nguồn hàng sỉ - Đầu mối tận xưởng", "Sàn TMĐT",
     "Hỏi giá ngũ cốc số lượng 100 hũ, cần hóa đơn", 90, "sample"),
    ("Anh Quân Ads", "Inbox page", "Facebook", "Hội chạy quảng cáo Facebook Ads", "Chạy quảng cáo",
     "Tìm sản phẩm biên lợi nhuận cao để test ads", 65, "new"),
]


def init():
    with _lock:
        conn().executescript(SCHEMA)
        conn().commit()
        for table, col, typ in MIGRATIONS:
            cols = [r[1] for r in conn().execute(f"PRAGMA table_info({table})").fetchall()]
            if col not in cols:
                conn().execute(f"ALTER TABLE {table} ADD COLUMN {col} {typ}")
        conn().commit()
    # bài đang đăng dở khi tắt máy -> đưa về hàng đợi
    run("UPDATE posts SET status='scheduled' WHERE status='posting'")
    run("UPDATE bumps SET status='scheduled' WHERE status='running'")
    for k, v in DEFAULT_SETTINGS.items():
        run("INSERT OR IGNORE INTO settings(key, value) VALUES (?, ?)", (k, v))
    if not one("SELECT id FROM products LIMIT 1"):
        for p in SEED_PRODUCTS:
            run("""INSERT INTO products(name, category, description, wholesale_price, retail_price,
                   moq, selling_points, created_at) VALUES (?,?,?,?,?,?,?,?)""", (*p, now()))
        for g in SEED_GROUPS:
            run("""INSERT INTO groups(name, url, topic, members, rules, min_days_between_posts, created_at)
                   VALUES (?,?,?,?,?,?,?)""", (*g, now()))
        for l in SEED_LEADS:
            run("""INSERT INTO leads(name, contact, channel, source, business_type, need, score, status,
                   last_contact_at, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (*l, now(), now(), now()))


def get_settings() -> dict:
    return {r["key"]: r["value"] for r in q("SELECT key, value FROM settings")}


def set_setting(key: str, value: str):
    run("INSERT INTO settings(key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value))


def log(agent_id: str, action: str, detail: str = ""):
    run("INSERT INTO activity(agent_id, action, detail, created_at) VALUES (?,?,?,?)",
        (agent_id, action, detail, now()))


def dumps(x) -> str:
    return json.dumps(x, ensure_ascii=False)
