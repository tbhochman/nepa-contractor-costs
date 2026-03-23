/**
 * Searchable, sortable, paginated data table with EIS project grouping.
 *
 * EIS contracts matched to a project are collapsed into one row showing the
 * project title and total cost. Clicking the row expands to show individual
 * contracts. EA contracts and unmatched EIS contracts appear as normal rows.
 */

const ROWS_PER_PAGE = 50;

function awardLinkFormat(v) {
  if (!v) return "";
  return `<a href="https://www.usaspending.gov/award/${v}" target="_blank" rel="noopener">View</a>`;
}

function typeFormat(v) {
  const cls = v || "UNKNOWN";
  const labels = { EIS: "EIS", EA: "EA", NEPA_SUPPORT: "Support", UNKNOWN: "?" };
  return `<span class="doc-type-badge ${cls}">${labels[cls] || cls}</span>`;
}

function amountFormat(v) {
  if (v == null) return "";
  return "$" + Number(v).toLocaleString("en-US", { maximumFractionDigits: 0 });
}

function truncate(s, len) {
  if (!s) return "";
  return s.length > len ? s.slice(0, len - 3) + "..." : s;
}

/**
 * Build grouped rows: EIS contracts with the same eis_title are collapsed
 * into a single group row. EA contracts and unmatched EIS contracts are
 * individual rows.
 */
function buildGroupedRows(records) {
  const eisGroups = {};
  const individualRows = [];

  for (const r of records) {
    if (r.document_type === "EIS" && r.eis_title) {
      if (!eisGroups[r.eis_title]) {
        eisGroups[r.eis_title] = {
          isGroup: true,
          eis_title: r.eis_title,
          document_type: "EIS",
          contracts: [],
          award_amount: 0,
          awarding_sub_agency: r.awarding_sub_agency || r.awarding_agency || "",
          start_date: r.start_date,
          fiscal_year: r.fiscal_year,
        };
      }
      const g = eisGroups[r.eis_title];
      g.contracts.push(r);
      g.award_amount += (r.award_amount || 0);
      // Use earliest start date
      if (r.start_date && (!g.start_date || r.start_date < g.start_date)) {
        g.start_date = r.start_date;
      }
      if (r.fiscal_year && (!g.fiscal_year || r.fiscal_year < g.fiscal_year)) {
        g.fiscal_year = r.fiscal_year;
      }
    } else {
      individualRows.push({ isGroup: false, ...r });
    }
  }

  return [...Object.values(eisGroups), ...individualRows];
}

export function renderDataTable(records, container, paginationContainer, countEl, d3) {
  let sortKey = "award_amount";
  let sortAsc = false;
  let page = 0;
  let searchText = "";
  let expandedGroups = new Set();

  function getFiltered() {
    const q = searchText ? searchText.toLowerCase() : "";
    const grouped = buildGroupedRows(records);
    if (!q) return grouped;
    return grouped.filter(r => {
      if (r.isGroup) {
        return (r.eis_title || "").toLowerCase().includes(q) ||
          (r.awarding_sub_agency || "").toLowerCase().includes(q) ||
          r.contracts.some(c =>
            (c.description || "").toLowerCase().includes(q) ||
            (c.recipient_name || "").toLowerCase().includes(q)
          );
      }
      return (r.description || "").toLowerCase().includes(q) ||
        (r.recipient_name || "").toLowerCase().includes(q) ||
        (r.awarding_sub_agency || "").toLowerCase().includes(q) ||
        (r.eis_title || "").toLowerCase().includes(q) ||
        (r.award_id || "").toLowerCase().includes(q);
    });
  }

  function getSorted(data) {
    return [...data].sort((a, b) => {
      let av = a[sortKey], bv = b[sortKey];
      if (av == null) return 1;
      if (bv == null) return -1;
      if (typeof av === "string") {
        av = av.toLowerCase();
        bv = (bv || "").toLowerCase();
      }
      if (av < bv) return sortAsc ? -1 : 1;
      if (av > bv) return sortAsc ? 1 : -1;
      return 0;
    });
  }

  function render() {
    const filtered = getFiltered();
    const sorted = getSorted(filtered);
    const totalPages = Math.max(1, Math.ceil(sorted.length / ROWS_PER_PAGE));
    page = Math.min(page, totalPages - 1);
    const start = page * ROWS_PER_PAGE;
    const pageData = sorted.slice(start, start + ROWS_PER_PAGE);

    // Count: groups + individual rows, and total contracts
    const totalContracts = filtered.reduce((n, r) => n + (r.isGroup ? r.contracts.length : 1), 0);
    countEl.textContent = `${filtered.length.toLocaleString()} rows (${totalContracts.toLocaleString()} contracts)`;

    // Build table
    let html = `<table><thead><tr>
      <th data-key="document_type">Type<span class="sort-arrow">${sortKey === "document_type" ? (sortAsc ? "\u25B2" : "\u25BC") : "\u25BC"}</span></th>
      <th data-key="award_amount" class="${sortKey === "award_amount" ? "sorted" : ""}">Amount<span class="sort-arrow">${sortKey === "award_amount" ? (sortAsc ? "\u25B2" : "\u25BC") : "\u25BC"}</span></th>
      <th data-key="awarding_sub_agency">Agency<span class="sort-arrow">\u25BC</span></th>
      <th>Detail</th>
      <th data-key="start_date">Start<span class="sort-arrow">\u25BC</span></th>
      <th data-key="fiscal_year">FY<span class="sort-arrow">\u25BC</span></th>
      <th>Link</th>
    </tr></thead><tbody>`;

    for (const row of pageData) {
      if (row.isGroup) {
        const expanded = expandedGroups.has(row.eis_title);
        const chevron = expanded ? "\u25BC" : "\u25B6";
        const contractCount = row.contracts.length;

        html += `<tr class="group-row" data-group="${escapeHtml(row.eis_title)}">
          <td>${typeFormat(row.document_type)}</td>
          <td class="col-amount">${amountFormat(row.award_amount)}</td>
          <td>${escapeHtml(row.awarding_sub_agency)}</td>
          <td class="col-description"><span class="expand-chevron">${chevron}</span> <strong>${escapeHtml(truncate(row.eis_title, 60))}</strong> <span class="contract-count">(${contractCount} contracts)</span></td>
          <td>${row.start_date || ""}</td>
          <td>${row.fiscal_year || ""}</td>
          <td></td>
        </tr>`;

        if (expanded) {
          for (const c of row.contracts) {
            html += `<tr class="child-row">
              <td></td>
              <td class="col-amount">${amountFormat(c.award_amount)}</td>
              <td></td>
              <td class="col-description">${escapeHtml(truncate(c.recipient_name, 30))} — ${escapeHtml(truncate(c.description, 55))}</td>
              <td>${c.start_date || ""}</td>
              <td>${c.fiscal_year || ""}</td>
              <td>${awardLinkFormat(c.generated_internal_id)}</td>
            </tr>`;
          }
        }
      } else {
        // Individual row (EA or unmatched EIS)
        const detail = row.eis_title
          ? `<em>${escapeHtml(truncate(row.eis_title, 40))}</em> — ${escapeHtml(truncate(row.description, 40))}`
          : `${escapeHtml(truncate(row.recipient_name, 25))} — ${escapeHtml(truncate(row.description, 55))}`;
        html += `<tr>
          <td>${typeFormat(row.document_type)}</td>
          <td class="col-amount">${amountFormat(row.award_amount)}</td>
          <td>${escapeHtml(row.awarding_sub_agency || "")}</td>
          <td class="col-description">${detail}</td>
          <td>${row.start_date || ""}</td>
          <td>${row.fiscal_year || ""}</td>
          <td>${awardLinkFormat(row.generated_internal_id)}</td>
        </tr>`;
      }
    }

    html += "</tbody></table>";
    container.innerHTML = html;

    // Expand/collapse handlers
    container.querySelectorAll(".group-row").forEach(tr => {
      tr.addEventListener("click", () => {
        const title = tr.dataset.group;
        if (expandedGroups.has(title)) {
          expandedGroups.delete(title);
        } else {
          expandedGroups.add(title);
        }
        render();
      });
    });

    // Sort handlers
    container.querySelectorAll("th[data-key]").forEach(th => {
      th.addEventListener("click", () => {
        const key = th.dataset.key;
        if (sortKey === key) {
          sortAsc = !sortAsc;
        } else {
          sortKey = key;
          sortAsc = key === "awarding_sub_agency";
        }
        render();
      });
    });

    // Pagination
    let pHtml = "";
    if (totalPages > 1) {
      if (page > 0) pHtml += `<button data-page="${page - 1}">&laquo; Prev</button>`;
      const startPage = Math.max(0, page - 3);
      const endPage = Math.min(totalPages - 1, page + 3);
      for (let i = startPage; i <= endPage; i++) {
        pHtml += `<button data-page="${i}" class="${i === page ? "active" : ""}">${i + 1}</button>`;
      }
      if (page < totalPages - 1) pHtml += `<button data-page="${page + 1}">Next &raquo;</button>`;
    }
    paginationContainer.innerHTML = pHtml;
    paginationContainer.querySelectorAll("button").forEach(btn => {
      btn.addEventListener("click", () => {
        page = parseInt(btn.dataset.page);
        render();
        container.scrollIntoView({ behavior: "smooth" });
      });
    });
  }

  return {
    render,
    setSearch(text) {
      searchText = text;
      page = 0;
      render();
    },
    update(newRecords) {
      records = newRecords;
      page = 0;
      expandedGroups.clear();
      render();
    },
  };
}

function escapeHtml(s) {
  if (!s) return "";
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}
