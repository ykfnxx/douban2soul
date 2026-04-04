#!/usr/bin/env python3
"""
Profile Analyzer - LLM-powered personality analysis
Generates L2 comment analysis, L4 comprehensive personality profile,
and L5 综合中文报告.
"""

import json
import sys
from typing import List, Dict

from douban2soul.analysis.llm_client import BaseLLMClient


class ProfileAnalyzer:
    """LLM-powered personality profile analyzer"""

    def __init__(self, llm_client: BaseLLMClient, stream: bool = False):
        self.llm = llm_client
        self.stream = stream

    def _call_llm(self, prompt: str) -> str:
        """Call LLM with optional streaming output to stdout."""
        if not self.stream:
            return self.llm.complete(prompt)
        chunks: list[str] = []
        for chunk in self.llm.stream(prompt):
            sys.stdout.write(chunk)
            sys.stdout.flush()
            chunks.append(chunk)
        sys.stdout.write("\n")
        sys.stdout.flush()
        return "".join(chunks)

    def generate_comment_analysis(self, data: List[Dict]) -> str:
        """
        L2: Comment semantic analysis (requires LLM)

        Key design: ~192 comments can be fed to LLM in one shot, no chunking needed.
        - Total chars: ~15,000
        - Estimated tokens: ~22,500
        - Kimi 128K context: sufficient
        """
        commented = [d for d in data if d.get("myComment")]

        if not commented:
            return "# L2: Comment Semantic Analysis\n\nNo comments found for this user."

        print(f"[L2] Analyzing {len(commented)} comments...")

        # Build comment text
        comments_text = []
        for i, d in enumerate(commented, 1):
            comment = d.get("myComment", "").strip()
            if comment:
                comments_text.append(
                    f"{i}. \u300a{d['title']}\u300b(rating: {d.get('myRating', 'N/A')}): {comment}"
                )

        full_comments = "\n".join(comments_text)

        estimated_tokens = int(len(full_comments) * 1.5 + 2000)
        print(f"  Estimated tokens: ~{estimated_tokens} (Kimi 128K limit: sufficient)")

        prompt = f"""You are an expert in film psychology, text analysis, and Big Five personality theory.
Please perform a deep analysis of the following Douban user's movie comments.
Note: The comments are in Chinese. Analyze them in their original language for accuracy,
but write your analysis output in English.

## User Basic Data
- Total movies watched: {len(data)}
- Comments available: {len(commented)}

## User Comment List
{full_comments}

## Analysis Requirements

Please conduct a professional analysis from the following dimensions:

### 1. Topic Focus Distribution (Top 5)
What movie elements does the user discuss most frequently?

### 2. Sentiment Analysis
- Overall sentiment tone (positive / negative / neutral)
- Emotional expression intensity
- Emotional responses to different types of films

### 3. Value Clues
Inferred values, stances, and beliefs from the comments

### 4. Aesthetic Standards
The user's core criteria for evaluating movies
- What earns a positive review?
- What leads to a negative review?
- Does the user prioritize form or content?

### 5. Language Style Features
Expression patterns, expertise level, unique phrasing, humor

### 6. Personality Trait Inference (Big Five)
- Openness
- Conscientiousness
- Extraversion
- Agreeableness
- Neuroticism

### 7. Unique Insights
3-5 unique discoveries about this user

### 8. Structured Comment Metrics (IMPORTANT: output as structured data)
Analyze the comments and provide the following metrics in a structured format:

**Sentiment Summary:**
- Overall polarity: [positive/negative/mixed] with percentage breakdown
- Emotional intensity (1-5 scale): [score]

**Language Style Metrics:**
- Analytical vs. emotional language ratio: [X% analytical / Y% emotional]
- First-person pronoun frequency ("我"/"我觉得"): [high/medium/low]
- Comparative language frequency ("比...好"/"不如"): [high/medium/low]
- Average comment sophistication (vocabulary richness): [high/medium/low]

Please output in structured Markdown format."""

        result = self._call_llm(prompt)
        return f"# L2: Comment Semantic Analysis\n\n{result}"

    def generate_final_profile(self, data: List[Dict], l2_analysis: str, l3_analysis: str) -> str:
        """
        L4: Comprehensive personality profile (requires LLM synthesis)
        Input: L2 comment analysis + L3 dimensional analysis
        """
        total = len(data)
        rated = [d for d in data if d.get("myRating")]
        avg_rating = sum(d["myRating"] for d in rated) / len(rated) if rated else 0

        print("[L4] Generating comprehensive personality profile...")

        prompt = f"""You are a professional psychoanalyst, film critic, and cultural researcher.
Based on the following analysis results, generate a comprehensive Movie Viewer Personality Profile
Diagnostic Report for this Douban user.

## Basic Data
- Total movies watched: {total}
- Average rating: {avg_rating:.1f}/10

## L2: Comment Analysis Summary
{l2_analysis[:2500]}

## L3: Dimensional Analysis Summary
{l3_analysis[:1500]}

## Report Requirements

Please generate a diagnostic report containing the following sections:

# Movie Viewer Personality Profile Diagnostic Report

## 1. Core Personality Profile
Big Five personality analysis based on viewing behavior, with vivid metaphors to describe
the user's "movie personality".

## 2. Aesthetic Orientation & Taste
- Genre preference tendencies
- Balance between art-house and commercial films
- Psychological traits reflected by era preferences
- Personal definition of a "good movie"

## 3. Values & Worldview
Values, social attitudes, and emotional needs inferred from movie choices.

## 4. Psychological Needs Analysis
Core psychological needs fulfilled by viewing behavior (emotional, cognitive, social).

## 5. Unique Labels
3-5 precise labels that encapsulate this user.

## 6. Movie Recommendation Directions
Personalized viewing recommendations based on the profile.

## 7. Summary
A core insight in under 200 words.

Report style: professional but accessible, warm yet insightful, well-reasoned."""

        result = self._call_llm(prompt)
        return f"# L4: Comprehensive Personality Profile\n\n{result}"

    def generate_comprehensive_report(
        self,
        llm_context: dict,
        l2_report: str,
        l4_report: str,
    ) -> str:
        """
        L5: Comprehensive Chinese personality analysis report.
        Synthesizes structured statistics + L2/L4 LLM analysis into a single Chinese report.

        Uses llm_context (structured JSON) for all statistical data — this already
        contains everything from L1/L3 in structured form, so no truncation needed.
        L2 and L4 are LLM-generated content not available elsewhere.
        """
        print("[L5] Generating comprehensive Chinese report...")

        context_json = json.dumps(llm_context, ensure_ascii=False, indent=2)

        prompt = f"""你是一位专业的电影心理学分析师。请基于以下全部分析数据，生成一份完整的中文人格分析报告。

注意：以下数据不包含任何观影时间信息（豆瓣标记时间不等于观影时间），请不要对观影时间做任何推断。

## 结构化统计数据（完整）
{context_json}

## L2 评论语义分析
{l2_report}

## L4 综合人格画像
{l4_report}

## 报告要求

请生成包含以下章节的中文报告：

# 综合人格分析报告

## 一、数据概览
简要概述观影数据的规模和完整度。

## 二、核心人格特质分析
基于大五人格模型（开放性、尽责性、外向性、宜人性、神经质），逐维度分析：
- 每个维度给出 0-100 分的量化评分
- 结合具体观影数据和评论给出 2-3 句解读
- 引用具体电影作为证据

## 三、审美偏好画像
- 类型偏好与审美倾向
- 艺术片与商业片的平衡
- 文化视野广度（国产vs外语、地区多样性）
- 片长偏好与审美耐心

## 四、独特品味特征
- 高于个人均值的类型（真爱类型）
- 低于个人均值的类型（踩雷类型）
- Hidden Gems（用户发现的宝藏电影）
- 与大众品味的差异点

## 五、观影行为模式
- 评分习惯（宽容度、一致性）
- 评论习惯（频率、深度）
- 导演/演员忠诚度

## 六、个性标签
5-8 个精准标签，概括这位观影者的核心特征。

## 七、观影推荐方向
基于画像给出个性化的观影建议。

## 八、总结
200字以内的核心洞察，突出最显著的 2-3 个特质。

**写作要求：**
1. 用第二人称"你"叙述，保持亲切但专业的语气
2. 避免模板化套话，保持个人化分析
3. 每个论点都要有数据或电影实例支撑
4. 全文使用中文"""

        result = self._call_llm(prompt)
        return f"# 综合人格分析报告\n\n{result}"

    def generate_mbti_analysis(
        self,
        llm_context: dict,
        l2_report: str,
    ) -> str:
        """
        L6: MBTI tendency analysis (optional).

        Uses LLM to directly infer MBTI probability distributions from
        statistical data. Outputs probabilities, not deterministic labels.
        """
        print("[L6] Generating MBTI tendency analysis...")

        context_json = json.dumps(llm_context, ensure_ascii=False, indent=2)

        prompt = f"""你是一位熟悉 MBTI 和大五人格理论的心理学分析师。基于以下观影数据和评论分析，
推断该用户在 MBTI 四个维度上的倾向性概率。

**重要：不要输出确定性的四字母类型标签。只输出每个维度的概率分布和推理依据。**

## 结构化统计数据
{context_json}

## L2 评论分析摘要
{l2_report[:2000]}

## 各维度分析指引

请逐维度分析，每个维度参考以下数据字段：

### E/I（外向/内向）
参考数据：评论率 (comment_rate)、评论长度 (avg_length)、binge_days、社交类型比例
- 高评论率 + 长评论 + 频繁观影 → E 倾向
- 低评论率 + 独立观影 → I 倾向

### S/N（感觉/直觉）
参考数据：类型多样性 (shannon_entropy)、年代跨度、外语片比例、隐藏佳作数量
- 高多样性 + 跨文化观影 + 发现冷门佳作 → N 倾向
- 类型集中 + 主流偏好 → S 倾向

### T/F（思考/情感）
参考数据：大众对齐度 (crowd_alignment)、评分标准差、评论中分析性vs情感性语言比例
- 低大众对齐 + 高评分方差 + 分析性语言 → T 倾向
- 高大众对齐 + 情感性语言 → F 倾向

### J/P（判断/知觉）
参考数据：观影间隔规律性 (viewing_interval)、导演忠诚度、类型集中度
- 规律间隔 + 高导演忠诚 + 类型集中 → J 倾向
- 不规则间隔 + 类型分散 → P 倾向

## 输出格式

# MBTI 倾向性分析

⚠️ 声明：MBTI 是一种性格类型参考框架，以下分析基于观影行为推断，
仅供参考，不构成心理学诊断。

## E/I 维度
- **E 倾向**: X% | **I 倾向**: Y%
- 推理依据：（1-2句，引用具体数据）

## S/N 维度
- **S 倾向**: X% | **N 倾向**: Y%
- 推理依据：（1-2句）

## T/F 维度
- **T 倾向**: X% | **F 倾向**: Y%
- 推理依据：（1-2句）

## J/P 维度
- **J 倾向**: X% | **P 倾向**: Y%
- 推理依据：（1-2句）

## 综合画像
（2-3句总结性描述，不使用四字母标签，用倾向性表述）"""

        result = self._call_llm(prompt)
        return f"# L6: MBTI 倾向性分析\n\n{result}"
