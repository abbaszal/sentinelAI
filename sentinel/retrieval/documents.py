from dataclasses import dataclass
from pathlib import Path


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

POLICY_DIRECTORY = Path("data/policies")

DEFAULT_CHUNK_SIZE = 200
DEFAULT_CHUNK_OVERLAP = 40


# ---------------------------------------------------------
# Data models
# ---------------------------------------------------------

@dataclass
class Document:
    """
    Represents one complete source document.
    """

    document_id: str
    title: str
    content: str
    source: str


@dataclass
class DocumentChunk:
    """
    Represents one searchable piece of a document.
    """

    chunk_id: str
    document_id: str
    title: str
    section: str
    content: str
    source: str


# ---------------------------------------------------------
# Document loading
# ---------------------------------------------------------

def extract_title(content: str) -> str:
    """
    Extract the first level-1 Markdown heading.

    Example:

        # NovaShop Payment Policy

    becomes:

        NovaShop Payment Policy
    """

    for line in content.splitlines():
        line = line.strip()

        if line.startswith("# "):
            return line[2:].strip()

    return "Untitled Document"


def load_policy_documents() -> list[Document]:
    """
    Load all Markdown policy documents.

    Returns:
        A list of Document objects.
    """

    documents: list[Document] = []

    for path in sorted(
        POLICY_DIRECTORY.glob("*.md")
    ):
        content = path.read_text(
            encoding="utf-8"
        )

        document = Document(
            document_id=path.stem,
            title=extract_title(content),
            content=content,
            source=str(path),
        )

        documents.append(document)

    return documents


# ---------------------------------------------------------
# Section extraction
# ---------------------------------------------------------

def split_document_into_sections(
    document: Document,
) -> list[tuple[str, str]]:
    """
    Split a Markdown document using level-2 headings.

    Example:

        ## Duplicate Payments

        Some text...

        ## Failed Payments

        More text...

    becomes:

        [
            ("Duplicate Payments", "Some text..."),
            ("Failed Payments", "More text...")
        ]
    """

    sections: list[tuple[str, str]] = []

    current_section = "Introduction"
    current_lines: list[str] = []

    def save_section() -> None:
        content = "\n".join(
            current_lines
        ).strip()

        if content:
            sections.append(
                (
                    current_section,
                    content,
                )
            )

    for line in document.content.splitlines():

        stripped = line.strip()

        # Ignore document title.
        if stripped.startswith("# "):
            continue

        # Start a new semantic section.
        if stripped.startswith("## "):
            save_section()

            current_lines.clear()

            current_section = (
                stripped[3:].strip()
            )

            continue

        current_lines.append(line)

    # Save final section.
    save_section()

    return sections


# ---------------------------------------------------------
# Fixed-size splitting
# ---------------------------------------------------------

def split_text_with_overlap(
    text: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[str]:
    """
    Split text into word-based chunks with overlap.

    chunk_size:
        Maximum number of words per chunk.

    overlap:
        Number of words repeated between neighboring chunks.

    Example:

        chunk_size = 200
        overlap = 40

        chunk 1 = words 0-199
        chunk 2 = words 160-359
        chunk 3 = words 320-519
    """

    if chunk_size <= 0:
        raise ValueError(
            "chunk_size must be greater than 0"
        )

    if overlap < 0:
        raise ValueError(
            "overlap cannot be negative"
        )

    if overlap >= chunk_size:
        raise ValueError(
            "overlap must be smaller than chunk_size"
        )

    words = text.split()

    if not words:
        return []

    # If the text is already small enough,
    # keep it as one chunk.
    if len(words) <= chunk_size:
        return [text.strip()]

    chunks: list[str] = []

    start = 0

    step = chunk_size - overlap

    while start < len(words):

        end = start + chunk_size

        chunk_words = words[start:end]

        chunk = " ".join(chunk_words).strip()

        if chunk:
            chunks.append(chunk)

        start += step

    return chunks


# ---------------------------------------------------------
# Hybrid chunking
# ---------------------------------------------------------

def chunk_document(
    document: Document,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[DocumentChunk]:
    """
    Chunk a document using a hybrid strategy.

    Step 1:
        Split using Markdown headings.

    Step 2:
        If a section is larger than chunk_size,
        split that section using overlapping
        word-based windows.

    This preserves semantic structure while also
    preventing very large chunks.
    """

    chunks: list[DocumentChunk] = []

    sections = split_document_into_sections(
        document
    )

    chunk_number = 0

    for section_name, section_content in sections:

        section_chunks = split_text_with_overlap(
            text=section_content,
            chunk_size=chunk_size,
            overlap=overlap,
        )

        for section_chunk in section_chunks:

            chunk_number += 1

            chunk = DocumentChunk(
                chunk_id=(
                    f"{document.document_id}-"
                    f"{chunk_number}"
                ),
                document_id=document.document_id,
                title=document.title,
                section=section_name,
                content=section_chunk,
                source=document.source,
            )

            chunks.append(chunk)

    return chunks


# ---------------------------------------------------------
# Load all policy chunks
# ---------------------------------------------------------

def load_policy_chunks(
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[DocumentChunk]:
    """
    Load all policies and convert them into
    searchable chunks.
    """

    documents = load_policy_documents()

    chunks: list[DocumentChunk] = []

    for document in documents:

        document_chunks = chunk_document(
            document=document,
            chunk_size=chunk_size,
            overlap=overlap,
        )

        chunks.extend(document_chunks)

    return chunks