(function () {
    "use strict";

    const list = document.querySelector("#wd-result-list");
    const preview = document.querySelector("[data-testid='preview-pane']");
    const queryInput = document.querySelector("[data-testid='search-query']");
    const form = document.querySelector(".wd-query-bar");
    const conditionView = document.querySelector("#wd-effective-conditions");
    const activeView = document.querySelector("#wd-active-refinements");
    const state = {rawQuery: "", resources: new Set(), refinements: [], cursor: null};
    let currentPreviewRequest;

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
                search();
            });
        });
    }

    function renderCounts(counts) {
        const byResource = (counts && counts.by_resource) || {};
        document.querySelectorAll("[data-count-for]").forEach((element) => {
            const key = element.dataset.countFor;
            element.textContent = Object.prototype.hasOwnProperty.call(byResource, key)
                ? String(byResource[key])
                : "—";
        });
    }

    function renderPreview(data) {
        if (data.status !== "SUCCESS") {
            preview.innerHTML = '<div class="wd-safe-message" data-testid="preview-safe-state">'
                + "Record unavailable or permission changed</div>";
            return;
        }
        const fields = data.fields.map((field) => (
            '<div class="wd-field"><span class="wd-field-label">'
            + text(field.label) + '</span><span class="wd-field-value">'
            + text(field.value) + "</span></div>"
        )).join("");
        preview.innerHTML = '<div class="wd-preview-card" data-testid="readonly-form-preview">'
            + '<span class="wd-status">READ ONLY · FORM VIEW ' + text(data.view_id) + "</span>"
            + "<h3>" + text(data.display_name) + "</h3>" + fields + "</div>";
    }

    async function loadPreview(model, recordId) {
        if (currentPreviewRequest) {
            currentPreviewRequest.abort();
        }
        currentPreviewRequest = new AbortController();
        const query = new URLSearchParams({model: model, record_id: recordId});
        const response = await fetch("/wd_global_search/api/preview?" + query.toString(), {
            credentials: "same-origin",
            headers: {"Accept": "application/json"},
            signal: currentPreviewRequest.signal,
        });
        renderPreview(await response.json());
    }

    async function openNativeForm(model, recordId) {
        const query = new URLSearchParams({model: model, record_id: recordId});
        const response = await fetch("/wd_global_search/api/form_url?" + query.toString(), {
            credentials: "same-origin",
            headers: {"Accept": "application/json"},
        });
        const data = await response.json();
        if (data.status !== "SUCCESS") {
            renderPreview(data);
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
        if (data.status === "EMPTY" || !data.results.length) {
            list.innerHTML = '<p class="wd-muted" data-testid="empty-results">No results found.</p>';
            return;
        }
        list.innerHTML = data.results.map((result) => {
            const title = result.display_name || result.name || result._record_id;
            const model = result._model;
            return '<button class="wd-record-card" type="button" data-model="' + model
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
            button.addEventListener("click", () => loadPreview(
                button.dataset.model, button.dataset.recordId
            ));
            button.addEventListener("dblclick", () => openNativeForm(
                button.dataset.model, button.dataset.recordId
            ));
            button.title = "Double-click to open the read-only Odoo form";
        });
    }

    async function search() {
        const payload = {
            query: state.rawQuery,
            conditions: [],
            refinement_conditions: conditionPayload(),
            resources: Array.from(state.resources),
            limit: 20,
            cursor: state.cursor,
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
            renderCounts(data.counts || {});
            renderResults(data);
            renderUnderstanding(data.effective_conditions || conditionPayload());
        } catch (error) {
            list.innerHTML = '<p class="wd-safe-message">Search unavailable</p>';
        }
    }

    form.addEventListener("submit", (event) => {
        event.preventDefault();
        state.rawQuery = queryInput.value.trim();
        state.refinements = [];
        state.cursor = null;
        document.querySelector("#wd-date-refinement").value = "";
        document.querySelector("#wd-date-start").value = "";
        document.querySelector("#wd-date-end").value = "";
        document.querySelector("#wd-state-refinement").value = "";
        state.resources.clear();
        document.querySelectorAll(".wd-resource-tab").forEach((tab) => {
            tab.setAttribute("aria-pressed", "false");
        });
        search();
    });
    document.querySelectorAll(".wd-resource-tab").forEach((tab) => {
        tab.addEventListener("click", () => {
            const resource = tab.dataset.resource || "";
            if (!resource) {
                state.resources.clear();
            } else if (state.resources.has(resource)) {
                state.resources.delete(resource);
            } else {
                state.resources.add(resource);
            }
            document.querySelectorAll(".wd-resource-tab").forEach((item) => {
                item.setAttribute(
                    "aria-pressed",
                    item.dataset.resource
                        ? String(state.resources.has(item.dataset.resource))
                        : String(state.resources.size === 0)
                );
            });
            state.cursor = null;
            search();
        });
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
        search();
    });
    document.addEventListener("submit", (event) => event.preventDefault());
    document.addEventListener("keydown", (event) => {
        if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "s") {
            event.preventDefault();
        }
    });
}());
