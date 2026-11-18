# ------------------------------------------------------------------ họp
class StartMeeting(BaseModel):
    topic: str = ""


class BossSay(BaseModel):
    text: str


@app.get("/api/meetings")
def meetings():
    return db.q("SELECT * FROM meetings ORDER BY id DESC LIMIT 30")


@app.get("/api/meetings/topics")
def topics():
    return meeting.TOPICS


@app.post("/api/meetings")
def start_meeting(s: StartMeeting):
    return {"id": meeting.start(s.topic)}


@app.get("/api/meetings/{mid}")
def get_meeting(mid: int, after: int = 0):
    m = db.one("SELECT * FROM meetings WHERE id=?", (mid,))
    if not m:
        raise HTTPException(404)
    m["action_items"] = json.loads(m["action_items"]) if m.get("action_items") else []
    m["messages"] = db.q("SELECT * FROM meeting_messages WHERE meeting_id=? AND id>? ORDER BY id", (mid, after))
    return m


@app.post("/api/meetings/{mid}/say")
def say(mid: int, b: BossSay):
    meeting.boss_say(mid, b.text)
    return {"ok": True}
