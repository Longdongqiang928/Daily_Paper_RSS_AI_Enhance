# Daily Paper RSS AI Enhance

[中文](README.md) | **English**

**Intelligent Academic Paper Recommendation System Based on RSS Subscriptions**

> 📚 Automatically discover the latest academic papers related to your research interests through AI enhancement and intelligent Zotero library-based ranking.

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![uv](https://img.shields.io/badge/uv-package%20manager-orange.svg)](https://github.com/astral-sh/uv)

---

## 💡 Overview

This is a **locally-run** academic paper recommendation system that integrates RSS subscriptions, AI-powered summary generation, and personalized ranking based on your Zotero library.

### ✨ Key Features

- 🎯 **Smart Ranking**: Recommends the most relevant papers by calculating embedding similarity with your Zotero library.
- 🤖 **AI Enhancement**: Generates structured summaries (TL;DR, motivation, method, results, and conclusions) using LLMs (local or cloud-based).
- 📡 **Multi-Source Support**: Automatically fetches latest papers from arXiv, Nature, Science, Optica, APS, and more.
- 🌐 **Beautiful Web UI**: Responsive design with search, filtering, analytics, and a persistent favorites system.
- 💾 **Privacy First**: All data is stored locally. Supports local AI (e.g., Ollama) for complete data privacy.
- 📝 **Markdown Export**: Automatically converts paper content into Markdown for easy knowledge base integration.

---

## 📸 Screenshots

| 🔐 Login | 🏠 Home Page |
| :---: | :---: |
| ![Login](assets/login_page.png) | ![Home](assets/home_page.png) |

| 📚 Paper List | 📑 Details & AI Summary |
| :---: | :---: |
| ![List](assets/papers_page.png) | ![Details](assets/paper_details.png) |

| 📊 Analytics | ⭐ Favorites |
| :---: | :---: |
| ![Analytics](assets/analytics_page.png) | ![Favorites](assets/favorites_system.png) |

---

## 🚀 Quick Start

### 1. Prerequisites
- **Python 3.12+**
- **[uv](https://github.com/astral-sh/uv)** package manager (recommended)

### 2. Installation
```bash
# Clone repository
git clone https://github.com/yourusername/Daily_Paper_RSS_AI_Enhance.git
cd Daily_Paper_RSS_AI_Enhance

# Install dependencies
uv sync

# Configure environment variables
cp .env.example .env
```

### 3. Configuration (`.env`)
Fill in the following key configurations in your `.env` file:

| Category | Variable | Description |
| :--- | :--- | :--- |
| **API** | `NEWAPI_BASE_URL` | Base URL for OpenAI-compatible API |
| | `NEWAPI_KEY_AD` | API Key |
| **Zotero** | `ZOTERO_ID` | Zotero User ID |
| | `ZOTERO_KEY_AD` | Zotero API Key (read permission required) |
| **Tools** | `TAVILY_API_KEY` | Tavily Search API (for scraping abstracts) |
| | `NATURE_API_KEY` | Springer Nature API Key |
| **RSS** | `RSS_SOURCES` | RSS source config (see format below) |
| | `MODEL_NAME` | AI model for summaries (e.g., `gpt-4o`) |
| | `EMBEDDING_MODEL` | Embedding model (e.g., `text-embedding-3-small`) |
| | `OUTPUT_LANGUAGE` | Output language (`Chinese` / `English`) |

---

## 🔧 Advanced Usage

### 📡 RSS Source Format
`RSS_SOURCES` format: `source:cat1+cat2,source2:cat1`
- **arXiv**: `arxiv:physics+quant-ph+cs.AI`
- **Nature**: `nature:nature+nphoton+nphys+ncomms`
- **Science**: `science:science+sciadv`
- **Optica**: `optica:optica`
- **APS**: `aps:prl+prx`

### ⚡ Running the Application

#### Scheduled Execution
```bash
uv run main.py
```
- **Daily Task** (08:00): Fetches new papers, ranks them, and generates AI summaries.
- **Weekly Task** (Sun 10:00): Re-ranks historical papers based on the latest Zotero library.

#### Immediate Execution
```bash
# Run today's task immediately
uv run main.py --immediate --mode daily

# Run task for a specific date
uv run main.py --immediate --mode daily --date 2026-01-22

# Re-rank historical papers immediately
uv run main.py --immediate --mode weekly
```

#### Launch Web UI
```bash
uv run api_server.py
```
Access at: `http://127.0.0.1:8000`

---

## 📁 Project Structure

```text
Daily_Paper_RSS_AI_Enhance/
├── ai/                  # AI logic (summarization, recommendation, translation)
├── fetcher/             # RSS fetching & abstract extraction
├── md/                  # Markdown conversion tools
├── data/                # Data storage
│   ├── cache/           # RSS cache, Zotero index, favorites
│   └── md_files/        # Auto-generated Markdown papers
├── assets/              # Screenshots & icons
├── css/ & js/           # Web frontend assets
├── api_server.py        # Web backend (Flask)
├── main.py              # Main entry (scheduler / immediate)
├── config.py            # Configuration management
├── .env.example         # Environment variable template
└── pyproject.toml       # Dependency management (uv)
```

---

## 📊 Data Format
Papers are stored in JSONL format, containing fields such as: `journal`, `id`, `title`, `authors`, `published`, `score` (Zotero relevance), and `AI` (structured summary).

---

## ⚠️ Disclaimer
Before using this project, please read and understand the [Disclaimer](DISCLAIMER_EN.md). The AI-generated content is for reference only and should not be the sole basis for research decisions.

---

## 📋 TODO & Known Issues
- [ ] Improve Science/APS scraping stability (anti-scraping measures)
- [ ] Add more RSS sources
- [ ] Enhance Obsidian/Logseq integration
- [x] Web UI analytics page
- [x] Markdown export feature

---

## 📝 License & Acknowledgements
Licensed under [AGPL-3.0](LICENSE).
Special thanks to [daily-arXiv-ai-enhanced](https://github.com/dw-dengwei/daily-arXiv-ai-enhanced) and [zotero-arxiv-daily](https://github.com/TideDra/zotero-arxiv-daily) for their inspiration and foundational code.
