export function createSearchApi(context) {
    const { state, list, pagination } = context;
    const isNarrowWorkspace = (...args) => context.isNarrowWorkspace(...args);
    const conditionPayload = (...args) => context.conditionPayload(...args);
    const isSupportedStructuredCondition = (...args) => (
        context.isSupportedStructuredCondition(...args)
    );
    const showUnsupportedConditions = (...args) => (
        context.showUnsupportedConditions(...args)
    );
    const renderUnderstanding = (...args) => context.renderUnderstanding(...args);
    const resourceKeys = (...args) => context.resourceKeys(...args);
    const clearResourceCounts = (...args) => context.clearResourceCounts(...args);
    const renderResourceDescriptors = (...args) => (
        context.renderResourceDescriptors(...args)
    );
    const renderCounts = (...args) => context.renderCounts(...args);
    const renderResults = (...args) => context.renderResults(...args);
    const renderPagination = (...args) => context.renderPagination(...args);
    let searchSequence = 0;

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

    return search;
}
