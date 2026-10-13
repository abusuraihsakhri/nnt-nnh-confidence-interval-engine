# NNT / NNH Confidence Interval Engine

Calculate number needed to treat (NNT), number needed to harm (NNH), absolute risk reduction (ARR), relative risk (RR), and two-sided confidence intervals from adverse-event counts in **two independent groups**. The standalone browser tool and Python library implement Newcombe's uncorrected Wilson-score method for the risk difference.

## Features

- Counts-based risks, relative effects, NNT/NNH, and upward whole-person rounding
- Two-sided 90%, 95%, or 99% score intervals in the browser; configurable confidence levels in Python
- Explicitly undefined/unbounded reciprocal intervals when the risk-difference interval contains zero
- Browser batch CSV processing and download; no calculation backend required
- Python single-case CLI and atomic validated batch CSV export
- Optional REST API and separately maintained, nonclinical legacy audit demo

## Use the browser application

Serve this repository as a static site (e.g., run **python -m http.server 8000**) and open **http://localhost:8000**. Enter **adverse-event counts**, not percentages, for control and treatment plus each group's total participants. Click **Calculate**.

CSV import requires the columns **control_events, control_total, treatment_events, treatment_total**. See [sample.csv](sample.csv). Optional de-identified study metadata is preserved. Browser imports are limited to 1 MB and 4,000 data rows; a bad row aborts export.

**Privacy:** Browser calculations and CSV handling are entirely local using JavaScript and the File API. The application does not transmit entered data or store it on a backend. Host platforms may still record normal page requests. Use aggregated study data rather than personal identifiers.

## Python CLI

Python 3.10+; the statistical engine uses the standard library only.

    python nnt_calc.py single \
      --control-events 120 --control-total 1000 \
      --treatment-events 80 --treatment-total 1000 \
      --confidence 0.95

    python nnt_calc.py batch -i sample.csv -o results.csv

Batch processing validates all rows before replacing the destination CSV. When the risk-difference interval contains zero, reciprocal confidence endpoints are not finite: JSON returns null and CSV leaves endpoints blank.

## REST API and legacy demonstration tools

    python -m pip install -r requirements.txt
    python cli.py serve --host 127.0.0.1 --port 8000

The browser app is served at **/**, interactive API documentation at **/docs**, and the actual calculator is **POST /api/nnt**:

    curl -s http://127.0.0.1:8000/api/nnt \
      -H 'Content-Type: application/json' \
      -d '{"control_events":120,"control_total":1000,"treatment_events":80,"treatment_total":1000}'

Legacy **cli.py audit, chat, batch, verify-audit** commands and related API routes remain for compatibility. They are *demonstration audit workflows*, not validated NNT calculations or clinical decision-support rules. The mock chat does not invoke an external model.

Those legacy audit features require a private **AUDIT_SECRET_KEY**. Generate and export a unique key before serving audit routes or starting Docker Compose:

    export AUDIT_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
    docker compose up --build

The default Compose port binds to 127.0.0.1:8000. The audit ledger is held in memory, and the legacy API is not designed as an authenticated multi-user service. Do not submit protected health information. Do not reuse a secret that has appeared in Git history.

## Statistical method

For adverse events, event risk = events / participants and ARR = control risk − treatment risk. Positive ARR implies benefit (NNT = 1/ARR); negative ARR implies harm (NNH = 1/|ARR|). Zero ARR has no finite reciprocal. Relative risk is undefined when control risk is zero.

Two-sided uncertainty uses Newcombe (1998), method 10, combining uncorrected Wilson score intervals for the *independent* binomial groups. If the resulting ARR interval touches or crosses zero, the reciprocal interval is unbounded/disconnected; do not report a spurious finite interval. The method is not suitable for matched, clustered, adjusted, time-to-event, or non-binary outcomes, and does not confer clinical validation.

Reference: Newcombe RG. *Interval estimation for the difference between independent proportions: comparison of eleven methods.* Statistics in Medicine. 1998;17:873–890. [PubMed](https://pubmed.ncbi.nlm.nih.gov/9595617/).

## Development and tests

    python -m pip install -r requirements.txt
    python -m pytest -q
    node --check app.js
    node --test tests/test_web.cjs

CI tests Python 3.10–3.13 and Node's built-in test runner. A successful production-branch build attempts to deploy the client-side application to GitHub Pages. Python itself does not run on GitHub Pages; the browser calculates in JavaScript without Pyodide.

Modern Chrome, Firefox, Safari, and Edge support the required JavaScript and File APIs. Manual real-browser end-to-end validation remains separate from automated tests.

## License

[MIT](LICENSE).
