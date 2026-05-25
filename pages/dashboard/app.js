(() => {
  const PAGE_ENDPOINT_PREFIX = "page";
  const state = {
    page: 1,
    pageSize: 30,
    total: 0,
    hasMore: false,
    items: [],
    selected: new Set(),
    currentItem: null,
    searchTimer: null,
  };

  const $ = (id) => document.getElementById(id);
  const dom = {
    refreshBtn: $("refresh-btn"),
    maintenanceBtn: $("maintenance-btn"),
    keyword: $("keyword-input"),
    platform: $("platform-input"),
    chat: $("chat-input"),
    db: $("db-select"),
    role: $("role-select"),
    imageStatus: $("image-status-select"),
    source: $("source-input"),
    includeDeleted: $("include-deleted-input"),
    body: $("messages-body"),
    resultSummary: $("result-summary"),
    selectAll: $("select-all"),
    batchDelete: $("batch-delete-btn"),
    prevPage: $("prev-page"),
    nextPage: $("next-page"),
    pageLabel: $("page-label"),
    errorPanel: $("error-panel"),
    toast: $("toast"),
    modal: $("modal"),
    modalClose: $("modal-close"),
    modalMeta: $("modal-meta"),
    editContent: $("edit-content"),
    editSender: $("edit-sender"),
    editImageStatus: $("edit-image-status"),
    editImageDescriptions: $("edit-image-descriptions"),
    editReason: $("edit-reason"),
    rawJson: $("raw-json"),
    saveBtn: $("save-btn"),
    softDeleteBtn: $("soft-delete-btn"),
    restoreBtn: $("restore-btn"),
  };

  function normalizeBridgeResponse(response) {
    if (
      response &&
      typeof response === "object" &&
      Object.prototype.hasOwnProperty.call(response, "success")
    ) {
      return response;
    }
    return { success: true, data: response };
  }

  async function apiRequest(path, options = {}) {
    const bridge = window.AstrBotPluginPage;
    if (!bridge) {
      throw new Error("当前页面必须运行在 AstrBot 官方插件 Page 内");
    }
    const method = options.method || "GET";
    const endpoint = `${PAGE_ENDPOINT_PREFIX}/${path}`.replace(/\/+/g, "/");
    const response =
      method === "GET"
        ? await bridge.apiGet(endpoint, options.params || {})
        : await bridge.apiPost(endpoint, options.body || {});
    const normalized = normalizeBridgeResponse(response);
    if (!normalized.success) {
      throw new Error(normalized.error || "请求失败");
    }
    return normalized.data;
  }

  function showToast(message, isError = false) {
    dom.toast.textContent = message;
    dom.toast.classList.toggle("error", isError);
    dom.toast.classList.remove("hidden");
    window.clearTimeout(showToast.timer);
    showToast.timer = window.setTimeout(() => dom.toast.classList.add("hidden"), 2600);
  }

  function showError(error) {
    dom.errorPanel.textContent = error ? String(error.message || error) : "";
    dom.errorPanel.classList.toggle("hidden", !error);
  }

  function formatTime(ts) {
    if (!ts) return "--";
    try {
      return new Date(Number(ts) * 1000).toLocaleString();
    } catch {
      return "--";
    }
  }

  function escapeText(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function truncate(value, max = 180) {
    const text = String(value || "");
    return text.length > max ? `${text.slice(0, max)}...` : text;
  }

  function getFilters() {
    return {
      page: state.page,
      page_size: state.pageSize,
      keyword: dom.keyword.value.trim(),
      platform_id: dom.platform.value.trim(),
      chat_id: dom.chat.value.trim(),
      db: dom.db.value,
      role: dom.role.value,
      image_status: dom.imageStatus.value,
      source: dom.source.value.trim(),
      include_deleted: dom.includeDeleted.checked ? "1" : "",
    };
  }

  async function fetchStats() {
    const data = await apiRequest("stats", {
      params: {
        platform_id: dom.platform.value.trim(),
        chat_id: dom.chat.value.trim(),
      },
    });
    const scoped = data.scoped || {};
    $("stat-hot").textContent = scoped.hot_messages ?? 0;
    $("stat-cold").textContent = scoped.cold_messages ?? 0;
    $("stat-deleted").textContent =
      Number(scoped.hot_deleted_messages || 0) + Number(scoped.cold_deleted_messages || 0);
    $("stat-image-success").textContent = scoped.image_success ?? 0;
    $("stat-image-pending").textContent = scoped.image_pending_retry ?? 0;
    $("stat-image-failed").textContent = scoped.image_failed_final ?? 0;
  }

  async function fetchMessages() {
    const data = await apiRequest("messages", { params: getFilters() });
    state.items = data.items || [];
    state.total = Number(data.total || 0);
    state.hasMore = Boolean(data.has_more);
    state.selected.clear();
    renderMessages();
  }

  async function refreshAll() {
    showError(null);
    await Promise.all([fetchStats(), fetchMessages()]);
  }

  function selectorFor(item) {
    return {
      id: item.id,
      platform_id: item.platform_id,
      chat_id: item.chat_id,
      message_id: item.message_id,
      role: item.role,
      db: item.db,
    };
  }

  function itemKey(item) {
    return `${item.db}:${item.id}`;
  }

  function renderMessages() {
    dom.selectAll.checked = false;
    dom.resultSummary.textContent = `共 ${state.total} 条，当前第 ${state.page} 页`;
    dom.pageLabel.textContent = `第 ${state.page} 页`;
    dom.prevPage.disabled = state.page <= 1;
    dom.nextPage.disabled = !state.hasMore;

    if (!state.items.length) {
      dom.body.innerHTML = `<tr><td colspan="11">没有匹配的上下文消息</td></tr>`;
      return;
    }

    dom.body.innerHTML = state.items
      .map((item) => {
        const deleted = Number(item.deleted_at || 0) > 0;
        const statusClass = deleted ? "deleted" : item.image_status === "success" ? "ok" : item.image_status ? "warn" : "";
        const statusText = deleted ? "已删除" : "可见";
        const imageText = item.image_status || (item.image_refs?.length ? "has_image" : "");
        return `
          <tr>
            <td><input class="row-select" type="checkbox" data-key="${escapeText(itemKey(item))}" /></td>
            <td>${escapeText(formatTime(item.timestamp))}</td>
            <td><span class="pill">${escapeText(item.db)}</span></td>
            <td>${escapeText(item.chat_id)}</td>
            <td>${escapeText(item.sender_name || item.sender_id || "--")}</td>
            <td>${escapeText(item.role)}</td>
            <td class="content-cell">${escapeText(truncate(item.content))}</td>
            <td>${imageText ? `<span class="pill ${statusClass}">${escapeText(imageText)}</span>` : "--"}</td>
            <td>${escapeText(item.trigger_source || "--")}</td>
            <td><span class="pill ${deleted ? "deleted" : ""}">${statusText}</span></td>
            <td>
              <div class="row-actions">
                <button class="btn secondary edit-row" type="button" data-key="${escapeText(itemKey(item))}">编辑</button>
                ${
                  deleted
                    ? `<button class="btn secondary restore-row" type="button" data-key="${escapeText(itemKey(item))}">恢复</button>`
                    : `<button class="btn danger delete-row" type="button" data-key="${escapeText(itemKey(item))}">软删</button>`
                }
              </div>
            </td>
          </tr>
        `;
      })
      .join("");
  }

  function findItem(key) {
    return state.items.find((item) => itemKey(item) === key);
  }

  function openEditor(item) {
    state.currentItem = item;
    dom.modalMeta.innerHTML = [
      ["库", item.db],
      ["ID", item.id],
      ["message_id", item.message_id],
      ["platform_id", item.platform_id],
      ["chat_id", item.chat_id],
      ["时间", formatTime(item.timestamp)],
    ]
      .map(([label, value]) => `<div><strong>${escapeText(label)}:</strong> ${escapeText(value)}</div>`)
      .join("");
    dom.editContent.value = item.content || "";
    dom.editSender.value = item.sender_name || "";
    dom.editImageStatus.value = item.image_status || "";
    dom.editImageDescriptions.value = (item.image_descriptions || []).join("\n");
    dom.editReason.value = "";
    dom.rawJson.textContent = JSON.stringify(
      {
        image_refs: item.image_refs || [],
        raw_json: item.raw_json || {},
      },
      null,
      2,
    );
    const deleted = Number(item.deleted_at || 0) > 0;
    dom.restoreBtn.disabled = !deleted;
    dom.softDeleteBtn.disabled = deleted;
    dom.modal.classList.remove("hidden");
  }

  function closeEditor() {
    state.currentItem = null;
    dom.modal.classList.add("hidden");
  }

  async function saveCurrent() {
    if (!state.currentItem) return;
    await apiRequest("messages/update", {
      method: "POST",
      body: {
        ...selectorFor(state.currentItem),
        content: dom.editContent.value,
        sender_name: dom.editSender.value,
        image_status: dom.editImageStatus.value,
        image_descriptions: dom.editImageDescriptions.value,
        reason: dom.editReason.value,
      },
    });
    showToast("已保存");
    closeEditor();
    await refreshAll();
  }

  async function softDeleteItem(item) {
    if (!item) return;
    if (!window.confirm("确认软删除这条上下文消息？软删除后不会进入 bot 上下文。")) return;
    await apiRequest("messages/soft-delete", {
      method: "POST",
      body: {
        ...selectorFor(item),
        reason: "deleted from GCP WebUI",
      },
    });
    showToast("已软删除");
    closeEditor();
    await refreshAll();
  }

  async function restoreItem(item) {
    if (!item) return;
    await apiRequest("messages/restore", {
      method: "POST",
      body: selectorFor(item),
    });
    showToast("已恢复");
    closeEditor();
    await refreshAll();
  }

  async function batchDelete() {
    const items = state.items.filter((item) => state.selected.has(itemKey(item)));
    if (!items.length) {
      showToast("请先选择消息", true);
      return;
    }
    if (!window.confirm(`确认软删除选中的 ${items.length} 条消息？`)) return;
    await apiRequest("messages/batch-soft-delete", {
      method: "POST",
      body: {
        messages: items.map(selectorFor),
        reason: "batch deleted from GCP WebUI",
      },
    });
    showToast("批量软删除完成");
    await refreshAll();
  }

  function bindEvents() {
    dom.refreshBtn.addEventListener("click", () => refreshAll().catch(handleError));
    dom.maintenanceBtn.addEventListener("click", async () => {
      try {
        if (!window.confirm("确认立即执行 SQLite 维护/归档？")) return;
        await apiRequest("maintenance", { method: "POST", body: {} });
        showToast("维护完成");
        await refreshAll();
      } catch (error) {
        handleError(error);
      }
    });

    [dom.keyword, dom.platform, dom.chat, dom.source].forEach((input) => {
      input.addEventListener("input", () => {
        window.clearTimeout(state.searchTimer);
        state.searchTimer = window.setTimeout(() => {
          state.page = 1;
          refreshAll().catch(handleError);
        }, 300);
      });
    });

    [dom.db, dom.role, dom.imageStatus, dom.includeDeleted].forEach((input) => {
      input.addEventListener("change", () => {
        state.page = 1;
        refreshAll().catch(handleError);
      });
    });

    dom.prevPage.addEventListener("click", () => {
      if (state.page > 1) {
        state.page -= 1;
        fetchMessages().catch(handleError);
      }
    });
    dom.nextPage.addEventListener("click", () => {
      if (state.hasMore) {
        state.page += 1;
        fetchMessages().catch(handleError);
      }
    });

    dom.selectAll.addEventListener("change", () => {
      state.selected.clear();
      if (dom.selectAll.checked) {
        state.items.forEach((item) => state.selected.add(itemKey(item)));
      }
      document.querySelectorAll(".row-select").forEach((input) => {
        input.checked = dom.selectAll.checked;
      });
    });

    dom.body.addEventListener("click", (event) => {
      const target = event.target;
      if (!(target instanceof HTMLElement)) return;
      const key = target.dataset.key;
      const item = key ? findItem(key) : null;
      if (target.classList.contains("edit-row")) openEditor(item);
      if (target.classList.contains("delete-row")) softDeleteItem(item).catch(handleError);
      if (target.classList.contains("restore-row")) restoreItem(item).catch(handleError);
    });

    dom.body.addEventListener("change", (event) => {
      const target = event.target;
      if (!(target instanceof HTMLInputElement) || !target.classList.contains("row-select")) return;
      if (target.checked) {
        state.selected.add(target.dataset.key);
      } else {
        state.selected.delete(target.dataset.key);
      }
    });

    dom.batchDelete.addEventListener("click", () => batchDelete().catch(handleError));
    dom.modalClose.addEventListener("click", closeEditor);
    dom.modal.addEventListener("click", (event) => {
      if (event.target === dom.modal) closeEditor();
    });
    dom.saveBtn.addEventListener("click", () => saveCurrent().catch(handleError));
    dom.softDeleteBtn.addEventListener("click", () => softDeleteItem(state.currentItem).catch(handleError));
    dom.restoreBtn.addEventListener("click", () => restoreItem(state.currentItem).catch(handleError));
  }

  function handleError(error) {
    showError(error);
    showToast(error.message || "操作失败", true);
  }

  async function init() {
    bindEvents();
    if (window.AstrBotPluginPage?.ready) {
      await window.AstrBotPluginPage.ready();
    }
    await refreshAll();
  }

  init().catch(handleError);
})();
