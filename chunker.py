"""
RHD Chunking Module
Splits document pages into high-precision semantic chunks.
Preserves:
- Tables and slabs intact
- Exact rule codes (Rule 25, CC 10 of 2024, etc.)
- English & Hindi sentence boundaries (including Hindi Purna Viram '।')
- Complete metadata according to Capstone Section 2
"""

import re
from typing import List, Dict, Any, Optional

# Precedence dates and official circular authority mappings
METADATA_REGISTRY = {
    "indianrail_refund_rules_2015.html": {
        "title": "Revised Refund Rules w.e.f. 12.11.2015",
        "date": "2015-11-12",
        "authority": "Gazette 04-Nov-2015"
    },
    "irctc_refund_rules_jan2026.pdf": {
        "title": "IRCTC Refund Rules & TDR Filing (Jan 2026)",
        "date": "2026-01-01",
        "authority": "IRCTC Website Rules"
    },
    "pib_2026-03-24_reform_express.html": {
        "title": "PIB Reform Express - Indian Railways Modernization",
        "date": "2026-03-24",
        "authority": "Press Information Bureau"
    },
    "rb_cc08_2025_tatkal.pdf": {
        "title": "Commercial Circular No. 08 of 2025 - Tatkal Modification",
        "date": "2025-06-10",
        "authority": "Railway Board CC 08/2025"
    },
    "rb_cc08_2026_vande_bharat_sleeper_refund.pdf": {
        "title": "Commercial Circular No. 08 of 2026 & Gazette G.S.R. 41(E) - Vande Bharat Sleeper",
        "date": "2026-01-19",
        "authority": "Railway Board CC 08/2026 & Gazette G.S.R. 41(E)"
    },
    "rb_cc10_2024_advance_reservation.pdf": {
        "title": "Commercial Circular No. 10 of 2024 - Reduction of ARP to 60 Days",
        "date": "2024-10-16",
        "authority": "Railway Board CC 10/2024"
    },
    "rb_cc10_2025_reservation_charts.pdf": {
        "title": "Commercial Circular No. 10 of 2025 - Chart Preparation Timelines",
        "date": "2025-07-02",
        "authority": "Railway Board CC 10/2025"
    }
}


def split_text_recursive(text: str, chunk_size: int = 650, chunk_overlap: int = 120) -> List[str]:
    """
    Recursively splits text on natural boundaries:
    1. Blank lines (\n\n) - preserves paragraphs & table rows
    2. Single lines (\n)
    3. Hindi Purna Viram ('। ') & English Sentence stops ('. ', '? ')
    4. Spaces (' ')
    """
    if len(text) <= chunk_size:
        return [text.strip()] if text.strip() else []

    separators = ["\n\n", "\n", "। ", ". ", "? ", " "]

    def _split(raw: str, sep_idx: int) -> List[str]:
        if sep_idx >= len(separators):
            return [raw[i:i + chunk_size] for i in range(0, len(raw), chunk_size - chunk_overlap)]

        sep = separators[sep_idx]
        parts = raw.split(sep)
        result = []
        current = ""

        for p in parts:
            candidate = f"{current}{sep}{p}" if current else p
            if len(candidate) <= chunk_size:
                current = candidate
            else:
                if current.strip():
                    result.append(current.strip())
                if len(p) > chunk_size:
                    result.extend(_split(p, sep_idx + 1))
                    current = ""
                else:
                    current = p

        if current.strip():
            result.append(current.strip())
        return result

    base_chunks = _split(text, 0)

    # Apply sliding window overlap
    final_chunks = []
    for i, ch in enumerate(base_chunks):
        if i == 0 or chunk_overlap <= 0:
            final_chunks.append(ch)
        else:
            prev = base_chunks[i - 1]
            overlap = prev[-chunk_overlap:] if len(prev) > chunk_overlap else prev
            final_chunks.append(f"...{overlap}\n{ch}")

    return [c for c in final_chunks if len(c.strip()) > 30]


def build_chunks(
    pages_data: List[Dict[str, Any]],
    source_filename: str,
    chunk_size: int = 650,
    chunk_overlap: int = 120
) -> List[Dict[str, Any]]:
    """
    Builds chunks strictly conforming to the Capstone benchmark:
    {
        "id": str,
        "text": str,
        "source": str,
        "page": int or None,
        "metadata": {
            "source": str,
            "page": int or None,
            "date": str,
            "authority": str,
            "language": str,
            "chunk_index": int
        }
    }
    """
    reg_info = METADATA_REGISTRY.get(source_filename, {
        "title": source_filename,
        "date": "2025-01-01",
        "authority": "Indian Railways"
    })

    clean_source = source_filename.replace(".", "_")
    chunks = []
    counter = 0

    for page in pages_data:
        page_num = page["page_number"]
        page_text = page["text"]
        lang = page["language"]

        splits = split_text_recursive(page_text, chunk_size=chunk_size, chunk_overlap=chunk_overlap)

        for s in splits:
            chunk_id = f"{clean_source}_p{page_num if page_num is not None else 'web'}_c{counter}"
            chunks.append({
                "id": chunk_id,
                "text": s,
                "source": source_filename,
                "page": page_num,
                "metadata": {
                    "source": source_filename,
                    "page": page_num,
                    "date": reg_info["date"],
                    "authority": reg_info["authority"],
                    "language": lang,
                    "chunk_index": counter
                }
            })
            counter += 1

    return chunks
