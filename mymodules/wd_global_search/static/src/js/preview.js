(function () {
    "use strict";

    const list = document.querySelector("#wd-result-list");
    const preview = document.querySelector("[data-testid='preview-pane']");
    const tabs = document.querySelectorAll(".wd-resource-tab");
    let currentRequest;

    function text(value) {
        if (value === false || value === null || value === undefined) {
            return "—";
        }
        if (Array.isArray(value)) {
            return value.length > 1 ? value[1] : String(value[0] || "—");
        }
        return String(value);
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

    async function load(model, recordId) {
        if (currentRequest) {
            currentRequest.abort();
        }
        currentRequest = new AbortController();
        const query = new URLSearchParams({model: model});
        if (recordId) {
            query.set("record_id", recordId);
        }
        const response = await fetch("/wd_global_search/api/preview?" + query.toString(), {
            credentials: "same-origin",
            headers: {"Accept": "application/json"},
            signal: currentRequest.signal,
        });
        renderPreview(await response.json());
    }

    tabs.forEach((tab) => {
        tab.addEventListener("click", async () => {
            const model = tab.dataset.model;
            try {
                await load(model);
            } catch (error) {
                if (error.name !== "AbortError") {
                    preview.innerHTML = '<div class="wd-safe-message">Preview unavailable</div>';
                }
                return;
            }
            list.innerHTML = '<button class="wd-record-card" type="button" '
                + 'data-testid="preview-record-card"><strong>Selected record</strong>'
                + "<span>Loaded under current permissions</span></button>";
            list.querySelector("button").addEventListener("click", () => load(model));
        });
    });

    document.addEventListener("submit", (event) => event.preventDefault());
    document.addEventListener("keydown", (event) => {
        if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "s") {
            event.preventDefault();
        }
    });
}());
