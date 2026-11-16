"""대비수칙 RAG: knowledge/*.md를 섹션 단위로 쪼개 색인하고, 질문과 관련된 섹션만 찾아 준다.

- 00_답변원칙.md 는 검색 대상이 아니라 시스템 프롬프트(규칙)로 항상 들어간다.
- 01~04 파일은 '## ' 제목 단위로 잘라 검색한다.
- 검색은 글자 n-gram TF-IDF(scikit-learn)라서 한국어 형태소 분석기나 임베딩 API 없이 동작한다.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

RULES_FILE_PREFIX = "00_"
PRIORITY_WEIGHT = {"1": 1.0, "2": 0.9, "3": 0.8, "4": 0.7}


@dataclass
class Chunk:
    file: str
    title: str          # 문서 제목 (front matter의 '문서')
    heading: str        # 섹션 제목 (## ...)
    text: str           # 섹션 본문
    meta: dict = field(default_factory=dict)

    @property
    def source(self) -> dict:
        return {"기관": self.meta.get("기관", ""), "url": self.meta.get("출처URL", "")}

    def as_context(self) -> str:
        return f"(출처: {self.meta.get('기관', '')})\n## {self.heading}\n{self.text}"


def _parse_front_matter(raw: str) -> tuple[dict, str]:
    """'---' 로 감싼 머리말을 dict 로, 나머지를 본문으로 돌려준다."""
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", raw, re.S)
    if not m:
        return {}, raw
    meta = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip()
    return meta, raw[m.end():]


def _split_sections(body: str) -> list[tuple[str, str]]:
    sections, heading, buf = [], None, []
    for line in body.splitlines():
        if line.startswith("## "):
            if heading and "".join(buf).strip():
                sections.append((heading, "\n".join(buf).strip()))
            heading, buf = line[3:].strip(), []
        elif heading is not None:
            buf.append(line)
    if heading and "".join(buf).strip():
        sections.append((heading, "\n".join(buf).strip()))
    return sections


class KnowledgeBase:
    def __init__(self, folder: str | Path):
        folder = Path(folder)
        self.rules = ""
        self.chunks: list[Chunk] = []
        for path in sorted(folder.glob("*.md")):
            meta, body = _parse_front_matter(path.read_text(encoding="utf-8"))
            if path.name.startswith(RULES_FILE_PREFIX):
                self.rules = body.strip()
                continue
            for heading, text in _split_sections(body):
                self.chunks.append(Chunk(path.name, meta.get("문서", path.stem), heading, text, meta))
        if not self.chunks:
            raise RuntimeError(f"{folder} 에서 검색할 섹션을 찾지 못했습니다.")

        # 한국어는 띄어쓰기 단위가 들쭉날쭉해서 글자 2~4개 묶음으로 색인한다.
        self._vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4), sublinear_tf=True)
        self._matrix = self._vec.fit_transform([f"{c.title} {c.heading} {c.text}" for c in self.chunks])
        # 우선순위가 높은 자료(01 응급처치)가 비슷한 점수면 먼저 뽑히도록 가중치를 준다.
        self._weights = np.array([PRIORITY_WEIGHT.get(c.meta.get("우선순위", "")[:1], 0.8) for c in self.chunks])

    def search(self, query: str, k: int = 4, min_score: float = 0.03,
               must_include: tuple[str, ...] = ()) -> list[Chunk]:
        """질문과 비슷한 섹션 k개. must_include 에 든 단어가 제목에 있는 섹션은 항상 넣는다."""
        scores = cosine_similarity(self._vec.transform([query]), self._matrix)[0] * self._weights
        forced: list[int] = []
        for w in must_include:  # must_include 순서대로 (응급이면 '중증'이 맨 앞)
            forced += [i for i, c in enumerate(self.chunks) if w in c.heading and i not in forced]
        ranked = [i for i in scores.argsort()[::-1] if scores[i] >= min_score and i not in forced]
        return [self.chunks[i] for i in (forced + ranked)[:max(k, len(forced))]]
