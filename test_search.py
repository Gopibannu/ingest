"""
RHD ChromaDB Search & Retrieval Test Script
Tests cosine similarity search across both English and Hindi rules.
Includes interactive query mode for testing arbitrary passenger questions.
"""

import sys
import io
from pathlib import Path

# Fix terminal encoding on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# Add current folder to sys.path
CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

try:
    from .chroma_store import search_chroma
except ImportError:
    from chroma_store import search_chroma


def run_benchmark_tests():
    """Runs verification queries covering the major Capstone requirements."""
    test_queries = [
        {
            "query": "What is the advance reservation period (ARP) for booking train tickets?",
            "expected": "rb_cc10_2024_advance_reservation.pdf (60 days rule)",
            "lang": None
        },
        {
            "query": "What are the cancellation charges if a confirmed ticket is cancelled 48 hours before train departure?",
            "expected": "irctc_refund_rules_jan2026.pdf / vande bharat",
            "lang": None
        },
        {
            "query": "What are the Aadhaar authentication rules for Tatkal booking?",
            "expected": "rb_cc08_2025_tatkal.pdf",
            "lang": None
        },
        {
            "query": "वंदे भारत स्लीपर एक्सप्रेस के लिए टिकट रद्दीकरण प्रभार क्या हैं?",
            "expected": "rb_cc08_2026_vande_bharat_sleeper_refund.pdf (Gazette G.S.R. 41(E))",
            "lang": "hi"
        }
    ]

    print("=" * 70)
    print("RUNNING CHROMADB RETRIEVAL BENCHMARKS")
    print("=" * 70)

    for i, test in enumerate(test_queries, 1):
        q = test["query"]
        expected = test["expected"]
        lang = test["lang"]

        print(f"\n[Test {i}] Query: {q}")
        print(f"Target Concept: {expected}")
        if lang:
            print(f"Language Filter: {lang}")

        results = search_chroma(q, k=2, language_filter=lang)

        if not results or not results["documents"] or not results["documents"][0]:
            print("  ❌ No results found in ChromaDB!")
            continue

        for rank, (doc, meta) in enumerate(zip(results["documents"][0], results["metadatas"][0]), 1):
            src = meta.get("source", "unknown")
            page = meta.get("page", -1)
            page_str = str(page) if page != -1 else "null (web)"
            date = meta.get("date", "N/A")
            authority = meta.get("authority", "N/A")

            print(f"\n  Result #{rank}:")
            print(f"    Source:    {src}")
            print(f"    Page:      {page_str}")
            print(f"    Date:      {date} ({authority})")
            print(f"    Content:   {doc[:220].replace(chr(10), ' ')}...")

    print("\n" + "=" * 70)
    print("BENCHMARK COMPLETED SUCCESSFULLY!")
    print("=" * 70)


def interactive_mode():
    """Allows arbitrary user queries directly from the terminal."""
    print("\nStarting Interactive Query Mode (type 'exit' or 'q' to quit):")
    while True:
        try:
            q = input("\nEnter Passenger Query: ").strip()
            if not q or q.lower() in ["exit", "q", "quit"]:
                break
            results = search_chroma(q, k=2)
            if not results or not results["documents"] or not results["documents"][0]:
                print("No matching rules found.")
                continue
            for rank, (doc, meta) in enumerate(zip(results["documents"][0], results["metadatas"][0]), 1):
                page_str = str(meta.get("page")) if meta.get("page") != -1 else "null"
                print(f"\n[{rank}] Source: {meta.get('source')} | Page: {page_str} | Date: {meta.get('date')}")
                print(f"    {doc[:300].replace(chr(10), ' ')}...")
        except (KeyboardInterrupt, EOFError):
            break


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
        interactive_mode()
    else:
        run_benchmark_tests()
