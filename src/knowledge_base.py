import os

from src.document_engine import (
    extract_pdf_text,
    split_text
)


def build_knowledge_base(
    uploaded_files
):

    knowledge = []


    for file in uploaded_files:

        file_name = file.name

        extension = (
            os.path.splitext(
                file_name
            )[1]
            .lower()
        )


        if extension != ".pdf":

            continue


        temp_path = os.path.join(
            "temp",
            file_name
        )


        os.makedirs(
            "temp",
            exist_ok=True
        )


        with open(
            temp_path,
            "wb"
        ) as output:

            output.write(
                file.getbuffer()
            )


        text = extract_pdf_text(
            temp_path
        )


        chunks = split_text(
            text
        )


        for index, chunk in enumerate(
            chunks
        ):

            knowledge.append(
                {
                    "source": file_name,
                    "chunk_id": index,
                    "text": chunk
                }
            )


    return knowledge