# Douban2Soul

> 基于豆瓣观影记录的人格画像分析工具

通过分析你的豆瓣观影记录，使用LLM能力生成多维度的人格画像与审美报告。

## 特性

- 📊 **分层诊断**: L1-L4四层分析文档，从数据到人格画像
- 🤖 **多LLM支持**: Moonshot/OpenAI/DashScope/DeepSeek
- 🎬 **元数据抓取**: 自动获取电影类型、导演、国家等信息
- 📝 **短评分析**: 192条短评可一次性LLM分析，无需分块
- 🔒 **本地处理**: 数据仅本地存储，保护隐私

## 快速开始

### 1. 安装依赖

本项目使用 [UV](https://github.com/astral-sh/uv) 作为包管理器。

```bash
# 使用 UV (推荐)
uv venv --python 3.11
source .venv/bin/activate  # Linux/Mac
# 或: .venv\Scripts\activate  # Windows

uv pip install -e .
```

或使用 pip:
```bash
pip install -r requirements.txt
```

### 2. 配置API Key

```bash
# 推荐: Moonshot (Kimi)，128K上下文适合分析大量评论
export MOONSHOT_API_KEY="sk-xxx"

# 备选: OpenAI
export OPENAI_API_KEY="sk-xxx"

# 备选: 阿里云通义千问
export DASHSCOPE_API_KEY="sk-xxx"
```

### 3. 运行分析

```bash
python main.py
```

或使用其他LLM:
```bash
python main.py --provider openai
```

## 输出报告

分析完成后，在 `output/` 目录生成:

| 文件 | 说明 | 使用LLM |
|------|------|---------|
| `01_base_stats.md` | 基础统计 | ❌ |
| `02_comment_insights.md` | 短评语义分析 | ✅ |
| `04_final_profile.md` | 综合人格画像 | ✅ |

## 架构

```
Douban2Soul/
├── solid-yang.json          # 观影记录数据 (OpenCLI抓取)
├── main.py                  # 主入口
├── scripts/
│   ├── llm_client.py        # LLM统一接口
│   ├── analysis_engine.py   # 分析引擎
│   └── metadata_fetcher.py  # 元数据抓取
├── docs/
│   └── PRD.md               # 需求文档
├── output/                  # 诊断报告输出
└── cache/                   # 元数据缓存
```

## 技术选型

| 层面 | 技术 |
|------|------|
| 数据抓取 | OpenCLI |
| 元数据 | wmdb.tv API |
| LLM | Moonshot-v1-128k (推荐) |
| 语言 | Python 3.10+ |

## 关于短评分析

**常见问题**: 192条短评是否过长？

**回答**: 完全可以一次性输入LLM分析。
- 总字符: ~15,000
- 估算Tokens: ~22,500
- Kimi 128K限制: ✅ 充足

**未来>500条的方案**:
- 聚类抽样: 按评分分层抽样
- 分块递归: 分块分析后汇总

## License

MIT
