# SEC filing chunk-construction strategy

## The upstream unit being split

The corpus unit is a single SEC filing, identified by accession number and document ID. After the filing HTML is cleaned, the text is first divided at natural SEC `Item` boundaries such as `Item 1. Business` and `Item 1A. Risk Factors`. Only then is each section divided into paragraph-aligned retrieval chunks.

This matters because a character window that crosses from Business into Risk Factors can retrieve a misleading mixture of topics and produce a citation that is difficult to audit.

## Evidence-sized chunks

The starting configuration is:

| Parameter | Initial value | Rationale |
|---|---:|---|
| Target length | 1,800 characters | Usually holds one to three related filing paragraphs: enough evidence for one planning claim without flooding the reranker |
| Maximum length | 2,400 characters | Accommodates a long disclosure paragraph while bounding embedding and generation context |
| Overlap | Up to 300 characters | Reuses complete trailing paragraphs where possible; it does not cut arbitrary character fragments |
| Retrieval | Top 10 dense candidates | Preserves the original MVP retrieval breadth |
| Reranking | Top 5 | Preserves the original Cohere evidence budget |

No chunk may cross an SEC Item boundary. Every chunk carries:

- document ID and accession number
- ticker, form type, and filing date
- source URL
- section ID and title
- section-local chunk index
- character count and construction strategy

The stable chunk ID includes the document, section, chunk index, and content digest. This supports duplicate detection and reproducible evaluation.

## Corpus rationale

Apple's fiscal 2025 Form 10-K remains the reproducible baseline for comparison with the original n8n pilot. The ingestion and retrieval design is now multi-ticker: the command resolves any supported SEC ticker, and every retrieval is filtered by ticker. A ticker is answerable only after its filing has been indexed; the assistant must not imply that SEC filings provide current valuation.

After the baseline is reproduced, expand by document class in this order:

1. Add 10-Q filings for updated financial and risk context.
2. Add 8-K filings and earnings releases for event-level evidence.
3. Expand the evaluated issuer set while enforcing ticker and accession filters.

## How chunk size will be tuned

Chunk length is a testable retrieval parameter, not a permanent constant. Evaluate at least 1,000, 1,500, 1,800, and 2,400 target characters using the same question set and record:

- Hit@5 and mean reciprocal rank
- expected-topic coverage
- section and metadata accuracy
- answer faithfulness to retrieved passages
- citation completeness at the claim level
- unsupported-question refusal accuracy
- average evidence tokens supplied to generation

Select the smallest configuration that preserves answer-level evidence completeness. Report results by question category—business description, supply chain, risk, management discussion, and financial statement—not only as aggregate averages.

## Known parser boundary

`extract_item_sections` expects cleaned text with real line breaks around Item headings. The production HTML ingestion step must remove the table of contents and repeated page headers before calling it. DOM-aware subsection extraction can later preserve headings inside an Item, but the current implementation already prevents cross-Item chunks.
