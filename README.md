# NEPA Contractor Costs

A public dashboard tracking federal procurement spending on NEPA (National Environmental Policy Act) contractor services — Environmental Impact Statements (EIS), Environmental Assessments (EA), and general NEPA support.

**[View the Dashboard](https://thomashochman.github.io/nepa-contractor-costs/)**

## What This Is

No one has systematically used federal procurement data to analyze NEPA costs across agencies. The GAO's 2014 report ([GAO-14-369](https://www.gao.gov/products/gao-14-369)) found that agencies don't track NEPA costs, and no governmentwide mechanism exists. This project fills that gap by pulling contract award data from [USASpending.gov](https://usaspending.gov).

## Data

The pipeline queries USASpending.gov using three layered searches:

1. **PSC code F110** — contracts coded "Development of EIS/EA, Technical Analysis/Environmental Audits"
2. **Keyword "environmental impact statement"** — catches mis-coded EIS contracts
3. **Keyword "environmental assessment" + NAICS 541620** — catches EA contracts under Environmental Consulting Services

Results are deduplicated and classified as EIS, EA, or NEPA Support based on description text.

## Caveats

- **Contractor costs only** — does not include internal agency staff time
- **No Categorical Exclusions** — CEs are done in-house, below reporting thresholds
- **No applicant-funded work** — private NEPA consulting (e.g., for FERC-jurisdictional projects) is invisible to procurement data
- **Classification is heuristic** — regex on contract descriptions, with manual override support

## Running Locally

```bash
pip install -r requirements.txt

# Full pipeline run
python -m pipeline.run_pipeline --skip-enrich

# Serve dashboard locally
cd site && python -m http.server 8080
# Then copy data/nepa_contracts.json and data/metadata.json into site/
```

## Project Structure

```
pipeline/          Python data pipeline (USASpending API client)
site/              Static dashboard (Observable Plot + vanilla JS)
data/              Output CSV/JSON datasets
overrides/         Manual classification corrections
.github/workflows/ Monthly data refresh + GitHub Pages deploy
```

## License

MIT
