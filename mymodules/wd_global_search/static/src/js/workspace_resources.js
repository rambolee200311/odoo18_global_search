export function createResources(context) {
    const { state, resourceTabs, resourceEmpty, reselectAllButton, stateInput } = context;
    const renderFieldSelector = (...args) => context.renderFieldSelector(...args);
    const renderActiveRefinementControls = (...args) => (
        context.renderActiveRefinementControls(...args)
    );
    const text = (...args) => context.text(...args);

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
                const keepSelected = state.resources.has(key);
                element.textContent = keepSelected ? "0" : "";
                button.hidden = !keepSelected;
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

    return {
        resourceKeys,
        renderSelectionState,
        clearResourceCounts,
        renderResourceDescriptors,
        renderStateOptions,
        renderCounts,
    };
}
