"""Bounded retrieval-augmented generation (RAG) index for project documentation.

This layer stays dependency-free and deterministic: documents are chunked once,
then ranked with a BM25-style lexical score plus phrase/coverage boosts. It is
safe for production use because only an explicit allow-list is indexed; user
memory and jokes_data.json are handled elsewhere and are never read here.
"""
from __future__ import annotations
from bot.utils.modular_loader import load_modular_part

import math
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
ALLOWED_DOCUMENTS = ("README.md", "RELEASE.md", ".env.example", "render.yaml", "pyproject.toml")
MAX_FILE_CHARS = 80_000
CHUNK_CHARS = 1_200
CHUNK_OVERLAP = 180
MAX_RESULTS = 8
MAX_CONTEXT_CHARS = 4_000

_TOKEN_RE = re.compile(r"[\w\u0600-\u06ff]{2,}")


load_modular_part(__file__, 'rag_parts/part_001_Chunk.py')


load_modular_part(__file__, 'rag_parts/part_002_ScoredChunk.py')


load_modular_part(__file__, 'rag_parts/part_003__normalize.py')


load_modular_part(__file__, 'rag_parts/part_004__tokens.py')


load_modular_part(__file__, 'rag_parts/part_005__chunk_text.py')


load_modular_part(__file__, 'rag_parts/part_006__index.py')


load_modular_part(__file__, 'rag_parts/part_007_refresh_index.py')


load_modular_part(__file__, 'rag_parts/part_008_index_stats.py')


load_modular_part(__file__, 'rag_parts/part_009_search.py')


load_modular_part(__file__, 'rag_parts/part_010_build_context.py')
