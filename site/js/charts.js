/**
 * Chart rendering functions using Observable Plot.
 */

const COLORS = {
  EIS: "#2563eb",
  EA: "#16a34a",
};

const DOC_TYPE_LABELS = {
  EIS: "EIS",
  EA: "EA",
};

export function renderAvgCostByYear(records, container, Plot, d3) {
  container.innerHTML = "";
  const valid = records.filter(d => d.fiscal_year && d.award_amount > 0);
  if (!valid.length) { container.textContent = "No data"; return; }

  const byYearType = d3.rollup(
    valid,
    v => d3.median(v, d => d.award_amount),
    d => d.fiscal_year,
    d => d.document_type
  );

  const data = [];
  for (const [year, types] of byYearType) {
    for (const [type, median] of types) {
      data.push({ year, type, median });
    }
  }
  data.sort((a, b) => a.year - b.year);

  const chart = Plot.plot({
    width: Math.min(container.clientWidth - 48, 900),
    height: 350,
    marginBottom: 50,
    marginLeft: 80,
    x: { label: "Fiscal Year", tickFormat: d => String(d) },
    y: { label: "Median Contract Cost ($)", grid: true, tickFormat: d => d3.format("$.2s")(d) },
    color: { domain: ["EIS", "EA"], range: [COLORS.EIS, COLORS.EA], legend: true },
    marks: [
      Plot.line(data, { x: "year", y: "median", stroke: "type", strokeWidth: 2, tip: true }),
      Plot.dot(data, { x: "year", y: "median", fill: "type", r: 3 }),
      Plot.ruleY([0]),
    ],
  });

  container.append(chart);
}

export function renderAvgDurationByYear(records, container, Plot, d3) {
  container.innerHTML = "";
  const valid = records.filter(d => d.fiscal_year && d.duration_days > 0 && d.duration_days < 5000);
  if (!valid.length) { container.textContent = "No data"; return; }

  const byYearType = d3.rollup(
    valid,
    v => d3.median(v, d => d.duration_days),
    d => d.fiscal_year,
    d => d.document_type
  );

  const data = [];
  for (const [year, types] of byYearType) {
    for (const [type, median] of types) {
      data.push({ year, type, median });
    }
  }
  data.sort((a, b) => a.year - b.year);

  const chart = Plot.plot({
    width: Math.min(container.clientWidth - 48, 900),
    height: 350,
    marginBottom: 50,
    marginLeft: 80,
    x: { label: "Fiscal Year", tickFormat: d => String(d) },
    y: { label: "Median Duration (days)", grid: true },
    color: { domain: ["EIS", "EA"], range: [COLORS.EIS, COLORS.EA], legend: true },
    marks: [
      Plot.line(data, { x: "year", y: "median", stroke: "type", strokeWidth: 2, tip: true }),
      Plot.dot(data, { x: "year", y: "median", fill: "type", r: 3 }),
      Plot.ruleY([0]),
    ],
  });

  container.append(chart);
}

export function renderCostByType(records, container, Plot, d3) {
  container.innerHTML = "";
  const typed = records.filter(d => d.award_amount > 0);
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
    v => d3.median(v, d => d.award_amount || 0),
    d => d.awarding_sub_agency || d.awarding_agency || "Unknown"
  );

  const data = Array.from(byAgency, ([agency, median]) => ({ agency, median }))
    .sort((a, b) => b.median - a.median)
    .slice(0, 15);

  const chart = Plot.plot({
    width: Math.min(container.clientWidth - 48, 900),
    height: 450,
    marginLeft: 280,
    x: { label: "Median Contract Cost ($)", grid: true, tickFormat: d => d3.format("$.2s")(d) },
    y: { label: null },
    marks: [
      Plot.barX(data, {
        y: "agency",
        x: "median",
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
    v => ({ total: d3.sum(v, d => d.award_amount || 0), count: v.length }),
    d => d.recipient_name || "Unknown"
  );

  const data = Array.from(byContractor, ([contractor, { total, count }]) => ({ contractor, total, count }))
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
        title: d => `${d.contractor}\n$${d3.format(",.0f")(d.total)} (${d.count} contracts)`,
      }),
      Plot.ruleX([0]),
    ],
  });

  container.append(chart);
}

export function renderEISProjects(eisProjects, container, Plot, d3) {
  container.innerHTML = "";
  if (!eisProjects || !eisProjects.projects || !eisProjects.projects.length) {
    container.textContent = "No matched EIS projects";
    return;
  }

  const data = eisProjects.projects
    .slice(0, 20)
    .map(p => ({
      title: p.eis_title.length > 60 ? p.eis_title.slice(0, 57) + "..." : p.eis_title,
      full_title: p.eis_title,
      total: p.total_contractor_cost,
      count: p.contract_count,
      agency: p.eis_agency,
      duration: p.eis_duration_years,
    }));

  const chart = Plot.plot({
    width: Math.min(container.clientWidth - 48, 900),
    height: 550,
    marginLeft: 380,
    x: { label: "Total Contractor Cost ($)", grid: true, tickFormat: d => d3.format("$.2s")(d) },
    y: { label: null },
    marks: [
      Plot.barX(data, {
        y: "title",
        x: "total",
        fill: "#2563eb",
        sort: { y: "-x" },
        tip: true,
        title: d => `${d.full_title}\n${d.agency} | ${d.count} contract(s)\n$${d3.format(",.0f")(d.total)}${d.duration ? `\nEIS duration: ${d.duration.toFixed(1)} years` : ""}`,
      }),
      Plot.ruleX([0]),
      Plot.text(data, {
        y: "title",
        x: "total",
        text: d => `${d.count}`,
        dx: 12,
        fontSize: 10,
        fill: "#555",
      }),
    ],
  });

  container.append(chart);
}
