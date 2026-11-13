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


# Múi giờ của phần mềm: mặc định giờ Việt Nam (GMT+7), không phụ thuộc múi giờ cài trên máy tính (Windows hay đặt sai).
TZ_CHOICES = {
    "Asia/Ho_Chi_Minh": ("Việt Nam (GMT+7)", 7), "Asia/Bangkok": ("Thái Lan, Lào, Campuchia (GMT+7)", 7),
    "Asia/Singapore": ("Singapore, Malaysia (GMT+8)", 8), "Asia/Shanghai": ("Trung Quốc, Đài Loan (GMT+8)", 8),
    "Asia/Seoul": ("Hàn Quốc (GMT+9)", 9), "Asia/Tokyo": ("Nhật Bản (GMT+9)", 9), "Australia/Sydney": ("Sydney (GMT+10/+11)", 10),
    "Europe/London": ("Anh (GMT+0/+1)", 0), "Europe/Berlin": ("Đức, Pháp (GMT+1/+2)", 1),
    "America/New_York": ("New York (GMT-5/-4)", -5), "America/Los_Angeles": ("California (GMT-8/-7)", -8), "UTC": ("UTC (GMT+0)", 0),
}
DEFAULT_TZ = "Asia/Ho_Chi_Minh"
_TZ = {"name": os.getenv("APP_TZ") or DEFAULT_TZ, "zone": None}


def set_tz(name: str | None):
    name = name if name in TZ_CHOICES else DEFAULT_TZ
    zone = None
    try:
        from zoneinfo import ZoneInfo
        zone = ZoneInfo(name)
    except Exception:  # Windows chưa có dữ liệu múi giờ (thư viện tzdata): dùng độ lệch cố định
        zone = None
    _TZ.update(name=name, zone=zone)


def clock() -> datetime:
    """Giờ hiện tại theo múi giờ của phần mềm (mặc định giờ Việt Nam), dạng không kèm múi giờ."""
    from datetime import timedelta, timezone
    z = _TZ["zone"]
    if z is not None:
        return datetime.now(z).replace(tzinfo=None)
    return (datetime.now(timezone.utc) + timedelta(hours=TZ_CHOICES.get(_TZ["name"], ("", 7))[1])).replace(tzinfo=None)


def tz_info() -> dict:
    c = clock()
    return {"tz": _TZ["name"], "label": TZ_CHOICES.get(_TZ["name"], (_TZ["name"],))[0], "now": c.strftime("%Y-%m-%d %H:%M:%S"),
            "pc_now": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "choices": [{"id": k, "label": v[0]} for k, v in TZ_CHOICES.items()]}


set_tz(_TZ["name"])


def now() -> str:
    return clock().strftime("%Y-%m-%d %H:%M:%S")


def today() -> str:
    return clock().strftime("%Y-%m-%d")


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=15)
    conn.row_factory = sqlite3.Row
    # WAL: mỗi lần ghi không phải chép lại cả trang và ép ổ đĩa ghi ngay (Windows rất chậm khoản này), bản mới khởi động
    # lại đọc được trong lúc bản cũ còn chạy. NORMAL trong WAL vẫn an toàn khi phần mềm tắt đột ngột.
    for pragma in ("journal_mode=WAL", "synchronous=NORMAL", "busy_timeout=15000", "temp_store=MEMORY",
                   "cache_size=-32000", "journal_size_limit=67108864"):
        try:
            conn.execute("PRAGMA " + pragma)
        except sqlite3.DatabaseError:
            pass
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


def many(sql: str, rows) -> int:
    """Ghi nhiều dòng trong một lần lưu (nhanh hơn hàng trăm lần so với gọi run() từng dòng)."""
    rows = list(rows)
    if not rows:
        return 0
    with _lock:
        conn().executemany(sql, rows)
        conn().commit()
    return len(rows)


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
CREATE TABLE IF NOT EXISTS ai_fallback (
  id INTEGER PRIMARY KEY AUTOINCREMENT, task TEXT, reason TEXT, detail TEXT, created_at TEXT
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
CREATE TABLE IF NOT EXISTS image_usage (
  id INTEGER PRIMARY KEY AUTOINCREMENT, path TEXT, product_id INTEGER, post_id INTEGER, bump_id INTEGER,
  sale_id INTEGER, group_id INTEGER, kind TEXT, used_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_image_usage_path ON image_usage(path);
CREATE TABLE IF NOT EXISTS orders (
  id INTEGER PRIMARY KEY AUTOINCREMENT, lead_id INTEGER, amount INTEGER, note TEXT, via TEXT, created_at TEXT
);
CREATE TABLE IF NOT EXISTS expenses (
  id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, category TEXT, amount INTEGER, note TEXT, created_at TEXT
);
CREATE TABLE IF NOT EXISTS fb_accounts (
  id INTEGER PRIMARY KEY AUTOINCREMENT, sale_id INTEGER, name TEXT, profile_dir TEXT, login_status TEXT DEFAULT 'not_logged_in',
  enabled INTEGER DEFAULT 1, position INTEGER DEFAULT 0, max_posts_per_day INTEGER DEFAULT 3, min_gap_minutes INTEGER DEFAULT 45,
  active_from TEXT DEFAULT '08:00', active_to TEXT DEFAULT '22:00', last_check_at TEXT, last_error TEXT, last_post_at TEXT,
  last_session_at TEXT, created_at TEXT
);
CREATE TABLE IF NOT EXISTS account_groups (
  group_id INTEGER, account_id INTEGER, status TEXT, note TEXT, requested_at TEXT, updated_at TEXT,
  PRIMARY KEY (group_id, account_id)
);
CREATE TABLE IF NOT EXISTS ceo_messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT, role TEXT, text TEXT, actions TEXT, via TEXT, created_at TEXT
);
CREATE TABLE IF NOT EXISTS ceo_orders (
  id INTEGER PRIMARY KEY AUTOINCREMENT, agent TEXT, text TEXT, active INTEGER DEFAULT 1, source TEXT, created_at TEXT
);
CREATE TABLE IF NOT EXISTS group_candidates (
  id INTEGER PRIMARY KEY AUTOINCREMENT, url TEXT UNIQUE, name TEXT, members INTEGER DEFAULT 0, posts_per_day REAL DEFAULT 0,
  privacy TEXT, joined INTEGER DEFAULT 0, keyword TEXT, relevance REAL DEFAULT 0, score REAL DEFAULT 0, found_by INTEGER,
  status TEXT DEFAULT 'new', group_id INTEGER, found_at TEXT, last_seen_at TEXT
);
CREATE TABLE IF NOT EXISTS content_library (
  id INTEGER PRIMARY KEY AUTOINCREMENT, agent_id TEXT, post_id INTEGER, product_id INTEGER, product_name TEXT, category TEXT,
  angle TEXT, target_type TEXT, title TEXT, content TEXT, hashtags TEXT, image_idea TEXT, source TEXT, status TEXT,
  leads INTEGER DEFAULT 0, comments INTEGER DEFAULT 0, edited INTEGER DEFAULT 0, created_at TEXT
);
CREATE TABLE IF NOT EXISTS content_snippets (
  id INTEGER PRIMARY KEY AUTOINCREMENT, library_id INTEGER, kind TEXT, angle TEXT, target_type TEXT, product_id INTEGER,
  text TEXT, score REAL DEFAULT 1, seen INTEGER DEFAULT 1, uses INTEGER DEFAULT 0, created_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_snip_kind ON content_snippets(kind);
CREATE TABLE IF NOT EXISTS prospects (
  id INTEGER PRIMARY KEY AUTOINCREMENT, platform TEXT, account_name TEXT, shop_name TEXT, account_url TEXT, shop_url TEXT,
  live_url TEXT, products TEXT, categories TEXT, seller_type TEXT, tags TEXT, direction INTEGER, keyword TEXT,
  recent_activity TEXT, live_freq TEXT, followers INTEGER, phone TEXT, zalo TEXT, email TEXT, import_signals TEXT,
  evidence TEXT, score INTEGER, grade TEXT, parts TEXT, suggested TEXT, approach TEXT, next_action TEXT,
  status TEXT DEFAULT 'verified', lead_id INTEGER, found_by INTEGER, phone_tries INTEGER DEFAULT 0, note TEXT, verified_at TEXT, created_at TEXT, updated_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_prospect_url ON prospects(account_url);
CREATE TABLE IF NOT EXISTS junk (
  id INTEGER PRIMARY KEY AUTOINCREMENT, lead_id INTEGER, prospect_id INTEGER, name TEXT, phone TEXT, url TEXT, seller_type TEXT,
  reason TEXT, note TEXT, text TEXT, created_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_junk_url ON junk(url);
CREATE INDEX IF NOT EXISTS idx_junk_phone ON junk(phone);
CREATE TABLE IF NOT EXISTS fb_policy_sources (
  key TEXT PRIMARY KEY, name TEXT, url TEXT, kind TEXT, last_hash TEXT, last_text TEXT, last_checked TEXT, last_changed TEXT,
  status TEXT, error TEXT
);
CREATE TABLE IF NOT EXISTS fb_policy_changes (
  id INTEGER PRIMARY KEY AUTOINCREMENT, source_key TEXT, name TEXT, url TEXT, detected_at TEXT, added TEXT, removed TEXT,
  summary TEXT, status TEXT DEFAULT 'new'
);
CREATE TABLE IF NOT EXISTS fb_incidents (
  id INTEGER PRIMARY KEY AUTOINCREMENT, account_id INTEGER, kind TEXT, detail TEXT, posts_24h INTEGER DEFAULT 0,
  bumps_24h INTEGER DEFAULT 0, joins_24h INTEGER DEFAULT 0, group_id INTEGER, post_id INTEGER, lesson TEXT, created_at TEXT
);
CREATE TABLE IF NOT EXISTS site_posts (
  id INTEGER PRIMARY KEY AUTOINCREMENT, keyword TEXT, title TEXT, slug TEXT, meta_title TEXT, meta_desc TEXT, excerpt TEXT,
  body TEXT, faq TEXT, product_ids TEXT, cover TEXT, cover_alt TEXT, status TEXT DEFAULT 'draft', seo_score INTEGER DEFAULT 0,
  seo_report TEXT, policy_note TEXT, words INTEGER DEFAULT 0, author TEXT DEFAULT 'vy', note TEXT, created_at TEXT, updated_at TEXT,
  published_at TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_site_slug ON site_posts(slug);
CREATE TABLE IF NOT EXISTS site_keywords (
  id INTEGER PRIMARY KEY AUTOINCREMENT, keyword TEXT UNIQUE, intent TEXT, cluster TEXT, priority INTEGER DEFAULT 2,
  status TEXT DEFAULT 'planned', post_id INTEGER, source TEXT DEFAULT 'vy', created_at TEXT
);
CREATE TABLE IF NOT EXISTS comment_samples (
  id INTEGER PRIMARY KEY AUTOINCREMENT, text TEXT, template TEXT, product TEXT, source TEXT, score INTEGER, created_at TEXT
);
CREATE TABLE IF NOT EXISTS reply_tasks (
  id INTEGER PRIMARY KEY AUTOINCREMENT, account_id INTEGER, group_id INTEGER, post_url TEXT UNIQUE, author TEXT, author_url TEXT,
  post_text TEXT, reply TEXT, source TEXT, status TEXT DEFAULT 'draft', scheduled_for TEXT, sent_at TEXT, error TEXT, shot TEXT,
  created_at TEXT, decided_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_reply_status ON reply_tasks(account_id, status, scheduled_for);
CREATE TABLE IF NOT EXISTS feed_scans (
  id INTEGER PRIMARY KEY AUTOINCREMENT, account_id INTEGER, status TEXT DEFAULT 'queued', created_at TEXT, done_at TEXT,
  read INTEGER DEFAULT 0, buyers INTEGER DEFAULT 0, sellers INTEGER DEFAULT 0, note TEXT
);
CREATE TABLE IF NOT EXISTS friend_suggestions (
  id INTEGER PRIMARY KEY AUTOINCREMENT, account_id INTEGER, group_id INTEGER, name TEXT, profile_url TEXT, reason TEXT,
  score INTEGER DEFAULT 0, snippet TEXT, status TEXT DEFAULT 'suggested', created_at TEXT, opened_at TEXT, sent_at TEXT,
  decided_at TEXT, UNIQUE(account_id, profile_url)
);
CREATE INDEX IF NOT EXISTS idx_friend_status ON friend_suggestions(account_id, status);
CREATE TABLE IF NOT EXISTS post_samples (
  id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, content TEXT, enabled INTEGER DEFAULT 1, note TEXT, created_at TEXT, updated_at TEXT
);
CREATE TABLE IF NOT EXISTS prospect_lessons (
  id INTEGER PRIMARY KEY AUTOINCREMENT, text TEXT, suggest TEXT, applied INTEGER DEFAULT 0, knowledge_id INTEGER, created_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_prospect_grade ON prospects(grade);
CREATE TABLE IF NOT EXISTS knowledge (
  id INTEGER PRIMARY KEY AUTOINCREMENT, agent_id TEXT, topic TEXT, question TEXT, content TEXT, keywords TEXT, source TEXT,
  confidence REAL DEFAULT 0.8, uses INTEGER DEFAULT 0, last_used_at TEXT, status TEXT DEFAULT 'active', created_at TEXT, updated_at TEXT,
  kind TEXT DEFAULT 'guide'
);
CREATE INDEX IF NOT EXISTS idx_knowledge_agent ON knowledge(agent_id, status);
CREATE TABLE IF NOT EXISTS knowledge_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT, agent_id TEXT, kind TEXT, question TEXT, item_id INTEGER, created_at TEXT
);
CREATE TABLE IF NOT EXISTS group_searches (
  id INTEGER PRIMARY KEY AUTOINCREMENT, keyword TEXT, sale_id INTEGER, results INTEGER, new INTEGER, searched_at TEXT
);
CREATE TABLE IF NOT EXISTS group_joins (
  group_id INTEGER, sale_id INTEGER, status TEXT, note TEXT, requested_at TEXT, updated_at TEXT,
  PRIMARY KEY (group_id, sale_id)
);
CREATE TABLE IF NOT EXISTS coach_outcomes (
  id INTEGER PRIMARY KEY AUTOINCREMENT, agent_id TEXT, verdict TEXT, work TEXT, result TEXT, ref TEXT,
  batch_id TEXT, coached_at TEXT, created_at TEXT
);
CREATE TABLE IF NOT EXISTS errors (
  id INTEGER PRIMARY KEY AUTOINCREMENT, source TEXT, title TEXT, message TEXT, detail TEXT, hint TEXT, screen TEXT,
  action TEXT, ref_type TEXT, ref_id TEXT, screenshot TEXT, fingerprint TEXT, count INTEGER DEFAULT 1,
  status TEXT DEFAULT 'new', created_at TEXT, last_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_errors_fp ON errors(fingerprint);
CREATE TABLE IF NOT EXISTS ceo_decisions (
  id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT, status TEXT, sale_id INTEGER, title TEXT, reason TEXT,
  data TEXT, created_at TEXT, decided_at TEXT
);
CREATE TABLE IF NOT EXISTS sale_days (
  sale_id INTEGER, date TEXT, target INTEGER, PRIMARY KEY (sale_id, date)
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
    ("posts", "source", "TEXT"),
    ("leads", "lost_reason", "TEXT"), ("leads", "lost_note", "TEXT"), ("leads", "lost_at", "TEXT"),  # vì sao khách không mua
    ("posts", "orig_content", "TEXT"), ("posts", "fit_group_id", "INTEGER"), ("posts", "fit_note", "TEXT"),  # Lan chỉnh bài theo nhóm
    ("products", "hot", "INTEGER DEFAULT 0"), ("products", "hot_note", "TEXT DEFAULT ''"), ("products", "hot_since", "TEXT"),
    ("products", "is_general", "INTEGER DEFAULT 0"), ("products", "site_show", "INTEGER"),
    ("posts", "img_fails", "INTEGER DEFAULT 0"),  # số lần Facebook không nhận ảnh khi đăng
    ("posts", "policy_note", "TEXT"),  # bài vi phạm luật Facebook (CEO kiểm)
    ("fb_accounts", "rest_until", "TEXT"), ("fb_accounts", "limit_factor", "REAL DEFAULT 1"), ("fb_accounts", "factor_until", "TEXT"),
    ("groups", "policy_rest_until", "TEXT"),  # nhóm hay gỡ bài: tạm ngừng đăng
    ("posts", "link_tries", "INTEGER DEFAULT 0"), ("posts", "link_next_at", "TEXT"), ("posts", "link_error", "TEXT"),  # lấy lại link bài  # ảnh tổng hợp nhà máy: tích thì mọi bài chỉ lấy ảnh ở đây
    # chỉ số tương tác của nhóm (sale khảo sát) và đánh giá của Tuấn
    ("group_candidates", "posts_today", "REAL"), ("group_candidates", "posts_month", "INTEGER"), ("group_candidates", "new_members_week", "INTEGER"), ("group_candidates", "avg_reactions", "REAL"), ("group_candidates", "avg_comments", "REAL"), ("group_candidates", "sampled_posts", "INTEGER"), ("group_candidates", "last_post_hours", "REAL"), ("group_candidates", "selling_ratio", "REAL"), ("group_candidates", "no_selling", "INTEGER DEFAULT 0"), ("group_candidates", "rules_note", "TEXT"), ("group_candidates", "scouted_at", "TEXT"), ("group_candidates", "eng_score", "REAL"), ("group_candidates", "verdict", "TEXT"), ("group_candidates", "review_note", "TEXT"), ("group_candidates", "reviewed_at", "TEXT"),
    ("groups", "posts_today", "REAL"), ("groups", "posts_month", "INTEGER"), ("groups", "new_members_week", "INTEGER"), ("groups", "avg_reactions", "REAL"), ("groups", "avg_comments", "REAL"), ("groups", "sampled_posts", "INTEGER"), ("groups", "last_post_hours", "REAL"), ("groups", "selling_ratio", "REAL"), ("groups", "no_selling", "INTEGER DEFAULT 0"), ("groups", "rules_note", "TEXT"), ("groups", "scouted_at", "TEXT"), ("groups", "eng_score", "REAL"), ("groups", "verdict", "TEXT"), ("groups", "review_note", "TEXT"), ("groups", "reviewed_at", "TEXT"),
    ("posts", "account_id", "INTEGER"), ("bumps", "account_id", "INTEGER"), ("comment_seen", "account_id", "INTEGER"),
    ("groups", "member_account_ids", "TEXT DEFAULT ''"), ("sales", "last_account_id", "INTEGER"),
    ("groups", "source", "TEXT DEFAULT 'manual'"), ("groups", "keyword", "TEXT"), ("groups", "privacy", "TEXT"),
    ("groups", "posts_per_day", "REAL"), ("groups", "score", "REAL"),
    ("orders", "customer", "TEXT"),
    ("sales", "hired_by", "TEXT"), ("sales", "hire_reason", "TEXT"), ("sales", "ceo_reminded_at", "TEXT"),
    ("sales", "ceo_handled", "INTEGER"), ("sales", "fire_review", "TEXT"),
    ("posts", "sale_id", "INTEGER"), ("posts", "error", "TEXT"), ("posts", "screenshot", "TEXT"),
    ("groups", "member_sale_ids", "TEXT DEFAULT ''"), ("products", "images", "TEXT DEFAULT '[]'"),
    ("posts", "permalink_status", "TEXT"), ("posts", "bump_enabled", "INTEGER DEFAULT 1"),
    ("posts", "bump_count", "INTEGER DEFAULT 0"), ("posts", "last_bump_at", "TEXT"),
    ("leads", "post_id", "INTEGER"),
    ("leads", "phone", "TEXT"), ("leads", "origin", "TEXT DEFAULT 'manual'"), ("leads", "fb_author", "TEXT"),
    ("leads", "escalated_at", "TEXT"), ("leads", "escalate_reason", "TEXT"), ("leads", "consult_note", "TEXT"),
    ("posts", "last_scan_at", "TEXT"),
    ("products", "image_folder", "TEXT DEFAULT ''"), ("posts", "images_used", "TEXT"),
    ("sales", "is_sample", "INTEGER DEFAULT 0"),
    ("sales", "status", "TEXT DEFAULT 'active'"), ("sales", "fired_at", "TEXT"), ("sales", "fire_reason", "TEXT"),
    ("sales", "kpi_period_start", "TEXT"), ("sales", "kpi_warned", "TEXT"), ("sales", "replaced_by", "INTEGER"),
    ("sales", "fired_gen", "TEXT"), ("leads", "is_sample", "INTEGER DEFAULT 0"),
    ("groups", "is_sample", "INTEGER DEFAULT 0"), ("products", "is_sample", "INTEGER DEFAULT 0"),
    ("leads", "phone_at", "TEXT"), ("leads", "boss_status", "TEXT"), ("leads", "remind_at", "TEXT"),
    ("prospects", "phone_tries", "INTEGER DEFAULT 0"), ("prospects", "rule_bonus", "INTEGER DEFAULT 0"),
    ("prospects", "rule_note", "TEXT"), ("prospects", "rule_fail", "TEXT"), ("posts", "sample_id", "INTEGER"), ("posts", "review_score", "INTEGER"),
    ("posts", "review_note", "TEXT"), ("posts", "reviewed_by", "TEXT"), ("posts", "reviewed_at", "TEXT"), ("posts", "review_ok", "INTEGER"),
    ("account_groups", "role", "TEXT DEFAULT 'member'"), ("account_groups", "origin", "TEXT"), ("account_groups", "joined_at", "TEXT"),
    ("account_groups", "verdict", "TEXT"), ("account_groups", "verdict_note", "TEXT"), ("account_groups", "left_at", "TEXT"),
    ("account_groups", "seen_at", "TEXT"), ("groups", "managed", "INTEGER DEFAULT 0"), ("groups", "pinned", "INTEGER DEFAULT 0"),
    ("groups", "focus", "INTEGER DEFAULT 0"), ("groups", "friends_scanned_at", "TEXT"),
    ("groups", "slug", "TEXT"), ("posts", "managed", "INTEGER DEFAULT 0"), ("fb_accounts", "groups_synced_at", "TEXT"),
    ("reply_tasks", "kind", "TEXT DEFAULT 'buyer'"), ("reply_tasks", "origin", "TEXT DEFAULT 'group'"), ("reply_tasks", "image", "TEXT"),
    ("reply_tasks", "score", "INTEGER"), ("reply_tasks", "reason", "TEXT"), ("reply_tasks", "checked_at", "TEXT"),
    ("reply_tasks", "removed", "INTEGER DEFAULT 0"), ("groups", "no_pitch_until", "TEXT"),
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
    "spread_posts": "1",  # rải bài của mỗi nick đều trong khung giờ làm việc thay vì dồn sớm nhất có thể
    "browser_mode": "background",  # background: chạy ngầm ngoài màn hình; show: hiện cửa sổ; headless: ẩn hoàn toàn
    "cost_preset": "can_bang",
    "model_posts": "claude-sonnet-5-5",
    "model_replies": "claude-sonnet-5-5", "model_ceo": "claude-sonnet-5-5", "model_review": "claude-haiku-5-5",
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
    "bump_contact": "Cần hàng liên hệ Zalo 0386992326",  # Bảo luôn gắn dòng này cuối mỗi bình luận up bài
    "bump_text_mode": "ai",  # ai: Bảo tự viết mỗi lần (Claude nếu có khóa); list: chọn ngẫu nhiên từ bump_texts
    "bump_texts": "Còn hàng sỉ nhé cả nhà\nAi cần báo giá sỉ cứ inbox mình nha\nHàng mới về, ảnh thật tại xưởng\n",
    "bump_planned_date": "",
    "learn_enabled": "1",
    "learn_time": "23:15",
    "learn_last_date": "",
    "learn_explore": "0.25",
    "model_learning": "claude-haiku-5-5",
    "anthropic_api_key": "",
    "company_status": "setup",
    "company_founded_at": "",
    "company_founded_ts": "",
    "company_gen": "0",
    "capital_vnd": "10000000",
    "ceo_autopilot": "1",
    "discover_enabled": "1", "discover_time": "10:30", "discover_keywords_per_day": "3", "discover_add_per_day": "5",
    "join_enabled": "1", "join_per_nick_day": "2", "browse_minutes": "2",
    "app_tz": "",  # trống = giờ Việt Nam (hoặc APP_TZ trong .env)
    "idle_learning": "1", "idle_study_per_day": "6", "growth_state": "",
    "knowledge_enabled": "1", "self_study": "0", "group_fit": "1", "group_fit_min": "2",
    "learn_min_each": "15", "learn_min_total": "40", "learn_prior": "10", "learn_z": "1.96", "learn_ai_every": "7", "learn_ai_last": "",
    "ceo_weekly": "1", "ceo_weekly_time": "08:20", "ceo_weekly_last": "", "ceo_kw_auto": "1", "ceo_kw_trials": "", "fanpage_scan": "1",
    "focus_enabled": "1", "focus_days": "14", "focus_min_phones": "8", "focus_min_called": "5", "focus_weekday": "1",
    "focus_paused": "", "focus_resumed": "", "focus_last": "", "prospect_pages": "1", "study_time": "07:00", "study_per_agent": "2", "knowledge_answer_threshold": "0.8",
    "study_last_date": "", "model_knowledge": "claude-haiku-5-5",
    "self_write_mode": "auto", "self_write_min": "12", "lan_style": "", "content_library_migrated": "",
    "hot_share": "0.7",  # tỉ lệ bài Lan viết về sản phẩm đang bán chạy (khi sếp có tích sản phẩm bán chạy)
    "scout_per_run": "6", "review_posts_day": "10", "review_avg_reactions": "20", "review_avg_comments": "5",
    "review_growth_week": "0.5", "review_min_members": "1000", "review_join_score": "60", "review_consider_score": "40",
    "review_use_best_groups": "1", "group_keywords": "", "ceo_kw_today": "",
    "discover_last": "", "join_last": "", "discover_last_sale": "", "discover_last_result": "",
    "ceo_enabled": "1", "ceo_mode": "auto", "ceo_milestones": "50000000:1,100000000:1", "ceo_milestones_done": "",
    "ceo_potential": "1", "ceo_hire_cooldown_days": "14", "ceo_last_potential_hire": "", "ceo_last_daily": "", "ceo_last_review": "",
    "usd_vnd": "25800",
    "trial_days": "60",
    "dissolved_at": "",
    "dissolved_reason": "",
    "trial_warned": "",
    "capital_warned": "",
    "images_min": "2",
    "images_max": "4",
    "image_reuse_days": "14",
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
    "tg_report_done": "1",
    "prospect_enabled": "1", "prospect_time": "14:30", "prospect_inspect_per_run": "10", "prospect_facebook": "1",
    "prospect_tiktok": "0", "prospect_shopee": "0", "prospect_fb_keywords": "2", "prospect_ads": "1", "prospect_groups": "1", "prospect_groups_per_run": "3",
    "price_zalo": "0386992326", "price_contact": "", "template_mode": "1", "template_ai": "1", "post_template": "",
    "ceo_review_min": "70", "ceo_review_ai": "1",
    "mygroups_enabled": "1", "mygroups_time": "09:15", "auto_leave": "1", "leave_per_nick_day": "3", "new_group_rest_days": "7",
    "mygroups_review_per_run": "8", "admin_posts_min": "5", "admin_posts_max": "10", "admin_care_ai": "1", "admin_sell_share": "50", "prospect_auto_crm": "1", "prospect_ai_script": "1", "prospect_keywords": "",
    "tg_sent_log": "{}",
    "attach_images": "1",
    "require_images": "1",  # bài đăng Facebook bắt buộc kèm ảnh, không có ảnh thì không đăng
    # Luật Facebook: giới hạn an toàn cho mỗi nick, kiểm bài, theo dõi chính sách
    # Sếp chỉ đạo nơi đăng: all / prefer / only, từ khóa nhóm nên đăng, từ khóa nhóm tránh
    "post_target_mode": "all", "post_group_keywords": "", "post_group_exclude": "",
    # Gợi ý kết bạn: Tuấn tìm người trong nhóm sôi nổi, sale tự bấm Thêm bạn bè
    "friends_enabled": "1", "friends_time": "10:40", "friends_groups_per_run": "2", "friends_per_group": "12",
    "friends_last": "", "fbp_friends_day": "10",
    # Bảo trả lời khách: tìm bài hỏi mua trong nhóm sôi nổi, sếp duyệt, nick gửi trong giờ làm (có trần, giãn cách)
    "replies_enabled": "1", "replies_time": "09:20", "replies_per_nick_day": "5", "replies_groups_per_run": "3",
    "replies_per_group": "4", "replies_last": "", "reply_contact": "",
    "feed_enabled": "1", "feed_min_posts": "20", "feed_scans_day": "2", "feed_gap_hours": "3", "feed_min_score": "70",
    "feed_buyer_image": "1", "feed_seller_enabled": "1", "feed_comment_all": "1", "feed_general_style": "invite", "feed_per_group_day": "2", "reply_gap_min": "60", "feed_seller_per_nick_day": "2", "feed_seller_words": "",
    "fbp_enabled": "1", "fbp_posts_day": "6", "fbp_gap_minutes": "30", "fbp_bumps_day": "6", "fbp_joins_day": "2",
    "fbp_same_group_hours": "24", "fbp_new_nick_days": "14", "fbp_new_nick_factor": "0.5", "fbp_rest_days": "3",
    "fbp_after_days": "7", "fbp_after_factor": "0.5", "fbp_hashtags_max": "5", "fbp_caption_max": "2500",
    "fbp_similar_block": "0.95", "fbp_similar_max": "0.85", "fbp_removed_max": "2", "fbp_group_rest_days": "30",
    "fbp_auto_tighten": "1", "fbp_custom_rules": "[]", "fbp_extra_sources": "[]",
    "fbp_watch_enabled": "1", "fbp_watch_time": "06:40", "fbp_watch_every_days": "7", "fbp_watch_last": "",
    # Website công ty + Vy viết bài chuẩn SEO
    "site_name": "MỘC TÂM", "site_legal_name": "", "site_tagline": "Nhà máy sản xuất & gia công trà túi lọc, cà phê, ngũ cốc, bột thiên nhiên",
    "site_domain": "", "site_about": "", "site_address": "", "site_email": "", "site_phone": "0386992326",
    "site_certs": "GMP – ISO – FDA – VSATTP", "site_founded": "", "site_color": "#2f5d3a", "site_ga_id": "",
    "site_posts_week": "3", "site_write_days": "1,3,5", "site_write_time": "09:45", "site_auto_publish": "1",
    "site_min_seo": "75", "site_last_write": "", "site_last_build": "", "site_last_deploy": "",
    "site_ftp_host": "", "site_ftp_user": "", "site_ftp_pass": "", "site_ftp_dir": "/public_html", "site_ftp_tls": "1", "site_deploy_mode": "auto", "site_auto_deploy": "1", "site_sync_url": "",
    "site_sync_token": "", "site_sync_fp": "", "site_deploy_ok_mode": "", "site_deploy_msg": "", "site_check_msg": "",
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

# Khách mẫu của các bản cũ: KHÔNG còn được tạo, chỉ giữ tên để nhận diện và dọn ở máy đã cài bản cũ
SEED_LEADS = [
    ("Thu Trang", "fb.com/thutrang.shop", "Facebook", "Hội Livestream bán hàng", "Livestream",
     "Muốn lấy sỉ trà đậu biếc để live pha chế", 80, "contacted"),
    ("Shop Mộc An", "Zalo 09xx", "Zalo", "Tìm nguồn hàng sỉ - Đầu mối tận xưởng", "Sàn TMĐT",
     "Hỏi giá ngũ cốc số lượng 100 hũ, cần hóa đơn", 90, "sample"),
    ("Anh Quân Ads", "Inbox page", "Facebook", "Hội chạy quảng cáo Facebook Ads", "Chạy quảng cáo",
     "Tìm sản phẩm biên lợi nhuận cao để test ads", 65, "new"),
]


# Chỉ mục cho các truy vấn chạy mỗi 30 giây / mỗi lần mở trang (đo trên dữ liệu giả lập 1 năm, 25 nick)
INDEXES = [
    ("idx_posts_status", "posts(status, posted_at)"), ("idx_posts_acc", "posts(account_id, status)"),
    ("idx_posts_group", "posts(group_id, status)"), ("idx_posts_sample_cov", "posts(sample_id, status, comments, leads)"),
    ("idx_posts_created", "posts(created_at)"),
    ("idx_bumps_post", "bumps(post_id)"), ("idx_bumps_acc", "bumps(account_id, status, done_at)"),
    ("idx_bumps_status", "bumps(status, done_at)"),
    ("idx_activity_at", "activity(created_at)"), ("idx_usage_cov", "usage(created_at, task, cost_usd)"),
    ("idx_cseen_at", "comment_seen(created_at)"), ("idx_fallback_at", "ai_fallback(created_at)"),
    ("idx_ceomsg_at", "ceo_messages(created_at)"), ("idx_klog_at", "knowledge_log(created_at)"),
    ("idx_feedscan_at", "feed_scans(created_at)"), ("idx_mmsg_meeting", "meeting_messages(meeting_id)"),
    ("idx_lib_post", "content_library(post_id)"), ("idx_snip_lib", "content_snippets(library_id)"),
    ("idx_leads_at", "leads(created_at)"), ("idx_reply_at", "reply_tasks(status, created_at)"),
    ("idx_friend_at", "friend_suggestions(status, created_at)"), ("idx_coach", "coach_outcomes(agent_id, coached_at, batch_id)"),
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
        for name, on in INDEXES:  # sau migration: cột mới đã có
            try:
                conn().execute(f"CREATE INDEX IF NOT EXISTS {name} ON {on}")
            except sqlite3.DatabaseError as e:
                print("[db] chỉ mục", name, e)
        conn().commit()
    # bài đang đăng dở khi tắt máy -> đưa về hàng đợi
    run("UPDATE posts SET status='scheduled' WHERE status='posting'")
    run("UPDATE bumps SET status='scheduled' WHERE status='running'")
    # gói Cân bằng mới: Hà tư vấn khách + CEO hiểu lệnh dùng Sonnet (chỉ đổi khi sếp đang dùng đúng gói Cân bằng, chưa tùy chỉnh)
    if get_settings().get("preset_v2") != "1":
        if get_settings().get("cost_preset", "can_bang") == "can_bang":
            for k in ("model_replies", "model_ceo"):
                set_setting(k, "claude-sonnet-5-5")
            set_setting("model_review", "claude-haiku-5-5")
        set_setting("preset_v2", "1")
    # sếp chốt: Vy viết xong bài đạt chuẩn thì tự đăng và đẩy lên website, không chờ bấm tay (bật một lần khi cập nhật)
    if get_settings().get("site_autopub_v1") != "1":
        set_setting("site_auto_publish", "1")
        set_setting("site_autopub_v1", "1")
    # luật Facebook là luật thật (không phải kiến thức chung tự học) -> nguồn riêng, luôn được dùng
    run("UPDATE knowledge SET source='rule' WHERE source='library' AND topic LIKE 'Luật Facebook:%'")
    for k, v in DEFAULT_SETTINGS.items():
        run("INSERT OR IGNORE INTO settings(key, value) VALUES (?, ?)", (k, v))
    if not one("SELECT id FROM products LIMIT 1"):
        for p in SEED_PRODUCTS:
            run("""INSERT INTO products(name, category, description, wholesale_price, retail_price,
                   moq, selling_points, created_at, is_sample) VALUES (?,?,?,?,?,?,?,?,1)""", (*p, now()))
        for g in SEED_GROUPS:
            run("""INSERT INTO groups(name, url, topic, members, rules, min_days_between_posts, created_at, is_sample)
                   VALUES (?,?,?,?,?,?,?,1)""", (*g, now()))
    # Máy đã cài bản cũ: đánh dấu dữ liệu mẫu theo đúng tên đã gieo (1 lần)
    if not one("SELECT value FROM settings WHERE key='sample_marked'"):
        for name, *_ in SEED_LEADS:
            run("UPDATE leads SET is_sample=1 WHERE name=? AND COALESCE(origin,'manual')='manual' AND post_id IS NULL", (name,))
        for name, url, *_ in SEED_GROUPS:
            run("UPDATE groups SET is_sample=1 WHERE name=? AND COALESCE(url,'')=''", (name,))
        for name, *_ in SEED_PRODUCTS:
            run("UPDATE products SET is_sample=1 WHERE name=? AND COALESCE(images,'[]')='[]'", (name,))
        run("INSERT OR REPLACE INTO settings(key, value) VALUES ('sample_marked','1')")
    import accounts
    set_tz(get_settings().get("app_tz") or os.getenv("APP_TZ") or DEFAULT_TZ)
    accounts.migrate()
    if get_settings().get("prospect_fb_first") != "1":  # sếp chốt: tập trung Facebook, TikTok/Shopee mặc định tắt
        for k, v in (("prospect_tiktok", "0"), ("prospect_shopee", "0"), ("prospect_fb_first", "1")):
            set_setting(k, v)
    try:
        import content_style
        content_style.migrate()  # bài Claude viết trước đây -> kho bài để Lan học phong cách
    except Exception as e:
        print("[content_style migrate]", e)
    if get_settings().get("care_posts_removed") != "1":  # sếp chốt: nhóm chỉ đăng bài theo mẫu tìm khách sỉ
        run("UPDATE posts SET status='rejected', error='Sếp chốt chỉ đăng bài theo mẫu' WHERE source='care' AND status IN ('scheduled','approved','draft')")
        set_setting("care_posts_removed", "1")
    try:
        import post_template
        post_template.seed()  # thư viện bài mẫu: đưa mẫu MỘC TÂM vào làm bài đầu tiên
    except Exception as e:
        print("[post_template seed]", e)
    try:
        import pricing
        pricing.migrate()  # sếp chốt: bỏ giá khỏi sản phẩm, mời liên hệ Zalo
    except Exception as e:
        print("[pricing migrate]", e)  # bản cũ 1 sale = 1 nick -> bảng nick riêng, mỗi sale nhiều nick
    try:
        import website
        website.seed()  # kế hoạch từ khóa ban đầu cho Vy
    except Exception as e:
        print("[website seed]", e)
    import fb_policy
    if not get_settings().get("fbp_taught") or get_settings().get("fbp_rules_n") != str(len(fb_policy.RULES)):
        try:
            set_setting("fbp_rules_n", str(len(fb_policy.RULES)))
            fb_policy.teach()  # ghi luật Facebook vào sổ kiến thức của các agent (1 lần, cập nhật khi sếp thêm luật)
        except Exception as e:
            print("[fb policy teach]", e)


def sample_counts() -> dict:
    return {t: one(f"SELECT COUNT(*) n FROM {t} WHERE is_sample=1")["n"] for t in ("sales", "leads", "groups", "products")}


# ---------------------------------------------------------------- bắt đầu chạy thật
RESET_TABLES = {  # bảng: mô tả cho sếp
    "posts": "bài đăng", "prospects": "khách sỉ Mai tìm", "bumps": "lượt up bài", "image_usage": "lịch sử dùng ảnh", "leads": "khách hàng",
    "replies": "tin nhắn Hà soạn", "comment_seen": "bình luận đã quét", "meetings": "cuộc họp",
    "meeting_messages": "lời thoại trong họp", "tasks": "việc được giao", "activity": "nhật ký hoạt động",
    "lessons": "bài học của agent", "feedback": "phản hồi duyệt bài", "agent_progress": "cấp độ, kinh nghiệm agent",
    "kpi_daily": "lịch sử KPI", "ai_batches": "lô viết bài đang chờ",
    "orders": "doanh thu đã nhập", "ceo_decisions": "quyết định của CEO", "errors": "sổ lỗi", "ceo_messages": "trao đổi sếp – CEO", "group_candidates": "nhóm tìm được chưa thêm", "group_searches": "lượt tìm nhóm", "group_joins": "trạng thái xin vào nhóm (bản cũ)", "expenses": "chi phí ghi tay (bản cũ)", "sale_days": "ngày công của sale",
}
RUN_STATE_KEYS = ["bump_planned_date", "learn_last_date", "scan_last", "tg_sent_log", "company_founded_at", "company_founded_ts",
                  "dissolved_at", "dissolved_reason", "trial_warned", "capital_warned",
                  "ceo_milestones_done", "ceo_last_potential_hire", "ceo_last_daily", "ceo_last_review",
                  "ceo_kw_today", "discover_last", "join_last", "discover_last_result"]


def reset_preview() -> dict:
    counts = {t: one(f"SELECT COUNT(*) n FROM {t}" + (" WHERE action!='Bắt đầu chạy thật'" if t == "activity" else ""))["n"]
              for t in RESET_TABLES}
    return {"delete": [{"table": t, "label": RESET_TABLES[t], "count": n} for t, n in counts.items() if n],
            "keep": {"sales": one("SELECT COUNT(*) n FROM sales WHERE COALESCE(is_sample,0)=0")["n"],
                     "products": one("SELECT COUNT(*) n FROM products WHERE COALESCE(is_sample,0)=0")["n"],
                     "groups": one("SELECT COUNT(*) n FROM groups WHERE COALESCE(is_sample,0)=0")["n"]},
            "samples": {"products": one("SELECT COUNT(*) n FROM products WHERE is_sample=1")["n"],
                        "groups": one("SELECT COUNT(*) n FROM groups WHERE is_sample=1")["n"],
                        "sales": one("SELECT COUNT(*) n FROM sales WHERE is_sample=1")["n"]},
            "shots": len(list(SHOTS_DIR.glob("*.png")))}


def reset_test_data(products: bool = False, groups: bool = False) -> dict:
    """Xóa dữ liệu thử nghiệm, GIỮ nhân viên sale (kèm hồ sơ Chrome đã đăng nhập Facebook),
    cài đặt (khóa API, Telegram, KPI, thư mục ảnh), chi phí AI đã tiêu. Tự sao lưu trước khi xóa."""
    import shutil
    backup_dir = DATA_DIR / "backups"
    backup_dir.mkdir(exist_ok=True)
    backup = backup_dir / f"truoc-khi-chay-that-{clock().strftime('%Y%m%d-%H%M%S')}.db"
    with _lock:
        conn().commit()
        bk = sqlite3.connect(backup)
        conn().backup(bk)
        bk.close()
    before = reset_preview()
    with _lock:
        c = conn()
        for t in RESET_TABLES:
            c.execute(f"DELETE FROM {t}")
        c.execute("DELETE FROM fb_accounts WHERE sale_id IN (SELECT id FROM sales WHERE is_sample=1)")
        c.execute("DELETE FROM sales WHERE is_sample=1")
        c.execute("UPDATE sales SET last_post_at=NULL, last_error=NULL, last_account_id=NULL")
        c.execute("UPDATE fb_accounts SET last_post_at=NULL, last_session_at=NULL")
        if products:
            c.execute("DELETE FROM products")
        else:
            c.execute("DELETE FROM products WHERE is_sample=1")
        if groups:
            c.execute("DELETE FROM groups")
            c.execute("DELETE FROM account_groups")
        else:
            c.execute("DELETE FROM account_groups WHERE group_id IN (SELECT id FROM groups WHERE is_sample=1)"
                      " OR account_id NOT IN (SELECT id FROM fb_accounts)")
            c.execute("DELETE FROM groups WHERE is_sample=1")
            c.execute("UPDATE groups SET last_posted_at=NULL, leads_count=0")
        for k in RUN_STATE_KEYS:
            c.execute("UPDATE settings SET value=? WHERE key=?", ("{}" if k == "tg_sent_log" else "", k))
        c.execute("UPDATE settings SET value='setup' WHERE key='company_status'")
        c.execute("UPDATE sales SET kpi_period_start=NULL, kpi_warned=NULL")
        tables = list(RESET_TABLES) + (["products"] if products else []) + (["groups"] if groups else [])
        c.execute("DELETE FROM sqlite_sequence WHERE name IN (%s)" % ",".join("?" * len(tables)), tables)
        c.commit()
        c.execute("VACUUM")
    shots = 0
    for f in SHOTS_DIR.glob("*.png"):
        f.unlink(missing_ok=True)
        shots += 1
    if products:  # ảnh tải lên trong phần mềm (thư mục ảnh trên máy sếp KHÔNG bị đụng tới)
        shutil.rmtree(MEDIA_DIR, ignore_errors=True)
        MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    log("minh", "Bắt đầu chạy thật", "Đã xóa dữ liệu thử nghiệm, giữ nhân viên sale và cài đặt")
    return {"deleted": before["delete"], "shots": shots, "backup": str(backup)}


def clear_samples(tables=("sales", "leads", "groups", "products")) -> dict:
    """Xóa dữ liệu mẫu. Khách mẫu: xóa cả tin nhắn đã soạn; sản phẩm/nhóm mẫu: bài đăng cũ vẫn giữ."""
    done = {}
    for t in tables:
        n = one(f"SELECT COUNT(*) n FROM {t} WHERE is_sample=1")["n"]
        if not n:
            continue
        if t == "leads":
            run("DELETE FROM replies WHERE lead_id IN (SELECT id FROM leads WHERE is_sample=1)")
        if t == "sales":
            run("UPDATE posts SET sale_id=NULL, account_id=NULL, status='approved', scheduled_for=NULL WHERE status='scheduled' AND sale_id IN (SELECT id FROM sales WHERE is_sample=1)")
            run("DELETE FROM account_groups WHERE account_id IN (SELECT a.id FROM fb_accounts a JOIN sales s ON s.id=a.sale_id WHERE s.is_sample=1)")
            run("DELETE FROM fb_accounts WHERE sale_id IN (SELECT id FROM sales WHERE is_sample=1)")
        run(f"DELETE FROM {t} WHERE is_sample=1")
        done[t] = n
    return done


def get_settings() -> dict:
    return {r["key"]: r["value"] for r in q("SELECT key, value FROM settings")}


def set_setting(key: str, value: str):
    run("INSERT INTO settings(key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value))


LOG_HOOKS: list = []  # hàm nhận (agent_id, action, detail) mỗi khi có hoạt động mới (VD: báo Telegram việc đã xong)


def log(agent_id: str, action: str, detail: str = ""):
    run("INSERT INTO activity(agent_id, action, detail, created_at) VALUES (?,?,?,?)",
        (agent_id, action, detail, now()))
    for h in LOG_HOOKS:
        try:
            h(agent_id, action, detail)
        except Exception as e:
            print("[log hook]", e)


def dumps(x) -> str:
    return json.dumps(x, ensure_ascii=False)
