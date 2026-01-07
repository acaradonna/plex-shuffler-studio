const state = {
  config: null,
  tokenSet: false,
  libraries: [],
  servers: [],
  account: null,
  selectedIndex: 0,
  pinPoll: null,
  queryCatalog: [],
  queryOptions: { tv: {}, movies: {} },
  queryOptionErrors: { tv: {}, movies: {} },
  queryStates: { tv: null, movies: null },
};

const $ = (id) => document.getElementById(id);

const defaultPlaylist = (name) => ({
  name: name || "New Playlist",
  description: "",
  tv: {
    library: "",
    query: "",
    include_titles: [],
    exclude_titles: [],
    episode_filters: {
      unwatched_only: false,
      exclude_watched_days: 0,
      max_per_show: 0,
    },
    order: {
      strategy: "rounds",
      chunk_size: 1,
      seed: "",
    },
  },
  movies: {
    enabled: false,
    library: "",
    query: "",
    collections_as_shows: false,
    include_collections: [],
    exclude_collections: [],
    order: {
      strategy: "rounds",
      chunk_size: 1,
      seed: "",
    },
    ratio: {
      every_episodes: 0,
      max_movies: 0,
    },
    filters: {
      unwatched_only: false,
      exclude_watched_days: 0,
    },
  },
  output: {
    mode: "replace",
    limit_items: 0,
    chunk_size: 200,
  },
});

const toInt = (value) => {
  const parsed = parseInt(value, 10);
  return Number.isNaN(parsed) ? 0 : parsed;
};

const linesToList = (value) =>
  value
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);

const listToLines = (value) => (Array.isArray(value) ? value.join("\n") : "");

const normalizeUrl = (value) => value.trim().replace(/\/+$/, "");

const showToast = (message) => {
  const toast = $("toast");
  toast.textContent = message;
  toast.classList.add("show");
  clearTimeout(showToast._timer);
  showToast._timer = setTimeout(() => toast.classList.remove("show"), 2600);
};

const setButtonBusy = (button, busy, label) => {
  if (!button) {
    return;
  }
  if (busy) {
    button.dataset.label = button.textContent;
    if (label) {
      button.textContent = label;
    }
    button.classList.add("is-loading");
    button.disabled = true;
    return;
  }
  if (button.dataset.label) {
    button.textContent = button.dataset.label;
    delete button.dataset.label;
  }
  button.classList.remove("is-loading");
  button.disabled = false;
};

const setPreviewMeta = (text, loading = false) => {
  const meta = $("preview-meta");
  meta.textContent = text;
  meta.classList.toggle("loading", loading);
};

const defaultQueryState = () => ({
  mode: "builder",
  groups: [{ clauses: [] }],
  advanced_query: "",
});

const normalizeQueryState = (raw) => {
  if (!raw || typeof raw !== "object") {
    return defaultQueryState();
  }
  const mode = raw.mode === "advanced" ? "advanced" : "builder";
  const advanced_query = String(raw.advanced_query ?? raw.advancedQuery ?? "");
  const groups = Array.isArray(raw.groups) ? raw.groups : [];
  const normalizedGroups = groups.map((group) => {
    if (!group || typeof group !== "object") {
      return { clauses: [] };
    }
    const clauses = Array.isArray(group.clauses) ? group.clauses : [];
    const normalizedClauses = clauses
      .map((clause) => {
        if (!clause || typeof clause !== "object") {
          return null;
        }
        const field = String(clause.field ?? "").trim();
        const op = clause.op || "eq";
        const rawValues = clause.values ?? [];
        const values = Array.isArray(rawValues)
          ? rawValues.map((value) => String(value).trim()).filter(Boolean)
          : [String(rawValues).trim()].filter(Boolean);
        if (!field && values.length === 0) {
          return null;
        }
        return { field, op, values };
      })
      .filter(Boolean);
    return { clauses: normalizedClauses };
  });
  return {
    mode,
    groups: normalizedGroups.length ? normalizedGroups : [{ clauses: [] }],
    advanced_query,
  };
};

const parseQueryString = (query) => {
  const trimmed = String(query || "").trim();
  if (!trimmed) {
    return defaultQueryState();
  }
  const params = new URLSearchParams(trimmed);
  const clauses = [];
  const index = new Map();
  for (const [rawKey, rawValue] of params.entries()) {
    const key = String(rawKey || "").trim();
    const value = String(rawValue || "").trim();
    if (!key) {
      continue;
    }
    if (!index.has(key)) {
      const clause = { field: key, op: "eq", values: [] };
      index.set(key, clause);
      clauses.push(clause);
    }
    if (value) {
      index.get(key).values.push(value);
    }
  }
  return { mode: "builder", groups: [{ clauses }], advanced_query: "" };
};

const serializeQueryState = (queryState) => {
  if (queryState?.mode === "advanced") {
    return String(queryState.advanced_query || "").trim();
  }
  const params = new URLSearchParams();
  const groups = Array.isArray(queryState?.groups) ? queryState.groups : [];
  groups.forEach((group) => {
    const clauses = Array.isArray(group?.clauses) ? group.clauses : [];
    clauses.forEach((clause) => {
      const key = String(clause.field || "").trim();
      const values = Array.isArray(clause.values) ? clause.values : [];
      if (!key) {
        return;
      }
      values.forEach((value) => {
        const trimmed = String(value || "").trim();
        if (trimmed) {
          params.append(key, trimmed);
        }
      });
    });
  });
  return params.toString();
};

const ensureQueryState = (sectionKey) => {
  if (!state.queryStates[sectionKey]) {
    state.queryStates[sectionKey] = defaultQueryState();
  }
  return state.queryStates[sectionKey];
};

const getQueryGroup = (queryState) => {
  if (!Array.isArray(queryState.groups) || !queryState.groups.length) {
    queryState.groups = [{ clauses: [] }];
  }
  const group = queryState.groups[0];
  if (!Array.isArray(group.clauses)) {
    group.clauses = [];
  }
  return group;
};

const getCatalogFields = () => (Array.isArray(state.queryCatalog) ? state.queryCatalog : []);

const getCatalogField = (key) => getCatalogFields().find((field) => field.key === key);

const api = async (path, options = {}) => {
  const response = await fetch(path, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({ error: "Request failed" }));
    throw new Error(payload.error || "Request failed");
  }
  return response.json();
};

const getPlaylist = () => {
  if (!state.config) {
    return null;
  }
  return state.config.playlists[state.selectedIndex];
};

const updateStatus = (connected, metaText = "") => {
  const dot = $("plex-status-dot");
  const text = $("plex-status-text");
  const meta = $("plex-status-meta");
  if (connected) {
    dot.classList.add("connected");
    text.textContent = "Connected";
  } else {
    dot.classList.remove("connected");
    text.textContent = "Not connected";
  }
  meta.textContent = metaText;
};

const updatePlaylistOptions = () => {
  const select = $("playlist-select");
  select.innerHTML = "";
  state.config.playlists.forEach((playlist, index) => {
    const option = document.createElement("option");
    option.value = index;
    option.textContent = playlist.name || `Playlist ${index + 1}`;
    select.appendChild(option);
  });
  select.value = String(state.selectedIndex);
};

const updateAccountUI = () => {
  const pill = $("account-pill");
  const name = $("account-name");
  const username =
    state.account?.username ||
    state.account?.title ||
    state.account?.email ||
    "";
  if (username) {
    name.textContent = username;
    pill.hidden = false;
    updateStatus(true, `Connected as ${username}`);
  } else {
    pill.hidden = true;
  }
};

const updateServerPill = (serverName) => {
  const pill = $("server-pill");
  const name = $("server-name");
  if (serverName) {
    name.textContent = serverName;
    pill.hidden = false;
  } else {
    pill.hidden = true;
  }
};

const applyServers = () => {
  const select = $("plex-server-select");
  select.innerHTML = "";
  if (!state.servers.length) {
    const option = document.createElement("option");
    option.value = "";
    option.textContent = "No servers found";
    select.appendChild(option);
    return;
  }

  const currentUrl = normalizeUrl($("plex-url").value || "");
  let matched = false;
  state.servers.forEach((server, index) => {
    const option = document.createElement("option");
    option.value = server.preferredUri || "";
    option.textContent = server.name || `Server ${index + 1}`;
    select.appendChild(option);
    if (server.preferredUri && normalizeUrl(server.preferredUri) === currentUrl) {
      matched = true;
      select.value = server.preferredUri;
      updateServerPill(server.name);
    }
  });

  if (!matched && state.servers.length) {
    const preferred = state.servers[0];
    if (preferred && preferred.preferredUri) {
      $("plex-url").value = preferred.preferredUri;
      select.value = preferred.preferredUri;
      updateServerPill(preferred.name);
      showToast(`Using server: ${preferred.name}`);
    }
  }
};

const applyLibraries = () => {
  const tvSelect = $("tv-library");
  const movieSelect = $("movies-library");
  const currentTv = tvSelect.value;
  const currentMovies = movieSelect.value;
  tvSelect.innerHTML = "<option value=\"\">Select a library</option>";
  movieSelect.innerHTML = "<option value=\"\">Select a library</option>";
  state.libraries.forEach((library) => {
    const option = document.createElement("option");
    option.value = library.title;
    option.textContent = `${library.title} (${library.type})`;
    if (library.type === "show") {
      tvSelect.appendChild(option.cloneNode(true));
    }
    if (library.type === "movie") {
      movieSelect.appendChild(option);
    }
  });
  if (currentTv) {
    tvSelect.value = currentTv;
  }
  if (currentMovies) {
    movieSelect.value = currentMovies;
  }
};

const applyQueryState = (sectionKey, sectionConfig) => {
  const rawState = sectionConfig?.query_state;
  let queryState = normalizeQueryState(rawState);
  if (!rawState) {
    const fallbackQuery = sectionConfig?.query || "";
    queryState = fallbackQuery ? parseQueryString(fallbackQuery) : defaultQueryState();
  }
  if (queryState.mode === "advanced" && !queryState.advanced_query) {
    queryState.advanced_query = String(sectionConfig?.query || "");
  }
  state.queryStates[sectionKey] = queryState;
  renderQuerySection(sectionKey);
};

const renderQuerySection = (sectionKey) => {
  const queryState = ensureQueryState(sectionKey);
  const builderEl = $(`${sectionKey}-query-builder`);
  const advancedEl = $(`${sectionKey}-query-advanced`);
  const advancedInput = $(`${sectionKey}-query-advanced-input`);
  const buttons = document.querySelectorAll(
    `.query-mode-btn[data-section="${sectionKey}"]`,
  );
  buttons.forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.mode === queryState.mode);
  });
  if (builderEl) {
    builderEl.hidden = queryState.mode !== "builder";
  }
  if (advancedEl) {
    advancedEl.hidden = queryState.mode !== "advanced";
  }
  if (advancedInput && queryState.mode === "advanced") {
    advancedInput.value = queryState.advanced_query || "";
  }
  if (builderEl && queryState.mode === "builder") {
    renderQueryBuilder(sectionKey);
  }
};

const setQueryMode = (sectionKey, mode) => {
  const queryState = ensureQueryState(sectionKey);
  if (mode === "advanced" && queryState.mode !== "advanced") {
    queryState.advanced_query = serializeQueryState(queryState);
    queryState.mode = "advanced";
    renderQuerySection(sectionKey);
    return;
  }
  if (mode === "builder" && queryState.mode !== "builder") {
    const parsed = parseQueryString(queryState.advanced_query);
    queryState.mode = "builder";
    queryState.groups = parsed.groups;
    renderQuerySection(sectionKey);
    return;
  }
  queryState.mode = mode;
  renderQuerySection(sectionKey);
};

const renderQueryBuilder = (sectionKey) => {
  const container = $(`${sectionKey}-query-builder`);
  if (!container) {
    return;
  }
  container.innerHTML = "";
  const queryState = ensureQueryState(sectionKey);
  const group = getQueryGroup(queryState);
  const clauses = group.clauses;
  if (!clauses.length) {
    const empty = document.createElement("div");
    empty.className = "query-empty";
    empty.textContent = "No filters yet. Add one to get started.";
    container.appendChild(empty);
  }

  clauses.forEach((clause, index) => {
    const row = document.createElement("div");
    row.className = "query-clause";

    const rowGrid = document.createElement("div");
    rowGrid.className = "query-row";

    const fieldCell = document.createElement("div");
    fieldCell.className = "query-field";
    const fieldSelect = document.createElement("select");
    const catalog = getCatalogFields();
    catalog.forEach((field) => {
      const option = document.createElement("option");
      option.value = field.key;
      option.textContent = field.label || field.key;
      fieldSelect.appendChild(option);
    });
    const customOption = document.createElement("option");
    customOption.value = "__custom__";
    customOption.textContent = "Custom filter";
    fieldSelect.appendChild(customOption);

    const fieldDef = getCatalogField(clause.field);
    const isCustom = !fieldDef;
    fieldSelect.value = isCustom ? "__custom__" : fieldDef.key;
    fieldSelect.addEventListener("change", (event) => {
      const next = event.target.value;
      if (next === "__custom__") {
        clause.field = "";
        clause.op = "custom";
        clause.values = [];
      } else {
        const selected = getCatalogField(next);
        clause.field = selected?.key || next;
        clause.op = selected?.ops?.[0] || "eq";
        clause.values = [];
      }
      renderQueryBuilder(sectionKey);
    });
    fieldCell.appendChild(fieldSelect);

    if (isCustom) {
      const keyInput = document.createElement("input");
      keyInput.type = "text";
      keyInput.placeholder = "Field key (e.g., label)";
      keyInput.value = clause.field || "";
      keyInput.addEventListener("input", (event) => {
        clause.field = event.target.value;
      });
      fieldCell.appendChild(keyInput);
    }

    const valuesCell = document.createElement("div");
    valuesCell.className = "query-values";

    if (isCustom) {
      const textarea = document.createElement("textarea");
      textarea.rows = 2;
      textarea.placeholder = "Values (one per line)";
      textarea.value = listToLines(clause.values || []);
      textarea.addEventListener("input", (event) => {
        clause.values = linesToList(event.target.value);
      });
      valuesCell.appendChild(textarea);
    } else if (fieldDef.input_kind === "boolean") {
      const label = document.createElement("label");
      label.className = "checkbox";
      const input = document.createElement("input");
      input.type = "checkbox";
      input.checked = Array.isArray(clause.values) && clause.values.length > 0;
      input.addEventListener("change", () => {
        clause.values = input.checked ? ["1"] : [];
      });
      label.appendChild(input);
      const span = document.createElement("span");
      span.textContent = fieldDef.label || "Enabled";
      label.appendChild(span);
      valuesCell.appendChild(label);
    } else if (fieldDef.input_kind === "multiselect") {
      const selected = new Set(Array.isArray(clause.values) ? clause.values : []);
      const options = state.queryOptions[sectionKey]?.[fieldDef.key] || [];
      const merged = options.slice();
      selected.forEach((value) => {
        if (!merged.includes(value)) {
          merged.push(value);
        }
      });
      const optionsWrap = document.createElement("div");
      optionsWrap.className = "query-options";
      if (!merged.length) {
        const empty = document.createElement("div");
        empty.className = "query-option";
        empty.textContent = "No options loaded yet.";
        optionsWrap.appendChild(empty);
      } else {
        merged.forEach((value) => {
          const optionLabel = document.createElement("label");
          optionLabel.className = "query-option";
          if (!options.includes(value)) {
            optionLabel.classList.add("custom");
          }
          const checkbox = document.createElement("input");
          checkbox.type = "checkbox";
          checkbox.checked = selected.has(value);
          checkbox.addEventListener("change", () => {
            if (checkbox.checked) {
              selected.add(value);
            } else {
              selected.delete(value);
            }
            clause.values = merged.filter((item) => selected.has(item));
          });
          optionLabel.appendChild(checkbox);
          optionLabel.appendChild(document.createTextNode(value));
          optionsWrap.appendChild(optionLabel);
        });
      }
      valuesCell.appendChild(optionsWrap);

      const addRow = document.createElement("div");
      addRow.className = "inline-add";
      const otherInput = document.createElement("input");
      otherInput.type = "text";
      otherInput.placeholder = "Other...";
      const addBtn = document.createElement("button");
      addBtn.type = "button";
      addBtn.className = "btn ghost small";
      addBtn.textContent = "Add";
      addBtn.addEventListener("click", () => {
        const value = otherInput.value.trim();
        if (!value) {
          return;
        }
        if (!selected.has(value)) {
          const existing = Array.isArray(clause.values) ? clause.values : [];
          clause.values = Array.from(new Set([...existing, value].filter(Boolean)));
          renderQueryBuilder(sectionKey);
        }
        otherInput.value = "";
      });
      addRow.appendChild(otherInput);
      addRow.appendChild(addBtn);
      valuesCell.appendChild(addRow);
    } else {
      const input = document.createElement("input");
      input.type = fieldDef.input_kind === "number" ? "number" : "text";
      input.placeholder = "Value";
      input.value = Array.isArray(clause.values) ? clause.values[0] || "" : "";
      input.addEventListener("input", (event) => {
        const value = event.target.value.trim();
        clause.values = value ? [value] : [];
      });
      valuesCell.appendChild(input);
    }

    const actions = document.createElement("div");
    actions.className = "query-actions";
    const removeBtn = document.createElement("button");
    removeBtn.type = "button";
    removeBtn.className = "btn small danger";
    removeBtn.textContent = "Remove";
    removeBtn.addEventListener("click", () => {
      group.clauses.splice(index, 1);
      renderQueryBuilder(sectionKey);
    });
    actions.appendChild(removeBtn);

    rowGrid.appendChild(fieldCell);
    rowGrid.appendChild(valuesCell);
    rowGrid.appendChild(actions);
    row.appendChild(rowGrid);
    container.appendChild(row);
  });

  const addWrap = document.createElement("div");
  addWrap.className = "query-add";
  const addBtn = document.createElement("button");
  addBtn.type = "button";
  addBtn.className = "btn ghost small";
  addBtn.textContent = "Add filter";
  addBtn.addEventListener("click", () => {
    const group = getQueryGroup(queryState);
    const catalog = getCatalogFields();
    const seedField = catalog[0];
    if (seedField) {
      group.clauses.push({ field: seedField.key, op: seedField.ops?.[0] || "eq", values: [] });
    } else {
      group.clauses.push({ field: "", op: "custom", values: [] });
    }
    renderQueryBuilder(sectionKey);
  });
  addWrap.appendChild(addBtn);
  container.appendChild(addWrap);
};

const loadQueryOptions = async (sectionKey) => {
  if (!state.tokenSet) {
    state.queryOptions[sectionKey] = {};
    renderQueryBuilder(sectionKey);
    return;
  }
  const library = $(`${sectionKey}-library`).value.trim();
  if (!library) {
    state.queryOptions[sectionKey] = {};
    renderQueryBuilder(sectionKey);
    return;
  }
  const catalog = getCatalogFields().filter((field) => field.options_source);
  if (!catalog.length) {
    return;
  }
  const mediaType = sectionKey === "tv" ? "show" : "movie";
  let hadError = false;
  const results = await Promise.all(
    catalog.map(async (field) => {
      const source = String(field.options_source || "").replace("plex:", "");
      const url = `/api/plex/options?library=${encodeURIComponent(library)}&source=${encodeURIComponent(
        source,
      )}&media_type=${encodeURIComponent(mediaType)}`;
      try {
        const data = await api(url);
        return { key: field.key, options: data.options || [], error: null };
      } catch (err) {
        if (!hadError) {
          showToast(err.message);
          hadError = true;
        }
        return { key: field.key, options: [], error: err.message };
      }
    }),
  );
  results.forEach((result) => {
    state.queryOptions[sectionKey][result.key] = result.options;
    if (result.error) {
      state.queryOptionErrors[sectionKey][result.key] = result.error;
    } else {
      delete state.queryOptionErrors[sectionKey][result.key];
    }
  });
  renderQueryBuilder(sectionKey);
};

const loadAccount = async () => {
  try {
    const data = await api("/api/plex/account");
    state.account = data.account || null;
    updateAccountUI();
  } catch (err) {
    state.account = null;
    updateAccountUI();
  }
};

const loadServers = async () => {
  try {
    const data = await api("/api/plex/resources");
    state.servers = data.servers || [];
    applyServers();
  } catch (err) {
    state.servers = [];
    applyServers();
  }
};

const loadConfig = async () => {
  const data = await api("/api/config");
  state.config = data.config || { playlists: [defaultPlaylist()] };
  state.tokenSet = Boolean(data.meta && data.meta.token_set);
  state.queryCatalog = Array.isArray(data.meta?.query_fields) ? data.meta.query_fields : [];
  if (!state.config.playlists || !state.config.playlists.length) {
    state.config.playlists = [defaultPlaylist()];
  }
  state.selectedIndex = 0;
  updateStatus(state.tokenSet);
  updatePlaylistOptions();
  applyConfigToForm();
};

const applyConfigToForm = () => {
  if (!state.config) {
    return;
  }
  const playlist = getPlaylist();
  const schedule = state.config.schedule || {};
  $("plex-url").value = state.config.plex?.url || "";
  $("schedule-interval").value = schedule.interval_minutes ?? 0;
  $("schedule-jitter").value = schedule.jitter_seconds ?? 0;

  $("playlist-name").value = playlist.name || "";
  $("playlist-description").value = playlist.description || "";

  $("tv-library").value = playlist.tv?.library || "";
  applyQueryState("tv", playlist.tv || {});
  $("tv-include").value = listToLines(playlist.tv?.include_titles || []);
  $("tv-exclude").value = listToLines(playlist.tv?.exclude_titles || []);
  $("tv-unwatched").checked = Boolean(playlist.tv?.episode_filters?.unwatched_only);
  $("tv-exclude-days").value = playlist.tv?.episode_filters?.exclude_watched_days ?? 0;
  $("tv-max-per-show").value = playlist.tv?.episode_filters?.max_per_show ?? 0;
  $("tv-strategy").value = playlist.tv?.order?.strategy || "rounds";
  $("tv-chunk").value = playlist.tv?.order?.chunk_size ?? 1;
  $("tv-seed").value = playlist.tv?.order?.seed || "";

  $("movies-enabled").checked = Boolean(playlist.movies?.enabled);
  $("movies-library").value = playlist.movies?.library || "";
  applyQueryState("movies", playlist.movies || {});
  $("movies-collections").checked = Boolean(playlist.movies?.collections_as_shows);
  $("movies-include-collections").value = listToLines(playlist.movies?.include_collections || []);
  $("movies-exclude-collections").value = listToLines(playlist.movies?.exclude_collections || []);
  $("movies-every").value = playlist.movies?.ratio?.every_episodes ?? 0;
  $("movies-max").value = playlist.movies?.ratio?.max_movies ?? 0;
  $("movies-unwatched").checked = Boolean(playlist.movies?.filters?.unwatched_only);
  $("movies-exclude-days").value = playlist.movies?.filters?.exclude_watched_days ?? 0;
  $("movies-strategy").value = playlist.movies?.order?.strategy || "rounds";
  $("movies-chunk").value = playlist.movies?.order?.chunk_size ?? 1;
  $("movies-seed").value = playlist.movies?.order?.seed || "";

  $("output-mode").value = playlist.output?.mode || "replace";
  $("output-limit").value = playlist.output?.limit_items ?? 0;
  $("output-chunk").value = playlist.output?.chunk_size ?? 200;

  toggleMoviesSection();
  updatePlaylistOptions();
};

const readFormToConfig = () => {
  if (!state.config) {
    state.config = { playlists: [defaultPlaylist()] };
  }
  const playlist = getPlaylist();
  state.config.plex = state.config.plex || {};
  state.config.plex.url = $("plex-url").value.trim();
  state.config.schedule = state.config.schedule || {};
  state.config.schedule.interval_minutes = toInt($("schedule-interval").value);
  state.config.schedule.jitter_seconds = toInt($("schedule-jitter").value);

  playlist.name = $("playlist-name").value.trim();
  playlist.description = $("playlist-description").value.trim();

  playlist.tv = playlist.tv || {};
  playlist.tv.library = $("tv-library").value.trim();
  {
    const queryState = normalizeQueryState(state.queryStates.tv);
    playlist.tv.query_state = queryState;
    playlist.tv.query = serializeQueryState(queryState);
  }
  playlist.tv.include_titles = linesToList($("tv-include").value);
  playlist.tv.exclude_titles = linesToList($("tv-exclude").value);
  playlist.tv.episode_filters = playlist.tv.episode_filters || {};
  playlist.tv.episode_filters.unwatched_only = $("tv-unwatched").checked;
  playlist.tv.episode_filters.exclude_watched_days = toInt($("tv-exclude-days").value);
  playlist.tv.episode_filters.max_per_show = toInt($("tv-max-per-show").value);
  playlist.tv.order = playlist.tv.order || {};
  playlist.tv.order.strategy = $("tv-strategy").value;
  playlist.tv.order.chunk_size = toInt($("tv-chunk").value) || 1;
  playlist.tv.order.seed = $("tv-seed").value.trim();

  playlist.movies = playlist.movies || {};
  playlist.movies.enabled = $("movies-enabled").checked;
  playlist.movies.library = $("movies-library").value.trim();
  {
    const queryState = normalizeQueryState(state.queryStates.movies);
    playlist.movies.query_state = queryState;
    playlist.movies.query = serializeQueryState(queryState);
  }
  playlist.movies.collections_as_shows = $("movies-collections").checked;
  playlist.movies.include_collections = linesToList($("movies-include-collections").value);
  playlist.movies.exclude_collections = linesToList($("movies-exclude-collections").value);
  playlist.movies.ratio = playlist.movies.ratio || {};
  playlist.movies.ratio.every_episodes = toInt($("movies-every").value);
  playlist.movies.ratio.max_movies = toInt($("movies-max").value);
  playlist.movies.filters = playlist.movies.filters || {};
  playlist.movies.filters.unwatched_only = $("movies-unwatched").checked;
  playlist.movies.filters.exclude_watched_days = toInt($("movies-exclude-days").value);
  playlist.movies.order = playlist.movies.order || {};
  playlist.movies.order.strategy = $("movies-strategy").value;
  playlist.movies.order.chunk_size = toInt($("movies-chunk").value) || 1;
  playlist.movies.order.seed = $("movies-seed").value.trim();

  playlist.output = playlist.output || {};
  playlist.output.mode = $("output-mode").value;
  playlist.output.limit_items = toInt($("output-limit").value);
  playlist.output.chunk_size = toInt($("output-chunk").value) || 200;

  updatePlaylistOptions();
};

const saveConfig = async ({ silent = false, toast = "Config saved" } = {}) => {
  readFormToConfig();
  await api("/api/config", {
    method: "POST",
    body: JSON.stringify(state.config),
  });
  if (!silent) {
    showToast(toast);
  }
};

const toggleMoviesSection = () => {
  const enabled = $("movies-enabled").checked;
  const section = [
    "movies-library",
    "movies-collections",
    "movies-include-collections",
    "movies-exclude-collections",
    "movies-every",
    "movies-max",
    "movies-unwatched",
    "movies-exclude-days",
    "movies-strategy",
    "movies-chunk",
    "movies-seed",
  ];
  section.forEach((id) => {
    const el = $(id);
    if (el) {
      el.disabled = !enabled;
    }
  });
  toggleQueryBlock("movies", enabled);
};

const toggleQueryBlock = (sectionKey, enabled) => {
  const block = $(`${sectionKey}-query-block`);
  if (!block) {
    return;
  }
  block.querySelectorAll("input, select, textarea, button").forEach((el) => {
    el.disabled = !enabled;
  });
};

const addPlaylist = () => {
  readFormToConfig();
  const count = state.config.playlists.length + 1;
  state.config.playlists.push(defaultPlaylist(`Playlist ${count}`));
  state.selectedIndex = state.config.playlists.length - 1;
  updatePlaylistOptions();
  applyConfigToForm();
};

const connectPlex = async () => {
  try {
    const plexUrl = $("plex-url").value.trim();
    const payload = await api("/api/plex/pin", {
      method: "POST",
      body: JSON.stringify({ plex_url: plexUrl }),
    });
    $("auth-code").textContent = payload.code;
    $("auth-code-pill").hidden = false;
    updateStatus(false, "Waiting for Plex authorization...");
    window.open(payload.auth_url, "_blank", "noopener,noreferrer");
    if (state.pinPoll) {
      clearInterval(state.pinPoll);
    }
    state.pinPoll = setInterval(async () => {
      try {
        const result = await api(`/api/plex/pin/${payload.pin_id}`);
        if (result.authorized) {
          clearInterval(state.pinPoll);
          state.pinPoll = null;
          $("auth-code-pill").hidden = true;
          updateStatus(true, "Token stored");
          await loadConfig();
          await loadAccount();
          await loadServers();
          await refreshLibraries();
          showToast("Plex connected");
        }
      } catch (err) {
        showToast(err.message);
      }
    }, 3000);
  } catch (err) {
    showToast(err.message);
  }
};

const refreshLibraries = async () => {
  try {
    await saveConfig({ silent: true });
    const data = await api("/api/libraries");
    state.libraries = data.libraries || [];
    applyLibraries();
    await loadQueryOptions("tv");
    await loadQueryOptions("movies");
    showToast("Libraries refreshed");
  } catch (err) {
    showToast(err.message);
  }
};

const previewPlaylist = async () => {
  const previewBtn = $("preview-btn");
  const runBtn = $("run-btn");
  const list = $("preview-list");
  setButtonBusy(previewBtn, true, "Generating preview...");
  runBtn.disabled = true;
  list.innerHTML = "";
  setPreviewMeta("Generating preview... this can take a minute for large libraries.", true);
  try {
    await saveConfig({ silent: true });
    const payload = await api("/api/preview", {
      method: "POST",
      body: JSON.stringify({ playlist_index: state.selectedIndex, limit: 40 }),
    });
    payload.items.forEach((item) => {
      const row = document.createElement("div");
      row.className = "preview-item";
      if (item.type === "episode") {
        const season = String(item.season || 0).padStart(2, "0");
        const episode = String(item.episode || 0).padStart(2, "0");
        row.textContent = `${item.show_title} S${season}E${episode} - ${item.title}`;
      } else {
        row.textContent = `Movie - ${item.title}`;
      }
      list.appendChild(row);
    });
    const stats = payload.stats || {};
    setPreviewMeta(
      `${stats.shows || 0} shows, ${stats.episodes || 0} episodes, ${stats.movies || 0} movies`,
      false,
    );
    showToast("Preview generated");
  } catch (err) {
    setPreviewMeta(`Preview failed: ${err.message}`, false);
    showToast(err.message);
  } finally {
    setButtonBusy(previewBtn, false);
    runBtn.disabled = false;
  }
};

const runPlaylist = async () => {
  const runBtn = $("run-btn");
  const previewBtn = $("preview-btn");
  setButtonBusy(runBtn, true, "Generating playlist...");
  previewBtn.disabled = true;
  setPreviewMeta("Generating playlist in Plex...", true);
  try {
    await saveConfig({ silent: true });
    const payload = await api("/api/run", {
      method: "POST",
      body: JSON.stringify({ playlist_index: state.selectedIndex }),
    });
    setPreviewMeta(
      payload.playlist ? `Playlist updated: ${payload.playlist}` : "Playlist updated",
      false,
    );
    if (payload.playlist) {
      showToast(`Playlist updated: ${payload.playlist}`);
    } else {
      showToast("Playlist updated");
    }
  } catch (err) {
    setPreviewMeta(`Playlist generation failed: ${err.message}`, false);
    showToast(err.message);
  } finally {
    setButtonBusy(runBtn, false);
    previewBtn.disabled = false;
  }
};

const bindEvents = () => {
  $("connect-btn").addEventListener("click", connectPlex);
  $("refresh-libraries").addEventListener("click", refreshLibraries);
  $("plex-server-select").addEventListener("change", (event) => {
    const value = event.target.value || "";
    if (value) {
      $("plex-url").value = value;
    }
    const server = state.servers.find((entry) => entry.preferredUri === value);
    updateServerPill(server ? server.name : "");
  });
  $("playlist-select").addEventListener("change", (event) => {
    readFormToConfig();
    state.selectedIndex = toInt(event.target.value);
    applyConfigToForm();
  });
  $("playlist-add").addEventListener("click", addPlaylist);
  $("save-btn").addEventListener("click", saveConfig);
  $("movies-enabled").addEventListener("change", toggleMoviesSection);
  $("tv-library").addEventListener("change", () => {
    loadQueryOptions("tv");
    renderQuerySection("tv");
  });
  $("movies-library").addEventListener("change", () => {
    loadQueryOptions("movies");
    renderQuerySection("movies");
  });
  document.querySelectorAll(".query-mode-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const section = btn.dataset.section;
      const mode = btn.dataset.mode;
      if (section && mode) {
        setQueryMode(section, mode);
      }
    });
  });
  ["tv", "movies"].forEach((sectionKey) => {
    const input = $(`${sectionKey}-query-advanced-input`);
    if (input) {
      input.addEventListener("input", () => {
        const queryState = ensureQueryState(sectionKey);
        queryState.advanced_query = input.value;
      });
    }
  });
  $("preview-btn").addEventListener("click", previewPlaylist);
  $("run-btn").addEventListener("click", runPlaylist);
  [
    "playlist-name",
    "playlist-description",
    "tv-library",
    "movies-library",
  ].forEach((id) => {
    const el = $(id);
    if (el) {
      el.addEventListener("input", updatePlaylistOptions);
    }
  });
};

const init = async () => {
  bindEvents();
  await loadConfig();
  if (state.tokenSet) {
    await loadAccount();
    await loadServers();
    await refreshLibraries();
  }
};

document.addEventListener("DOMContentLoaded", init);
