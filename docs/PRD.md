# Douban2Soul Product Requirements Document

## 1. Project Overview
Analyze user personality, aesthetic preferences, and values based on Douban movie viewing records using LLM capabilities.

## 2. Technology Stack (Confirmed)
1. **Data Scraping**: OpenCLI
2. **Analysis Engine**: LLM (Moonshot/DeepSeek/OpenAI etc.)

## 3. Layered Diagnostic Reports

### L1: Base Statistics (01_base_stats.md)
Pure data statistics, no LLM required
- Total movies watched, rating distribution
- Year distribution, temporal trends

### L2: Comment Semantic Analysis (02_comment_insights.md)
LLM-powered analysis of ~192 comments
- Topic focus distribution
- Sentiment analysis
- Value clues
- Personality trait inference

**Comment volume**: ~192 comments, ~15,000 characters, ~22,500 tokens
**Processing**: Kimi 128K can handle the entire input directly, no chunking needed

### L3: Dimensional Deep Analysis
- 03a_genre_analysis.md - Genre preferences
- 03b_director_analysis.md - Director preferences
- 03c_regional_analysis.md - Regional/cultural analysis

### L4: Comprehensive Diagnosis (04_final_profile.md)
LLM-synthesized summary across all dimensions
- Core personality profile
- Aesthetic orientation and taste
- Values and worldview
- Psychological needs analysis
- Unique labels
- Movie recommendation directions

## 4. Metadata Fetching Strategy

### Primary Source: wmdb.tv API
```
GET https://api.wmdb.tv/movie/api?id={douban_id}
```

### Fallback Sources
- TMDB API (international films)
- OMDB API
- Douban direct scraping

### Processing Strategy
- Smart rate limiting
- Resume from breakpoints
- Multi-proxy support

## 5. LLM SDK Integration

### Supported Providers
- Moonshot (Kimi) - Recommended
- OpenAI (GPT-4)
- DashScope (Tongyi Qianwen)
- DeepSeek

### Unified Interface
```python
from scripts.llm_client import LLMClientFactory, AnalysisConfig

config = AnalysisConfig(llm_provider="moonshot")
client = LLMClientFactory.create(config)
```

## 6. Directory Structure
```
Douban2Soul/
├── solid-yang.json        # Movie viewing records
├── scripts/
│   ├── llm_client.py      # LLM unified interface
│   ├── analysis_engine.py # Analysis engine
│   └── metadata_fetcher.py# Metadata fetcher
├── docs/
│   └── PRD.md             # Product requirements
├── output/                # Report output
└── cache/                 # Metadata cache
```

## 7. Dependencies
```
openai>=1.0.0
dashscope>=1.14.0
requests>=2.31.0
python-dotenv>=1.0.0
```

## 8. Environment Variables
```bash
export MOONSHOT_API_KEY="sk-xxx"
export OPENAI_API_KEY="sk-xxx"
export DASHSCOPE_API_KEY="sk-xxx"
```
