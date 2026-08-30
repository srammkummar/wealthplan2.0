"""Section-aware chunk construction for SEC filing evidence."""

from __future__ import annotations

from hashlib import sha256
import re

from pydantic import BaseModel, Field


ITEM_HEADING = re.compile(
    r"(?im)^\s*ITEM\s+(?P<item>\d+[A-Z]?)\s*[.\-—:]\s*(?P<title>[^\n]+?)\s*$"
)
SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9])")


class FilingSection(BaseModel):
    document_id: str
    ticker: str
    form_type: str
    filing_date: str
    accession_number: str
    source_url: str
    section_id: str
    section_title: str
    text: str


class FilingChunk(BaseModel):
    chunk_id: str
    text: str
    document_id: str
    ticker: str
    form_type: str
    filing_date: str
    accession_number: str
    source_url: str
    section_id: str
    section_title: str
    chunk_index: int
    char_count: int
    construction: str = "section-aware-paragraph-window"


class ChunkingConfig(BaseModel):
    target_chars: int = Field(default=1800, ge=300)
    max_chars: int = Field(default=2400, ge=500)
    overlap_chars: int = Field(default=300, ge=0)

    def model_post_init(self, __context: object) -> None:
        if self.max_chars < self.target_chars:
            raise ValueError("max_chars must be greater than or equal to target_chars")
        if self.overlap_chars >= self.target_chars:
            raise ValueError("overlap_chars must be smaller than target_chars")


def extract_item_sections(
    text: str,
    *,
    document_id: str,
    ticker: str,
    form_type: str,
    filing_date: str,
    accession_number: str,
    source_url: str,
) -> list[FilingSection]:
    """Split cleaned filing text on SEC Item headings before chunk construction."""

    matches = list(ITEM_HEADING.finditer(text))
    sections: list[FilingSection] = []
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        if not body:
            continue
        item = match.group("item").upper()
        title = " ".join(match.group("title").split())
        sections.append(
            FilingSection(
                document_id=document_id,
                ticker=ticker.upper(),
                form_type=form_type.upper(),
                filing_date=filing_date,
                accession_number=accession_number,
                source_url=source_url,
                section_id=f"item-{item.lower()}",
                section_title=f"Item {item}. {title}",
                text=body,
            )
        )
    return sections


def _normalize_paragraphs(text: str) -> list[str]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    paragraphs = re.split(r"\n\s*\n+", normalized)
    return [" ".join(paragraph.split()) for paragraph in paragraphs if paragraph.strip()]


def _split_long_paragraph(paragraph: str, max_chars: int) -> list[str]:
    if len(paragraph) <= max_chars:
        return [paragraph]
    sentences = SENTENCE_BOUNDARY.split(paragraph)
    units: list[str] = []
    current = ""
    for sentence in sentences:
        candidate = f"{current} {sentence}".strip()
        if current and len(candidate) > max_chars:
            units.append(current)
            current = sentence
        else:
            current = candidate
        while len(current) > max_chars:
            split_at = current.rfind(" ", 0, max_chars + 1)
            split_at = split_at if split_at > 0 else max_chars
            units.append(current[:split_at].strip())
            current = current[split_at:].strip()
    if current:
        units.append(current)
    return units


def _section_units(section: FilingSection, max_chars: int) -> list[str]:
    units: list[str] = []
    for paragraph in _normalize_paragraphs(section.text):
        units.extend(_split_long_paragraph(paragraph, max_chars))
    return units


def _stable_chunk_id(section: FilingSection, index: int, text: str) -> str:
    digest = sha256(
        f"{section.document_id}|{section.section_id}|{index}|{text}".encode("utf-8")
    ).hexdigest()[:16]
    return f"{section.document_id}:{section.section_id}:{index}:{digest}"


def chunk_filing_sections(
    sections: list[FilingSection], config: ChunkingConfig | None = None
) -> list[FilingChunk]:
    """Create paragraph-aligned windows that never cross filing sections."""

    config = config or ChunkingConfig()
    chunks: list[FilingChunk] = []
    for section in sections:
        units = _section_units(section, config.max_chars)
        start = 0
        section_chunk_index = 0
        while start < len(units):
            end = start
            selected: list[str] = []
            while end < len(units):
                candidate = "\n\n".join([*selected, units[end]])
                if selected and len(candidate) > config.target_chars:
                    break
                selected.append(units[end])
                end += 1
                if len(candidate) >= config.target_chars:
                    break

            chunk_text = "\n\n".join(selected)
            chunks.append(
                FilingChunk(
                    chunk_id=_stable_chunk_id(
                        section, section_chunk_index, chunk_text
                    ),
                    text=chunk_text,
                    document_id=section.document_id,
                    ticker=section.ticker,
                    form_type=section.form_type,
                    filing_date=section.filing_date,
                    accession_number=section.accession_number,
                    source_url=section.source_url,
                    section_id=section.section_id,
                    section_title=section.section_title,
                    chunk_index=section_chunk_index,
                    char_count=len(chunk_text),
                )
            )
            section_chunk_index += 1
            if end >= len(units):
                break

            overlap_start = end
            overlap_size = 0
            while overlap_start > start:
                prior = units[overlap_start - 1]
                added = len(prior) + (2 if overlap_size else 0)
                if overlap_size + added > config.overlap_chars:
                    break
                overlap_size += added
                overlap_start -= 1
            start = overlap_start if overlap_start > start else end
    return chunks
