#!/usr/bin/env python3
"""Optimize the number of topics for AI-related 10-K topic modeling.

Why this exists
---------------
The number of topics must not be fixed arbitrarily. This script evaluates a
candidate range of K values before the final topic model is run.

Evaluation logic
----------------
For each candidate K, the script clusters AI-related 10-K mention windows and
computes:

1. silhouette_score: higher is better; cluster separation in embedding space.
2. davies_bouldin_score: lower is better; cluster compactness/separation.
3. calinski_harabasz_score: higher is better; between/within-cluster dispersion.
4. topic_coherence_umass: higher is better; internal coherence of top terms.
5. min_topic_share: small-topic penalty guard against fragmented topics.

The final recommendation uses a normalized composite score:

    composite = mean(
        silhouette_norm,
        inverted_davies_bouldin_norm,
        calinski_harabasz_norm,
        coherence_norm,
        min_topic_share_norm
    )

Outputs
-------
- data/processed/10k_ai_topics/topic_count_optimization.csv
- data/audit/10k_ai_topics/topic_count_recommendation.csv

Example
-------
python scripts/optimize_10k_ai_topic_count.py \
  --input-csv data/processed/fortune2025_top100_10k_report_linked_text_sample.csv \
  --min-topics 4 \
  --max-topics 20 \
  --window-size 1
"""

from __future__ import annotations

import argparse
import csv
import math
import re
import sys
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Reuse the extraction/tokenization logic from the final topic model script.
from run_10k_ai_bert_topic_model import (  # type: ignore
    DEFAULT_INPUT_CSV,
    REPO_ROOT,
    extract_windows,
    read_csv,
    tokenize,
    write_csv,
)

OUTPUT_DIR = REPO_ROOT / "data" / "processed" / "10k_ai_topics"
AUDIT_DIR = REPO_ROOT / "data" / "audit" / "10k_ai_topics"
OPTIMIZATION_OUT = OUTPUT_DIR / "topic_count_optimization.csv"
RECOMMENDATION_OUT = AUDIT_DIR / "topic_count_recommendation.csv"


def vectorize_texts_tfidf(texts: List[str]):
    from sklearn.feature_extraction.text import TfidfVectorizer

    vectorizer = TfidfVectorizer(
        stop_words="english",
        min_df=2,
        max_df=0.95,
        ngram_range=(1, 2),
        max_features=7000,
    )
    x = vectorizer.fit_transform(texts)
    return x, vectorizer


def make_embeddings(texts: List[str], model_name: str, tfidf_only: bool):
    if tfidf_only:
        x, vectorizer = vectorize_texts_tfidf(texts)
        return x, vectorizer, "tfidf"
    try:
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer(model_name)
        embeddings = model.encode(texts, show_progress_bar=True, normalize_embeddings=True)
        _x, vectorizer = vectorize_texts_tfidf(texts)
        return embeddings, vectorizer, f"sentence_bert:{model_name}"
    except Exception as exc:
        print(f"WARN Sentence-BERT embedding failed; falling back to TF-IDF: {type(exc).__name__}: {exc}")
        x, vectorizer = vectorize_texts_tfidf(texts)
        return x, vectorizer, "tfidf_fallback"


def cluster_labels(embeddings, k: int, random_state: int) -> List[int]:
    from sklearn.cluster import KMeans

    model = KMeans(n_clusters=k, random_state=random_state, n_init=20)
    return model.fit_predict(embeddings).tolist()


def topic_terms_from_tfidf(texts: List[str], labels: List[int], k: int, top_n: int = 15) -> List[List[str]]:
    x, vectorizer = vectorize_texts_tfidf(texts)
    terms = vectorizer.get_feature_names_out()
    topic_terms: List[List[str]] = []
    for topic_id in range(k):
        idxs = [i for i, label in enumerate(labels) if label == topic_id]
        if not idxs:
            topic_terms.append([])
            continue
        mean_scores = x[idxs].mean(axis=0).A1
        top_idx = mean_scores.argsort()[::-1][:top_n]
        topic_terms.append([terms[i] for i in top_idx if mean_scores[i] > 0])
    return topic_terms


def umass_coherence(texts: List[str], topic_terms: List[List[str]], epsilon: float = 1.0) -> float:
    """Lightweight UMass-style coherence on document-level window texts.

    Higher is better. Values are often negative; less negative means more coherent.
    """
    doc_tokens = [set(tokenize(text)) for text in texts]
    if not doc_tokens:
        return 0.0

    def doc_freq(term: str) -> int:
        return sum(1 for tokens in doc_tokens if term in tokens)

    def co_doc_freq(term_i: str, term_j: str) -> int:
        return sum(1 for tokens in doc_tokens if term_i in tokens and term_j in tokens)

    scores: List[float] = []
    for terms in topic_terms:
        clean_terms = [term for term in terms if " " not in term][:10]
        if len(clean_terms) < 2:
            continue
        pair_scores: List[float] = []
        for m in range(1, len(clean_terms)):
            for l in range(0, m):
                numerator = co_doc_freq(clean_terms[m], clean_terms[l]) + epsilon
                denominator = doc_freq(clean_terms[l]) + epsilon
                pair_scores.append(math.log(numerator / denominator))
        if pair_scores:
            scores.append(sum(pair_scores) / len(pair_scores))
    return round(sum(scores) / len(scores), 6) if scores else 0.0


def normalize_metric(values: List[float], higher_is_better: bool = True) -> List[float]:
    if not values:
        return []
    lo, hi = min(values), max(values)
    if math.isclose(lo, hi):
        return [0.5 for _ in values]
    if higher_is_better:
        return [(v - lo) / (hi - lo) for v in values]
    return [(hi - v) / (hi - lo) for v in values]


def evaluate_candidates(
    texts: List[str],
    embeddings,
    min_topics: int,
    max_topics: int,
    random_state: int,
) -> List[Dict[str, object]]:
    from sklearn.metrics import calinski_harabasz_score, davies_bouldin_score, silhouette_score

    n = len(texts)
    max_valid_k = min(max_topics, n - 1)
    min_valid_k = max(2, min_topics)
    if max_valid_k < min_valid_k:
        raise ValueError(f"Not enough AI mention windows ({n}) to evaluate K in range {min_topics}-{max_topics}")

    raw_rows: List[Dict[str, object]] = []
    for k in range(min_valid_k, max_valid_k + 1):
        print(f"Evaluating K={k}")
        labels = cluster_labels(embeddings, k, random_state)
        counts = Counter(labels)
        min_topic_size = min(counts.values()) if counts else 0
        min_topic_share = min_topic_size / n if n else 0.0
        topic_terms = topic_terms_from_tfidf(texts, labels, k)
        coherence = umass_coherence(texts, topic_terms)

        try:
            silhouette = silhouette_score(embeddings, labels)
        except Exception:
            silhouette = float("nan")
        try:
            db = davies_bouldin_score(embeddings, labels)
        except Exception:
            db = float("nan")
        try:
            ch = calinski_harabasz_score(embeddings, labels)
        except Exception:
            ch = float("nan")

        raw_rows.append(
            {
                "candidate_k": k,
                "n_windows": n,
                "silhouette_score": round(float(silhouette), 6),
                "davies_bouldin_score": round(float(db), 6),
                "calinski_harabasz_score": round(float(ch), 6),
                "topic_coherence_umass": coherence,
                "min_topic_size": min_topic_size,
                "min_topic_share": round(min_topic_share, 6),
                "topic_size_distribution": "; ".join(f"{topic_id}:{count}" for topic_id, count in sorted(counts.items())),
                "topic_terms_preview": " | ".join(f"T{idx}:" + ", ".join(terms[:8]) for idx, terms in enumerate(topic_terms)),
            }
        )

    silhouette_norm = normalize_metric([float(row["silhouette_score"]) for row in raw_rows], True)
    db_norm = normalize_metric([float(row["davies_bouldin_score"]) for row in raw_rows], False)
    ch_norm = normalize_metric([float(row["calinski_harabasz_score"]) for row in raw_rows], True)
    coherence_norm = normalize_metric([float(row["topic_coherence_umass"]) for row in raw_rows], True)
    min_share_norm = normalize_metric([float(row["min_topic_share"]) for row in raw_rows], True)

    for idx, row in enumerate(raw_rows):
        composite = sum(
            [
                silhouette_norm[idx],
                db_norm[idx],
                ch_norm[idx],
                coherence_norm[idx],
                min_share_norm[idx],
            ]
        ) / 5
        row["silhouette_norm"] = round(silhouette_norm[idx], 6)
        row["davies_bouldin_norm_inverted"] = round(db_norm[idx], 6)
        row["calinski_harabasz_norm"] = round(ch_norm[idx], 6)
        row["topic_coherence_norm"] = round(coherence_norm[idx], 6)
        row["min_topic_share_norm"] = round(min_share_norm[idx], 6)
        row["composite_score"] = round(composite, 6)

    return sorted(raw_rows, key=lambda row: (-float(row["composite_score"]), int(row["candidate_k"])))


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Optimize topic count for 10-K AI topic modeling.")
    parser.add_argument("--input-csv", type=Path, default=DEFAULT_INPUT_CSV)
    parser.add_argument("--min-topics", type=int, default=4)
    parser.add_argument("--max-topics", type=int, default=20)
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

    texts = [window.window_text for window in windows]
    embeddings, _vectorizer, embedding_method = make_embeddings(texts, args.model_name, args.tfidf_fallback_only)
    ranked_rows = evaluate_candidates(texts, embeddings, args.min_topics, args.max_topics, args.random_state)
    recommended = ranked_rows[0]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)

    fieldnames = list(ranked_rows[0].keys()) + ["rank"]
    ranked_with_rank = []
    for idx, row in enumerate(ranked_rows, start=1):
        out = dict(row)
        out["rank"] = idx
        ranked_with_rank.append(out)
    write_csv(OPTIMIZATION_OUT, ranked_with_rank, fieldnames)

    recommendation = [
        {"metric": "recommended_n_topics", "value": str(recommended["candidate_k"]), "note": "Highest composite_score across candidate K values"},
        {"metric": "recommended_composite_score", "value": str(recommended["composite_score"]), "note": "Mean of normalized silhouette, inverted Davies-Bouldin, Calinski-Harabasz, UMass coherence, and min-topic-share"},
        {"metric": "candidate_range", "value": f"{args.min_topics}-{args.max_topics}", "note": "Evaluated inclusive range"},
        {"metric": "n_windows", "value": str(len(windows)), "note": "AI mention windows used for optimization"},
        {"metric": "window_size", "value": str(args.window_size), "note": "AI sentence +/- window size"},
        {"metric": "embedding_method", "value": embedding_method, "note": "Sentence-BERT preferred unless TF-IDF fallback requested or needed"},
        {"metric": "selection_rule", "value": "argmax(composite_score)", "note": "Do not set topic count arbitrarily; use this optimization output before final topic modeling"},
    ]
    write_csv(RECOMMENDATION_OUT, recommendation, ["metric", "value", "note"])

    print(f"Recommended K: {recommended['candidate_k']}")
    print(f"Composite score: {recommended['composite_score']}")
    print(f"Optimization table: {OPTIMIZATION_OUT.relative_to(REPO_ROOT)}")
    print(f"Recommendation: {RECOMMENDATION_OUT.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
