from datetime import datetime, date, time
from typing import List, Optional
import os
import time as time_module
import requests
from jose import jwt
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, validator
from dotenv import load_dotenv

load_dotenv()

API_BASE = os.getenv("LW_API_BASE")
CLIENT_ID = os.getenv("LW_CLIENT_ID")
CLIENT_SECRET = os.getenv("LW_CLIENT_SECRET")
SERVICE_ACCOUNT = os.getenv("LW_SERVICE_ACCOUNT")
PRIVATE_KEY_PATH = os.getenv("LW_PRIVATE_KEY_PATH")
CALENDAR_ID = os.getenv("LW_CALENDAR_ID")

app = FastAPI(title="Meeting Room Reservation API")


# ---------- ISO8601 パーサー（Python 3.6 用） ----------
def parse_iso8601(dt_str: str) -> datetime:
    # "2024-06-05T10:00:00+09:00" → Python 3.6 では fromisoformat が使えない
    try:
        if dt_str.endswith("Z"):
            dt_str = dt_str.replace("Z", "+00:00")
        return datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%S%z")
    except:
        # ミリ秒付き
        try:
            if "." in dt_str:
                base, ms = dt_str.split(".")
                ms = ms.rstrip("Z")
                if "+" in ms:
                    ms, tz = ms.split("+")
                    dt_str = base + "+" + tz
                return datetime.strptime(base, "%Y-%m-%dT%H:%M:%S")
        except:
            raise ValueError("Invalid datetime format: " + dt_str)


# ---------- モデル ----------

class AvailabilityItem(BaseModel):
    start: str
    end: str


class ReserveRequest(BaseModel):
    date: date
    start_time: str
    end_time: str
    title: str = "会議室予約"
    requester_name: Optional[str] = None
    requester_id: Optional[str] = None

    @validator("start_time", "end_time")
    def validate_time_format(cls, v: str) -> str:
        datetime.strptime(v, "%H:%M")
        return v

    @validator("end_time")
    def validate_time_order(cls, v: str, values):
        if "start_time" in values:
            st = datetime.strptime(values["start_time"], "%H:%M").time()
            et = datetime.strptime(v, "%H:%M").time()
            if et <= st:
                raise ValueError("end_time must be after start_time")
        return v


class EditRequest(BaseModel):
    event_id: str
    date: date
    start_time: str
    end_time: str
    title: str = "会議室予約"

    @validator("start_time", "end_time")
    def validate_time_format(cls, v: str) -> str:
        datetime.strptime(v, "%H:%M")
        return v


# ---------- アクセストークン取得 ----------

def get_access_token() -> str:
    with open(PRIVATE_KEY_PATH, "r") as f:
        private_key = f.read()

    now = int(time_module.time())
    payload = {
        "iss": CLIENT_ID,
        "sub": SERVICE_ACCOUNT,
        "iat": now,
        "exp": now + 3600,
    }

    assertion = jwt.encode(payload, private_key, algorithm="RS256")

    url = f"{API_BASE}/oauth2/v2.0/token"
    data = {
        "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
        "assertion": assertion,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "scope": "calendar"
    }

    resp = requests.post(url, data=data)
    if resp.status_code != 200:
        raise HTTPException(status_code=500, detail="Token error: " + resp.text)

    return resp.json()["access_token"]


# ---------- カレンダーから予定取得 ----------

def fetch_events_for_date(target_date: date) -> List[dict]:
    access_token = get_access_token()

    start_dt = datetime.combine(target_date, time(0, 0))
    end_dt = datetime.combine(target_date, time(23, 59))

    url = f"{API_BASE}/calendar/v1/calendars/{CALENDAR_ID}/events"
    params = {
        "start": start_dt.isoformat(),
        "end": end_dt.isoformat(),
    }
    headers = {"Authorization": "Bearer " + access_token}

    resp = requests.get(url, headers=headers, params=params)

    if resp.status_code != 200:
        raise HTTPException(status_code=500, detail="Fetch error: " + resp.text)

    return resp.json().get("events", [])


# ---------- 予約済み時間帯を整形 ----------

def to_time_str(dt_str: str) -> str:
    dt = parse_iso8601(dt_str)
    return dt.strftime("%H:%M")


def build_busy_slots(events: List[dict]) -> List[AvailabilityItem]:
    busy = []
    for ev in events:
        start_str = to_time_str(ev["start"]["dateTime"])
        end_str = to_time_str(ev["end"]["dateTime"])
        busy.append(AvailabilityItem(start=start_str, end=end_str))
    return busy


# ---------- 30分単位チェック ----------

def is_30min_unit(t: time) -> bool:
    return t.minute in (0, 30)


def check_30min_unit(start: time, end: time):
    if not is_30min_unit(start) or not is_30min_unit(end):
        raise HTTPException(status_code=400, detail="Time must be 30-minute units")


# ---------- 重複チェック ----------

def check_overlap(start: time, end: time, busy_slots: List[AvailabilityItem]):
    for slot in busy_slots:
        bs = datetime.strptime(slot.start, "%H:%M").time()
        be = datetime.strptime(slot.end, "%H:%M").time()
        if not (end <= bs or be <= start):
            raise HTTPException(status_code=400, detail="Time slot already reserved")


# ---------- 予約作成 ----------

def create_event(req: ReserveRequest):
    access_token = get_access_token()

    start_dt = datetime.combine(req.date, datetime.strptime(req.start_time, "%H:%M").time())
    end_dt = datetime.combine(req.date, datetime.strptime(req.end_time, "%H:%M").time())

    url = f"{API_BASE}/calendar/v1/calendars/{CALENDAR_ID}/events"
    headers = {
        "Authorization": "Bearer " + access_token,
        "Content-Type": "application/json",
    }
    body = {
        "summary": req.title,
        "start": {"dateTime": start_dt.isoformat()},
        "end": {"dateTime": end_dt.isoformat()},
        "description": "Requester: {} ({})".format(req.requester_name or "", req.requester_id or ""),
    }

    resp = requests.post(url, headers=headers, json=body)

    if resp.status_code not in (200, 201):
        raise HTTPException(status_code=500, detail="Create error: " + resp.text)

    return resp.json()


# ---------- 予約編集 ----------

@app.put("/edit")
def edit_event(req: EditRequest):
    access_token = get_access_token()

    start_dt = datetime.combine(req.date, datetime.strptime(req.start_time, "%H:%M").time())
    end_dt = datetime.combine(req.date, datetime.strptime(req.end_time, "%H:%M").time())

    url = f"{API_BASE}/calendar/v1/calendars/{CALENDAR_ID}/events/{req.event_id}"
    headers = {
        "Authorization": "Bearer " + access_token,
        "Content-Type": "application/json",
    }

    body = {
        "summary": req.title,
        "start": {"dateTime": start_dt.isoformat()},
        "end": {"dateTime": end_dt.isoformat()},
    }

    resp = requests.put(url, headers=headers, json=body)

    if resp.status_code not in (200, 201):
        raise HTTPException(status_code=500, detail="Edit error: " + resp.text)

    return {"status": "ok", "event_id": req.event_id}


# ---------- 予約キャンセル ----------

@app.delete("/cancel")
def cancel(event_id: str):
    access_token = get_access_token()

    url = f"{API_BASE}/calendar/v1/calendars/{CALENDAR_ID}/events/{event_id}"
    headers = {"Authorization": "Bearer " + access_token}

    resp = requests.delete(url, headers=headers)

    if resp.status_code not in (200, 204):
        raise HTTPException(status_code=500, detail="Cancel error: " + resp.text)

    return {"status": "ok", "event_id": event_id}


# ---------- 自分の予約一覧 ----------

@app.get("/my_reservations")
def my_reservations(user_id: str, target_date: date):
    events = fetch_events_for_date(target_date)
    my_events = []

    for ev in events:
        desc = ev.get("description", "")
        if user_id in desc:
            my_events.append({
                "event_id": ev["id"],
                "summary": ev.get("summary", ""),
                "start": ev["start"]["dateTime"],
                "end": ev["end"]["dateTime"],
            })

    return my_events


# ---------- 空き状況 ----------

@app.get("/availability")
def get_availability(target_date: date):
    events = fetch_events_for_date(target_date)
    return build_busy_slots(events)


# ---------- 予約 ----------

@app.post("/reserve")
def reserve(req: ReserveRequest):
    start_t = datetime.strptime(req.start_time, "%H:%M").time()
    end_t = datetime.strptime(req.end_time, "%H:%M").time()

    check_30min_unit(start_t, end_t)

    events = fetch_events_for_date(req.date)
    busy_slots = build_busy_slots(events)

    check_overlap(start_t, end_t, busy_slots)

    created = create_event(req)
    return {"status": "ok", "event": created}
