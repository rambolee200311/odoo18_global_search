(function () {
    "use strict";

    const root = document.querySelector(".wd-template-designer-page");
    if (!root) {
        return;
    }

    const resourceId = root.dataset.resourceId;
    const csrfToken = root.dataset.csrfToken;
    const editor = document.getElementById("wd-template-input");
    const separator = document.getElementById("wd-template-separator");
    const source = document.getElementById("wd-template-source");
    const recordSelect = document.getElementById("wd-template-record");
    const rendered = document.getElementById("wd-template-rendered");
    const message = document.getElementById("wd-template-message");
    const saveButton = document.getElementById("wd-template-save");
    const checkButton = document.getElementById("wd-template-check");
    const applyButton = document.getElementById("wd-template-apply");
    const fieldsList = document.getElementById("wd-template-fields");
    const fieldByName = new Map();
    let pending = false;
    let previewTimer;
    let previewRequest = 0;

    function setMessage(text, isError) {
        message.textContent = text || "";
        message.classList.toggle("is-error", Boolean(isError));
    }

    async function getJson(path, params) {
        const query = new URLSearchParams(params);
        const response = await fetch(`${path}?${query}`, {
            credentials: "same-origin",
        });
        const data = await response.json();
        if (!response.ok && !data.status) {
            throw new Error(`Request failed (${response.status}).`);
        }
        return data;
    }

    async function postJson(path, params) {
        const body = new URLSearchParams({ ...params, csrf_token: csrfToken });
        const response = await fetch(path, {
            method: "POST",
            credentials: "same-origin",
            headers: { "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8" },
            body,
        });
        const data = await response.json();
        if (!response.ok && !data.status) {
            throw new Error(`Request failed (${response.status}).`);
        }
        return data;
    }

    function addField(field) {
        fieldByName.set(field.name, field);
        const item = document.createElement("li");
        item.setAttribute("role", "option");
        const button = document.createElement("button");
        button.type = "button";
        button.draggable = true;
        const label = document.createElement("span");
        label.textContent = `${field.name} · ${field.type} · ${field.label}`;
        button.append(label);
        const readability = document.createElement("span");
        readability.className = "wd-template-field-access";
        readability.textContent = field.readable
            ? "Readable by preview user"
            : "Not readable by preview user";
        button.append(readability);
        if (field.group_restricted) {
            const groupWarning = document.createElement("span");
            groupWarning.className = "wd-template-field-group-warning";
            groupWarning.textContent = "Group-restricted; visibility may vary by user";
            button.append(groupWarning);
        }
        button.addEventListener("click", () => insertField(field));
        button.addEventListener("keydown", (event) => {
            if (event.key === "Enter") {
                event.preventDefault();
                insertField(field);
            }
        });
        button.addEventListener("dragstart", (event) => {
            event.dataTransfer.setData("text/plain", `{${field.name}}`);
            event.dataTransfer.setData(
                "application/x-wd-global-search-field",
                JSON.stringify({ name: field.name, type: field.type })
            );
            event.dataTransfer.effectAllowed = "copy";
        });
        item.append(button);
        fieldsList.append(item);
    }

    function insertField(field) {
        let token = `{${field.name}}`;
        let cursorOffset = token.length;
        if (field.type === "one2many") {
            token = `{${field.name}}\n  \n{/${field.name}}`;
            cursorOffset = token.indexOf("\n  ") + 3;
        } else if (field.type === "many2many") {
            token = `{${field.name}.}`;
            cursorOffset = token.length - 1;
        }
        const start = editor.selectionStart;
        const end = editor.selectionEnd;
        editor.setRangeText(token, start, end, "select");
        editor.setSelectionRange(start + cursorOffset, start + cursorOffset);
        editor.focus();
        schedulePreview();
    }

    function schedulePreview() {
        window.clearTimeout(previewTimer);
        previewTimer = window.setTimeout(renderPreview, 200);
    }

    async function loadRecords() {
        const result = await getJson("/wd_global_search/card_templates/records", {
            resource_id: resourceId,
        });
        if (result.status !== "SUCCESS") {
            throw new Error(result.message || "Unable to load readable records.");
        }
        recordSelect.replaceChildren();
        for (const record of result.records) {
            const option = document.createElement("option");
            option.value = record.record_id;
            option.textContent = record.label;
            recordSelect.append(option);
        }
    }

    async function renderPreview() {
        const requestNumber = ++previewRequest;
        try {
            if (source.value === "selected_readable_record" && !recordSelect.options.length) {
                await loadRecords();
            }
            const result = await postJson("/wd_global_search/card_templates/preview", {
                resource_id: resourceId,
                template: editor.value,
                source: source.value,
                record_id: recordSelect.value,
                many2many_separator: separator.value,
            });
            if (requestNumber !== previewRequest) {
                return;
            }
            if (result.status !== "SUCCESS") {
                throw new Error(
                    result.validation_errors?.join(" ") ||
                    result.message ||
                    "Unable to render the preview."
                );
            }
            rendered.textContent = result.rendered_plain_text || "—";
            setMessage("", false);
        } catch (error) {
            if (requestNumber === previewRequest) {
                rendered.textContent = "";
                setMessage(error.message || "Unable to render the preview.", true);
            }
        }
    }

    async function saveTemplate() {
        saveButton.disabled = true;
        applyButton.disabled = true;
        try {
            const result = await postJson("/wd_global_search/card_templates/save", {
                resource_id: resourceId,
                template: editor.value,
                many2many_separator: separator.value,
            });
            if (result.status !== "SUCCESS") {
                throw new Error(result.message || "Template could not be saved.");
            }
            pending = Boolean(result.pending);
            applyButton.disabled = !pending;
            setMessage("Template saved.", false);
            return true;
        } catch (error) {
            setMessage(error.message || "Template could not be saved.", true);
            return false;
        } finally {
            saveButton.disabled = false;
        }
    }

    async function checkTemplate() {
        checkButton.disabled = true;
        try {
            const result = await postJson("/wd_global_search/card_templates/check", {
                resource_id: resourceId,
                template: editor.value,
                many2many_separator: separator.value,
            });
            if (result.status !== "SUCCESS") {
                throw new Error(result.message || "Template structure is invalid.");
            }
            setMessage(result.message || "Template structure is valid.", false);
            return true;
        } catch (error) {
            setMessage(error.message || "Template structure is invalid.", true);
            return false;
        } finally {
            checkButton.disabled = false;
        }
    }

    async function applyChanges() {
        if (!(await saveTemplate())) {
            return;
        }
        applyButton.disabled = true;
        try {
            const result = await postJson("/wd_global_search/card_templates/apply", {
                resource_id: resourceId,
            });
            if (result.status !== "SUCCESS") {
                throw new Error(result.message || "Configuration changes could not be applied.");
            }
            pending = Boolean(result.pending);
            applyButton.disabled = !pending;
            setMessage("Changes applied to the Published Configuration.", false);
        } catch (error) {
            setMessage(error.message || "Configuration changes could not be applied.", true);
            applyButton.disabled = !pending;
        }
    }

    async function initialize() {
        try {
            const descriptor = await getJson(
                "/wd_global_search/card_templates/descriptor",
                { resource_id: resourceId }
            );
            if (descriptor.status !== "SUCCESS") {
                throw new Error("This Resource's template is unavailable.");
            }
            editor.value = descriptor.template || "";
            separator.value = descriptor.many2many_separator || ", ";
            pending = Boolean(descriptor.pending);
            applyButton.disabled = !pending;
            for (const field of descriptor.fields) {
                addField(field);
            }
            setMessage(descriptor.migration_warning || "", false);
            await renderPreview();
        } catch (error) {
            editor.disabled = true;
            separator.disabled = true;
            checkButton.disabled = true;
            saveButton.disabled = true;
            applyButton.disabled = true;
            setMessage(error.message || "Unable to load this Resource's template.", true);
        }
    }

    document.getElementById("wd-template-back").addEventListener("click", () => {
        if (window.parent !== window) {
            window.parent.postMessage(
                { type: "wd_global_search.close_card_template_editor" },
                window.location.origin
            );
        } else {
            window.history.back();
        }
    });
    editor.addEventListener("input", schedulePreview);
    separator.addEventListener("input", schedulePreview);
    editor.addEventListener("dragover", (event) => event.preventDefault());
    editor.addEventListener("drop", (event) => {
        event.preventDefault();
        const structured = event.dataTransfer.getData(
            "application/x-wd-global-search-field"
        );
        if (structured) {
            try {
                const field = JSON.parse(structured);
                if (fieldByName.has(field.name)) {
                    insertField(fieldByName.get(field.name));
                    return;
                }
            } catch (_error) {
                setMessage("The dragged field could not be inserted.", true);
                return;
            }
        }
        const match = /^\{([A-Za-z_]\w*)\}$/.exec(
            event.dataTransfer.getData("text/plain")
        );
        if (match && fieldByName.has(match[1])) {
            insertField(fieldByName.get(match[1]));
        }
    });
    source.addEventListener("change", () => {
        recordSelect.hidden = source.value !== "selected_readable_record";
        recordSelect.replaceChildren();
        renderPreview();
    });
    recordSelect.addEventListener("change", renderPreview);
    checkButton.addEventListener("click", checkTemplate);
    saveButton.addEventListener("click", saveTemplate);
    applyButton.addEventListener("click", applyChanges);
    document.addEventListener("keydown", (event) => {
        if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "s") {
            event.preventDefault();
            saveTemplate();
        }
    });
    initialize();
})();
