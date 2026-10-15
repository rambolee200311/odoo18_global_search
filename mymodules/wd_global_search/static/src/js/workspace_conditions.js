export function createConditions(context) {
    const {
        state, resourceTabs, queryInput, conditionView, keywordView,
        keywordCombinator, structuredView, effectiveRefinementView,
        conditionCombination, conditionField, conditionOperator,
        conditionValueContainer, conditionSubmit, conditionMessage, dateMessage,
        removeUnavailableConditions, keywordAddInput, keywordAddSubmit,
        activeView, stateInput,
    } = context;
    const resourceKeys = (...args) => context.resourceKeys(...args);
    const renderStateOptions = (...args) => context.renderStateOptions(...args);
    const renderSelectionState = (...args) => context.renderSelectionState(...args);
    const search = (...args) => context.search(...args);

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

    return {
        text,
        conditionPayload,
        isSupportedStructuredCondition,
        setConditionMessage,
        renderFieldSelector,
        updateConditionSubmitState,
        applyDateRefinement,
        renderActiveRefinementControls,
        renderUnderstanding,
        applyKeywordTerms,
        submitStructuredCondition,
        showUnsupportedConditions,
    };
}
