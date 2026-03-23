/**
 * Chart rendering functions using Observable Plot.
 */

const COLORS = {
  EIS: "#2563eb",
  EA: "#16a34a",
  NEPA_SUPPORT: "#9333ea",
  UNKNOWN: "#9ca3af",
};

const DOC_TYPE_LABELS = {
  EIS: "EIS",
  EA: "EA",
  NEPA_SUPPORT: "NEPA Support",
  UNKNOWN: "Unknown",
};

function docTypeColor(d) {
  return COLORS[d.document_type] || COLORS.UNKNOWN;
}

export function renderSpendingByYear(records, container, Plot, d3) {
  container.innerHTML = "";
  if (!records.length) { container.textContent = "No data"; return; }

  const byYear = d3.rollup(
    records.filter(d => d.fiscal_year),
    v => d3.sum(v, d => d.award_amount || 0),
    d => d.fiscal_year
  );

  const data = Array.from(byYear, ([year, total]) => ({ year, total }))
    .sort((a, b) => a.year - b.year);

  const chart = Plot.plot({
    width: Math.min(container.clientWidth - 48, 900),
    height: 350,
    marginBottom: 50,
    marginLeft: 80,
    x: { label: "Fiscal Year", tickFormat: d => String(d) },
    y: { label: "Total Spend ($)", grid: true, tickFormat: d => d3.format("$.2s")(d) },
    marks: [
      Plot.barY(data, { x: "year", y: "total", fill: "#2563eb", tip: true }),
      Plot.ruleY([0]),
    ],
  });

  container.append(chart);
}

export function renderCostByType(records, container, Plot, d3) {
  container.innerHTML = "";
  const typed = records.filter(d => d.document_type && d.document_type !== "UNKNOWN" && d.award_amount > 0);
  if (!typed.length) { container.textContent = "No data"; return; }

  const data = typed.map(d => ({
    ...d,
    type_label: DOC_TYPE_LABELS[d.document_type] || d.document_type,
  }));

  const chart = Plot.plot({
    width: Math.min(container.clientWidth - 48, 600),
    height: 350,
    marginLeft: 90,
    x: {
      label: "Award Amount ($)",
      grid: true,
      tickFormat: d => d3.format("$.2s")(d),
      type: "log",
    },
    y: { label: null },
    color: { range: [COLORS.EIS, COLORS.EA, COLORS.NEPA_SUPPORT] },
    marks: [
      Plot.dot(data, Plot.dodgeY({
        x: "award_amount",
        fill: d => COLORS[d.document_type],
        r: 3,
        fy: "type_label",
        tip: true,
        title: d => `${d.recipient_name}\n$${d3.format(",.0f")(d.award_amount)}\n${d.description?.slice(0, 80)}`,
      })),
    ],
    facet: { data, y: "type_label", marginRight: 0 },
  });

  container.append(chart);
}

export function renderByAgency(records, container, Plot, d3) {
  container.innerHTML = "";
  if (!records.length) { container.textContent = "No data"; return; }

  const byAgency = d3.rollup(
    records,
    v => d3.sum(v, d => d.award_amount || 0),
    d => d.awarding_sub_agency || d.awarding_agency || "Unknown"
  );

  const data = Array.from(byAgency, ([agency, total]) => ({ agency, total }))
    .sort((a, b) => b.total - a.total)
    .slice(0, 15);

  const chart = Plot.plot({
    width: Math.min(container.clientWidth - 48, 900),
    height: 450,
    marginLeft: 280,
    x: { label: "Total Spend ($)", grid: true, tickFormat: d => d3.format("$.2s")(d) },
    y: { label: null },
    marks: [
      Plot.barX(data, {
        y: "agency",
        x: "total",
        fill: "#2563eb",
        sort: { y: "-x" },
        tip: true,
      }),
      Plot.ruleX([0]),
    ],
  });

  container.append(chart);
}

export function renderDuration(records, container, Plot, d3) {
  container.innerHTML = "";
  const withDuration = records.filter(d => d.duration_days > 0 && d.duration_days < 5000);
  if (!withDuration.length) { container.textContent = "No data"; return; }

  const chart = Plot.plot({
    width: Math.min(container.clientWidth - 48, 900),
    height: 300,
    marginBottom: 50,
    x: { label: "Duration (days)" },
    y: { label: "Contracts", grid: true },
    marks: [
      Plot.rectY(
        withDuration,
        Plot.binX({ y: "count" }, { x: "duration_days", fill: "#2563eb", thresholds: 40 })
      ),
      Plot.ruleY([0]),
    ],
  });

  container.append(chart);
}

export function renderTopContractors(records, container, Plot, d3) {
  container.innerHTML = "";
  if (!records.length) { container.textContent = "No data"; return; }

  const byContractor = d3.rollup(
    records,
    v => d3.sum(v, d => d.award_amount || 0),
    d => d.recipient_name || "Unknown"
  );

  const data = Array.from(byContractor, ([contractor, total]) => ({ contractor, total }))
    .sort((a, b) => b.total - a.total)
    .slice(0, 15);

  const chart = Plot.plot({
    width: Math.min(container.clientWidth - 48, 900),
    height: 450,
    marginLeft: 280,
    x: { label: "Total Spend ($)", grid: true, tickFormat: d => d3.format("$.2s")(d) },
    y: { label: null },
    marks: [
      Plot.barX(data, {
        y: "contractor",
        x: "total",
        fill: "#16a34a",
        sort: { y: "-x" },
        tip: true,
      }),
      Plot.ruleX([0]),
    ],
  });

  container.append(chart);
}
