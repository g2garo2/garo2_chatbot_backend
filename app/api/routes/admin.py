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
from app.models.account_deletion_request import AccountDeletionRequest
from app.models.chat import Chat
from app.models.feedback_request import FeedbackRequest
from app.models.message import Message
from app.models.payment import Payment
from app.models.usage_daily import UsageDaily
from app.models.usage_monthly import UsageMonthly
from app.models.user import User
from app.schemas.account_deletion import AccountDeletionRequestResponse
from app.schemas.admin import DefaultPromptResponse, DefaultPromptUpdateRequest, PromptSuggestionsResponse, PromptSuggestionsUpdateRequest
from app.schemas.feedback import FeedbackRequestResponse
from app.schemas.plan import SubscriptionPlanCreateRequest, SubscriptionPlanResponse, SubscriptionPlanUpdateRequest
from app.services.plan_service import create_admin_plan, deactivate_admin_plan, list_admin_plans, update_admin_plan
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
      width: min(1240px, calc(100vw - 32px));
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
    .hero-nav, .actions, .csv-list, .section-head, .table-actions, .checkbox-row {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      align-items: center;
    }
    .section-head {
      justify-content: space-between;
      margin-bottom: 12px;
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
      margin-bottom: 18px;
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
    .prompt-suggestion-field, .field {
      display: grid;
      gap: 8px;
    }
    .prompt-suggestion-field label, .field label {
      color: var(--muted);
      font-size: 0.9rem;
    }
    .prompt-suggestion-field textarea {
      min-height: 112px;
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
    .pill {
      display: inline-flex;
      align-items: center;
      border-radius: 999px;
      padding: 5px 10px;
      font-size: 0.82rem;
      border: 1px solid var(--border);
      background: rgba(255,255,255,0.04);
    }
    .pill.yes {
      color: #9cf4d0;
      border-color: rgba(156, 244, 208, 0.28);
    }
    .pill.no {
      color: var(--muted);
    }
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
    .plan-modal-backdrop[hidden] { display: none; }
    .plan-modal-backdrop {
      position: fixed;
      inset: 0;
      background: rgba(4, 12, 18, 0.72);
      display: grid;
      place-items: center;
      padding: 18px;
    }
    .plan-modal {
      width: min(860px, 100%);
      border: 1px solid var(--border);
      border-radius: 24px;
      background: var(--panel);
      padding: 20px;
      box-shadow: 0 30px 80px rgba(0, 0, 0, 0.35);
    }
    .field-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
    }
    .field.full {
      grid-column: 1 / -1;
    }
    .field input {
      width: 100%;
      border: 1px solid var(--border);
      border-radius: 14px;
      background: var(--panel-soft);
      color: var(--text);
      padding: 12px 14px;
      font: inherit;
    }
    @media (max-width: 980px) {
      .grid, .two-col, .field-grid { grid-template-columns: 1fr 1fr; }
    }
    @media (max-width: 720px) {
      .shell { width: min(100vw - 20px, 1240px); padding-top: 14px; }
      .grid, .two-col, .field-grid { grid-template-columns: 1fr; }
      .chart-row { grid-template-columns: 1fr; }
      .section-head { align-items: flex-start; }
    }
  </style>
</head>
<body>
  <div class="shell">
    <section class="hero">
      <h1>Garo2 Admin Dashboard</h1>
      <p>Manage pricing, Meghalaya starter suggestions, monitor website activity, and export live backend data.</p>
      <p class="note">This page is served by the backend and reads directly from the production database tables.</p>
      <div class="hero-nav">
        <a class="csv-link" href="/admin/subscription-plans">Subscription Plans</a>
        <a class="csv-link" href="/admin/prompt-suggestions">Prompt Suggestions</a>
      </div>
    </section>

    <section class="grid" id="overview-grid"></section>

    <section class="panel" id="subscription-plans">
      <div class="section-head">
        <div>
          <h2 style="margin-bottom: 6px;">Subscription Plans</h2>
          <p class="muted">These plans power the public pricing page and can be updated any time.</p>
        </div>
        <div class="table-actions">
          <button class="primary" id="add-plan">Add Plan</button>
          <button id="reload-plans">Reload Plans</button>
        </div>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Plan name</th>
              <th>Price</th>
              <th>Billing cycle</th>
              <th>Chat/day</th>
              <th>Translation/day</th>
              <th>AI provider</th>
              <th>Button text</th>
              <th>Active</th>
              <th>Popular</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody id="subscription-plans-body"></tbody>
        </table>
      </div>
      <p class="status" id="plans-status"></p>
    </section>

    <section class="two-col">
      <div class="panel" id="prompt-manager" style="margin-bottom: 0;">
        <h2>Suggested Chat Prompts</h2>
        <p class="muted">Manage the Meghalaya starter prompts shown above the chat input on small devices.</p>
        <div id="prompt-suggestion-fields" class="prompt-suggestion-fields"></div>
        <div class="actions" style="margin-top: 14px;">
          <button class="primary" id="save-prompt">Save Prompts</button>
          <button id="reload-prompt">Reload</button>
        </div>
        <p class="status" id="prompt-status"></p>
      </div>

      <div class="panel" style="margin-bottom: 0;">
        <h2>CSV Downloads</h2>
        <p class="muted">Export users, chats, messages, payments, and usage tables.</p>
        <div class="csv-list" id="csv-links"></div>
      </div>
    </section>

    <section class="two-col">
      <div class="panel" style="margin-bottom: 0;">
        <h2>Plan Distribution</h2>
        <div class="chart-list" id="plan-chart"></div>
      </div>
      <div class="panel" style="margin-bottom: 0;">
        <h2>Output Language Distribution</h2>
        <div class="chart-list" id="language-chart"></div>
      </div>
    </section>

    <section class="two-col">
      <div class="panel table-wrap" style="margin-bottom: 0;">
        <h2>Recent Users</h2>
        <table>
          <thead><tr><th>Name</th><th>Email</th><th>Plan</th><th>Created</th></tr></thead>
          <tbody id="recent-users"></tbody>
        </table>
      </div>
      <div class="panel table-wrap" style="margin-bottom: 0;">
        <h2>Recent Chats</h2>
        <table>
          <thead><tr><th>Title</th><th>User</th><th>Messages</th><th>Updated</th></tr></thead>
          <tbody id="recent-chats"></tbody>
        </table>
      </div>
    </section>

    <section class="panel" id="account-deletion-requests">
      <div class="section-head">
        <div>
          <h2 style="margin-bottom: 6px;">Account Deletion Requests</h2>
          <p class="muted">Review user deletion submissions and remove them after handling the request.</p>
        </div>
        <div class="table-actions">
          <button id="reload-deletion-requests">Reload Requests</button>
        </div>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Email</th>
              <th>Reason</th>
              <th>Date</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody id="account-deletion-requests-body"></tbody>
        </table>
      </div>
      <p class="status" id="account-deletion-requests-status"></p>
    </section>

    <section class="panel" id="feedback-requests">
      <div class="section-head">
        <div>
          <h2 style="margin-bottom: 6px;">Feedback Requests</h2>
          <p class="muted">Review product feedback, suggestions, and bug reports sent from the app settings page.</p>
        </div>
        <div class="table-actions">
          <button id="reload-feedback-requests">Reload Feedback</button>
        </div>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Email</th>
              <th>Type</th>
              <th>Message</th>
              <th>Date</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody id="feedback-requests-body"></tbody>
        </table>
      </div>
      <p class="status" id="feedback-requests-status"></p>
    </section>
  </div>

  <div class="plan-modal-backdrop" id="plan-modal-backdrop" hidden>
    <div class="plan-modal">
      <div class="section-head">
        <div>
          <h2 id="plan-modal-title" style="margin-bottom: 6px;">Edit Plan</h2>
          <p class="muted">Update pricing, limits, copy, active status, and display order.</p>
        </div>
        <button id="close-plan-modal" type="button">Close</button>
      </div>
      <form id="plan-form">
        <div class="field-grid">
          <div class="field">
            <label for="plan-key">Plan key</label>
            <input id="plan-key" type="text" placeholder="plus" required />
          </div>
          <div class="field">
            <label for="plan-name">Plan name</label>
            <input id="plan-name" type="text" placeholder="Plus" required />
          </div>
          <div class="field">
            <label for="plan-price">Price (INR)</label>
            <input id="plan-price" type="number" min="0" required />
          </div>
          <div class="field">
            <label for="plan-billing-cycle">Billing cycle</label>
            <input id="plan-billing-cycle" type="text" placeholder="month" required />
          </div>
          <div class="field">
            <label for="plan-chat-limit">Chat/day</label>
            <input id="plan-chat-limit" type="number" min="0" placeholder="Leave empty for unlimited" />
          </div>
          <div class="field">
            <label for="plan-translation-limit">Translation/day</label>
            <input id="plan-translation-limit" type="number" min="0" required />
          </div>
          <div class="field full">
            <label for="plan-ai-provider">AI provider text</label>
            <textarea id="plan-ai-provider" required></textarea>
          </div>
          <div class="field full">
            <label for="plan-button-text">Button text</label>
            <input id="plan-button-text" type="text" placeholder="Pay for Plus" required />
          </div>
          <div class="field">
            <label for="plan-sort-order">Sort order</label>
            <input id="plan-sort-order" type="number" required />
          </div>
          <div class="field full checkbox-row">
            <label><input id="plan-is-active" type="checkbox" checked /> Active</label>
            <label><input id="plan-is-popular" type="checkbox" /> Popular</label>
          </div>
        </div>
        <div class="actions" style="margin-top: 16px;">
          <button class="primary" type="submit">Save Plan</button>
          <button id="cancel-plan" type="button">Cancel</button>
        </div>
      </form>
    </div>
  </div>

  <script>
    const overviewGrid = document.getElementById("overview-grid");
    const promptSuggestionFields = document.getElementById("prompt-suggestion-fields");
    const promptStatus = document.getElementById("prompt-status");
    const savePromptButton = document.getElementById("save-prompt");
    const reloadPromptButton = document.getElementById("reload-prompt");
    const planChart = document.getElementById("plan-chart");
    const languageChart = document.getElementById("language-chart");
    const recentUsers = document.getElementById("recent-users");
    const recentChats = document.getElementById("recent-chats");
    const csvLinks = document.getElementById("csv-links");
    const subscriptionPlansBody = document.getElementById("subscription-plans-body");
    const plansStatus = document.getElementById("plans-status");
    const deletionRequestsBody = document.getElementById("account-deletion-requests-body");
    const deletionRequestsStatus = document.getElementById("account-deletion-requests-status");
    const feedbackRequestsBody = document.getElementById("feedback-requests-body");
    const feedbackRequestsStatus = document.getElementById("feedback-requests-status");
    const addPlanButton = document.getElementById("add-plan");
    const reloadDeletionRequestsButton = document.getElementById("reload-deletion-requests");
    const reloadFeedbackRequestsButton = document.getElementById("reload-feedback-requests");
    const reloadPlansButton = document.getElementById("reload-plans");
    const planModalBackdrop = document.getElementById("plan-modal-backdrop");
    const closePlanModalButton = document.getElementById("close-plan-modal");
    const cancelPlanButton = document.getElementById("cancel-plan");
    const planModalTitle = document.getElementById("plan-modal-title");
    const planForm = document.getElementById("plan-form");
    const planKeyField = document.getElementById("plan-key");
    const planNameField = document.getElementById("plan-name");
    const planPriceField = document.getElementById("plan-price");
    const planBillingCycleField = document.getElementById("plan-billing-cycle");
    const planChatLimitField = document.getElementById("plan-chat-limit");
    const planTranslationLimitField = document.getElementById("plan-translation-limit");
    const planAiProviderField = document.getElementById("plan-ai-provider");
    const planButtonTextField = document.getElementById("plan-button-text");
    const planSortOrderField = document.getElementById("plan-sort-order");
    const planIsActiveField = document.getElementById("plan-is-active");
    const planIsPopularField = document.getElementById("plan-is-popular");

    const csvDatasets = [
      ["users", "Users"],
      ["chats", "Chats"],
      ["messages", "Messages"],
      ["payments", "Payments"],
      ["usage-daily", "Usage Daily"],
      ["usage-monthly", "Usage Monthly"],
    ];

    let editingPlanId = null;

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

    function formatPlanPrice(plan) {
      const suffix = plan.price > 0 && plan.billing_cycle && plan.billing_cycle !== "free" ? `/${plan.billing_cycle}` : "";
      return `Rs ${plan.price}${suffix}`;
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

    function renderPromptFields(prompts) {
      promptSuggestionFields.innerHTML = prompts.map((prompt, index) => `
        <div class="prompt-suggestion-field">
          <label for="prompt-suggestion-${index}">Prompt ${index + 1}</label>
          <textarea id="prompt-suggestion-${index}" data-prompt-index="${index}">${escapeHtml(prompt)}</textarea>
        </div>
      `).join("");
    }

    function readPromptFields() {
      return Array.from(promptSuggestionFields.querySelectorAll("textarea"))
        .map((field) => field.value.trim())
        .filter(Boolean);
    }

    function renderFlag(value) {
      return `<span class="pill ${value ? "yes" : "no"}">${value ? "Yes" : "No"}</span>`;
    }

    function renderDeletionRequests(requests) {
      deletionRequestsBody.innerHTML = requests.map((request) => `
        <tr>
          <td>${escapeHtml(request.name)}</td>
          <td>${escapeHtml(request.email)}</td>
          <td>${escapeHtml(request.reason)}</td>
          <td>${escapeHtml(formatDate(request.created_at))}</td>
          <td class="table-actions">
            <button type="button" data-delete-deletion-request="${request.id}">Remove</button>
          </td>
        </tr>
      `).join("") || `<tr><td colspan="5" class="muted">No account deletion requests yet.</td></tr>`;

      deletionRequestsBody.querySelectorAll("[data-delete-deletion-request]").forEach((button) => {
        button.addEventListener("click", async () => {
          const requestId = Number(button.dataset.deleteDeletionRequest);
          if (!window.confirm("Remove this deletion request from the admin list?")) {
            return;
          }
          deletionRequestsStatus.textContent = "Removing request...";
          deletionRequestsStatus.className = "status";
          try {
            const response = await fetch(`/api/admin/account-deletion-requests/${requestId}`, { method: "DELETE" });
            if (!response.ok) {
              const error = await response.json().catch(() => ({ detail: "Could not remove the request." }));
              throw new Error(error.detail || "Could not remove the request.");
            }
            await loadDeletionRequests();
            deletionRequestsStatus.textContent = "Request removed successfully.";
            deletionRequestsStatus.className = "status";
          } catch (error) {
            deletionRequestsStatus.textContent = error.message || "Could not remove the request.";
            deletionRequestsStatus.className = "status error";
          }
        });
      });
    }

    function renderFeedbackRequests(requests) {
      feedbackRequestsBody.innerHTML = requests.map((request) => `
        <tr>
          <td>${escapeHtml(request.name)}</td>
          <td>${escapeHtml(request.email)}</td>
          <td>${escapeHtml(request.feedback_type)}</td>
          <td>${escapeHtml(request.message)}</td>
          <td>${escapeHtml(formatDate(request.created_at))}</td>
          <td class="table-actions">
            <button type="button" data-delete-feedback-request="${request.id}">Remove</button>
          </td>
        </tr>
      `).join("") || `<tr><td colspan="6" class="muted">No feedback requests yet.</td></tr>`;

      feedbackRequestsBody.querySelectorAll("[data-delete-feedback-request]").forEach((button) => {
        button.addEventListener("click", async () => {
          const requestId = Number(button.dataset.deleteFeedbackRequest);
          if (!window.confirm("Remove this feedback request from the admin list?")) {
            return;
          }
          feedbackRequestsStatus.textContent = "Removing feedback...";
          feedbackRequestsStatus.className = "status";
          try {
            const response = await fetch(`/api/admin/feedback-requests/${requestId}`, { method: "DELETE" });
            if (!response.ok) {
              const error = await response.json().catch(() => ({ detail: "Could not remove the feedback request." }));
              throw new Error(error.detail || "Could not remove the feedback request.");
            }
            await loadFeedbackRequests();
            feedbackRequestsStatus.textContent = "Feedback removed successfully.";
            feedbackRequestsStatus.className = "status";
          } catch (error) {
            feedbackRequestsStatus.textContent = error.message || "Could not remove the feedback request.";
            feedbackRequestsStatus.className = "status error";
          }
        });
      });
    }

    function openPlanModal(plan = null) {
      editingPlanId = plan?.id ?? null;
      planModalTitle.textContent = plan ? "Edit Plan" : "Add Plan";
      planKeyField.value = plan?.plan_key ?? "";
      planKeyField.disabled = Boolean(plan);
      planNameField.value = plan?.name ?? "";
      planPriceField.value = plan?.price ?? 0;
      planBillingCycleField.value = plan?.billing_cycle ?? "month";
      planChatLimitField.value = plan?.chat_limit ?? "";
      planTranslationLimitField.value = plan?.translation_limit ?? 0;
      planAiProviderField.value = plan?.ai_provider ?? "";
      planButtonTextField.value = plan?.button_text ?? "";
      planSortOrderField.value = plan?.sort_order ?? 0;
      planIsActiveField.checked = plan ? Boolean(plan.is_active) : true;
      planIsPopularField.checked = plan ? Boolean(plan.is_popular) : false;
      planModalBackdrop.hidden = false;
    }

    function closePlanModal() {
      editingPlanId = null;
      planForm.reset();
      planKeyField.disabled = false;
      planModalBackdrop.hidden = true;
    }

    function readPlanForm() {
      const chatLimitValue = planChatLimitField.value.trim();
      return {
        plan_key: planKeyField.value.trim().toLowerCase(),
        name: planNameField.value.trim(),
        price: Number(planPriceField.value),
        billing_cycle: planBillingCycleField.value.trim(),
        chat_limit: chatLimitValue === "" ? null : Number(chatLimitValue),
        translation_limit: Number(planTranslationLimitField.value),
        ai_provider: planAiProviderField.value.trim(),
        button_text: planButtonTextField.value.trim(),
        is_active: planIsActiveField.checked,
        is_popular: planIsPopularField.checked,
        sort_order: Number(planSortOrderField.value),
      };
    }

    function renderPlans(plans) {
      subscriptionPlansBody.innerHTML = plans.map((plan) => `
        <tr>
          <td>${escapeHtml(plan.name)}</td>
          <td>${escapeHtml(formatPlanPrice(plan))}</td>
          <td>${escapeHtml(plan.billing_cycle)}</td>
          <td>${escapeHtml(plan.chat_limit == null ? "Unlimited with safe backend rate limit" : `${plan.chat_limit}/day`)}</td>
          <td>${escapeHtml(`${plan.translation_limit}/day`)}</td>
          <td>${escapeHtml(plan.ai_provider)}</td>
          <td>${escapeHtml(plan.button_text)}</td>
          <td>${renderFlag(Boolean(plan.is_active))}</td>
          <td>${renderFlag(Boolean(plan.is_popular))}</td>
          <td class="table-actions">
            <button type="button" data-edit-plan="${plan.id}">Edit</button>
            <button type="button" data-delete-plan="${plan.id}">Delete</button>
          </td>
        </tr>
      `).join("") || `<tr><td colspan="10" class="muted">No plans found.</td></tr>`;

      subscriptionPlansBody.querySelectorAll("[data-edit-plan]").forEach((button) => {
        button.addEventListener("click", () => {
          const plan = plans.find((entry) => entry.id === Number(button.dataset.editPlan));
          if (plan) {
            openPlanModal(plan);
          }
        });
      });

      subscriptionPlansBody.querySelectorAll("[data-delete-plan]").forEach((button) => {
        button.addEventListener("click", async () => {
          const planId = Number(button.dataset.deletePlan);
          if (!window.confirm("Delete will set this plan inactive on the pricing page. Continue?")) {
            return;
          }
          plansStatus.textContent = "Updating plan status...";
          plansStatus.className = "status";
          try {
            const response = await fetch(`/api/admin/plans/${planId}`, { method: "DELETE" });
            if (!response.ok) {
              const error = await response.json().catch(() => ({ detail: "Could not delete the plan." }));
              throw new Error(error.detail || "Could not delete the plan.");
            }
            await Promise.all([loadPlans(), loadDashboard()]);
            plansStatus.textContent = "Plan updated successfully.";
            plansStatus.className = "status";
          } catch (error) {
            plansStatus.textContent = error.message || "Could not delete the plan.";
            plansStatus.className = "status error";
          }
        });
      });
    }

    async function loadPrompt() {
      const response = await fetch("/api/admin/prompt-suggestions");
      if (!response.ok) {
        throw new Error("Could not load the suggested prompts.");
      }
      const data = await response.json();
      renderPromptFields(data.prompts || []);
      promptStatus.textContent = data.updated_at ? `Last updated: ${formatDate(data.updated_at)}` : "Using default Meghalaya prompts.";
      promptStatus.className = "status";
    }

    async function savePrompt() {
      const prompts = readPromptFields();
      promptStatus.textContent = "Saving prompts...";
      promptStatus.className = "status";
      const response = await fetch("/api/admin/prompt-suggestions", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompts }),
      });
      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: "Could not save the prompts." }));
        throw new Error(error.detail || "Could not save the prompts.");
      }
      const data = await response.json();
      renderPromptFields(data.prompts || []);
      promptStatus.textContent = `Prompts saved at ${formatDate(data.updated_at)}.`;
      promptStatus.className = "status";
    }

    async function loadPlans() {
      const response = await fetch("/api/admin/plans");
      if (!response.ok) {
        throw new Error("Could not load subscription plans.");
      }
      const data = await response.json();
      renderPlans(data);
      plansStatus.textContent = `${data.length} plan(s) loaded.`;
      plansStatus.className = "status";
    }

    async function savePlan(event) {
      event.preventDefault();
      const payload = readPlanForm();
      if (!editingPlanId && !payload.plan_key) {
        throw new Error("Plan key is required.");
      }

      const url = editingPlanId ? `/api/admin/plans/${editingPlanId}` : "/api/admin/plans";
      const method = editingPlanId ? "PUT" : "POST";
      const body = editingPlanId
        ? {
            name: payload.name,
            price: payload.price,
            billing_cycle: payload.billing_cycle,
            chat_limit: payload.chat_limit,
            translation_limit: payload.translation_limit,
            ai_provider: payload.ai_provider,
            button_text: payload.button_text,
            is_active: payload.is_active,
            is_popular: payload.is_popular,
            sort_order: payload.sort_order,
          }
        : payload;

      const response = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: "Could not save the plan." }));
        throw new Error(error.detail || "Could not save the plan.");
      }

      closePlanModal();
      await Promise.all([loadPlans(), loadDashboard()]);
      plansStatus.textContent = "Plan saved successfully.";
      plansStatus.className = "status";
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

    async function loadDeletionRequests() {
      const response = await fetch("/api/admin/account-deletion-requests");
      if (!response.ok) {
        throw new Error("Could not load account deletion requests.");
      }
      const data = await response.json();
      renderDeletionRequests(data);
      deletionRequestsStatus.textContent = `${data.length} request(s) loaded.`;
      deletionRequestsStatus.className = "status";
    }

    async function loadFeedbackRequests() {
      const response = await fetch("/api/admin/feedback-requests");
      if (!response.ok) {
        throw new Error("Could not load feedback requests.");
      }
      const data = await response.json();
      renderFeedbackRequests(data);
      feedbackRequestsStatus.textContent = `${data.length} feedback item(s) loaded.`;
      feedbackRequestsStatus.className = "status";
    }

    function renderCsvLinks() {
      csvLinks.innerHTML = csvDatasets.map(([key, label]) => `
        <a class="csv-link" href="/api/admin/exports/${key}" download>${escapeHtml(label)} CSV</a>
      `).join("");
    }

    async function boot() {
      renderCsvLinks();
      try {
        await Promise.all([loadPrompt(), loadPlans(), loadDashboard(), loadDeletionRequests(), loadFeedbackRequests()]);
      } catch (error) {
        promptStatus.textContent = error.message || "Could not load admin data.";
        promptStatus.className = "status error";
        plansStatus.textContent = error.message || "Could not load admin data.";
        plansStatus.className = "status error";
        deletionRequestsStatus.textContent = error.message || "Could not load admin data.";
        deletionRequestsStatus.className = "status error";
        feedbackRequestsStatus.textContent = error.message || "Could not load admin data.";
        feedbackRequestsStatus.className = "status error";
      }
    }

    savePromptButton.addEventListener("click", async () => {
      try {
        await savePrompt();
      } catch (error) {
        promptStatus.textContent = error.message || "Could not save the prompts.";
        promptStatus.className = "status error";
      }
    });

    reloadPromptButton.addEventListener("click", async () => {
      try {
        await loadPrompt();
      } catch (error) {
        promptStatus.textContent = error.message || "Could not reload the prompts.";
        promptStatus.className = "status error";
      }
    });

    addPlanButton.addEventListener("click", () => openPlanModal());
    reloadDeletionRequestsButton.addEventListener("click", async () => {
      try {
        await loadDeletionRequests();
      } catch (error) {
        deletionRequestsStatus.textContent = error.message || "Could not reload account deletion requests.";
        deletionRequestsStatus.className = "status error";
      }
    });
    reloadFeedbackRequestsButton.addEventListener("click", async () => {
      try {
        await loadFeedbackRequests();
      } catch (error) {
        feedbackRequestsStatus.textContent = error.message || "Could not reload feedback requests.";
        feedbackRequestsStatus.className = "status error";
      }
    });
    reloadPlansButton.addEventListener("click", async () => {
      try {
        await loadPlans();
      } catch (error) {
        plansStatus.textContent = error.message || "Could not reload plans.";
        plansStatus.className = "status error";
      }
    });
    closePlanModalButton.addEventListener("click", closePlanModal);
    cancelPlanButton.addEventListener("click", closePlanModal);
    planModalBackdrop.addEventListener("click", (event) => {
      if (event.target === planModalBackdrop) {
        closePlanModal();
      }
    });
    planForm.addEventListener("submit", async (event) => {
      try {
        await savePlan(event);
      } catch (error) {
        plansStatus.textContent = error.message || "Could not save the plan.";
        plansStatus.className = "status error";
      }
    });

    boot();
  </script>
</body>
</html>
"""


SUBSCRIPTION_PLANS_PAGE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Garo2 Admin - Subscription Plans</title>
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
    .hero-nav, .section-head, .table-actions, .actions, .checkbox-row {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      align-items: center;
    }
    .section-head {
      justify-content: space-between;
      margin-bottom: 12px;
    }
    .panel {
      padding: 20px;
    }
    .muted {
      margin: 0;
      color: var(--muted);
      line-height: 1.6;
    }
    button, .nav-link {
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
    .table-wrap { overflow-x: auto; }
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
    .pill {
      display: inline-flex;
      align-items: center;
      border-radius: 999px;
      padding: 5px 10px;
      font-size: 0.82rem;
      border: 1px solid var(--border);
      background: rgba(255,255,255,0.04);
    }
    .pill.yes {
      color: #9cf4d0;
      border-color: rgba(156, 244, 208, 0.28);
    }
    .pill.no { color: var(--muted); }
    .plan-modal-backdrop[hidden] { display: none; }
    .plan-modal-backdrop {
      position: fixed;
      inset: 0;
      background: rgba(4, 12, 18, 0.72);
      display: grid;
      place-items: center;
      padding: 18px;
    }
    .plan-modal {
      width: min(860px, 100%);
      border: 1px solid var(--border);
      border-radius: 24px;
      background: var(--panel);
      padding: 20px;
      box-shadow: 0 30px 80px rgba(0, 0, 0, 0.35);
    }
    .field-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
    }
    .field {
      display: grid;
      gap: 8px;
    }
    .field.full { grid-column: 1 / -1; }
    .field label {
      color: var(--muted);
      font-size: 0.9rem;
    }
    .field input, .field textarea {
      width: 100%;
      border: 1px solid var(--border);
      border-radius: 14px;
      background: var(--panel-soft);
      color: var(--text);
      padding: 12px 14px;
      font: inherit;
    }
    .field textarea { min-height: 120px; }
    @media (max-width: 720px) {
      .shell { width: min(100vw - 20px, 1180px); padding-top: 14px; }
      .field-grid { grid-template-columns: 1fr; }
      .section-head { align-items: flex-start; }
    }
  </style>
</head>
<body>
  <div class="shell">
    <section class="hero">
      <h1 style="margin:0;">Subscription Plans</h1>
      <p class="muted">Manage plan pricing, limits, button text, active status, and display order from a dedicated admin page.</p>
      <div class="hero-nav">
        <a class="nav-link" href="/admin">Dashboard</a>
        <a class="nav-link" href="/admin/prompt-suggestions">Prompt Suggestions</a>
      </div>
    </section>

    <section class="panel">
      <div class="section-head">
        <div>
          <h2 style="margin:0 0 6px;">All Plans</h2>
          <p class="muted">These plans power the public pricing page.</p>
        </div>
        <div class="table-actions">
          <button class="primary" id="add-plan">Add Plan</button>
          <button id="reload-plans">Reload Plans</button>
        </div>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Plan name</th>
              <th>Price</th>
              <th>Billing cycle</th>
              <th>Chat/day</th>
              <th>Translation/day</th>
              <th>AI provider</th>
              <th>Button text</th>
              <th>Active</th>
              <th>Popular</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody id="subscription-plans-body"></tbody>
        </table>
      </div>
      <p class="status" id="plans-status"></p>
    </section>
  </div>

  <div class="plan-modal-backdrop" id="plan-modal-backdrop" hidden>
    <div class="plan-modal">
      <div class="section-head">
        <div>
          <h2 id="plan-modal-title" style="margin:0 0 6px;">Edit Plan</h2>
          <p class="muted">Update pricing, limits, copy, active status, and display order.</p>
        </div>
        <button id="close-plan-modal" type="button">Close</button>
      </div>
      <form id="plan-form">
        <div class="field-grid">
          <div class="field">
            <label for="plan-key">Plan key</label>
            <input id="plan-key" type="text" placeholder="plus" required />
          </div>
          <div class="field">
            <label for="plan-name">Plan name</label>
            <input id="plan-name" type="text" placeholder="Plus" required />
          </div>
          <div class="field">
            <label for="plan-price">Price (INR)</label>
            <input id="plan-price" type="number" min="0" required />
          </div>
          <div class="field">
            <label for="plan-billing-cycle">Billing cycle</label>
            <input id="plan-billing-cycle" type="text" placeholder="month" required />
          </div>
          <div class="field">
            <label for="plan-chat-limit">Chat/day</label>
            <input id="plan-chat-limit" type="number" min="0" placeholder="Leave empty for unlimited" />
          </div>
          <div class="field">
            <label for="plan-translation-limit">Translation/day</label>
            <input id="plan-translation-limit" type="number" min="0" required />
          </div>
          <div class="field full">
            <label for="plan-ai-provider">AI provider text</label>
            <textarea id="plan-ai-provider" required></textarea>
          </div>
          <div class="field full">
            <label for="plan-button-text">Button text</label>
            <input id="plan-button-text" type="text" placeholder="Pay for Plus" required />
          </div>
          <div class="field">
            <label for="plan-sort-order">Sort order</label>
            <input id="plan-sort-order" type="number" required />
          </div>
          <div class="field full checkbox-row">
            <label><input id="plan-is-active" type="checkbox" checked /> Active</label>
            <label><input id="plan-is-popular" type="checkbox" /> Popular</label>
          </div>
        </div>
        <div class="actions" style="margin-top: 16px;">
          <button class="primary" type="submit">Save Plan</button>
          <button id="cancel-plan" type="button">Cancel</button>
        </div>
      </form>
    </div>
  </div>

  <script>
    const subscriptionPlansBody = document.getElementById("subscription-plans-body");
    const plansStatus = document.getElementById("plans-status");
    const addPlanButton = document.getElementById("add-plan");
    const reloadPlansButton = document.getElementById("reload-plans");
    const planModalBackdrop = document.getElementById("plan-modal-backdrop");
    const closePlanModalButton = document.getElementById("close-plan-modal");
    const cancelPlanButton = document.getElementById("cancel-plan");
    const planModalTitle = document.getElementById("plan-modal-title");
    const planForm = document.getElementById("plan-form");
    const planKeyField = document.getElementById("plan-key");
    const planNameField = document.getElementById("plan-name");
    const planPriceField = document.getElementById("plan-price");
    const planBillingCycleField = document.getElementById("plan-billing-cycle");
    const planChatLimitField = document.getElementById("plan-chat-limit");
    const planTranslationLimitField = document.getElementById("plan-translation-limit");
    const planAiProviderField = document.getElementById("plan-ai-provider");
    const planButtonTextField = document.getElementById("plan-button-text");
    const planSortOrderField = document.getElementById("plan-sort-order");
    const planIsActiveField = document.getElementById("plan-is-active");
    const planIsPopularField = document.getElementById("plan-is-popular");
    let editingPlanId = null;

    function escapeHtml(value) {
      return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
    }

    function formatPlanPrice(plan) {
      const suffix = plan.price > 0 && plan.billing_cycle && plan.billing_cycle !== "free" ? `/${plan.billing_cycle}` : "";
      return `Rs ${plan.price}${suffix}`;
    }

    function renderFlag(value) {
      return `<span class="pill ${value ? "yes" : "no"}">${value ? "Yes" : "No"}</span>`;
    }

    function openPlanModal(plan = null) {
      editingPlanId = plan?.id ?? null;
      planModalTitle.textContent = plan ? "Edit Plan" : "Add Plan";
      planKeyField.value = plan?.plan_key ?? "";
      planKeyField.disabled = Boolean(plan);
      planNameField.value = plan?.name ?? "";
      planPriceField.value = plan?.price ?? 0;
      planBillingCycleField.value = plan?.billing_cycle ?? "month";
      planChatLimitField.value = plan?.chat_limit ?? "";
      planTranslationLimitField.value = plan?.translation_limit ?? 0;
      planAiProviderField.value = plan?.ai_provider ?? "";
      planButtonTextField.value = plan?.button_text ?? "";
      planSortOrderField.value = plan?.sort_order ?? 0;
      planIsActiveField.checked = plan ? Boolean(plan.is_active) : true;
      planIsPopularField.checked = plan ? Boolean(plan.is_popular) : false;
      planModalBackdrop.hidden = false;
    }

    function closePlanModal() {
      editingPlanId = null;
      planForm.reset();
      planKeyField.disabled = false;
      planModalBackdrop.hidden = true;
    }

    function readPlanForm() {
      const chatLimitValue = planChatLimitField.value.trim();
      return {
        plan_key: planKeyField.value.trim().toLowerCase(),
        name: planNameField.value.trim(),
        price: Number(planPriceField.value),
        billing_cycle: planBillingCycleField.value.trim(),
        chat_limit: chatLimitValue === "" ? null : Number(chatLimitValue),
        translation_limit: Number(planTranslationLimitField.value),
        ai_provider: planAiProviderField.value.trim(),
        button_text: planButtonTextField.value.trim(),
        is_active: planIsActiveField.checked,
        is_popular: planIsPopularField.checked,
        sort_order: Number(planSortOrderField.value),
      };
    }

    function renderPlans(plans) {
      subscriptionPlansBody.innerHTML = plans.map((plan) => `
        <tr>
          <td>${escapeHtml(plan.name)}</td>
          <td>${escapeHtml(formatPlanPrice(plan))}</td>
          <td>${escapeHtml(plan.billing_cycle)}</td>
          <td>${escapeHtml(plan.chat_limit == null ? "Unlimited with safe backend rate limit" : `${plan.chat_limit}/day`)}</td>
          <td>${escapeHtml(`${plan.translation_limit}/day`)}</td>
          <td>${escapeHtml(plan.ai_provider)}</td>
          <td>${escapeHtml(plan.button_text)}</td>
          <td>${renderFlag(Boolean(plan.is_active))}</td>
          <td>${renderFlag(Boolean(plan.is_popular))}</td>
          <td class="table-actions">
            <button type="button" data-edit-plan="${plan.id}">Edit</button>
            <button type="button" data-delete-plan="${plan.id}">Delete</button>
          </td>
        </tr>
      `).join("") || `<tr><td colspan="10" class="muted">No plans found.</td></tr>`;

      subscriptionPlansBody.querySelectorAll("[data-edit-plan]").forEach((button) => {
        button.addEventListener("click", () => {
          const plan = plans.find((entry) => entry.id === Number(button.dataset.editPlan));
          if (plan) {
            openPlanModal(plan);
          }
        });
      });

      subscriptionPlansBody.querySelectorAll("[data-delete-plan]").forEach((button) => {
        button.addEventListener("click", async () => {
          const planId = Number(button.dataset.deletePlan);
          if (!window.confirm("Delete will set this plan inactive on the pricing page. Continue?")) {
            return;
          }
          plansStatus.textContent = "Updating plan status...";
          plansStatus.className = "status";
          try {
            const response = await fetch(`/api/admin/plans/${planId}`, { method: "DELETE" });
            if (!response.ok) {
              const error = await response.json().catch(() => ({ detail: "Could not delete the plan." }));
              throw new Error(error.detail || "Could not delete the plan.");
            }
            await loadPlans();
            plansStatus.textContent = "Plan updated successfully.";
            plansStatus.className = "status";
          } catch (error) {
            plansStatus.textContent = error.message || "Could not delete the plan.";
            plansStatus.className = "status error";
          }
        });
      });
    }

    async function loadPlans() {
      const response = await fetch("/api/admin/plans");
      if (!response.ok) {
        throw new Error("Could not load subscription plans.");
      }
      const data = await response.json();
      renderPlans(data);
      plansStatus.textContent = `${data.length} plan(s) loaded.`;
      plansStatus.className = "status";
    }

    async function savePlan(event) {
      event.preventDefault();
      const payload = readPlanForm();
      if (!editingPlanId && !payload.plan_key) {
        throw new Error("Plan key is required.");
      }

      const url = editingPlanId ? `/api/admin/plans/${editingPlanId}` : "/api/admin/plans";
      const method = editingPlanId ? "PUT" : "POST";
      const body = editingPlanId
        ? {
            name: payload.name,
            price: payload.price,
            billing_cycle: payload.billing_cycle,
            chat_limit: payload.chat_limit,
            translation_limit: payload.translation_limit,
            ai_provider: payload.ai_provider,
            button_text: payload.button_text,
            is_active: payload.is_active,
            is_popular: payload.is_popular,
            sort_order: payload.sort_order,
          }
        : payload;

      const response = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: "Could not save the plan." }));
        throw new Error(error.detail || "Could not save the plan.");
      }

      closePlanModal();
      await loadPlans();
      plansStatus.textContent = "Plan saved successfully.";
      plansStatus.className = "status";
    }

    addPlanButton.addEventListener("click", () => openPlanModal());
    reloadPlansButton.addEventListener("click", async () => {
      try {
        await loadPlans();
      } catch (error) {
        plansStatus.textContent = error.message || "Could not reload plans.";
        plansStatus.className = "status error";
      }
    });
    closePlanModalButton.addEventListener("click", closePlanModal);
    cancelPlanButton.addEventListener("click", closePlanModal);
    planModalBackdrop.addEventListener("click", (event) => {
      if (event.target === planModalBackdrop) {
        closePlanModal();
      }
    });
    planForm.addEventListener("submit", async (event) => {
      try {
        await savePlan(event);
      } catch (error) {
        plansStatus.textContent = error.message || "Could not save the plan.";
        plansStatus.className = "status error";
      }
    });

    loadPlans().catch((error) => {
      plansStatus.textContent = error.message || "Could not load subscription plans.";
      plansStatus.className = "status error";
    });
  </script>
</body>
</html>
"""


PROMPT_SUGGESTIONS_PAGE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Garo2 Admin - Prompt Suggestions</title>
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
      width: min(980px, calc(100vw - 32px));
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
    .hero-nav, .actions {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      align-items: center;
    }
    .panel {
      padding: 20px;
    }
    .muted {
      margin: 0;
      color: var(--muted);
      line-height: 1.6;
    }
    button, .nav-link {
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
    .prompt-suggestion-fields {
      display: grid;
      gap: 12px;
      margin-top: 14px;
    }
    .prompt-suggestion-field {
      display: grid;
      gap: 8px;
    }
    .prompt-suggestion-field label {
      color: var(--muted);
      font-size: 0.9rem;
    }
    textarea {
      width: 100%;
      min-height: 112px;
      resize: vertical;
      border: 1px solid var(--border);
      border-radius: 18px;
      background: var(--panel-soft);
      color: var(--text);
      padding: 14px 16px;
      font: inherit;
      line-height: 1.6;
    }
    @media (max-width: 720px) {
      .shell { width: min(100vw - 20px, 980px); padding-top: 14px; }
    }
  </style>
</head>
<body>
  <div class="shell">
    <section class="hero">
      <h1 style="margin:0;">Prompt Suggestions</h1>
      <p class="muted">Manage the suggested prompts shown above the chat input on small devices.</p>
      <div class="hero-nav">
        <a class="nav-link" href="/admin">Dashboard</a>
        <a class="nav-link" href="/admin/subscription-plans">Subscription Plans</a>
      </div>
    </section>

    <section class="panel">
      <h2 style="margin:0 0 6px;">Suggested Chat Prompts</h2>
      <p class="muted">Update the Meghalaya starter prompts without editing frontend code.</p>
      <div id="prompt-suggestion-fields" class="prompt-suggestion-fields"></div>
      <div class="actions" style="margin-top: 14px;">
        <button class="primary" id="save-prompt">Save Prompts</button>
        <button id="reload-prompt">Reload</button>
      </div>
      <p class="status" id="prompt-status"></p>
    </section>
  </div>

  <script>
    const promptSuggestionFields = document.getElementById("prompt-suggestion-fields");
    const promptStatus = document.getElementById("prompt-status");
    const savePromptButton = document.getElementById("save-prompt");
    const reloadPromptButton = document.getElementById("reload-prompt");

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

    function renderPromptFields(prompts) {
      promptSuggestionFields.innerHTML = prompts.map((prompt, index) => `
        <div class="prompt-suggestion-field">
          <label for="prompt-suggestion-${index}">Prompt ${index + 1}</label>
          <textarea id="prompt-suggestion-${index}" data-prompt-index="${index}">${escapeHtml(prompt)}</textarea>
        </div>
      `).join("");
    }

    function readPromptFields() {
      return Array.from(promptSuggestionFields.querySelectorAll("textarea"))
        .map((field) => field.value.trim())
        .filter(Boolean);
    }

    async function loadPrompt() {
      const response = await fetch("/api/admin/prompt-suggestions");
      if (!response.ok) {
        throw new Error("Could not load the suggested prompts.");
      }
      const data = await response.json();
      renderPromptFields(data.prompts || []);
      promptStatus.textContent = data.updated_at ? `Last updated: ${formatDate(data.updated_at)}` : "Using default Meghalaya prompts.";
      promptStatus.className = "status";
    }

    async function savePrompt() {
      const prompts = readPromptFields();
      promptStatus.textContent = "Saving prompts...";
      promptStatus.className = "status";
      const response = await fetch("/api/admin/prompt-suggestions", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompts }),
      });
      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: "Could not save the prompts." }));
        throw new Error(error.detail || "Could not save the prompts.");
      }
      const data = await response.json();
      renderPromptFields(data.prompts || []);
      promptStatus.textContent = `Prompts saved at ${formatDate(data.updated_at)}.`;
      promptStatus.className = "status";
    }

    savePromptButton.addEventListener("click", async () => {
      try {
        await savePrompt();
      } catch (error) {
        promptStatus.textContent = error.message || "Could not save the prompts.";
        promptStatus.className = "status error";
      }
    });

    reloadPromptButton.addEventListener("click", async () => {
      try {
        await loadPrompt();
      } catch (error) {
        promptStatus.textContent = error.message || "Could not reload the prompts.";
        promptStatus.className = "status error";
      }
    });

    loadPrompt().catch((error) => {
      promptStatus.textContent = error.message || "Could not load prompt suggestions.";
      promptStatus.className = "status error";
    });
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


@router.get("/admin/subscription-plans", response_class=HTMLResponse, include_in_schema=False)
@router.get("/api/admin/subscription-plans", response_class=HTMLResponse, include_in_schema=False)
def subscription_plans_page(_: str = Depends(get_admin_credentials)) -> HTMLResponse:
    return HTMLResponse(SUBSCRIPTION_PLANS_PAGE_HTML)


@router.get("/admin/prompt-suggestions", response_class=HTMLResponse, include_in_schema=False)
@router.get("/api/admin/prompt-suggestions-page", response_class=HTMLResponse, include_in_schema=False)
def prompt_suggestions_page(_: str = Depends(get_admin_credentials)) -> HTMLResponse:
    return HTMLResponse(PROMPT_SUGGESTIONS_PAGE_HTML)


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


@router.get("/api/admin/plans", response_model=list[SubscriptionPlanResponse], tags=["Admin"])
def get_admin_plans_endpoint(
    _: str = Depends(get_admin_credentials),
    db: Session = Depends(get_db),
) -> list[SubscriptionPlanResponse]:
    return list_admin_plans(db)


@router.post("/api/admin/plans", response_model=SubscriptionPlanResponse, tags=["Admin"])
def create_plan_endpoint(
    payload: SubscriptionPlanCreateRequest,
    _: str = Depends(get_admin_credentials),
    db: Session = Depends(get_db),
) -> SubscriptionPlanResponse:
    return create_admin_plan(db, payload)


@router.put("/api/admin/plans/{plan_id}", response_model=SubscriptionPlanResponse, tags=["Admin"])
def update_plan_endpoint(
    plan_id: int,
    payload: SubscriptionPlanUpdateRequest,
    _: str = Depends(get_admin_credentials),
    db: Session = Depends(get_db),
) -> SubscriptionPlanResponse:
    return update_admin_plan(db, plan_id, payload)


@router.delete("/api/admin/plans/{plan_id}", response_model=SubscriptionPlanResponse, tags=["Admin"])
def delete_plan_endpoint(
    plan_id: int,
    _: str = Depends(get_admin_credentials),
    db: Session = Depends(get_db),
) -> SubscriptionPlanResponse:
    return deactivate_admin_plan(db, plan_id)


@router.get("/api/admin/account-deletion-requests", response_model=list[AccountDeletionRequestResponse], tags=["Admin"])
def get_account_deletion_requests_endpoint(
    _: str = Depends(get_admin_credentials),
    db: Session = Depends(get_db),
) -> list[AccountDeletionRequestResponse]:
    return db.query(AccountDeletionRequest).order_by(AccountDeletionRequest.created_at.desc()).all()


@router.get("/api/admin/feedback-requests", response_model=list[FeedbackRequestResponse], tags=["Admin"])
def get_feedback_requests_endpoint(
    _: str = Depends(get_admin_credentials),
    db: Session = Depends(get_db),
) -> list[FeedbackRequestResponse]:
    return db.query(FeedbackRequest).order_by(FeedbackRequest.created_at.desc()).all()


@router.delete("/api/admin/account-deletion-requests/{request_id}", tags=["Admin"])
def delete_account_deletion_request_endpoint(
    request_id: int,
    _: str = Depends(get_admin_credentials),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    deletion_request = db.get(AccountDeletionRequest, request_id)
    if deletion_request is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account deletion request not found.")

    db.delete(deletion_request)
    db.commit()
    return {"status": "deleted"}


@router.delete("/api/admin/feedback-requests/{request_id}", tags=["Admin"])
def delete_feedback_request_endpoint(
    request_id: int,
    _: str = Depends(get_admin_credentials),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    feedback_request = db.get(FeedbackRequest, request_id)
    if feedback_request is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feedback request not found.")

    db.delete(feedback_request)
    db.commit()
    return {"status": "deleted"}


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
