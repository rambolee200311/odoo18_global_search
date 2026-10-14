(function () {
    "use strict";

    const list = document.querySelector("#wd-result-list");
    const queryInput = document.querySelector("[data-testid='search-query']");
    const form = document.querySelector(".wd-query-bar");
    const conditionView = document.querySelector("#wd-effective-conditions");
    const keywordView = document.querySelector("#wd-effective-keywords");
    const keywordCombinator = document.querySelector("#wd-keyword-combinator");
    const structuredView = document.querySelector("#wd-effective-structured");
    const effectiveRefinementView = document.querySelector("#wd-effective-refinements");
    const conditionCombination = document.querySelector("#wd-condition-combination");
    const conditionField = document.querySelector("#wd-condition-field");
    const conditionOperator = document.querySelector("#wd-condition-operator");
    const conditionValueContainer = document.querySelector("#wd-condition-value-container");
    const conditionSubmit = document.querySelector("#wd-condition-submit");
    const conditionMessage = document.querySelector("#wd-condition-message");
    const dateMessage = document.querySelector("#wd-date-message");
    const removeUnavailableConditions = document.querySelector(
        "#wd-remove-unavailable-conditions"
    );
    const keywordAddInput = document.querySelector("#wd-keyword-add");
    const keywordAddSubmit = document.querySelector("#wd-keyword-add-submit");
    const activeView = document.querySelector("#wd-active-refinements");
    const workspace = document.querySelector("[data-testid='global-search-workspace']");
    const resourceTabs = document.querySelector("#wd-resource-tabs");
    const resourceEmpty = document.querySelector("[data-testid='resource-empty']");
    const reselectAllButton = document.querySelector("[data-testid='reselect-all']");
    const pagination = document.querySelector("[data-testid='pagination']");
    const pageSizeInput = document.querySelector("[data-testid='page-size']");
    const pageSummary = document.querySelector("[data-testid='page-summary']");
    const pageControls = document.querySelector("[data-testid='page-controls']");
    const stateInput = document.querySelector("#wd-state-refinement");
    if (!list || !queryInput || !form || !conditionView || !keywordView
        || !keywordCombinator || !structuredView || !effectiveRefinementView
        || !conditionCombination || !conditionField || !conditionOperator
        || !conditionValueContainer || !conditionSubmit || !conditionMessage
        || !dateMessage || !removeUnavailableConditions
        || !keywordAddInput || !keywordAddSubmit
        || !activeView || !workspace
        || !resourceTabs || !resourceEmpty || !reselectAllButton
        || !pagination || !pageSizeInput || !pageSummary || !pageControls || !stateInput) {
        return;
    }
    function isNarrowWorkspace() {
        return window.matchMedia("(max-width: 700px)").matches;
    }

    const state = {
        rawQuery: "",
        resources: new Set(),
        refinements: [],
        structuredConditions: [],
        effectiveKeywordTerms: [],
        fieldOptions: [],
        editingConditionIndex: null,
        cursor: null,
        pageSize: 10,
        currentPage: 1,
        totalResultCount: 0,
        hasSearched: false,
        resourceSelectionInitialized: false,
        configVersion: workspace.dataset.configVersion || null,
        userTimezone: workspace.dataset.userTimezone || "UTC",
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

    function fieldOptionsForResource(resourceKey) {
        const button = Array.from(resourceTabs.querySelectorAll(".wd-resource-tab"))
            .find((item) => item.dataset.resource === resourceKey);
        if (!button) {
            return [];
        }
        try {
            const options = JSON.parse(button.dataset.searchableFields || "[]");
            if (
                !Array.isArray(options)
                || options.some((option) => !option || typeof option.dimension !== "string"
                    || typeof option.label !== "string" || !option.label
                    || typeof option.type !== "string"
                    || !["exact", "prefix", "contains"].includes(option.operator_set)
                    || typeof option.operator !== "string"
                    || typeof option.operator_label !== "string"
                    || !Array.isArray(option.selection))
            ) {
                console.error("Invalid Published searchable field descriptor", resourceKey);
                return [];
            }
            return options;
        } catch (error) {
            console.error("Unable to parse Published searchable field descriptor", error);
            return [];
        }
    }

    function fieldOptionSignature(option) {
        return JSON.stringify([
            option.label,
            option.type,
            option.operator_set,
            option.operator,
            option.operator_label,
            option.selection,
        ]);
    }

    function commonFieldOptions() {
        const selectedResources = state.resourceSelectionInitialized
            ? Array.from(state.resources)
            : resourceKeys();
        if (!selectedResources.length) {
            return [];
        }
        const lists = selectedResources.map(fieldOptionsForResource);
        return lists[0]
            .filter((option) => lists.slice(1).every((list) => (
                list.some((candidate) => candidate.dimension === option.dimension
                    && fieldOptionSignature(candidate) === fieldOptionSignature(option))
            )))
            .sort((left, right) => left.label.localeCompare(right.label));
    }

    function setConditionMessage(message) {
        conditionMessage.textContent = message || "";
        conditionMessage.hidden = !message;
    }

    function fieldOptionByDimension(dimension) {
        return state.fieldOptions.find((option) => option.dimension === dimension);
    }

    function sameScalar(left, right) {
        return typeof left === typeof right && left === right;
    }

    function conditionValueIsValid(option, value) {
        if (!option || value === null || value === undefined || value === "") {
            return false;
        }
        if (option.type === "char" || option.type === "text"
            || option.type === "date" || option.type === "datetime") {
            return typeof value === "string";
        }
        if (option.type === "integer") {
            return Number.isSafeInteger(value);
        }
        if (option.type === "float" || option.type === "monetary") {
            return typeof value === "number" && Number.isFinite(value);
        }
        if (option.type === "boolean") {
            return typeof value === "boolean";
        }
        if (option.type === "selection") {
            return option.selection.some((item) => (
                Array.isArray(item) && item.length === 2 && sameScalar(item[0], value)
            ));
        }
        return false;
    }

    function userDateTimeFormatter() {
        try {
            return new Intl.DateTimeFormat("en-US", {
                timeZone: state.userTimezone,
                year: "numeric",
                month: "2-digit",
                day: "2-digit",
                hour: "2-digit",
                minute: "2-digit",
                second: "2-digit",
                hourCycle: "h23",
            });
        } catch (error) {
            console.error("Invalid server-provided user timezone", error);
            return null;
        }
    }

    function dateTimeParts(formatter, date) {
        return Object.fromEntries(
            formatter.formatToParts(date)
                .filter((part) => part.type !== "literal")
                .map((part) => [part.type, Number(part.value)])
        );
    }

    function utcDateTimeToLocal(value) {
        const normalized = String(value).replace(" ", "T");
        const source = /(?:Z|[+-]\d{2}:\d{2})$/.test(normalized)
            ? normalized
            : normalized + "Z";
        const date = new Date(source);
        const formatter = userDateTimeFormatter();
        if (Number.isNaN(date.getTime()) || !formatter) {
            console.error("Unable to format the server date-time value");
            return null;
        }
        const parts = dateTimeParts(formatter, date);
        const pad = (part) => String(part).padStart(2, "0");
        return parts.year + "-" + pad(parts.month) + "-" + pad(parts.day)
            + "T" + pad(parts.hour) + ":" + pad(parts.minute) + ":" + pad(parts.second);
    }

    function isSupportedStructuredCondition(condition) {
        const option = fieldOptionByDimension(condition.dimension);
        return Boolean(option && condition.operator === option.operator
            && conditionValueIsValid(option, condition.value));
    }

    function localDateTimeToUtc(value) {
        const match = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})(?::(\d{2}))?$/.exec(value);
        if (!match) {
            return null;
        }
        const desired = match.slice(1, 7).map((part) => Number(part || 0));
        const target = Date.UTC(
            desired[0], desired[1] - 1, desired[2], desired[3], desired[4], desired[5]
        );
        const formatter = userDateTimeFormatter();
        if (!formatter) {
            return null;
        }
        let timestamp = target;
        for (let attempt = 0; attempt < 4; attempt += 1) {
            const parts = dateTimeParts(formatter, new Date(timestamp));
            const rendered = Date.UTC(
                parts.year, parts.month - 1, parts.day,
                parts.hour, parts.minute, parts.second
            );
            timestamp += target - rendered;
        }
        const actual = dateTimeParts(formatter, new Date(timestamp));
        if (
            actual.year !== desired[0] || actual.month !== desired[1]
            || actual.day !== desired[2] || actual.hour !== desired[3]
            || actual.minute !== desired[4] || actual.second !== desired[5]
        ) {
            return null;
        }
        return new Date(timestamp).toISOString().slice(0, 19).replace("T", " ");
    }

    function readConditionValue(option) {
        const control = conditionValueContainer.querySelector("#wd-condition-value");
        if (!option || !control || !control.value) {
            return null;
        }
        if (option.type === "char" || option.type === "text" || option.type === "date") {
            return control.value;
        }
        if (option.type === "datetime") {
            return localDateTimeToUtc(control.value);
        }
        if (option.type === "integer") {
            const value = Number(control.value);
            return Number.isSafeInteger(value) ? value : null;
        }
        if (option.type === "float" || option.type === "monetary") {
            const value = Number(control.value);
            return Number.isFinite(value) ? value : null;
        }
        if (option.type === "boolean") {
            return control.value === "true";
        }
        if (option.type === "selection") {
            const index = Number(control.value);
            return Number.isInteger(index) && option.selection[index]
                ? option.selection[index][0]
                : null;
        }
        return null;
    }

    function setConditionValueControl(option, initialValue) {
        let control;
        if (option && option.type === "selection") {
            control = document.createElement("select");
            control.append(new Option("Choose a value", ""));
            option.selection.forEach((item, index) => {
                const entry = document.createElement("option");
                entry.value = String(index);
                entry.textContent = item[1];
                control.append(entry);
                if (sameScalar(item[0], initialValue)) {
                    control.value = String(index);
                }
            });
        } else if (option && option.type === "boolean") {
            control = document.createElement("select");
            control.append(new Option("Choose a value", ""));
            [
                ["true", "Yes"],
                ["false", "No"],
            ].forEach(([value, label]) => {
                const entry = document.createElement("option");
                entry.value = value;
                entry.textContent = label;
                control.append(entry);
            });
            if (typeof initialValue === "boolean") {
                control.value = String(initialValue);
            }
        } else {
            control = document.createElement("input");
            control.type = option && option.type === "integer"
                ? "number"
                : option && (option.type === "float" || option.type === "monetary")
                    ? "number"
                    : option && option.type === "date"
                        ? "date"
                        : option && option.type === "datetime"
                            ? "datetime-local"
                            : "text";
            if (option && option.type === "integer") {
                control.step = "1";
            } else if (option && (option.type === "float" || option.type === "monetary")) {
                control.step = "any";
            } else if (option && option.type === "datetime") {
                control.step = "1";
            }
            if (initialValue !== null && initialValue !== undefined) {
                if (option && option.type === "datetime") {
                    const local = utcDateTimeToLocal(initialValue);
                    if (local) {
                        control.value = local;
                    } else {
                        setConditionMessage("The saved date and time cannot be edited safely.");
                    }
                } else {
                    control.value = String(initialValue);
                }
            }
        }
        control.id = "wd-condition-value";
        control.dataset.testid = "condition-value";
        control.disabled = !option;
        conditionValueContainer.replaceChildren(control);
        control.addEventListener("input", updateConditionSubmitState);
        control.addEventListener("change", updateConditionSubmitState);
    }

    function updateConditionSubmitState() {
        const index = conditionField.value ? Number(conditionField.value) : -1;
        const option = Number.isInteger(index) ? state.fieldOptions[index] : null;
        const control = conditionValueContainer.querySelector("#wd-condition-value");
        const value = readConditionValue(option);
        const valid = conditionValueIsValid(option, value);
        conditionSubmit.disabled = !valid;
        const dateTimeError = "This date and time is invalid in your timezone.";
        if (option && option.type === "datetime" && control.value && !valid) {
            setConditionMessage(dateTimeError);
        } else if (conditionMessage.textContent === dateTimeError) {
            setConditionMessage("");
        }
    }

    function renderFieldSelector(initialCondition) {
        const previousIndex = conditionField.value ? Number(conditionField.value) : -1;
        const currentDimension = initialCondition
            ? initialCondition.dimension
            : state.fieldOptions[previousIndex]?.dimension;
        state.fieldOptions = commonFieldOptions();
        conditionField.replaceChildren(new Option("Choose an accessible field", ""));
        state.fieldOptions.forEach((option, index) => {
            const entry = document.createElement("option");
            entry.value = String(index);
            entry.textContent = option.label;
            conditionField.append(entry);
            if (option.dimension === currentDimension) {
                conditionField.value = String(index);
            }
        });
        conditionField.disabled = state.fieldOptions.length === 0;

        const optionIndex = conditionField.value ? Number(conditionField.value) : -1;
        const option = state.fieldOptions[optionIndex] || null;
        conditionOperator.replaceChildren();
        if (option) {
            const entry = document.createElement("option");
            entry.value = option.operator;
            entry.textContent = option.operator_label;
            conditionOperator.append(entry);
            conditionOperator.value = option.operator;
        } else {
            conditionOperator.append(new Option("Choose an operator", ""));
        }
        conditionOperator.disabled = !option;
        setConditionValueControl(option, initialCondition && initialCondition.value);
        conditionSubmit.textContent = state.editingConditionIndex === null
            ? "Add condition"
            : "Update condition";
        updateConditionSubmitState();

        const hasUnavailable = state.structuredConditions.some(
            (condition) => !isSupportedStructuredCondition(condition)
        );
        removeUnavailableConditions.hidden = !hasUnavailable;
        if (hasUnavailable) {
            setConditionMessage(
                "A field condition is unavailable for the selected Resources or configuration."
            );
        } else if (!state.fieldOptions.length) {
            setConditionMessage("No accessible field is common to the selected Resources.");
        } else {
            setConditionMessage("");
        }
    }

    function dateRefinement() {
        const start = document.querySelector("#wd-date-start").value;
        const end = document.querySelector("#wd-date-end").value;
        if (start || end) {
            if (!start || !end) {
                return {error: "Choose both dates for a custom range."};
            }
            if (end <= start) {
                return {error: "The To date must be after the From date."};
            }
            return {
                condition: {
                    dimension: "date",
                    value: {start: start, end: end},
                    operator: "between",
                },
            };
        }
        const preset = document.querySelector("#wd-date-refinement").value;
        return {
            condition: preset
                ? {dimension: "date", value: preset, operator: "="}
                : null,
        };
    }

    function applyDateRefinement() {
        const result = dateRefinement();
        if (result.error) {
            dateMessage.textContent = result.error;
            dateMessage.hidden = false;
            return;
        }
        dateMessage.textContent = "";
        dateMessage.hidden = true;
        state.refinements = state.refinements.filter((item) => item.dimension !== "date");
        if (result.condition) {
            state.refinements.push(result.condition);
        }
        renderActiveRefinementControls();
        state.cursor = null;
        state.currentPage = 1;
        search();
    }

    function conditionDisplayValue(option, value) {
        if (option.type === "selection") {
            const selected = option.selection.find((item) => sameScalar(item[0], value));
            return selected ? selected[1] : "Unavailable";
        }
        if (option.type === "boolean") {
            return value ? "Yes" : "No";
        }
        if (option.type === "datetime") {
            const local = utcDateTimeToLocal(value);
            return local ? local.replace("T", " ") : "Unavailable";
        }
        return text(value);
    }

    function appendConditionAction(container, label, accessibleLabel, action) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "wd-condition-action";
        button.textContent = label;
        button.setAttribute("aria-label", accessibleLabel);
        button.addEventListener("click", action);
        container.append(button);
    }

    function renderKeywordChips(terms) {
        keywordView.replaceChildren();
        state.effectiveKeywordTerms = terms.slice();
        terms.forEach((term, index) => {
            const chip = document.createElement("span");
            chip.className = "wd-condition-chip";
            const value = document.createElement("span");
            value.textContent = term;
            chip.append(value);
            appendConditionAction(
                chip,
                "Edit",
                "Edit keyword " + term,
                () => editKeyword(index)
            );
            appendConditionAction(
                chip,
                "Remove",
                "Remove keyword " + term,
                () => removeKeyword(index)
            );
            keywordView.append(chip);
        });
        keywordCombinator.textContent = terms.length > 1
            ? "Keywords are combined with AND."
            : "";
    }

    function sameCondition(left, right) {
        return left.dimension === right.dimension
            && left.operator === right.operator
            && JSON.stringify(left.value) === JSON.stringify(right.value);
    }

    function renderStructuredConditions(conditions) {
        structuredView.replaceChildren();
        conditions.forEach((condition) => {
            const option = fieldOptionByDimension(condition.dimension);
            if (!option) {
                const unavailable = document.createElement("span");
                unavailable.className = "wd-safe-message";
                unavailable.textContent = "A field condition is unavailable.";
                structuredView.append(unavailable);
                return;
            }
            const index = state.structuredConditions.findIndex(
                (item) => sameCondition(item, condition)
            );
            const chip = document.createElement("span");
            chip.className = "wd-condition-chip";
            const description = document.createElement("span");
            description.textContent = option.label + " " + option.operator_label + " "
                + conditionDisplayValue(option, condition.value);
            chip.append(description);
            if (index >= 0) {
                appendConditionAction(
                    chip,
                    "Edit",
                    "Edit condition for " + option.label,
                    () => {
                        state.editingConditionIndex = index;
                        renderFieldSelector(condition);
                        conditionValueContainer.querySelector("#wd-condition-value").focus();
                    }
                );
                appendConditionAction(
                    chip,
                    "Remove",
                    "Remove condition for " + option.label,
                    () => removeStructuredCondition(index)
                );
            }
            structuredView.append(chip);
        });
    }

    function refinementDisplayValue(condition) {
        if (
            condition.dimension === "date"
            && condition.value && typeof condition.value === "object"
        ) {
            return [condition.value.start, condition.value.end].filter(Boolean).join(" – ");
        }
        return text(condition.value);
    }

    function renderEffectiveRefinements(conditions) {
        effectiveRefinementView.replaceChildren();
        conditions.forEach((condition) => {
            const label = document.createElement("span");
            label.className = "wd-condition-chip";
            label.textContent = (condition.dimension === "date" ? "Date"
                : condition.dimension === "state" ? "State" : "Refinement")
                + ": " + refinementDisplayValue(condition);
            effectiveRefinementView.append(label);
        });
    }

    function renderActiveRefinementControls() {
        activeView.replaceChildren();
        state.refinements.forEach((condition, index) => {
            const button = document.createElement("button");
            button.type = "button";
            button.className = "wd-refinement-chip";
            button.textContent = (condition.dimension === "date" ? "Date"
                : condition.dimension === "state" ? "State" : "Refinement")
                + ": " + refinementDisplayValue(condition) + " ×";
            button.addEventListener("click", () => {
                state.refinements.splice(index, 1);
                renderStateOptions();
                renderActiveRefinementControls();
                state.cursor = null;
                state.currentPage = 1;
                search();
            });
            activeView.append(button);
        });
    }

    function renderUnderstanding(conditions, status) {
        keywordView.replaceChildren();
        keywordCombinator.textContent = "";
        structuredView.replaceChildren();
        effectiveRefinementView.replaceChildren();
        conditionCombination.hidden = true;
        conditionView.textContent = "";
        keywordAddInput.hidden = !["SUCCESS", "EMPTY", "PARTIAL_SUCCESS"].includes(status);
        keywordAddSubmit.hidden = keywordAddInput.hidden;
        if (!["SUCCESS", "EMPTY", "PARTIAL_SUCCESS"].includes(status)) {
            state.effectiveKeywordTerms = [];
            conditionView.textContent = status === "SEARCHING"
                ? "Searching"
                : status === "TIMEOUT" ? "Search timed out" : "Conditions unavailable";
            return;
        }
        const keywords = [];
        const structured = [];
        const refinements = [];
        conditions.forEach((condition) => {
            if (
                condition.dimension === "keyword"
                || (condition.dimension === "name"
                    && !fieldOptionByDimension(condition.dimension))
            ) {
                if (typeof condition.value === "string") {
                    keywords.push(condition.value);
                }
            } else if (condition.dimension === "date" || condition.dimension === "state") {
                refinements.push(condition);
            } else {
                structured.push(condition);
            }
        });
        renderKeywordChips(keywords);
        renderStructuredConditions(structured);
        renderEffectiveRefinements(refinements);
        renderActiveRefinementControls();
        conditionCombination.hidden = !(
            keywords.length || structured.length || refinements.length
        );
        conditionView.textContent = keywords.length || structured.length || refinements.length
            ? "Conditions are shown as confirmed by the latest response."
            : "No conditions";
    }

    function applyKeywordTerms(terms) {
        state.rawQuery = terms.join(" ");
        queryInput.value = state.rawQuery;
        state.refinements = [];
        document.querySelector("#wd-date-refinement").value = "";
        document.querySelector("#wd-date-start").value = "";
        document.querySelector("#wd-date-end").value = "";
        stateInput.value = "";
        renderStateOptions();
        renderActiveRefinementControls();
        keywordAddInput.value = "";
        state.cursor = null;
        state.currentPage = 1;
        search();
    }

    function editKeyword(index) {
        const term = state.effectiveKeywordTerms[index];
        const chip = keywordView.children[index];
        if (typeof term !== "string" || !chip) {
            return;
        }
        const input = document.createElement("input");
        input.type = "text";
        input.value = term;
        input.setAttribute("aria-label", "Edit keyword");
        const save = document.createElement("button");
        save.type = "button";
        save.textContent = "Save";
        const cancel = document.createElement("button");
        cancel.type = "button";
        cancel.textContent = "Cancel";
        const saveEdit = () => {
            const terms = state.effectiveKeywordTerms.slice();
            if (input.value) {
                terms[index] = input.value;
            } else {
                terms.splice(index, 1);
            }
            applyKeywordTerms(terms);
        };
        save.addEventListener("click", saveEdit);
        cancel.addEventListener("click", () => renderKeywordChips(state.effectiveKeywordTerms));
        input.addEventListener("keydown", (event) => {
            if (event.key === "Enter") {
                event.preventDefault();
                saveEdit();
            } else if (event.key === "Escape") {
                renderKeywordChips(state.effectiveKeywordTerms);
            }
        });
        chip.replaceChildren(input, save, cancel);
        input.focus();
        input.select();
    }

    function removeKeyword(index) {
        const terms = state.effectiveKeywordTerms.slice();
        if (index < 0 || index >= terms.length) {
            return;
        }
        terms.splice(index, 1);
        applyKeywordTerms(terms);
    }

    function submitStructuredCondition() {
        const optionIndex = conditionField.value ? Number(conditionField.value) : -1;
        const option = state.fieldOptions[optionIndex];
        const value = readConditionValue(option);
        if (!conditionValueIsValid(option, value)) {
            setConditionMessage("Enter a value supported by the selected field.");
            return;
        }
        const condition = {
            dimension: option.dimension,
            operator: option.operator,
            value,
        };
        const editingIndex = state.editingConditionIndex;
        if (
            state.structuredConditions.some((item, index) => (
                index !== editingIndex && sameCondition(item, condition)
            ))
        ) {
            setConditionMessage("This condition is already added.");
            return;
        }
        if (editingIndex === null) {
            state.structuredConditions.push(condition);
        } else if (state.structuredConditions[editingIndex]) {
            state.structuredConditions[editingIndex] = condition;
        } else {
            console.error("Structured condition edit target is no longer available");
            state.editingConditionIndex = null;
            renderFieldSelector();
            return;
        }
        state.editingConditionIndex = null;
        renderFieldSelector();
        state.cursor = null;
        state.currentPage = 1;
        search();
    }

    function removeStructuredCondition(index) {
        if (!Number.isInteger(index) || !state.structuredConditions[index]) {
            return;
        }
        state.structuredConditions.splice(index, 1);
        state.editingConditionIndex = null;
        renderFieldSelector();
        state.cursor = null;
        state.currentPage = 1;
        search();
    }

    function showUnsupportedConditions() {
        const message = document.createElement("p");
        message.className = "wd-safe-message";
        message.textContent = "A field condition is unavailable. Remove or edit it before searching.";
        list.replaceChildren(message);
        pagination.hidden = true;
        renderUnderstanding([], "FAILED");
        renderFieldSelector();
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
            button.dataset.states = JSON.stringify(
                Array.isArray(descriptor.states) ? descriptor.states : []
            );
            button.dataset.searchableFields = JSON.stringify(
                Array.isArray(descriptor.searchable_fields)
                    ? descriptor.searchable_fields
                    : []
            );
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
        renderFieldSelector();
        return selectionChanged || previousVersion !== state.configVersion;
    }

    function resourceBusinessStates(resourceKey) {
        const button = Array.from(resourceTabs.querySelectorAll(".wd-resource-tab"))
            .find((item) => item.dataset.resource === resourceKey);
        if (!button) {
            return [];
        }
        try {
            const values = JSON.parse(button.dataset.states || "[]");
            if (
                !Array.isArray(values)
                || values.some((value) => typeof value !== "string" || !value)
            ) {
                console.error("Invalid Published state descriptor", resourceKey);
                return [];
            }
            return Array.from(new Set(values));
        } catch (error) {
            console.error("Unable to parse Published state descriptor", error);
            return [];
        }
    }

    function commonBusinessStates() {
        const selectedResources = state.resourceSelectionInitialized
            ? Array.from(state.resources)
            : resourceKeys();
        if (!selectedResources.length) {
            return [];
        }
        let common = resourceBusinessStates(selectedResources[0]);
        for (const resourceKey of selectedResources.slice(1)) {
            const available = new Set(resourceBusinessStates(resourceKey));
            common = common.filter((value) => available.has(value));
        }
        return common;
    }

    function renderStateOptions() {
        const activeCondition = state.refinements.find(
            (item) => item.dimension === "state"
        );
        const available = commonBusinessStates();
        const selectedValue = activeCondition && available.includes(activeCondition.value)
            ? activeCondition.value
            : "";
        stateInput.replaceChildren();
        const anyState = document.createElement("option");
        anyState.value = "";
        anyState.textContent = "Any state";
        stateInput.append(anyState);
        available.forEach((value) => {
            const option = document.createElement("option");
            option.value = value;
            option.textContent = value;
            stateInput.append(option);
        });
        stateInput.disabled = available.length === 0;
        stateInput.value = selectedValue;
        if (activeCondition && !selectedValue) {
            state.refinements = state.refinements.filter(
                (item) => item.dimension !== "state"
            );
            renderActiveRefinementControls();
            return true;
        }
        return false;
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
                const keepSelected = (
                    state.structuredConditions.length > 0 && state.resources.has(key)
                );
                element.textContent = keepSelected ? "0" : "";
                button.hidden = !keepSelected;
                if (!keepSelected) {
                    state.resources.delete(key);
                }
                return;
            }
            element.textContent = String(count);
            button.hidden = false;
        });
        renderSelectionState();
        const stateChanged = renderStateOptions();
        renderFieldSelector();
        return stateChanged;
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

            const renderedText = result.snapshot
                && typeof result.snapshot.rendered_text === "string"
                ? result.snapshot.rendered_text
                : null;
            const fields = result.snapshot && Array.isArray(result.snapshot.fields)
                ? result.snapshot.fields
                : [];
            if (renderedText !== null) {
                const content = document.createElement("div");
                content.className = "wd-card-template-text";
                content.textContent = renderedText;
                card.append(content);
            } else if (fields.length) {
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
        if (state.structuredConditions.some(
            (condition) => !isSupportedStructuredCondition(condition)
        )) {
            showUnsupportedConditions();
            return;
        }
        renderUnderstanding([], "SEARCHING");
        if (!state.resourceSelectionInitialized) {
            state.resources = new Set(resourceKeys());
            state.resourceSelectionInitialized = true;
        }
        state.hasSearched = true;
        clearResourceCounts();
        const payload = {
            query: state.rawQuery,
            conditions: state.structuredConditions,
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
                if (state.structuredConditions.some(
                    (condition) => !isSupportedStructuredCondition(condition)
                )) {
                    showUnsupportedConditions();
                    return;
                }
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
            if (renderCounts(data)) {
                state.cursor = null;
                state.currentPage = 1;
                return search(scrollToResults);
            }
            renderResults(data);
            renderUnderstanding(
                Array.isArray(data.effective_conditions) ? data.effective_conditions : [],
                data.status
            );
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
            renderUnderstanding([], "FAILED");
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

    conditionField.addEventListener("change", () => {
        renderFieldSelector();
    });
    conditionValueContainer.addEventListener("input", updateConditionSubmitState);
    conditionValueContainer.addEventListener("change", updateConditionSubmitState);
    conditionSubmit.addEventListener("click", submitStructuredCondition);
    removeUnavailableConditions.addEventListener("click", () => {
        state.structuredConditions = state.structuredConditions.filter(
            isSupportedStructuredCondition
        );
        state.editingConditionIndex = null;
        renderFieldSelector();
        state.cursor = null;
        state.currentPage = 1;
        search();
    });
    keywordAddSubmit.addEventListener("click", () => {
        const addition = keywordAddInput.value;
        if (!addition) {
            setConditionMessage("Enter a keyword to add.");
            return;
        }
        applyKeywordTerms([...state.effectiveKeywordTerms, addition]);
    });
    keywordAddInput.addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
            event.preventDefault();
            keywordAddSubmit.click();
        }
    });

    form.addEventListener("submit", (event) => {
        event.preventDefault();
        state.rawQuery = queryInput.value;
        state.refinements = [];
        renderStateOptions();
        renderActiveRefinementControls();
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
        renderStateOptions();
        renderFieldSelector();
        state.cursor = null;
        state.currentPage = 1;
        search();
    });
    reselectAllButton.addEventListener("click", () => {
        state.resources = new Set(resourceKeys());
        renderSelectionState();
        renderStateOptions();
        renderFieldSelector();
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
            renderActiveRefinementControls();
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
    renderStateOptions();
    renderFieldSelector();
    renderActiveRefinementControls();
    renderUnderstanding([], "EMPTY");
}());
