from pypdf import PdfReader


def extract_pdf_text(file_path):

    try:

        reader = PdfReader(
            file_path
        )

        pages = []

        for page in reader.pages:

            text = page.extract_text()

            if text:

                pages.append(text)

        return "\n\n".join(pages)

    except Exception as e:

        return f"PDF extraction error: {e}"


def split_text(
    text,
    chunk_size=1500,
    overlap=200
):

    if not text:

        return []


    chunks = []

    start = 0

    text_length = len(text)


    while start < text_length:

        end = start + chunk_size

        chunk = text[start:end]

        chunks.append(chunk)

        start = end - overlap


    return chunks