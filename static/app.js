/* Creative Jobs Dashboard — frontend */

const LIMIT = 50;

let state = {
  page: 1,
  total: 0,
  jobs: [],
  fetching: false,
};

// -----------------------------------------------------------------------
// Helpers
// -----------------------------------------------------------------------

function qs(id) { return document.getElementById(id); }

function showToast(msg, duration = 3000) {
  const t = qs("toast");
  t.textContent = msg;
  t.classList.add("show");
  setTimeout(() => t.classList.remove("show"), duration);
}

function formatDate(iso) {
  if (!iso) return "";
  try {
    return new Date(iso).toLocaleDateString("en-GB", {
      day: "numeric", month: "short", year: "numeric",
    });
  } catch {
    return iso.slice(0, 10);
  }
}

function isToday(iso) {
  if (!iso) return false;
  return iso.slice(0, 10) === new Date().toISOString().slice(0, 10);
}

function buildParams() {
  const p = new URLSearchParams();
  const q = qs("filter-q").value.trim();
  const source = qs("filter-source").value;
  const dateRange = qs("filter-date").value;
  const favs = qs("filter-favs").checked;

  if (q)      p.set("q", q);
  if (source) p.set("source", source);
  if (favs)   p.set("favorites", "1");

  if (dateRange === "today") {
    const today = new Date().toISOString().slice(0, 10);
    p.set("date_from", today);
  } else if (dateRange === "week") {
    const d = new Date(); d.setDate(d.getDate() - 7);
    p.set("date_from", d.toISOString().slice(0, 10));
  } else if (dateRange === "month") {
    const d = new Date(); d.setDate(d.getDate() - 30);
    p.set("date_from", d.toISOString().slice(0, 10));
  }

  p.set("page", state.page);
  p.set("limit", LIMIT);
  return p;
}

// -----------------------------------------------------------------------
// API calls
// -----------------------------------------------------------------------

async function fetchJobs(append = false) {
  if (state.fetching) return;
  state.fetching = true;

  if (!append) {
    state.page = 1;
    state.jobs = [];
    qs("job-list").innerHTML = '<div class="loading">Loading jobs…</div>';
    qs("empty-state").style.display = "none";
    qs("load-more-wrap").style.display = "none";
  }

  try {
    const resp = await fetch(`/api/jobs?${buildParams()}`);
    const data = await resp.json();

    state.total = data.total;
    if (append) {
      state.jobs = state.jobs.concat(data.jobs);
    } else {
      state.jobs = data.jobs;
    }

    renderJobs(append);
  } catch (err) {
    showToast("Failed to load jobs: " + err.message);
    qs("job-list").innerHTML = "";
  } finally {
    state.fetching = false;
  }
}

async function toggleFavorite(id) {
  const resp = await fetch(`/api/jobs/${id}/favorite`, { method: "POST" });
  const data = await resp.json();
  return data.is_favorited;
}

async function fetchStatus() {
  try {
    const resp = await fetch("/api/status");
    const data = await resp.json();

    // Badge
    const badge = qs("badge-new");
    if (data.new_today > 0) {
      badge.textContent = `${data.new_today} new today`;
    } else {
      badge.textContent = "";
    }

    // Last fetch
    const lastEl = qs("last-fetch");
    if (data.last_fetch) {
      const dt = formatDate(data.last_fetch.fetched_at);
      lastEl.textContent = `Last fetched: ${dt}`;
    } else {
      lastEl.textContent = "Never fetched";
    }

    // Populate source filter
    const sel = qs("filter-source");
    const current = sel.value;
    // Keep the first "All sources" option, rebuild the rest
    while (sel.options.length > 1) sel.remove(1);
    for (const src of (data.sources || [])) {
      const opt = document.createElement("option");
      opt.value = src;
      opt.textContent = src;
      if (src === current) opt.selected = true;
      sel.appendChild(opt);
    }
  } catch {
    // non-fatal
  }
}

async function triggerFetch() {
  const btn = qs("btn-fetch");
  btn.disabled = true;
  btn.textContent = "⏳ Fetching…";
  showToast("Scraping jobs… this may take a minute.", 60000);

  try {
    const resp = await fetch("/api/fetch", { method: "POST" });
    const data = await resp.json();
    showToast(`Done! ${data.new_jobs} new jobs found.`);
    await fetchStatus();
    await fetchJobs();
  } catch (err) {
    showToast("Fetch failed: " + err.message);
  } finally {
    btn.disabled = false;
    btn.textContent = "↻ Fetch now";
  }
}

// -----------------------------------------------------------------------
// Rendering
// -----------------------------------------------------------------------

function renderJobs(append) {
  const list = qs("job-list");

  if (!append) list.innerHTML = "";

  if (state.jobs.length === 0 && !append) {
    qs("empty-state").style.display = "block";
    qs("load-more-wrap").style.display = "none";
    return;
  }

  qs("empty-state").style.display = "none";

  const startIdx = append ? (state.page - 1) * LIMIT : 0;
  const newJobs = append ? state.jobs.slice(startIdx) : state.jobs;

  for (const job of newJobs) {
    list.appendChild(buildCard(job));
  }

  // Load more button
  if (state.jobs.length < state.total) {
    qs("load-more-wrap").style.display = "flex";
  } else {
    qs("load-more-wrap").style.display = "none";
  }
}

function buildCard(job) {
  const card = document.createElement("div");
  card.className = "job-card" + (isToday(job.date_fetched) ? " is-new" : "");
  card.dataset.id = job.id;

  const isFav = job.is_favorited === 1;

  card.innerHTML = `
    <div class="job-card-top">
      <a class="job-title" href="${escHtml(job.url)}" target="_blank" rel="noopener">
        ${escHtml(job.title)}
      </a>
      <div class="job-actions">
        <button
          class="btn-icon btn-fav ${isFav ? "active" : ""}"
          title="${isFav ? "Remove from favorites" : "Add to favorites"}"
          aria-label="Favorite"
          data-id="${job.id}"
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon></svg>
        </button>
        <button
          class="btn-icon btn-cal"
          title="Add to calendar"
          aria-label="Add to calendar"
          data-id="${job.id}"
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect><line x1="16" y1="2" x2="16" y2="6"></line><line x1="8" y1="2" x2="8" y2="6"></line><line x1="3" y1="10" x2="21" y2="10"></line></svg>
        </button>
      </div>
    </div>
    <div class="job-meta">
      ${job.company ? `<span class="meta-company">${escHtml(job.company)}</span>` : ""}
      <div class="meta-item meta-location">${escHtml(job.location || 'Remote/World')}</div>
      ${job.salary ? ` <div class="meta-item meta-salary">${escHtml(job.salary)}</div>` : ""}
      <span class="meta-source">${escHtml(job.source)}</span>
      ${job.date_fetched ? `<span class="meta-date">${formatDate(job.date_fetched)}</span>` : ""}
    </div>
    ${job.description ? `<p class="job-description">${escHtml(job.description)}</p>` : ""}
  `;

  // Favorite button
  card.querySelector(".btn-fav").addEventListener("click", async function () {
    const newVal = await toggleFavorite(job.id);
    job.is_favorited = newVal ? 1 : 0;
    this.classList.toggle("active", newVal);
    this.title = newVal ? "Remove from favorites" : "Add to favorites";
    showToast(newVal ? "Added to favorites" : "Removed from favorites");

    // If we're in favorites-only mode, remove the card
    if (qs("filter-favs").checked && !newVal) {
      card.remove();
    }
  });

  // Calendar button
  card.querySelector(".btn-cal").addEventListener("click", () => {
    window.location.href = `/api/jobs/${job.id}/ics`;
    showToast("Downloading calendar event…");
  });

  return card;
}

function escHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

// -----------------------------------------------------------------------
// Event listeners
// -----------------------------------------------------------------------

// Debounce helper
function debounce(fn, ms) {
  let timer;
  return (...args) => { clearTimeout(timer); timer = setTimeout(() => fn(...args), ms); };
}

qs("filter-q").addEventListener("input", debounce(() => fetchJobs(), 400));
qs("filter-source").addEventListener("change", () => fetchJobs());
qs("filter-date").addEventListener("change", () => fetchJobs());
qs("filter-favs").addEventListener("change", () => fetchJobs());

qs("btn-fetch").addEventListener("click", triggerFetch);

qs("btn-load-more").addEventListener("click", () => {
  state.page += 1;
  fetchJobs(true);
});

// -----------------------------------------------------------------------
// Init
// -----------------------------------------------------------------------

(async function init() {
  await fetchStatus();
  await fetchJobs();
  // Poll status every 60 seconds
  setInterval(fetchStatus, 60_000);
})();
