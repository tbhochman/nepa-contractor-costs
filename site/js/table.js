/**
 * Searchable, sortable, paginated data table.
 */

const ROWS_PER_PAGE = 50;

const COLUMNS = [
  { key: "document_type", label: "Type", format: typeFormat, className: "" },
  { key: "award_amount", label: "Amount", format: amountFormat, className: "col-amount" },
  { key: "awarding_sub_agency", label: "Agency", format: v => v || "", className: "" },
  { key: "recipient_name", label: "Contractor", format: v => v || "", className: "" },
  { key: "eis_title", label: "EIS Project", format: eisTitleFormat, className: "col-description" },
  { key: "description", label: "Description", format: v => v || "", className: "col-description" },
  { key: "start_date", label: "Start", format: v => v || "", className: "" },
  { key: "duration_days", label: "Days", format: v => v != null ? String(v) : "", className: "col-amount" },
  { key: "fiscal_year", label: "FY", format: v => v != null ? String(v) : "", className: "" },
  { key: "generated_internal_id", label: "Link", format: awardLinkFormat, className: "" },
];

function eisTitleFormat(v) {
  if (!v) return "<span style='color:#9ca3af'>—</span>";
  return v.length > 50 ? v.slice(0, 47) + "..." : v;
}

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

export function renderDataTable(records, container, paginationContainer, countEl, d3) {
  let sortKey = "award_amount";
  let sortAsc = false;
  let page = 0;
  let searchText = "";
  let filtered = records;

  function getFiltered() {
    if (!searchText) return records;
    const q = searchText.toLowerCase();
    return records.filter(r =>
      (r.description || "").toLowerCase().includes(q) ||
      (r.recipient_name || "").toLowerCase().includes(q) ||
      (r.awarding_sub_agency || "").toLowerCase().includes(q) ||
      (r.award_id || "").toLowerCase().includes(q)
    );
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
    filtered = getFiltered();
    const sorted = getSorted(filtered);
    const totalPages = Math.max(1, Math.ceil(sorted.length / ROWS_PER_PAGE));
    page = Math.min(page, totalPages - 1);
    const start = page * ROWS_PER_PAGE;
    const pageData = sorted.slice(start, start + ROWS_PER_PAGE);

    countEl.textContent = `${filtered.length.toLocaleString()} contracts`;

    // Build table
    let html = "<table><thead><tr>";
    for (const col of COLUMNS) {
      const isSorted = col.key === sortKey;
      const arrow = isSorted ? (sortAsc ? "\u25B2" : "\u25BC") : "\u25BC";
      html += `<th class="${isSorted ? "sorted" : ""}" data-key="${col.key}">`;
      html += `${col.label}<span class="sort-arrow">${arrow}</span></th>`;
    }
    html += "</tr></thead><tbody>";

    for (const row of pageData) {
      html += "<tr>";
      for (const col of COLUMNS) {
        html += `<td class="${col.className}">${col.format(row[col.key])}</td>`;
      }
      html += "</tr>";
    }

    html += "</tbody></table>";
    container.innerHTML = html;

    // Sorting click handlers
    container.querySelectorAll("th").forEach(th => {
      th.addEventListener("click", () => {
        const key = th.dataset.key;
        if (sortKey === key) {
          sortAsc = !sortAsc;
        } else {
          sortKey = key;
          sortAsc = key === "description" || key === "awarding_sub_agency" || key === "recipient_name";
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

  // Return updater
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
      render();
    },
  };
}
