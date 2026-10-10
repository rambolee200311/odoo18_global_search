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
    let cardDensityExpanded = window.innerWidth >= 768;

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

    function showNavigationError(message) {
        const notice = document.createElement("p");
        notice.className = "wd-safe-message";
        notice.dataset.testid = "action-error";
        notice.textContent = message;
        list.prepend(notice);
    }

    function openNativeForm(resourceKey, recordId) {
        const query = new URLSearchParams({
            resource_key: resourceKey,
            record_id: recordId,
        });
        const tab = window.open(
            "/wd_global_search/open_result?" + query.toString(),
            "_blank"
        );
        if (!tab) {
            showNavigationError("Allow pop-ups to open this record in a new tab.");
            return;
        }
        tab.focus();
        tab.opener = null;
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
        list.replaceChildren();
        if (data.status === "PARTIAL_SUCCESS") {
            const partial = document.createElement("p");
            partial.className = "wd-safe-message";
            partial.dataset.testid = "partial-success";
            partial.textContent = "Some resources are unavailable.";
            list.append(partial);
        }

        data.results.forEach((result) => {
            const card = document.createElement("article");
            card.className = "wd-record-card";
            card.dataset.testid = "record-card";
            card.dataset.resource = result._resource;
            card.dataset.recordId = result._record_id;
            card.setAttribute("role", "button");
            card.setAttribute("tabindex", "0");
            card.setAttribute("aria-pressed", "false");

            const fields = result.snapshot && Array.isArray(result.snapshot.fields)
                ? result.snapshot.fields
                : [];
            if (fields.length) {
                const primary = document.createElement("strong");
                primary.className = "wd-card-primary";
                primary.textContent = text(fields[0].value);
                card.append(primary);
                const primaryLabel = document.createElement("span");
                primaryLabel.className = "wd-card-primary-label";
                primaryLabel.textContent = text(fields[0].label);
                card.append(primaryLabel);
                if (fields.length > 1) {
                    const secondary = document.createElement("span");
                    secondary.className = "wd-card-secondary";
                    secondary.textContent = text(fields[1].label) + ": " + text(fields[1].value);
                    card.append(secondary);
                }
                if (fields.length > 2) {
                    const more = document.createElement("details");
                    more.className = "wd-card-more";
                    more.open = cardDensityExpanded;
                    const summary = document.createElement("summary");
                    summary.textContent = "More";
                    more.append(summary);
                    fields.slice(2).forEach((field) => {
                        const row = document.createElement("span");
                        row.className = "wd-card-field";
                        row.textContent = text(field.label) + ": " + text(field.value);
                        more.append(row);
                    });
                    card.append(more);
                }
            } else {
                const primary = document.createElement("strong");
                primary.className = "wd-card-primary";
                primary.textContent = "Record";
                card.append(primary);
            }
            const resourceLabel = Array.from(
                resourceTabs.querySelectorAll(".wd-resource-tab")
            ).find((item) => item.dataset.resource === result._resource)
                ?.querySelector(".wd-resource-label")?.textContent || result._resource;
            const resource = document.createElement("span");
            resource.className = "wd-card-resource";
            resource.textContent = resourceLabel;
            card.append(resource);

            const openLink = document.createElement("a");
            const navigationQuery = new URLSearchParams({
                resource_key: result._resource,
                record_id: result._record_id,
            });
            openLink.className = "wd-card-open";
            openLink.href = "/wd_global_search/open_result?" + navigationQuery.toString();
            openLink.target = "_blank";
            openLink.rel = "noopener noreferrer";
            openLink.tabIndex = -1;
            openLink.setAttribute("aria-hidden", "true");
            card.append(openLink);

            card.addEventListener("click", (event) => {
                if (event.target.closest(".wd-card-more summary")) {
                    return;
                }
                if (event.detail === 2) {
                    event.preventDefault();
                    openNativeForm(card.dataset.resource, card.dataset.recordId);
                }
                const openInNewTab = event.ctrlKey || event.metaKey;
                if (!openInNewTab) {
                    event.preventDefault();
                }
                list.querySelectorAll(".wd-record-card").forEach((record) => {
                    record.setAttribute("aria-pressed", "false");
                });
                card.setAttribute("aria-pressed", "true");
            });
            card.addEventListener("keydown", (event) => {
                if (event.target.closest(".wd-card-more summary")) {
                    return;
                }
                if (event.key === "Enter") {
                    event.preventDefault();
                    event.stopPropagation();
                    openNativeForm(card.dataset.resource, card.dataset.recordId);
                } else if (event.key === " " && !event.repeat) {
                    event.preventDefault();
                    list.querySelectorAll(".wd-record-card").forEach((record) => {
                        record.setAttribute(
                            "aria-pressed",
                            String(record === card && card.getAttribute("aria-pressed") !== "true")
                        );
                    });
                } else if (event.key === "Escape") {
                    event.preventDefault();
                    list.querySelectorAll(".wd-record-card").forEach((record) => {
                        record.setAttribute("aria-pressed", "false");
                    });
                }
            });
            card.title = "Double-click or press Enter to open the configured Odoo form";
            list.append(card);
        });
    }

    window.addEventListener("resize", () => {
        const expanded = window.innerWidth >= 768;
        if (expanded === cardDensityExpanded) {
            return;
        }
        cardDensityExpanded = expanded;
        list.querySelectorAll(".wd-card-more").forEach((details) => {
            details.open = expanded;
        });
    });

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
