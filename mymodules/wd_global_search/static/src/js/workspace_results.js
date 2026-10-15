export function createResults(context) {
    const {
        state, list, pageSummary, pageControls, pageSizeInput, pagination, resourceTabs,
    } = context;
    let cardDensityExpanded = context.cardDensityExpanded;
    const text = (...args) => context.text(...args);

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

            const hasStructuredCard = result.snapshot
                && Object.prototype.hasOwnProperty.call(result.snapshot, "card")
            const structuredCard = hasStructuredCard ? result.snapshot.card : null;
            if (hasStructuredCard) {
                if (
                    !structuredCard
                    || structuredCard.schema_version !== 1
                    || typeof structuredCard.title !== "string"
                    || typeof structuredCard.meta !== "string"
                    || typeof structuredCard.summary !== "string"
                    || !Array.isArray(structuredCard.details)
                    || !structuredCard.details.every((item) => typeof item === "string")
                    || typeof structuredCard.details_truncated !== "boolean"
                ) {
                    const unavailable = document.createElement("p");
                    unavailable.className = "wd-safe-message";
                    unavailable.dataset.testid = "structured-card-unavailable";
                    unavailable.textContent = "Structured card unavailable.";
                    card.append(unavailable);
                } else {
                    if (structuredCard.title) {
                        const title = document.createElement("h3");
                        title.className = "wd-card-title wd-card-primary";
                        title.textContent = structuredCard.title;
                        card.append(title);
                    }
                    if (structuredCard.meta) {
                        const meta = document.createElement("div");
                        meta.className = "wd-card-meta wd-card-resource";
                        meta.textContent = structuredCard.meta;
                        card.append(meta);
                    }
                    if (structuredCard.summary) {
                        const summary = document.createElement("p");
                        summary.className = "wd-card-summary wd-card-secondary";
                        summary.textContent = structuredCard.summary;
                        card.append(summary);
                    }
                    if (structuredCard.details.length || structuredCard.details_truncated) {
                        const details = document.createElement("div");
                        details.className = "wd-card-details wd-card-secondary";
                        structuredCard.details.forEach((item, index) => {
                            if (index) {
                                details.append(document.createTextNode(" · "));
                            }
                            const detail = document.createElement("span");
                            detail.className = "wd-card-detail";
                            detail.textContent = item;
                            details.append(detail);
                        });
                        if (structuredCard.details_truncated) {
                            if (structuredCard.details.length) {
                                details.append(document.createTextNode(" · "));
                            }
                            const overflow = document.createElement("span");
                            overflow.className = "wd-card-details-overflow";
                            overflow.textContent = "...";
                            details.append(overflow);
                        }
                        card.append(details);
                    }
                }
            }
            const renderedText = !hasStructuredCard && result.snapshot
                && typeof result.snapshot.rendered_text === "string"
                ? result.snapshot.rendered_text
                : null;
            const fields = !hasStructuredCard
                && result.snapshot && Array.isArray(result.snapshot.fields)
                ? result.snapshot.fields
                : [];
            if (!hasStructuredCard && renderedText !== null) {
                const content = document.createElement("div");
                content.className = "wd-card-template-text";
                content.textContent = renderedText;
                card.append(content);
            } else if (!hasStructuredCard && fields.length) {
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
            } else if (!hasStructuredCard) {
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

    return { renderResults, renderPagination };
}
