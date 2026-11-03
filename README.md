# Railway Help Desk — Ingestion, Chunking & ChromaDB Module (`rhd_ingestion`)

> **GENAI NEXUS · COHORT 1 · MODULE 2 CAPSTONE**  
> Covers **Piece 1: Documents In** (Document extraction, Scans OCR, Bilingual Hindi/English handling, Semantic chunking with provenance, and ChromaDB vector indexing).

---

## 1. Executive Summary & Team Quick Start

This module handles the entire extraction-to-vector pipeline. Anyone on the team can clone this repository, run two commands, and have a fully loaded, high-accuracy ChromaDB vector index with zero extra configuration.

### Fresh Clone Commands:
```bash
# 1. Run extraction + chunking across all 7 official documents
python -m rhd_ingestion.run_pipeline

# 2. Generate embeddings and index vectors into ChromaDB
python -m rhd_ingestion.chroma_store
```

---

## 2. Architecture & Pipeline

```
[Official Pack (data/ / documents/)]
     ├── Native PDFs (English + Hindi)
     ├── Scanned PDFs (ARP 60 Days, Charts)
     └── HTML Circulars & PIB Announcements
                 │
                 ▼
        [extractor.py]
     ├── Digital Extraction (pypdf)
     ├── Scanned OCR Engine (RapidOCR + onnxruntime)
     └── Devanagari Detection (\u0900-\u097F)
                 │
                 ▼
         [chunker.py]
     ├── Hierarchical Splitter (\n\n -> \n -> । -> . -> ' ')
     ├── Sliding Window Overlap (~120 chars)
     └── Provenance & Precedence Metadata Registry
                 │
                 ▼
    [rhd_ingestion/output/final_chunks.json] (145 Chunks)
                 │
                 ▼
      [chroma_store.py]
     ├── 384-d Dense ONNX Embeddings (all-MiniLM-L6-v2)
     ├── Cosine Metric HNSW Index
     └── Persistent ChromaDB Storage (rhd_ingestion/chroma_db/)
```

---

## 3. Directory Layout

```
rhd_ingestion/
├── __init__.py           # Package declarations
├── extractor.py          # Bilingual text extraction with OCR fallback for scans
├── chunker.py            # Sentence & Purna-Viram aware chunker with metadata & overlap
├── run_pipeline.py       # Orchestrator producing final_chunks.json
├── chroma_store.py       # ChromaDB vector indexer & query utility
├── README.md             # This comprehensive technical guide
├── output/
│   └── final_chunks.json # Complete list of 145 structured chunks
└── chroma_db/            # Persistent ChromaDB vector database files
```

---

## 4. The Data Contract (Capstone Specification)

Every chunk in `rhd_ingestion/output/final_chunks.json` strictly fulfills the evaluators' schema:

```json
{
  "id": "rb_cc10_2024_advance_reservation_pdf_p1_c1",
  "text": "...the existing time limit for advance reservations by trains will be reduced from 120 days to 60 days (excluding the date of journey) as mentioned below: i. With effect from 01.11.2024, the ARP will be of 60 days...",
  "source": "rb_cc10_2024_advance_reservation.pdf",
  "page": 1,
  "metadata": {
    "source": "rb_cc10_2024_advance_reservation.pdf",
    "page": 1,
    "date": "2024-10-16",
    "authority": "Railway Board CC 10/2024",
    "language": "en",
    "chunk_index": 1
  }
}
```

### Contract Rules & Details:
- **`id`**: Unique string ID formatted as `{source}_{page}_{index}`.
- **`source`**: The exact document filename (e.g., `irctc_refund_rules_jan2026.pdf`).
- **`page`**: 1-based page number for PDFs, or `null` (`-1` in ChromaDB) for HTML pages, per the Capstone rule:
  > *"page is null for the web pages"*
- **`metadata.date`**: Official issue date (`YYYY-MM-DD`). Allows your downstream prompt to resolve conflicts:
  > *"When they disagree, the newer one wins."*
- **`metadata.language`**: `"en"` or `"hi"`. Enables targeted multilingual retrieval.

---

## 5. How to Query ChromaDB in Your Code

To retrieve source-grounded chunks for any passenger query:

```python
from rhd_ingestion.chroma_store import search_chroma

# 1. Search for rules
results = search_chroma("What is the advance reservation period?", k=3)

# 2. Iterate retrieved chunks
for doc, meta in zip(results['documents'][0], results['metadatas'][0]):
    page_display = meta['page'] if meta['page'] != -1 else "null"
    print(f"Source: {meta['source']} (Page: {page_display}, Date: {meta['date']})")
    print(f"Content: {doc}\n")
```

### Optional Language Filtering:
```python
# Query only Hindi Gazette chunks
hindi_results = search_chroma("वंदे भारत स्लीपर रिफंड नियम", k=2, language_filter="hi")
```

---

## 6. How the Hard Challenges Were Solved

| Capstone Requirement | Root Problem | Engineered Solution |
| :--- | :--- | :--- |
| **Scanned Circulars** | `rb_cc10_2024`, `rb_cc10_2025`, and `rb_cc08_2025` contain scanned images yielding 0 text in standard parsers. | High-resolution PDF page rendering via `pypdfium2` coupled with an onnxruntime-accelerated `RapidOCR` fallback engine. |
| **Bilingual Text (Hindi & English)** | Hindi text suffers from broken ligatures and missing sentence stops. | Regex-based Unicode detection (`\u0900-\u097F`) and boundary splitting on Hindi *Purna Viram* (`।`) and English punctuation. |
| **Newer Rules Win** | Older 2015 rules conflict with 2024/2026 circulars (e.g. 120 vs 60 days ARP). | Every chunk includes official issuance `date` and `authority` in its metadata registry. |
| **HTML Provenance** | Evaluators mandate `page: null` for web pages. | HTML extractors assign `page: None` (`null` in JSON, `-1` in Chroma metadata). |
| **Context Boundary Loss** | Slicing by character count splits conditions from deductions. | Hierarchical paragraph splitting with 120-character sliding-window overlap (`...prefix\n`). |

---

## 7. Verification & Production Benchmarks

- **Total Documents Processed**: 7 / 7 (100% of official pack)
- **Total Chunks Generated**: 145
  - **English Chunks**: 123
  - **Hindi Chunks**: 22
- **Scanned Rules Recovered**:
  - `rb_cc10_2024_advance_reservation.pdf`: 4 chunks (ARP 120 -> 60 days)
  - `rb_cc10_2025_reservation_charts.pdf`: 4 chunks (Chart prep timelines)
  - `rb_cc08_2025_tatkal.pdf`: 10 chunks (Aadhaar authentication)
- **ChromaDB Status**: 145 vectors indexed and ready for retrieval at `rhd_ingestion/chroma_db/`.
