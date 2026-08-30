from wealthplan.ingestion.chunking import (
    ChunkingConfig,
    chunk_filing_sections,
    extract_item_sections,
)


def sample_sections():
    paragraph_a = "Apple sells products and services globally. " * 8
    paragraph_b = "Manufacturing depends on external partners. " * 8
    paragraph_c = "Supply disruptions can affect production. " * 8
    text = f"""ITEM 1. BUSINESS
{paragraph_a}

{paragraph_b}

{paragraph_c}

ITEM 1A. RISK FACTORS
{paragraph_b}

{paragraph_c}
"""
    return extract_item_sections(
        text,
        document_id="aapl-2025-10k",
        ticker="AAPL",
        form_type="10-K",
        filing_date="2025-09-27",
        accession_number="0000320193-25-000079",
        source_url="https://example.test/aapl-10k",
    )


def test_extracts_natural_sec_item_boundaries():
    sections = sample_sections()

    assert [section.section_id for section in sections] == ["item-1", "item-1a"]
    assert sections[0].section_title == "Item 1. BUSINESS"
    assert "RISK FACTORS" not in sections[0].text


def test_chunks_never_cross_sections_and_preserve_metadata():
    sections = sample_sections()
    chunks = chunk_filing_sections(
        sections,
        ChunkingConfig(target_chars=500, max_chars=700, overlap_chars=300),
    )

    assert chunks
    assert all(chunk.char_count == len(chunk.text) for chunk in chunks)
    assert all(chunk.char_count <= 700 for chunk in chunks)
    assert all(chunk.ticker == "AAPL" for chunk in chunks)
    assert all(chunk.section_id in {"item-1", "item-1a"} for chunk in chunks)
    assert len({chunk.chunk_id for chunk in chunks}) == len(chunks)


def test_overlap_reuses_whole_paragraph_not_arbitrary_character_slice():
    section = sample_sections()[0]
    chunks = chunk_filing_sections(
        [section],
        ChunkingConfig(target_chars=750, max_chars=900, overlap_chars=400),
    )

    assert len(chunks) >= 2
    first_last_paragraph = chunks[0].text.split("\n\n")[-1]
    assert chunks[1].text.startswith(first_last_paragraph)
