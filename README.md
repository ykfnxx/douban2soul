# Douban2Soul

> Personality profiling tool based on Douban movie viewing records

Analyze your Douban movie viewing history using LLM capabilities to generate multi-dimensional personality profiles and aesthetic reports.

[中文文档](README_ZH.md)

## Features

- **Layered Diagnosis**: L1-L4 four-layer analysis from raw data to personality profile
- **Multi-LLM Support**: Moonshot / OpenAI / DashScope / DeepSeek
- **Metadata Fetching**: Automatically retrieve movie genre, director, country, etc.
- **Comment Analysis**: ~192 comments analyzed in a single LLM call, no chunking needed
- **Local Processing**: All data stored locally, privacy preserved

## Quick Start

### 1. Install Dependencies

This project uses [UV](https://github.com/astral-sh/uv) as the package manager.

```bash
uv sync
```

### 2. Configure API Key

```bash
# Recommended: Moonshot (Kimi), 128K context suitable for analyzing large volumes of comments
export MOONSHOT_API_KEY="sk-xxx"

# Alternative: OpenAI
export OPENAI_API_KEY="sk-xxx"

# Alternative: Alibaba Cloud Tongyi Qianwen
export DASHSCOPE_API_KEY="sk-xxx"
```

### 3. Run Analysis

```bash
uv run python main.py
```

Or use a different LLM provider:
```bash
uv run python main.py --provider openai
```

## Output Reports

After analysis completes, reports are generated in the `output/` directory:

| File | Description | Uses LLM |
|------|-------------|----------|
| `01_base_stats.md` | Base statistics | No |
| `02_comment_insights.md` | Comment semantic analysis | Yes |
| `03_dimension_analysis.md` | Dimensional deep analysis | No |
| `04_final_profile.md` | Comprehensive personality profile | Yes |

## Architecture

```
Douban2Soul/
├── main.py                  # Entry point
├── scripts/
│   ├── llm_client.py        # Unified LLM interface
│   ├── analysis_engine.py   # Analysis engine
│   └── metadata_fetcher.py  # Metadata fetcher
├── docs/
│   └── PRD.md               # Product requirements
├── output/                  # Report output
└── cache/                   # Metadata cache
```

## Tech Stack

| Layer | Technology |
|-------|------------|
| Data Scraping | OpenCLI |
| Metadata | wmdb.tv API |
| LLM | Moonshot-v1-128k (recommended) |
| Language | Python 3.10+ |
| Package Manager | UV |

## About Comment Analysis

**FAQ**: Are ~192 comments too many for a single LLM call?

**Answer**: They can be analyzed in a single LLM call without any issues.
- Total characters: ~15,000
- Estimated tokens: ~22,500
- Kimi 128K limit: sufficient

**Future plans for >500 comments**:
- Clustered sampling: stratified sampling by rating
- Chunked recursion: analyze in chunks, then summarize

## License

MIT
