# NNT & NNH Confidence Interval Engine

> **Domain:** Clinical Decision Support & Biomedical Computing  
> **Standards:** CAP / CLSI / ISO Quality Frameworks

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB.svg?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688.svg?logo=fastapi&logoColor=white)
![Audit Trail](https://img.shields.io/badge/Audit-HMAC--SHA256_Tamper--Evident-brightgreen.svg)
![Zero-PHI Guard](https://img.shields.io/badge/Guard-Zero--PHI_Outbound-blue.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker&logoColor=white)

</div>

---

## 📖 What It Does

Number Needed to Treat (NNT) & NNH Calculator with enterprise-grade security and audit capabilities.

- Calculates risk scores and clinical classifications
- Single and batch evaluation modes
- Multi-worker consensus system with specialized agents
- REST API via FastAPI
- WebSocket telemetry streaming

Author: Dr. Abu Suraih Sakhri
License: MIT

---

## 🚀 Installation

### Local Development
```bash
# Clone the repository
git clone https://github.com/abusuraihsakhri/nnt-nnh-confidence-interval-engine.git
cd nnt-nnh-confidence-interval-engine

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set required environment variable
export AUDIT_SECRET_KEY="your-secure-random-key-here"  # On Windows: set AUDIT_SECRET_KEY=...
```

### Docker
```bash
docker build -t nnt-nnh-confidence-interval-engine .
docker run -p 8000:8000 -e AUDIT_SECRET_KEY="your-secure-key" nnt-nnh-confidence-interval-engine
```

---

## ⚙️ Usage

### CLI Commands

#### 1. Single Evaluation
```bash
python cli.py audit --task-id TASK-001 --target TARGET-01 --primary 28.5 --secondary 14.2
```

#### 2. Batch Processing
```bash
python cli.py batch -i sample.csv -o results.csv
```

#### 3. Chat Query
```bash
python cli.py chat "Explain the current system status"
```

#### 4. Verify Audit Trail
```bash
python cli.py verify-audit
```

#### 5. Start API Server
```bash
python cli.py serve --host 127.0.0.1 --port 8000
```

### Direct NNT Calculator
```bash
# Single calculation
python nnt_calc.py single --v1 14.5 --v2 4.2 --v3 1.8

# Batch CSV processing
python nnt_calc.py batch -i sample.csv -o results.csv
```

### REST API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/metrics` | Prometheus-style metrics |
| POST | `/api/audit` | Submit task for evaluation |
| POST | `/api/chat` | Query the system |
| GET | `/api/audit/logs` | Get audit trail |

---

## 🛡️ Security Features

* **Zero-PHI Outbound Interceptor:** Active regex inspection blocking SSNs, MRNs, phone numbers, emails, and patient identifiers.
* **Tamper-Evident HMAC-SHA256 Audit Trail:** Chained, cryptographically signed logs for every evaluation.
* **Environment-Based Secret Management:** No hardcoded secrets; `AUDIT_SECRET_KEY` must be provided via environment variable.

---

## 🧪 Testing

```bash
# Set test environment variable
export AUDIT_SECRET_KEY="test-key"

# Run all tests
pytest -v

# Run with coverage
pytest -v --cov=.
```

---

## 📁 Project Structure

```
nnt-nnh-confidence-interval-engine/
├── agents/                 # Enterprise agent system
│   ├── api.py             # FastAPI REST server
│   ├── base.py            # Security, PHI guard, audit trail
│   ├── models.py          # Pydantic data models
│   ├── supervisor.py      # Multi-agent orchestrator
│   ├── workers.py         # Specialized evaluation workers
│   ├── llm_factory.py     # LLM provider abstraction
│   ├── metrics.py         # Prometheus metrics collector
│   ├── learning.py        # Bayesian calibration engine
│   └── streamer.py        # WebSocket telemetry
├── tests/                 # Test suite
├── cli.py                 # Command-line interface
├── nnt_calc.py            # Core NNT calculation engine
├── enrichment.py          # Enrichment feature modules
├── simulator.py           # High-throughput stress testing
├── web/index.html         # Operations console UI
├── Dockerfile             # Container definition
├── docker-compose.yml     # Docker Compose config
└── requirements.txt       # Python dependencies
```

---

## 🐳 Docker Compose

```bash
docker-compose up -d
```

---

## 📝 License

MIT License - see [LICENSE](LICENSE) for details.
