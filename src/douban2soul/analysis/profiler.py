#!/usr/bin/env python3
"""
Profile Analyzer - LLM-powered personality analysis
Generates L2 comment analysis and L4 comprehensive personality profile
"""

from typing import List, Dict

from douban2soul.analysis.llm_client import BaseLLMClient


class ProfileAnalyzer:
    """LLM-powered personality profile analyzer"""

    def __init__(self, llm_client: BaseLLMClient):
        self.llm = llm_client

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

Please output in structured Markdown format."""

        result = self.llm.complete(prompt)
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

        result = self.llm.complete(prompt)
        return f"# L4: Comprehensive Personality Profile\n\n{result}"
