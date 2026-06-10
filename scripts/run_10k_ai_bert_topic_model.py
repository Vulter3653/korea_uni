#!/usr/bin/env python3
"""Run BERT-style topic modeling on AI-related 10-K disclosure windows.

Purpose
-------
This script supports the next stage after building the linked Fortune 2025 Top 100
10-K report CSV. It extracts AI-related sentence windows from each collected 10-K
text and clusters them into topics using sentence embeddings.

Default design
--------------
- Unit of input text: AI keyword sentence window, defined as AI sentence +/- N sentences.
- Embedding model: sentence-transformers/all-MiniLM-L6-v2 by default.
- Clustering model: KMeans by default for reproducibility and low dependency burden.
- Optional HDBSCAN can be added later if BERTopic-style dynamic topic counts are required.

Outputs
-------
- data/processed/10k_ai_topics/ai_mention_windows.csv
- data/processed/10k_ai_topics/ai_topic_assignments.csv
- data/processed/10k_ai_topics/firm_year_topic_distribution.csv
- data/processed/10k_ai_topics/topic_terms.csv
- data/audit/10k_ai_topics/topic_model_summary.csv

Installation
------------
pip install pandas scikit-learn sentence-transformers

Example
-------
python scripts/run_10k_ai_bert_topic_model.py \
  --input-csv data/processed/fortune2025_top100_10k_report_linked_text_sample.csv \
  --n-topics 12 \
  --window-size 1
"""

from __future__ import annotations

import argparse
import csv
import math
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_CSV = REPO_ROOT / "data" / "processed" / "fortune2025_top100_10k_report_linked_text_sample.csv"
OUTPUT_DIR = REPO_ROOT / "data" / "processed" / "10k_ai_topics"
AUDIT_DIR = REPO_ROOT / "data" / "audit" / "10k_ai_topics"

STRICT_AI_TERMS = [
    r"artificial intelligence",
    r"generative ai",
    r"genai",
    r"machine learning",
    r"deep learning",
    r"natural language processing",
    r"nlp",
    r"computer vision",
    r"neural network(?:s)?",
    r"large language model(?:s)?",
    r"llm(?:s)?",
    r"ai",
]
BROAD_AI_RELATED_TERMS = [
    r"predictive analytics",
    r"algorithmic",
    r"automation",
    r"automated decision",
]
STRICT_AI_REGEX = re.compile(r"\b(" + "|".join(STRICT_AI_TERMS) + r")\b", flags=re.IGNORECASE)
BROAD_AI_RELATED_REGEX = re.compile(r"\b(" + "|".join(BROAD_AI_RELATED_TERMS) + r")\b", flags=re.IGNORECASE)
AI_REGEX = re.compile(
    r"\b(" + "|".join(STRICT_AI_TERMS + BROAD_AI_RELATED_TERMS) + r")\b",
    flags=re.IGNORECASE,
)
STANDALONE_AI_REGEX = re.compile(r"\bai\b", flags=re.IGNORECASE)
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9])")
TOKEN_RE = re.compile(r"\b[a-z][a-z0-9_\-]{2,}\b")
STOPWORDS = set(
    "a an and are as at be by for from has have in into is it its of on or our that the their these this to was were will with within without we us may can could would should including included include company companies business businesses year years report reports item section form annual fiscal".split()
)

SEED_FRAME_DICTIONARY: Dict[str, List[str]] = {
    "efficiency_productivity": [
        "efficiency", "productivity", "cost", "costs", "savings", "streamline", "optimize", "automation", "workflow", "scale", "margin", "resource", "process",
    ],
    "negative_sensitive": [
        "trust", "credibility", "quality", "accuracy", "bias", "fairness", "ethical", "ethics", "accountability", "transparency", "privacy", "personal", "customer", "cybersecurity", "security", "breach", "copyright", "content", "generated", "reputational", "legal", "risk",
    ],
    "content_generation": [
        "content", "generation", "generated", "text", "image", "video", "article", "copy", "creative", "editorial", "synthetic",
    ],
    "privacy_data_security": [
        "privacy", "data", "personal", "customer", "security", "cybersecurity", "encryption", "access", "identity", "breach", "protection",
    ],
    "infrastructure_platform": [
        "infrastructure", "platform", "cloud", "architecture", "pipeline", "system", "systems", "model", "models", "governance", "mlops", "compute", "integration",
    ],
}


@dataclass
class MentionWindow:
    mention_id: str
    fortune_rank_2025: str
    company_name: str
    ticker: str
    cik_padded: str
    target_report_year: str
    filing_date: str
    report_date: str
    local_text_path: str
    sentence_index: int
    window_start: int
    window_end: int
    ai_keyword: str
    keyword_match_type: str
    standalone_ai_only: str
    window_text: str
    token_count: int


def read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: List[Dict[str, object]], fieldnames: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def split_sentences(text: str) -> List[str]:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if not cleaned:
        return []
    return [sent.strip() for sent in SENTENCE_SPLIT_RE.split(cleaned) if sent.strip()]


def tokenize(text: str) -> List[str]:
    return [tok for tok in TOKEN_RE.findall(text.lower()) if tok not in STOPWORDS and not tok.isdigit()]


def extract_windows(rows: List[Dict[str, str]], window_size: int, max_windows_per_doc: int) -> List[MentionWindow]:
    windows: List[MentionWindow] = []
    for row in rows:
        local_text_path = row.get("local_text_path", "")
        if not local_text_path:
            continue
        text_path = REPO_ROOT / local_text_path
        if not text_path.exists():
            print(f"WARN missing local text file: {local_text_path}")
            continue
        text = text_path.read_text(encoding="utf-8", errors="replace")
        sentences = split_sentences(text)
        doc_windows = 0
        for idx, sentence in enumerate(sentences):
            match = AI_REGEX.search(sentence)
            if not match:
                continue
            start = max(0, idx - window_size)
            end = min(len(sentences) - 1, idx + window_size)
            window_text = " ".join(sentences[start : end + 1])
            token_count = len(tokenize(window_text))
            keyword = match.group(0)
            keyword_match_type = "strict" if STRICT_AI_REGEX.fullmatch(keyword) else "broad"
            strict_terms_in_window = STRICT_AI_REGEX.findall(window_text)
            standalone_only = "TRUE" if strict_terms_in_window and all(term.lower() == "ai" for term in strict_terms_in_window) and not BROAD_AI_RELATED_REGEX.search(window_text) else "FALSE"
            mention_id = f"{row.get('ticker','NA')}_{row.get('target_report_year','NA')}_{idx}"
            windows.append(
                MentionWindow(
                    mention_id=mention_id,
                    fortune_rank_2025=row.get("fortune_rank_2025", ""),
                    company_name=row.get("company_name", ""),
                    ticker=row.get("ticker", ""),
                    cik_padded=row.get("cik_padded", ""),
                    target_report_year=row.get("target_report_year", ""),
                    filing_date=row.get("filing_date", ""),
                    report_date=row.get("report_date", ""),
                    local_text_path=local_text_path,
                    sentence_index=idx,
                    window_start=start,
                    window_end=end,
                    ai_keyword=keyword,
                    keyword_match_type=keyword_match_type,
                    standalone_ai_only=standalone_only,
                    window_text=window_text,
                    token_count=token_count,
                )
            )
            doc_windows += 1
            if max_windows_per_doc and doc_windows >= max_windows_per_doc:
                break
    return windows


def compute_seed_frame_scores(text: str) -> Dict[str, int]:
    tokens = tokenize(text)
    token_counts = Counter(tokens)
    scores = {}
    for frame, words in SEED_FRAME_DICTIONARY.items():
        scores[f"seed_{frame}_count"] = sum(token_counts.get(word, 0) for word in words)
    return scores


def fallback_tfidf_kmeans(texts: List[str], n_topics: int, random_state: int) -> Tuple[List[int], List[List[str]]]:
    from sklearn.cluster import KMeans
    from sklearn.feature_extraction.text import TfidfVectorizer

    vectorizer = TfidfVectorizer(stop_words="english", min_df=2, max_df=0.90, ngram_range=(1, 2), max_features=5000)
    x = vectorizer.fit_transform(texts)
    model = KMeans(n_clusters=n_topics, random_state=random_state, n_init=20)
    labels = model.fit_predict(x)
    terms = vectorizer.get_feature_names_out()
    topic_terms: List[List[str]] = []
    for topic_id in range(n_topics):
        center = model.cluster_centers_[topic_id]
        top_idx = center.argsort()[::-1][:15]
        topic_terms.append([terms[i] for i in top_idx])
    return labels.tolist(), topic_terms


def sentence_bert_kmeans(texts: List[str], n_topics: int, random_state: int, model_name: str) -> Tuple[List[int], List[List[str]]]:
    from sentence_transformers import SentenceTransformer
    from sklearn.cluster import KMeans
    from sklearn.feature_extraction.text import TfidfVectorizer

    model = SentenceTransformer(model_name)
    embeddings = model.encode(texts, show_progress_bar=True, normalize_embeddings=True)
    clusterer = KMeans(n_clusters=n_topics, random_state=random_state, n_init=20)
    labels = clusterer.fit_predict(embeddings)

    # Extract topic terms through class-specific TF-IDF approximation.
    topic_terms: List[List[str]] = []
    vectorizer = TfidfVectorizer(stop_words="english", min_df=2, max_df=0.95, ngram_range=(1, 2), max_features=7000)
    x = vectorizer.fit_transform(texts)
    terms = vectorizer.get_feature_names_out()
    for topic_id in range(n_topics):
        idxs = [i for i, label in enumerate(labels) if label == topic_id]
        if not idxs:
            topic_terms.append([])
            continue
        mean_scores = x[idxs].mean(axis=0).A1
        top_idx = mean_scores.argsort()[::-1][:15]
        topic_terms.append([terms[i] for i in top_idx if mean_scores[i] > 0])
    return labels.tolist(), topic_terms


def assign_topics(texts: List[str], n_topics: int, random_state: int, model_name: str, use_tfidf_fallback: bool) -> Tuple[List[int], List[List[str]], str]:
    if not texts:
        return [], [], "none"
    effective_topics = min(n_topics, max(1, len(texts)))
    if use_tfidf_fallback:
        labels, terms = fallback_tfidf_kmeans(texts, effective_topics, random_state)
        return labels, terms, "tfidf_kmeans"
    try:
        labels, terms = sentence_bert_kmeans(texts, effective_topics, random_state, model_name)
        return labels, terms, f"sentence_bert_kmeans:{model_name}"
    except Exception as exc:
        print(f"WARN sentence-transformers failed; falling back to TF-IDF KMeans: {type(exc).__name__}: {exc}")
        labels, terms = fallback_tfidf_kmeans(texts, effective_topics, random_state)
        return labels, terms, "tfidf_kmeans_fallback"


def build_firm_year_distribution(assignments: List[Dict[str, object]], n_topics: int) -> List[Dict[str, object]]:
    grouped: Dict[Tuple[str, str, str, str, str], List[Dict[str, object]]] = defaultdict(list)
    for row in assignments:
        key = (
            str(row.get("fortune_rank_2025", "")),
            str(row.get("company_name", "")),
            str(row.get("ticker", "")),
            str(row.get("cik_padded", "")),
            str(row.get("target_report_year", "")),
        )
        grouped[key].append(row)

    out: List[Dict[str, object]] = []
    for key, rows in sorted(grouped.items(), key=lambda item: (int(item[0][0]) if item[0][0].isdigit() else 9999, item[0][4])):
        total = len(rows)
        topic_counts = Counter(int(row["topic_id"]) for row in rows)
        base = {
            "fortune_rank_2025": key[0],
            "company_name": key[1],
            "ticker": key[2],
            "cik_padded": key[3],
            "target_report_year": key[4],
            "ai_window_count": total,
        }
        for topic_id in range(n_topics):
            base[f"topic_{topic_id}_count"] = topic_counts.get(topic_id, 0)
            base[f"topic_{topic_id}_share"] = round(topic_counts.get(topic_id, 0) / total, 6) if total else 0.0
        for frame in SEED_FRAME_DICTIONARY:
            col = f"seed_{frame}_count"
            base[col] = sum(int(row.get(col, 0)) for row in rows)
            base[f"seed_{frame}_share"] = round(base[col] / total, 6) if total else 0.0
        out.append(base)
    return out


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Run AI-related 10-K BERT topic modeling.")
    parser.add_argument("--input-csv", type=Path, default=DEFAULT_INPUT_CSV)
    parser.add_argument("--n-topics", type=int, default=12)
    parser.add_argument("--window-size", type=int, default=1)
    parser.add_argument("--max-windows-per-doc", type=int, default=0, help="0 means no cap")
    parser.add_argument("--model-name", default="sentence-transformers/all-MiniLM-L6-v2")
    parser.add_argument("--random-state", type=int, default=42)
    parser.add_argument("--tfidf-fallback-only", action="store_true")
    args = parser.parse_args(argv)

    rows = read_csv(args.input_csv)
    windows = extract_windows(rows, args.window_size, args.max_windows_per_doc)
    if not windows:
        raise SystemExit("No AI mention windows extracted. Check input CSV and local_text_path files.")

    window_dicts = [asdict(window) for window in windows]
    for row in window_dicts:
        row.update(compute_seed_frame_scores(str(row["window_text"])))

    labels, topic_terms, model_used = assign_topics(
        [str(row["window_text"]) for row in window_dicts],
        args.n_topics,
        args.random_state,
        args.model_name,
        args.tfidf_fallback_only,
    )
    effective_topics = len(topic_terms)

    assignments: List[Dict[str, object]] = []
    for row, label in zip(window_dicts, labels):
        assigned = dict(row)
        assigned["topic_id"] = int(label)
        assigned["topic_terms"] = "; ".join(topic_terms[int(label)]) if int(label) < len(topic_terms) else ""
        assignments.append(assigned)

    topic_term_rows = [
        {"topic_id": topic_id, "topic_terms": "; ".join(terms), "topic_window_count": sum(1 for label in labels if label == topic_id)}
        for topic_id, terms in enumerate(topic_terms)
    ]
    distribution = build_firm_year_distribution(assignments, effective_topics)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)

    window_fields = list(window_dicts[0].keys())
    seed_fields = [f"seed_{frame}_count" for frame in SEED_FRAME_DICTIONARY]
    write_csv(OUTPUT_DIR / "ai_mention_windows.csv", window_dicts, window_fields + seed_fields)
    write_csv(OUTPUT_DIR / "ai_topic_assignments.csv", assignments, window_fields + seed_fields + ["topic_id", "topic_terms"])
    write_csv(OUTPUT_DIR / "topic_terms.csv", topic_term_rows, ["topic_id", "topic_terms", "topic_window_count"])

    dist_fields = list(distribution[0].keys()) if distribution else []
    write_csv(OUTPUT_DIR / "firm_year_topic_distribution.csv", distribution, dist_fields)

    summary = [
        {"metric": "input_rows", "value": str(len(rows)), "note": str(args.input_csv.relative_to(REPO_ROOT) if args.input_csv.is_absolute() else args.input_csv)},
        {"metric": "ai_mention_windows", "value": str(len(windows)), "note": f"window_size={args.window_size}"},
        {"metric": "firm_years_with_ai_windows", "value": str(len(distribution)), "note": "Firm-years with at least one AI mention window"},
        {"metric": "n_topics", "value": str(effective_topics), "note": f"requested={args.n_topics}"},
        {"metric": "model_used", "value": model_used, "note": "Sentence-BERT preferred; TF-IDF fallback when unavailable"},
    ]
    write_csv(AUDIT_DIR / "topic_model_summary.csv", summary, ["metric", "value", "note"])

    print(f"AI mention windows: {len(windows)}")
    print(f"Firm-years with AI windows: {len(distribution)}")
    print(f"Topics: {effective_topics}")
    print(f"Model used: {model_used}")
    print(f"Outputs: {OUTPUT_DIR.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
