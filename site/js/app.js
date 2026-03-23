/**
 * Main application: data loading, filter state, chart orchestration.
 */

import * as Plot from "https://cdn.jsdelivr.net/npm/@observablehq/plot@0.6/+esm";
import * as d3 from "https://cdn.jsdelivr.net/npm/d3@7/+esm";
import {
  renderAvgCostByYear,
  renderAvgDurationByYear,
  renderCostByType,
  renderEISProjects,
} from "./charts.js";
import { renderDataTable } from "./table.js";

let allRecords = [];
let filteredRecords = [];
let eisProjects = null;
let tableController = null;

// Filters
const filterDocType = document.getElementById("filter-doc-type");
const filterAgency = document.getElementById("filter-agency");
const filterYearStart = document.getElementById("filter-year-start");
const filterYearEnd = document.getElementById("filter-year-end");
const resetBtn = document.getElementById("reset-filters");
const searchInput = document.getElementById("table-search");

async function loadData() {
  const [contractResp, eisResp] = await Promise.all([
    fetch("nepa_contracts.json"),
    fetch("eis_projects.json").catch(() => null),
  ]);
  const data = await contractResp.json();
  if (eisResp && eisResp.ok) {
    eisProjects = await eisResp.json();
  }

  document.getElementById("last-updated").textContent =
    `Data last updated: ${new Date(data.generated_at).toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" })}`;

  return data.records.map(r => ({
    ...r,
    award_amount: r.award_amount ? Number(r.award_amount) : null,
    duration_days: r.duration_days ? Number(r.duration_days) : null,
    fiscal_year: r.fiscal_year ? Number(r.fiscal_year) : null,
  }));
}

function populateFilters(records) {
  const agencies = [...new Set(records.map(r => r.awarding_sub_agency || r.awarding_agency).filter(Boolean))].sort();
  for (const ag of agencies) {
    const opt = document.createElement("option");
    opt.value = ag;
    opt.textContent = ag;
    filterAgency.appendChild(opt);
  }

  const years = [...new Set(records.map(r => r.fiscal_year).filter(Boolean))].sort((a, b) => a - b);
  for (const yr of years) {
    const optStart = document.createElement("option");
    optStart.value = yr;
    optStart.textContent = yr;
    filterYearStart.appendChild(optStart);

    const optEnd = document.createElement("option");
    optEnd.value = yr;
    optEnd.textContent = yr;
    filterYearEnd.appendChild(optEnd);
  }
  if (years.length) {
    filterYearStart.value = years[0];
    filterYearEnd.value = years[years.length - 1];
  }
}

function applyFilters() {
  const docType = filterDocType.value;
  const agency = filterAgency.value;
  const yearStart = parseInt(filterYearStart.value) || 0;
  const yearEnd = parseInt(filterYearEnd.value) || 9999;

  filteredRecords = allRecords.filter(r => {
    if (docType !== "eis_ea" && r.document_type !== docType) return false;
    if (agency !== "all") {
      const recAgency = r.awarding_sub_agency || r.awarding_agency || "";
      if (recAgency !== agency) return false;
    }
    if (r.fiscal_year && (r.fiscal_year < yearStart || r.fiscal_year > yearEnd)) return false;
    return true;
  });
}

function formatCurrency(n) {
  if (n >= 1e9) return "$" + (n / 1e9).toFixed(1) + "B";
  if (n >= 1e6) return "$" + (n / 1e6).toFixed(1) + "M";
  if (n >= 1e3) return "$" + (n / 1e3).toFixed(0) + "K";
  return "$" + n.toFixed(0);
}

function median(arr) {
  if (!arr.length) return 0;
  const sorted = [...arr].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
}

function mean(arr) {
  if (!arr.length) return 0;
  return d3.sum(arr) / arr.length;
}

function updateStats() {
  const amounts = filteredRecords.map(r => r.award_amount).filter(v => v != null && v > 0);
  const durations = filteredRecords.map(r => r.duration_days).filter(v => v != null && v > 0);

  document.getElementById("stat-count").textContent =
    filteredRecords.length.toLocaleString();
  document.getElementById("stat-median-cost").textContent =
    amounts.length ? formatCurrency(median(amounts)) : "--";
  document.getElementById("stat-median-duration").textContent =
    durations.length ? Math.round(median(durations)).toLocaleString() : "--";
  document.getElementById("stat-mean-cost").textContent =
    amounts.length ? formatCurrency(mean(amounts)) : "--";
  document.getElementById("stat-eis-matched").textContent =
    eisProjects ? eisProjects.project_count.toLocaleString() : "--";
}

function renderCharts() {
  renderAvgCostByYear(filteredRecords, document.getElementById("chart-avg-cost-by-year"), Plot, d3);
  renderAvgDurationByYear(filteredRecords, document.getElementById("chart-avg-duration-by-year"), Plot, d3);
  renderCostByType(filteredRecords, document.getElementById("chart-cost-by-type"), Plot, d3);
  renderEISProjects(eisProjects, document.getElementById("chart-eis-projects"), Plot, d3);
}

function renderAll() {
  applyFilters();
  updateStats();
  renderCharts();
  if (tableController) {
    tableController.update(filteredRecords);
  }
}

async function init() {
  try {
    allRecords = await loadData();
  } catch (e) {
    document.body.innerHTML = `<p style="color:red;padding:2rem">Failed to load data: ${e.message}</p>`;
    return;
  }

  populateFilters(allRecords);
  applyFilters();
  updateStats();
  renderCharts();

  tableController = renderDataTable(
    filteredRecords,
    document.getElementById("data-table"),
    document.getElementById("table-pagination"),
    document.getElementById("table-count"),
    d3,
  );
  tableController.render();

  filterDocType.addEventListener("change", renderAll);
  filterAgency.addEventListener("change", renderAll);
  filterYearStart.addEventListener("change", renderAll);
  filterYearEnd.addEventListener("change", renderAll);

  resetBtn.addEventListener("click", () => {
    filterDocType.value = "eis_ea";
    filterAgency.value = "all";
    const opts = [...filterYearStart.options];
    if (opts.length) {
      filterYearStart.value = opts[0].value;
      filterYearEnd.value = opts[opts.length - 1].value;
    }
    searchInput.value = "";
    if (tableController) tableController.setSearch("");
    renderAll();
  });

  searchInput.addEventListener("input", () => {
    if (tableController) tableController.setSearch(searchInput.value);
  });
}

init();
