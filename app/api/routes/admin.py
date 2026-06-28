import csv
import io
import secrets
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy import case, desc, distinct, func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.chat import Chat
from app.models.message import Message
from app.models.payment import Payment
from app.models.usage_daily import UsageDaily
from app.models.usage_monthly import UsageMonthly
from app.models.user import User
from app.schemas.admin import (
    DefaultPromptResponse,
    DefaultPromptUpdateRequest,
    PromptSuggestionsResponse,
    PromptSuggestionsUpdateRequest,
)
from app.services.prompt_settings_service import (
    get_default_prompt_setting,
    get_default_prompt_text,
    get_prompt_suggestions,
    get_prompt_suggestions_setting,
    upsert_default_prompt,
    upsert_prompt_suggestions,
)

router = APIRouter()
security = HTTPBasic()


ADMIN_PAGE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Garo2 Admin</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #0a1520;
      --panel: #102130;
      --panel-soft: #14293b;
      --border: rgba(183, 209, 223, 0.14);
      --text: #edf5f7;
      --muted: #90a9b7;
      --accent: #2eb59c;
      --danger: #ff7676;
      font-family: "Segoe UI", sans-serif;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      background:
        radial-gradient(circle at top left, rgba(46, 181, 156, 0.18), transparent 28%),
        linear-gradient(180deg, #09131d 0%, var(--bg) 100%);
      color: var(--text);
    }
    .shell {
      width: min(1180px, calc(100vw - 32px));
      margin: 0 auto;
      padding: 24px 0 40px;
    }
    .hero, .panel {
      border: 1px solid var(--border);
      background: rgba(16, 33, 48, 0.9);
      border-radius: 24px;
      backdrop-filter: blur(10px);
    }
    .hero {
      padding: 24px;
      margin-bottom: 18px;
      display: grid;
      gap: 8px;
    }
    .hero h1 {
      margin: 0;
      font-size: clamp(1.8rem, 4vw, 2.5rem);
    }
    .hero p, .note, .muted {
      margin: 0;
      color: var(--muted);
      line-height: 1.6;
    }
    .grid {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 14px;
      margin-bottom: 18px;
    }
    .card {
      padding: 18px;
      border-radius: 20px;
      background: var(--panel);
      border: 1px solid var(--border);
    }
    .card h2, .panel h2 {
      margin: 0 0 10px;
      font-size: 1rem;
    }
    .metric {
      font-size: 1.9rem;
      font-weight: 700;
      margin: 0 0 6px;
    }
    .two-col {
      display: grid;
      grid-template-columns: 1.4fr 1fr;
      gap: 18px;
      margin-bottom: 18px;
    }
    .panel {
      padding: 20px;
    }
    textarea {
      width: 100%;
      min-height: 190px;
      resize: vertical;
      border: 1px solid var(--border);
      border-radius: 18px;
      background: var(--panel-soft);
      color: var(--text);
      padding: 14px 16px;
      font: inherit;
      line-height: 1.6;
    }
    .prompt-suggestion-fields {
      display: grid;
      gap: 12px;
    }
    .prompt-suggestion-field {
      display: grid;
      gap: 8px;
    }
    .prompt-suggestion-field label {
      color: var(--muted);
      font-size: 0.9rem;
    }
    .prompt-suggestion-field textarea {
      min-height: 112px;
    }
    .actions, .csv-list {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      align-items: center;
    }
    button, .csv-link {
      border: 1px solid var(--border);
      border-radius: 999px;
      padding: 10px 14px;
      background: var(--panel-soft);
      color: var(--text);
      text-decoration: none;
      cursor: pointer;
      font: inherit;
    }
    button.primary {
      background: linear-gradient(135deg, var(--accent), #226d85);
      color: #07131c;
      font-weight: 700;
      border-color: transparent;
    }
    .status {
      min-height: 22px;
      color: var(--muted);
    }
    .status.error { color: var(--danger); }
    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.94rem;
    }
    th, td {
      text-align: left;
      padding: 10px 8px;
      border-bottom: 1px solid var(--border);
      vertical-align: top;
    }
    th { color: var(--muted); font-weight: 600; }
    .chart-list {
      display: grid;
      gap: 10px;
    }
    .chart-row {
      display: grid;
      grid-template-columns: 110px 1fr auto;
      gap: 12px;
      align-items: center;
    }
    .bar {
      height: 10px;
      border-radius: 999px;
      background: rgba(255,255,255,0.08);
      overflow: hidden;
    }
    .bar > span {
      display: block;
      height: 100%;
      border-radius: inherit;
      background: linear-gradient(90deg, var(--accent), #7ce2cf);
    }
    .table-wrap { overflow-x: auto; }
    @media (max-width: 980px) {
      .grid, .two-col { grid-template-columns: 1fr 1fr; }
    }
    @media (max-width: 720px) {
      .shell { width: min(100vw - 20px, 1180px); padding-top: 14px; }
      .grid, .two-col { grid-template-columns: 1fr; }
      .chart-row { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <div class="shell">
    <section class="hero">
      <h1>Garo2 Admin Dashboard</h1>
      <p>Manage the chatbot's default instruction prompt, monitor website activity, and export live backend data as CSV.</p>
      <p class="note">This page is served by the backend and reads directly from the production database tables.</p>
    </section>

    <section class="grid" id="overview-grid"></section>

    <section class="two-col">
      <div class="panel">
        <h2>Default Chat Prompt</h2>
        <p class="muted">Manage the built-in instruction used for founder and identity related chatbot answers.</p>
        <textarea id="prompt-input" placeholder="Loading default prompt..."></textarea>
        <div class="actions" style="margin-top: 14px;">
          <button class="primary" id="save-prompt">Save Prompt</button>
          <button id="reload-prompt">Reload</button>
        </div>
        <p class="status" id="prompt-status"></p>
      </div>

      <div class="panel">
        <h2>CSV Downloads</h2>
        <p class="muted">Export users, chats, messages, payments, and usage tables.</p>
        <div class="csv-list" id="csv-links"></div>
      </div>
    </section>

    <section class="two-col">
      <div class="panel">
        <h2>Plan Distribution</h2>
        <div class="chart-list" id="plan-chart"></div>
      </div>
      <div class="panel">
        <h2>Output Language Distribution</h2>
        <div class="chart-list" id="language-chart"></div>
      </div>
    </section>

    <section class="two-col">
      <div class="panel table-wrap">
        <h2>Recent Users</h2>
        <table>
          <thead><tr><th>Name</th><th>Email</th><th>Plan</th><th>Created</th></tr></thead>
          <tbody id="recent-users"></tbody>
        </table>
      </div>
      <div class="panel table-wrap">
        <h2>Recent Chats</h2>
        <table>
          <thead><tr><th>Title</th><th>User</th><th>Messages</th><th>Updated</th></tr></thead>
          <tbody id="recent-chats"></tbody>
        </table>
      </div>
    </section>

  </div>

  <script>
    const overviewGrid = document.getElementById("overview-grid");
    const promptInput = document.getElementById("prompt-input");
    const promptStatus = document.getElementById("prompt-status");
    const savePromptButton = document.getElementById("save-prompt");
    const reloadPromptButton = document.getElementById("reload-prompt");
    const planChart = document.getElementById("plan-chart");
    const languageChart = document.getElementById("language-chart");
    const recentUsers = document.getElementById("recent-users");
    const recentChats = document.getElementById("recent-chats");
    const csvLinks = document.getElementById("csv-links");

    const csvDatasets = [
      ["users", "Users"],
      ["chats", "Chats"],
      ["messages", "Messages"],
      ["payments", "Payments"],
      ["usage-daily", "Usage Daily"],
      ["usage-monthly", "Usage Monthly"],
    ];

    function escapeHtml(value) {
      return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
    }

    function formatDate(value) {
      if (!value) return "-";
      const date = new Date(value);
      if (Number.isNaN(date.getTime())) return value;
      return date.toLocaleString();
    }

    function renderMetricCard(label, value, note) {
      return `
        <article class="card">
          <h2>${escapeHtml(label)}</h2>
          <p class="metric">${escapeHtml(value)}</p>
          <p class="muted">${escapeHtml(note)}</p>
        </article>
      `;
    }

    function renderBarChart(target, items) {
      const max = Math.max(...items.map((item) => item.count), 1);
      target.innerHTML = items.map((item) => `
        <div class="chart-row">
          <strong>${escapeHtml(item.label)}</strong>
          <div class="bar"><span style="width:${(item.count / max) * 100}%"></span></div>
          <span>${escapeHtml(item.count)}</span>
        </div>
      `).join("") || `<p class="muted">No data yet.</p>`;
    }

    async function loadPrompt() {
      const response = await fetch("/api/admin/default-prompt");
      if (!response.ok) {
        throw new Error("Could not load the default prompt.");
      }
      const data = await response.json();
      promptInput.value = data.prompt || "";
      promptStatus.textContent = data.updated_at ? `Last updated: ${formatDate(data.updated_at)}` : "Using fallback default prompt.";
      promptStatus.className = "status";
    }

    async function savePrompt() {
      promptStatus.textContent = "Saving prompt...";
      promptStatus.className = "status";
      const response = await fetch("/api/admin/default-prompt", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: promptInput.value }),
      });
      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: "Could not save the prompt." }));
        throw new Error(error.detail || "Could not save the prompt.");
      }
      const data = await response.json();
      promptInput.value = data.prompt || "";
      promptStatus.textContent = `Prompt saved at ${formatDate(data.updated_at)}.`;
      promptStatus.className = "status";
    }

    async function loadDashboard() {
      const response = await fetch("/api/admin/dashboard");
      if (!response.ok) {
        throw new Error("Could not load dashboard data.");
      }
      const data = await response.json();

      overviewGrid.innerHTML = [
        renderMetricCard("Total Users", data.overview.total_users, "Registered accounts"),
        renderMetricCard("Total Chats", data.overview.total_chats, "Conversation threads"),
        renderMetricCard("Total Messages", data.overview.total_messages, "User + assistant messages"),
        renderMetricCard("Revenue (INR)", data.overview.total_revenue_inr, "Captured or successful payments"),
        renderMetricCard("Active Users", data.overview.active_users_last_7_days, "Users with recent messages"),
        renderMetricCard("User Messages", data.overview.user_messages_last_7_days, "Recent inbound prompts"),
        renderMetricCard("Translations Today", data.overview.translations_today, "From usage tracking"),
        renderMetricCard("New Users", data.overview.new_users_last_30_days, "Recent signups"),
      ].join("");

      renderBarChart(planChart, data.plan_breakdown);
      renderBarChart(languageChart, data.output_language_breakdown);

      recentUsers.innerHTML = data.recent_users.map((user) => `
        <tr>
          <td>${escapeHtml(user.name)}</td>
          <td>${escapeHtml(user.email)}</td>
          <td>${escapeHtml(user.plan)}</td>
          <td>${escapeHtml(formatDate(user.created_at))}</td>
        </tr>
      `).join("") || `<tr><td colspan="4" class="muted">No users yet.</td></tr>`;

      recentChats.innerHTML = data.recent_chats.map((chat) => `
        <tr>
          <td>${escapeHtml(chat.title)}</td>
          <td>${escapeHtml(chat.user_name)}</td>
          <td>${escapeHtml(chat.message_count)}</td>
          <td>${escapeHtml(formatDate(chat.updated_at))}</td>
        </tr>
      `).join("") || `<tr><td colspan="4" class="muted">No chats yet.</td></tr>`;

    }

    function renderCsvLinks() {
      csvLinks.innerHTML = csvDatasets.map(([key, label]) => `
        <a class="csv-link" href="/api/admin/exports/${key}" download>${escapeHtml(label)} CSV</a>
      `).join("");
    }

    async function boot() {
      renderCsvLinks();
      try {
        await Promise.all([loadPrompt(), loadDashboard()]);
      } catch (error) {
        promptStatus.textContent = error.message || "Could not load admin data.";
        promptStatus.className = "status error";
      }
    }

    savePromptButton.addEventListener("click", async () => {
      try {
        await savePrompt();
      } catch (error) {
        promptStatus.textContent = error.message || "Could not save the prompt.";
        promptStatus.className = "status error";
      }
    });

    reloadPromptButton.addEventListener("click", async () => {
      try {
        await loadPrompt();
      } catch (error) {
        promptStatus.textContent = error.message || "Could not reload the prompt.";
        promptStatus.className = "status error";
      }
    });

    boot();
  </script>
</body>
</html>
"""


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid admin credentials",
        headers={"WWW-Authenticate": "Basic"},
    )


def get_admin_credentials(credentials: HTTPBasicCredentials = Depends(security)) -> str:
    username_matches = secrets.compare_digest(credentials.username, settings.admin_username)
    password_matches = secrets.compare_digest(credentials.password, settings.admin_password)
    if not (username_matches and password_matches):
        raise _unauthorized()
    return credentials.username


def _to_iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(UTC).isoformat()


def _csv_response(filename: str, header: list[str], rows: list[list[object]]) -> StreamingResponse:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(header)
    writer.writerows(rows)
    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/admin", response_class=HTMLResponse, include_in_schema=False)
@router.get("/api/admin", response_class=HTMLResponse, include_in_schema=False)
def admin_page(_: str = Depends(get_admin_credentials)) -> HTMLResponse:
    return HTMLResponse(ADMIN_PAGE_HTML)


@router.get("/api/admin/default-prompt", response_model=DefaultPromptResponse, tags=["Admin"])
def get_default_prompt(
    _: str = Depends(get_admin_credentials),
    db: Session = Depends(get_db),
) -> DefaultPromptResponse:
    setting = get_default_prompt_setting(db)
    prompt = get_default_prompt_text(db)
    return DefaultPromptResponse(prompt=prompt, updated_at=_to_iso(setting.updated_at) if setting else None)


@router.put("/api/admin/default-prompt", response_model=DefaultPromptResponse, tags=["Admin"])
def update_default_prompt(
    payload: DefaultPromptUpdateRequest,
    _: str = Depends(get_admin_credentials),
    db: Session = Depends(get_db),
) -> DefaultPromptResponse:
    setting = upsert_default_prompt(db, payload.prompt)
    return DefaultPromptResponse(prompt=setting.value, updated_at=_to_iso(setting.updated_at))


@router.get("/api/admin/prompt-suggestions", response_model=PromptSuggestionsResponse, tags=["Admin"])
def get_admin_prompt_suggestions(
    _: str = Depends(get_admin_credentials),
    db: Session = Depends(get_db),
) -> PromptSuggestionsResponse:
    setting = get_prompt_suggestions_setting(db)
    return PromptSuggestionsResponse(
        prompts=get_prompt_suggestions(db),
        updated_at=_to_iso(setting.updated_at) if setting else None,
    )


@router.put("/api/admin/prompt-suggestions", response_model=PromptSuggestionsResponse, tags=["Admin"])
def update_admin_prompt_suggestions(
    payload: PromptSuggestionsUpdateRequest,
    _: str = Depends(get_admin_credentials),
    db: Session = Depends(get_db),
) -> PromptSuggestionsResponse:
    setting = upsert_prompt_suggestions(db, payload.prompts)
    return PromptSuggestionsResponse(
        prompts=get_prompt_suggestions(db),
        updated_at=_to_iso(setting.updated_at),
    )


@router.get("/api/admin/dashboard", tags=["Admin"])
def admin_dashboard(_: str = Depends(get_admin_credentials), db: Session = Depends(get_db)) -> dict:
    now = datetime.now(UTC)
    since_7_days = now - timedelta(days=7)
    since_30_days = now - timedelta(days=30)
    today = now.date()
    start_date = today - timedelta(days=13)

    total_users = db.query(func.count(User.id)).scalar() or 0
    total_chats = db.query(func.count(Chat.id)).scalar() or 0
    total_messages = db.query(func.count(Message.id)).scalar() or 0
    total_revenue_inr = (
        db.query(func.coalesce(func.sum(Payment.amount_inr), 0))
        .filter(Payment.status.in_(["captured", "paid", "active", "authenticated", "created"]))
        .scalar()
        or 0
    )
    active_users_last_7_days = (
        db.query(func.count(distinct(Chat.user_id)))
        .join(Message, Message.chat_id == Chat.id)
        .filter(Message.created_at >= since_7_days)
        .scalar()
        or 0
    )
    user_messages_last_7_days = (
        db.query(func.count(Message.id))
        .filter(Message.role == "user", Message.created_at >= since_7_days)
        .scalar()
        or 0
    )
    translations_today = (
        db.query(func.coalesce(func.sum(UsageDaily.translation_count), 0))
        .filter(UsageDaily.usage_date == today)
        .scalar()
        or 0
    )
    new_users_last_30_days = db.query(func.count(User.id)).filter(User.created_at >= since_30_days).scalar() or 0

    plan_rows = db.query(User.plan, func.count(User.id)).group_by(User.plan).order_by(func.count(User.id).desc()).all()
    language_rows = (
        db.query(Message.output_language, func.count(Message.id))
        .group_by(Message.output_language)
        .order_by(func.count(Message.id).desc())
        .all()
    )

    recent_users_rows = db.query(User).order_by(User.created_at.desc()).limit(8).all()
    recent_chats_rows = (
        db.query(
            Chat.id,
            Chat.title,
            User.name,
            Chat.updated_at,
            func.count(Message.id).label("message_count"),
        )
        .join(User, User.id == Chat.user_id)
        .outerjoin(Message, Message.chat_id == Chat.id)
        .group_by(Chat.id, Chat.title, User.name, Chat.updated_at)
        .order_by(Chat.updated_at.desc())
        .limit(8)
        .all()
    )

    user_message_case = case((Message.role == "user", 1), else_=0)
    assistant_message_case = case((Message.role == "assistant", 1), else_=0)
    daily_message_rows = (
        db.query(
            func.date(Message.created_at).label("day"),
            func.coalesce(func.sum(user_message_case), 0).label("user_messages"),
            func.coalesce(func.sum(assistant_message_case), 0).label("assistant_messages"),
        )
        .filter(Message.created_at >= datetime.combine(start_date, datetime.min.time(), tzinfo=UTC))
        .group_by(func.date(Message.created_at))
        .all()
    )
    daily_chat_rows = (
        db.query(func.date(Chat.created_at).label("day"), func.count(Chat.id).label("chats_created"))
        .filter(Chat.created_at >= datetime.combine(start_date, datetime.min.time(), tzinfo=UTC))
        .group_by(func.date(Chat.created_at))
        .all()
    )
    daily_new_user_rows = (
        db.query(func.date(User.created_at).label("day"), func.count(User.id).label("new_users"))
        .filter(User.created_at >= datetime.combine(start_date, datetime.min.time(), tzinfo=UTC))
        .group_by(func.date(User.created_at))
        .all()
    )
    daily_translation_rows = (
        db.query(UsageDaily.usage_date, func.coalesce(func.sum(UsageDaily.translation_count), 0).label("translations"))
        .filter(UsageDaily.usage_date >= start_date)
        .group_by(UsageDaily.usage_date)
        .all()
    )

    activity_map = {}
    for offset in range(14):
        current_day = start_date + timedelta(days=offset)
        activity_map[current_day.isoformat()] = {
            "date": current_day.isoformat(),
            "new_users": 0,
            "chats_created": 0,
            "user_messages": 0,
            "assistant_messages": 0,
            "translations": 0,
        }

    for day, count in daily_new_user_rows:
        key = str(day)
        if key in activity_map:
            activity_map[key]["new_users"] = int(count or 0)
    for day, count in daily_chat_rows:
        key = str(day)
        if key in activity_map:
            activity_map[key]["chats_created"] = int(count or 0)
    for day, user_count, assistant_count in daily_message_rows:
        key = str(day)
        if key in activity_map:
            activity_map[key]["user_messages"] = int(user_count or 0)
            activity_map[key]["assistant_messages"] = int(assistant_count or 0)
    for day, count in daily_translation_rows:
        key = str(day)
        if key in activity_map:
            activity_map[key]["translations"] = int(count or 0)

    return {
        "overview": {
            "total_users": int(total_users),
            "total_chats": int(total_chats),
            "total_messages": int(total_messages),
            "total_revenue_inr": int(total_revenue_inr),
            "active_users_last_7_days": int(active_users_last_7_days),
            "user_messages_last_7_days": int(user_messages_last_7_days),
            "translations_today": int(translations_today),
            "new_users_last_30_days": int(new_users_last_30_days),
        },
        "plan_breakdown": [{"label": plan or "unknown", "count": int(count)} for plan, count in plan_rows],
        "output_language_breakdown": [{"label": language or "unknown", "count": int(count)} for language, count in language_rows],
        "recent_users": [
            {
                "name": user.name,
                "email": user.email,
                "plan": user.plan,
                "created_at": _to_iso(user.created_at),
            }
            for user in recent_users_rows
        ],
        "recent_chats": [
            {
                "id": chat_id,
                "title": title,
                "user_name": user_name,
                "message_count": int(message_count or 0),
                "updated_at": _to_iso(updated_at),
            }
            for chat_id, title, user_name, updated_at, message_count in recent_chats_rows
        ],
        "daily_activity": [activity_map[key] for key in sorted(activity_map.keys())],
    }


@router.get("/api/admin/exports/{dataset}", tags=["Admin"])
def export_dataset(dataset: str, _: str = Depends(get_admin_credentials), db: Session = Depends(get_db)) -> StreamingResponse:
    if dataset == "users":
        rows = (
            db.query(User.id, User.name, User.email, User.plan, User.subscription_status, User.created_at)
            .order_by(User.created_at.desc())
            .all()
        )
        return _csv_response(
            "garo2-users.csv",
            ["id", "name", "email", "plan", "subscription_status", "created_at"],
            [[user_id, name, email, plan, status_value, _to_iso(created_at)] for user_id, name, email, plan, status_value, created_at in rows],
        )

    if dataset == "chats":
        rows = (
            db.query(Chat.id, Chat.title, Chat.user_id, User.name, Chat.created_at, Chat.updated_at)
            .join(User, User.id == Chat.user_id)
            .order_by(Chat.updated_at.desc())
            .all()
        )
        return _csv_response(
            "garo2-chats.csv",
            ["id", "title", "user_id", "user_name", "created_at", "updated_at"],
            [[chat_id, title, user_id, user_name, _to_iso(created_at), _to_iso(updated_at)] for chat_id, title, user_id, user_name, created_at, updated_at in rows],
        )

    if dataset == "messages":
        rows = (
            db.query(
                Message.id,
                Message.chat_id,
                Chat.user_id,
                User.name,
                Message.role,
                Message.input_language,
                Message.output_language,
                Message.image_url,
                Message.content,
                Message.created_at,
            )
            .join(Chat, Chat.id == Message.chat_id)
            .join(User, User.id == Chat.user_id)
            .order_by(Message.created_at.desc())
            .all()
        )
        return _csv_response(
            "garo2-messages.csv",
            ["id", "chat_id", "user_id", "user_name", "role", "input_language", "output_language", "image_url", "content", "created_at"],
            [
                [message_id, chat_id, user_id, user_name, role, input_language, output_language, image_url or "", content, _to_iso(created_at)]
                for message_id, chat_id, user_id, user_name, role, input_language, output_language, image_url, content, created_at in rows
            ],
        )

    if dataset == "payments":
        rows = (
            db.query(
                Payment.id,
                Payment.user_id,
                User.name,
                User.email,
                Payment.plan,
                Payment.amount_inr,
                Payment.provider,
                Payment.status,
                Payment.razorpay_payment_id,
                Payment.razorpay_subscription_id,
                Payment.created_at,
            )
            .join(User, User.id == Payment.user_id)
            .order_by(Payment.created_at.desc())
            .all()
        )
        return _csv_response(
            "garo2-payments.csv",
            ["id", "user_id", "user_name", "email", "plan", "amount_inr", "provider", "status", "razorpay_payment_id", "razorpay_subscription_id", "created_at"],
            [
                [payment_id, user_id, user_name, email, plan, amount_inr, provider, payment_status, payment_ref or "", subscription_ref or "", _to_iso(created_at)]
                for payment_id, user_id, user_name, email, plan, amount_inr, provider, payment_status, payment_ref, subscription_ref, created_at in rows
            ],
        )

    if dataset == "usage-daily":
        rows = (
            db.query(
                UsageDaily.id,
                UsageDaily.user_id,
                User.name,
                User.email,
                UsageDaily.usage_date,
                UsageDaily.chat_count,
                UsageDaily.translation_count,
                UsageDaily.image_upload_count,
            )
            .join(User, User.id == UsageDaily.user_id)
            .order_by(desc(UsageDaily.usage_date))
            .all()
        )
        return _csv_response(
            "garo2-usage-daily.csv",
            ["id", "user_id", "user_name", "email", "usage_date", "chat_count", "translation_count", "image_upload_count"],
            [[row_id, user_id, user_name, email, str(usage_date), chat_count, translation_count, image_upload_count] for row_id, user_id, user_name, email, usage_date, chat_count, translation_count, image_upload_count in rows],
        )

    if dataset == "usage-monthly":
        rows = (
            db.query(
                UsageMonthly.id,
                UsageMonthly.user_id,
                User.name,
                User.email,
                UsageMonthly.usage_month,
                UsageMonthly.image_generation_count,
            )
            .join(User, User.id == UsageMonthly.user_id)
            .order_by(desc(UsageMonthly.usage_month))
            .all()
        )
        return _csv_response(
            "garo2-usage-monthly.csv",
            ["id", "user_id", "user_name", "email", "usage_month", "image_generation_count"],
            [[row_id, user_id, user_name, email, usage_month, image_generation_count] for row_id, user_id, user_name, email, usage_month, image_generation_count in rows],
        )

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown export dataset")
