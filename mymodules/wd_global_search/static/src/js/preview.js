(function () {
    "use strict";

    const list = document.querySelector("#wd-result-list");
    const queryInput = document.querySelector("[data-testid='search-query']");
    const form = document.querySelector(".wd-query-bar");
    const conditionView = document.querySelector("#wd-effective-conditions");
    const activeView = document.querySelector("#wd-active-refinements");
    const workspace = document.querySelector("[data-testid='global-search-workspace']");
    const resourceTabs = document.querySelector("#wd-resource-tabs");
    const resourceEmpty = document.querySelector("[data-testid='resource-empty']");
    const reselectAllButton = document.querySelector("[data-testid='reselect-all']");
    const pagination = document.querySelector("[data-testid='pagination']");
    const pageSizeInput = document.querySelector("[data-testid='page-size']");
    const pageSummary = document.querySelector("[data-testid='page-summary']");
    const pageControls = document.querySelector("[data-testid='page-controls']");
    if (!list || !queryInput || !form || !conditionView || !activeView || !workspace
        || !resourceTabs || !resourceEmpty || !reselectAllButton
        || !pagination || !pageSizeInput || !pageSummary || !pageControls) {
        return;
    }
    function isNarrowWorkspace() {
        return window.matchMedia("(max-width: 700px)").matches;
    }

    const state = {
        rawQuery: "",
        resources: new Set(),
        refinements: [],
        cursor: null,
        pageSize: 10,
        currentPage: 1,
        totalResultCount: 0,
        hasSearched: false,
        resourceSelectionInitialized: false,
        configVersion: workspace.dataset.configVersion || null,
    };
    let searchSequence = 0;

    function text(value) {
        if (value === false || value === null || value === undefined || value === "") {
            return "—";
        }
        if (Array.isArray(value)) {
            return value.length > 1 ? value[1] : String(value[0] || "—");
        }
        return String(value);
    }

    function conditionPayload() {
        return state.refinements.map((item) => ({
            dimension: item.dimension,
            value: item.value,
            operator: item.operator || "ilike",
        }));
    }

    function dateRefinement() {
        const start = document.querySelector("#wd-date-start").value;
        const end = document.querySelector("#wd-date-end").value;
        if (start || end) {
            if (!start || !end || end <= start) {
                return null;
            }
            return {dimension: "date", value: {start: start, end: end}, operator: "between"};
        }
        const preset = document.querySelector("#wd-date-refinement").value;
        return preset ? {dimension: "date", value: preset, operator: "="} : null;
    }

    function applyDateRefinement() {
        state.refinements = state.refinements.filter((item) => item.dimension !== "date");
        const refinement = dateRefinement();
        if (refinement) {
            state.refinements.push(refinement);
        }
        state.cursor = null;
        state.currentPage = 1;
        search();
    }

    function renderUnderstanding(conditions) {
        conditionView.textContent = conditions.length
            ? conditions.map((item) => item.dimension + "=" + item.value).join(" · ")
            : "No conditions";
        activeView.innerHTML = state.refinements.map((item, index) => (
            '<button type="button" class="wd-refinement-chip" data-refinement-index="'
            + index + '">' + text(item.dimension) + ": " + text(item.value) + " ×</button>"
        )).join("");
        activeView.querySelectorAll("button").forEach((button) => {
            button.addEventListener("click", () => {
                state.refinements.splice(Number(button.dataset.refinementIndex), 1);
                state.cursor = null;
                state.currentPage = 1;
                search();
            });
        });
    }

    function resourceKeys() {
        return Array.from(resourceTabs.querySelectorAll(".wd-resource-tab"))
            .map((button) => button.dataset.resource)
            .filter(Boolean);
    }

    function renderSelectionState() {
        const keys = resourceKeys();
        const emptySelection = state.hasSearched && state.resources.size === 0;
        resourceTabs.hidden = !state.hasSearched;
        resourceEmpty.hidden = !emptySelection;
        reselectAllButton.hidden = !emptySelection || keys.length === 0;
        const message = resourceEmpty.querySelector("p");
        message.textContent = keys.length
            ? "Select at least one Resource to show results."
            : "No accessible Resources are available.";
        resourceTabs.querySelectorAll(".wd-resource-tab").forEach((button) => {
            button.setAttribute(
                "aria-pressed",
                String(state.resources.has(button.dataset.resource))
            );
        });
    }

    function clearResourceCounts() {
        document.querySelectorAll("[data-count-for]").forEach((element) => {
            element.textContent = "…";
            element.removeAttribute("title");
        });
    }

    function renderResourceDescriptors(descriptors, configVersion) {
        if (!Array.isArray(descriptors)) {
            return false;
        }
        const descriptorByKey = new Map(
            descriptors
                .filter((item) => item && typeof item.key === "string" && item.key)
                .map((item) => [item.key, item])
        );
        const nextKeys = new Set(descriptorByKey.keys());
        resourceTabs.querySelectorAll(".wd-resource-tab").forEach((button) => {
            if (!nextKeys.has(button.dataset.resource)) {
                state.resources.delete(button.dataset.resource);
                button.remove();
            }
        });
        descriptorByKey.forEach((descriptor, key) => {
            let button = Array.from(resourceTabs.querySelectorAll(".wd-resource-tab"))
                .find((item) => item.dataset.resource === key);
            if (!button) {
                button = document.createElement("button");
                button.type = "button";
                button.className = "wd-resource-tab";
                button.dataset.resource = key;
                button.dataset.testid = "resource-" + key;
                button.setAttribute("aria-pressed", "false");
                const label = document.createElement("span");
                label.className = "wd-resource-label";
                const count = document.createElement("span");
                count.className = "wd-resource-count";
                count.dataset.countFor = key;
                button.append(label, document.createTextNode(" "), count);
                resourceTabs.append(button);
            }
            button.querySelector(".wd-resource-label").textContent = text(descriptor.label || key);
        });
        let selectionChanged = false;
        for (const key of state.resources) {
            if (!nextKeys.has(key)) {
                state.resources.delete(key);
                selectionChanged = true;
            }
        }
        const previousVersion = state.configVersion;
        state.configVersion = configVersion === undefined || configVersion === null
            ? state.configVersion
            : String(configVersion);
        state.resourceSelectionInitialized = true;
        return selectionChanged || previousVersion !== state.configVersion;
    }

    function renderCounts(data) {
        const resourceCounts = (data && data.resource_counts) || {};
        const errors = (data && data.errors) || [];
        const failures = new Map();
        errors.forEach((item) => {
            if (item.resource) {
                failures.set(item.resource, item.code || "Unavailable");
            }
        });
        ((data && data.meta && data.meta.failed_resources) || []).forEach((key) => {
            if (!failures.has(key)) {
                failures.set(key, "Unavailable");
            }
        });
        document.querySelectorAll("[data-count-for]").forEach((element) => {
            const key = element.dataset.countFor;
            const button = element.closest(".wd-resource-tab");
            if (failures.has(key)) {
                const code = failures.get(key);
                const status = code === "TIMEOUT" ? "Timeout" : "Unavailable";
                element.textContent = "— " + status;
                button.hidden = false;
                button.title = status;
                return;
            }
            button.removeAttribute("title");
            if (!Object.prototype.hasOwnProperty.call(resourceCounts, key)) {
                element.textContent = "—";
                button.hidden = false;
                return;
            }
            const count = Number(resourceCounts[key]);
            if (!Number.isSafeInteger(count) || count < 0) {
                element.textContent = "—";
                button.hidden = false;
                return;
            }
            if (count === 0) {
                element.textContent = "";
                button.hidden = true;
                state.resources.delete(key);
                return;
            }
            element.textContent = String(count);
            button.hidden = false;
        });
        renderSelectionState();
    }

    async function openNativeForm(model, recordId) {
        const query = new URLSearchParams({model: model, record_id: recordId});
        const response = await fetch("/wd_global_search/api/form_url?" + query.toString(), {
            credentials: "same-origin",
            headers: {"Accept": "application/json"},
        });
        const data = await response.json();
        if (data.status !== "SUCCESS") {
            list.insertAdjacentHTML(
                "afterbegin",
                '<p class="wd-safe-message" data-testid="action-error">'
                    + text(data.status || "Record unavailable") + "</p>"
            );
            return;
        }
        window.open(data.url, "_blank", "noopener,noreferrer");
    }

    function renderResults(data) {
        if (data.status && !["SUCCESS", "EMPTY", "PARTIAL_SUCCESS"].includes(data.status)) {
            list.innerHTML = '<p class="wd-safe-message" data-testid="search-error">'
                + text(data.status) + "</p>";
            return;
        }
        if (state.hasSearched && state.resources.size === 0) {
            const message = data.status === "FAILED"
                ? "Resource counts are unavailable. Select a Resource and retry."
                : "Select at least one Resource to show results.";
            list.innerHTML = '<p class="wd-muted" data-testid="resource-selection-prompt">'
                + message + "</p>";
            if (data.status === "PARTIAL_SUCCESS") {
                list.insertAdjacentHTML(
                    "afterbegin",
                    '<p class="wd-safe-message" data-testid="partial-success">'
                        + "Some Resource counts are unavailable.</p>"
                );
            }
            return;
        }
        if (data.status === "EMPTY" || !data.results.length) {
            list.innerHTML = '<p class="wd-muted" data-testid="empty-results">No results found.</p>';
            return;
        }
        list.innerHTML = data.results.map((result) => {
            const title = result.display_name || result.name || result._record_id;
            const model = result._model;
            return '<button class="wd-record-card" type="button" data-testid="record-card"'
                + ' aria-pressed="false" data-model="' + model
                + '" data-record-id="' + result._record_id + '"><strong>' + text(title)
                + '</strong><span>' + text(result._resource) + "</span></button>";
        }).join("");
        if (data.status === "PARTIAL_SUCCESS") {
            list.insertAdjacentHTML(
                "afterbegin",
                '<p class="wd-safe-message" data-testid="partial-success">Some resources are unavailable.</p>'
            );
        }
        list.querySelectorAll("button").forEach((button) => {
            button.addEventListener("click", () => {
                list.querySelectorAll(".wd-record-card").forEach((record) => {
                    record.setAttribute("aria-pressed", "false");
                });
                button.setAttribute("aria-pressed", "true");
            });
            button.addEventListener("dblclick", () => openNativeForm(
                button.dataset.model, button.dataset.recordId
            ));
            button.title = "Double-click to open the configured read-only Odoo form";
        });
    }

    function pageNumberWindow(currentPage, totalPages) {
        if (totalPages <= 7) {
            return Array.from({length: totalPages}, (_, index) => index + 1);
        }
        if (currentPage <= 4) {
            return [1, 2, 3, 4, 5, "…", totalPages];
        }
        if (currentPage >= totalPages - 3) {
            return [1, "…", ...Array.from({length: 5}, (_, index) => totalPages - 4 + index)];
        }
        return [1, "…", currentPage - 1, currentPage, currentPage + 1, "…", totalPages];
    }

    function renderPagination(data) {
        if (!["SUCCESS", "EMPTY", "PARTIAL_SUCCESS"].includes(data.status)) {
            pagination.hidden = true;
            return;
        }
        pagination.hidden = !state.hasSearched;
        const count = Number(data.counts && data.counts.all);
        if (!Number.isSafeInteger(count) || count < 0) {
            pageSummary.textContent = "Pagination unavailable: exact result count is missing.";
            pageControls.hidden = true;
            return;
        }
        if (data.status === "PARTIAL_SUCCESS") {
            pageSummary.textContent = "Partial results; total pages are unavailable.";
            pageControls.hidden = true;
            return;
        }
        state.totalResultCount = count;
        const totalPages = Math.ceil(count / state.pageSize);
        pageSummary.textContent = count
            ? "Showing " + ((state.currentPage - 1) * state.pageSize + 1)
                + "–" + Math.min(state.currentPage * state.pageSize, count)
                + " of " + count
            : "0 records";
        pageControls.hidden = totalPages <= 1;
        if (totalPages <= 1) {
            pageControls.innerHTML = "";
            return;
        }

        const button = (label, action, page, disabled, current) => (
            '<button class="wd-page-button" type="button" data-page-action="' + action
            + '" data-page="' + page + '" aria-label="' + label
            + '"' + (current ? ' aria-current="page"' : "")
            + (disabled ? " disabled" : "") + ">" + label + "</button>"
        );
        const entries = pageNumberWindow(state.currentPage, totalPages).map((entry) => (
            entry === "…"
                ? '<span class="wd-page-ellipsis" aria-hidden="true">…</span>'
                : button(
                    String(entry),
                    "page",
                    entry,
                    false,
                    entry === state.currentPage
                )
        ));
        pageControls.innerHTML = [
            button("First", "first", 1, state.currentPage === 1, false),
            button("Previous", "previous", state.currentPage - 1, state.currentPage === 1, false),
            ...entries,
            button("Next", "next", state.currentPage + 1, state.currentPage === totalPages, false),
            button("Last", "last", totalPages, state.currentPage === totalPages, false),
        ].join("");
    }

    async function search(scrollToResults = false) {
        const requestSequence = ++searchSequence;
        if (!state.resourceSelectionInitialized) {
            state.resources = new Set(resourceKeys());
            state.resourceSelectionInitialized = true;
        }
        state.hasSearched = true;
        clearResourceCounts();
        const payload = {
            query: state.rawQuery,
            conditions: [],
            refinement_conditions: conditionPayload(),
            resources: Array.from(state.resources),
            limit: state.pageSize,
            offset: (state.currentPage - 1) * state.pageSize,
            cursor: null,
        };
        list.innerHTML = '<p class="wd-muted">Searching…</p>';
        try {
            const response = await fetch("/wd_global_search/api/search", {
                method: "POST",
                credentials: "same-origin",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({jsonrpc: "2.0", method: "call", params: payload}),
            });
            const envelope = await response.json();
            const data = envelope.result || envelope;
            if (requestSequence !== searchSequence) {
                return;
            }
            const versionChanged = renderResourceDescriptors(
                data.meta && data.meta.resource_descriptors,
                data.meta && data.meta.config_version
            );
            if (
                versionChanged
                && data.status === "FAILED"
                && (data.errors || []).some((item) => item.code === "INVALID_REQUEST")
            ) {
                state.currentPage = 1;
                state.cursor = null;
                return search(scrollToResults);
            }
            if (["SUCCESS", "EMPTY"].includes(data.status)) {
                const count = Number(data.counts && data.counts.all);
                if (Number.isSafeInteger(count) && count >= 0) {
                    const totalPages = Math.ceil(count / state.pageSize);
                    const lastPage = Math.max(totalPages, 1);
                    if (state.currentPage > lastPage) {
                        state.currentPage = lastPage;
                        state.cursor = null;
                        return search(scrollToResults);
                    }
                }
            }
            renderCounts(data);
            renderResults(data);
            renderUnderstanding(data.effective_conditions || conditionPayload());
            renderPagination(data);
            list.scrollTop = 0;
            if (scrollToResults && isNarrowWorkspace()) {
                document.querySelector("[data-testid='results-pane']")
                    .scrollIntoView({block: "start"});
            }
        } catch (error) {
            if (requestSequence !== searchSequence) {
                return;
            }
            console.error("Global Search request failed", error);
            list.innerHTML = '<p class="wd-safe-message" data-testid="search-error">'
                + "Search unavailable</p>";
            pagination.hidden = true;
        }
    }

    pageControls.addEventListener("click", (event) => {
        const button = event.target.closest("button[data-page-action]");
        if (!button || button.disabled) {
            return;
        }
        state.currentPage = Number(button.dataset.page);
        state.cursor = null;
        search(true);
    });

    pageSizeInput.addEventListener("change", () => {
        const pageSize = Number(pageSizeInput.value);
        if (![10, 20, 50, 100].includes(pageSize)) {
            return;
        }
        state.pageSize = pageSize;
        state.currentPage = 1;
        state.cursor = null;
        search();
    });

    form.addEventListener("submit", (event) => {
        event.preventDefault();
        state.rawQuery = queryInput.value.trim();
        state.refinements = [];
        state.cursor = null;
        state.currentPage = 1;
        document.querySelector("#wd-date-refinement").value = "";
        document.querySelector("#wd-date-start").value = "";
        document.querySelector("#wd-date-end").value = "";
        document.querySelector("#wd-state-refinement").value = "";
        search();
    });
    resourceTabs.addEventListener("click", (event) => {
        const button = event.target.closest(".wd-resource-tab");
        if (!button) {
            return;
        }
        const resource = button.dataset.resource;
        if (state.resources.has(resource)) {
            state.resources.delete(resource);
        } else {
            state.resources.add(resource);
        }
        renderSelectionState();
        state.cursor = null;
        state.currentPage = 1;
        search();
    });
    reselectAllButton.addEventListener("click", () => {
        state.resources = new Set(resourceKeys());
        renderSelectionState();
        state.cursor = null;
        state.currentPage = 1;
        search();
    });
    document.querySelector("#wd-date-refinement").addEventListener("change", (event) => {
        if (event.target.value) {
            document.querySelector("#wd-date-start").value = "";
            document.querySelector("#wd-date-end").value = "";
        }
        applyDateRefinement();
    });
    document.querySelector("#wd-date-start").addEventListener("change", () => {
        document.querySelector("#wd-date-refinement").value = "";
        applyDateRefinement();
    });
    document.querySelector("#wd-date-end").addEventListener("change", () => {
        document.querySelector("#wd-date-refinement").value = "";
        applyDateRefinement();
    });
    document.querySelector("#wd-state-refinement").addEventListener("change", (event) => {
        state.refinements = state.refinements.filter((item) => item.dimension !== "state");
        if (event.target.value) {
            state.refinements.push({dimension: "state", value: event.target.value, operator: "="});
        }
        state.cursor = null;
        state.currentPage = 1;
        search();
    });
    document.addEventListener("submit", (event) => event.preventDefault());
    document.addEventListener("keydown", (event) => {
        if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "s") {
            event.preventDefault();
        }
    });
}());
