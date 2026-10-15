import { createConditions } from "./workspace_conditions.js?v=cc018-phase4-v02";
import { createResources } from "./workspace_resources.js?v=cc018-phase4-v02";
import { createResults } from "./workspace_results.js?v=cc018-phase4-v02";
import { createSearchApi } from "./workspace_search.js?v=cc018-phase4-v02";

export function initializeWorkspace() {
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
        return false;
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
    const context = {
        list, queryInput, form, conditionView, keywordView, keywordCombinator,
        structuredView, effectiveRefinementView, conditionCombination,
        conditionField, conditionOperator, conditionValueContainer,
        conditionSubmit, conditionMessage, dateMessage,
        removeUnavailableConditions, keywordAddInput, keywordAddSubmit,
        activeView, workspace, resourceTabs, resourceEmpty, reselectAllButton,
        pagination, pageSizeInput, pageSummary, pageControls, stateInput, state,
        cardDensityExpanded: window.innerWidth >= 768,
        isNarrowWorkspace,
    };
    let searchImplementation;
    context.search = (...args) => searchImplementation(...args);
    Object.assign(context, createConditions(context));
    Object.assign(context, createResources(context));
    Object.assign(context, createResults(context));
    searchImplementation = createSearchApi(context);

    const {
        search, renderStateOptions,
        renderSelectionState, renderFieldSelector, updateConditionSubmitState,
        submitStructuredCondition, isSupportedStructuredCondition,
        setConditionMessage, applyKeywordTerms, renderActiveRefinementControls,
        applyDateRefinement, resourceKeys, renderUnderstanding,
    } = context;

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
    return true;
}
