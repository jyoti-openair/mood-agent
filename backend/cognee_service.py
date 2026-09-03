import os
import json
import urllib.parse
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
import cognee
from cognee.modules.search.types import SearchType
from backend.config import PDF_DIR


# ---------------------------------------------------------
# Environment
# ---------------------------------------------------------

load_dotenv(
    Path(__file__).resolve().parent.parent / ".env",
    override=True,
)


# ---------------------------------------------------------
# Paths
# ---------------------------------------------------------

PDF_DIR = (
    Path(__file__).resolve().parent.parent
    / "pdfs"
)


# ---------------------------------------------------------
# Gemini / OpenAI-compatible client
# ---------------------------------------------------------

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client

    if _client is None:
        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not set"
            )

        _client = OpenAI(
            api_key=api_key,
            base_url=(
                "https://generativelanguage.googleapis.com/"
                "v1beta/openai/"
            ),
        )

    return _client


# ---------------------------------------------------------
# System instruction
# ---------------------------------------------------------

SYSTEM_INSTRUCTION = """
You are a warm, compassionate guide helping people
navigate difficult emotions.

You are given:

1. The user's mood
2. Material retrieved from books and other provided sources,
   including summaries and raw excerpts from one or more authors.

Your tasks:

1. "response":
   Write a warm, compassionate 2-3 paragraph response
   addressed directly to the user.

2. Deeply analyze the provided material and explain
   possible reasons why humans may experience this mood.
   Draw meaningful connections across the retrieved
   sources when relevant.

3. Explain why the user might be experiencing this mood,
   based strictly on the provided material.

4. Provide practical, gentle guidance for navigating
   the mood, grounded in the provided material.

5. Do not attribute ideas to any specific author unless
   the provided material clearly identifies the author
   and attribution is relevant.

6. Do not introduce information, psychological theories,
   diagnoses, or advice that is not supported by the
   provided material.

7. Do not mention the retrieval process, PDFs, documents,
   knowledge base, or source material in the user's response.

8. Treat the retrieved material as perspectives and teachings
   to help the user reflect. Do not present them as medical,
   psychological, or scientific facts unless the provided
   material explicitly establishes them as such.

9. "image_prompt":
   Create a sleek, minimalist, use nature

- Visual Style: stick art with glows based on the solution of the mood, use water colors and paint effects
Use only the provided retrieved material for the written
response. The image_prompt does not need source material,
it should be derived from the tone of your response.

Return JSON when possible:

{
    "response": "...",
    "image_prompt": "..."
}
"""


# ---------------------------------------------------------
# Generate teaching and prompt
# ---------------------------------------------------------

def generate_teaching_and_prompt(
    mood_label: str,
    user_context: str,
    raw_excerpts: list[str],
    graph_answers: list[str] = None,
) -> dict:

    print("\n========== REFLECT START ==========")
    print("Mood:", mood_label)
    print("User context length:", len(user_context or ""))
    print("Graph answers:", len(graph_answers or []))
    print("Raw excerpts:", len(raw_excerpts or []))

    client = _get_client()

    # IMPORTANT:
    # This must be exactly the Gemini model name.
    model = os.getenv(
        "GEMINI_MODEL",
        "gemini-3.6-flash",
    )

    print("DEBUG: Gemini model =", repr(model))

    retrieved_material = (
        "SUMMARIES:\n"
        + "\n---\n".join(
            graph_answers or ["(none)"]
        )
    )

    retrieved_material += (
        "\n\nRAW EXCERPTS FROM BOOKS:\n"
        + "\n---\n".join(
            raw_excerpts or ["(none)"]
        )
    )

    prompt = (
        f"User mood: {mood_label}\n"
        f"User context: {user_context}\n\n"
        f"{retrieved_material}"
    )

    print(
        "DEBUG: Prompt length =",
        len(prompt),
    )

    # -----------------------------------------------------
    # Gemini call
    # -----------------------------------------------------

    print("DEBUG: Calling Gemini...")

    try:

        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_INSTRUCTION,
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            temperature=0.7,
        )

        print("DEBUG: Gemini response received")

    except Exception as e:

        print("\n========== GEMINI ERROR ==========")
        print("Exception type:", type(e).__name__)
        print("Exception:", repr(e))
        print("Model:", repr(model))
        print(
            "API key configured:",
            bool(os.getenv("GEMINI_API_KEY")),
        )
        print("==================================\n")

        raise

    # -----------------------------------------------------
    # Parse response
    # -----------------------------------------------------

    try:

        raw_content = (
            response.choices[0]
            .message
            .content
            .strip()
        )

        print(
            "DEBUG: Gemini response length =",
            len(raw_content),
        )

        # Remove markdown code fences if Gemini returns them
        if raw_content.startswith("```"):

            raw_content = (
                raw_content
                .split("```")[1]
            )

            if raw_content.startswith("json"):
                raw_content = raw_content[4:]

        parsed = json.loads(
            raw_content.strip()
        )

        print("DEBUG: JSON parsed successfully")
        print("========== REFLECT SUCCESS ==========\n")

        return parsed

    except Exception as e:

        print(
            "DEBUG: Gemini did not return valid JSON:",
            repr(e),
        )

        # Fallback to plain text response
        return {
            "response": response.choices[0]
            .message
            .content,
            "image_prompt": (
                "Flat cartoon illustration, minimal color "
                "palette, single splash of color accent, "
                "a small figure resting peacefully in warm "
                f"light, representing calm after {mood_label}"
            ),
        }


# ---------------------------------------------------------
# Generate mood image
# ---------------------------------------------------------

def generate_mood_image(
    image_prompt: str,
) -> str:

    """
    Generates an image URL using Pollinations.ai.

    Always reinforces the flat-cartoon / minimal-color /
    single-splash-of-color style, even if the upstream
    image_prompt from Gemini forgot to mention it, so the
    visuals stay consistent across the whole app.
    """

    if not image_prompt:

        image_prompt = (
            "A small figure resting peacefully by a "
            "glowing plant, calm and grounded"
        )

    style_suffix = (
        ", flat 2D cartoon illustration, simple clean "
        "line art, minimal shading, mostly a single "
        "muted neutral color palette with one small "
        "splash of bright accent color, no text, "
        "no realistic faces, friendly and relatable"
    )

    full_prompt = f"{image_prompt.strip().rstrip('.')}{style_suffix}"

    encoded_prompt = urllib.parse.quote(
        full_prompt
    )

    return (
        "https://image.pollinations.ai/prompt/"
        f"{encoded_prompt}"
        "?width=1024"
        "&height=1024"
        "&nologo=true"
    )


# ---------------------------------------------------------
# Bridge mood to teaching
# ---------------------------------------------------------

def bridge_mood_to_teaching(
    mood_label: str,
    user_context: str,
    graph_answers: list[str],
    raw_excerpts: list[str],
) -> str:

    print("\n========== BRIDGE START ==========")

    client = _get_client()

    model = os.getenv(
        "GEMINI_MODEL",
        "gemini-3.6-flash",
    )

    print(
        "DEBUG: Bridge Gemini model =",
        repr(model),
    )

    retrieved_material = (
        "REASONED SUMMARIES FROM THE KNOWLEDGE GRAPH:\n"
        + "\n---\n".join(
            graph_answers or ["(none found)"]
        )
    )

    retrieved_material += (
        "\n\nRAW EXCERPTS FROM THE PDFS "
        "(may contain stories/examples):\n"
    )

    retrieved_material += "\n---\n".join(
        raw_excerpts or ["(none found)"]
    )

    prompt = f"""
User's mood: {mood_label}

User's own words about what's going on:
{user_context or "(nothing typed)"}

{retrieved_material}

Write the response now.
"""

    print(
        "DEBUG: Bridge prompt length =",
        len(prompt),
    )

    print("DEBUG: Calling Gemini from bridge...")

    try:

        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_INSTRUCTION,
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            temperature=0.8,
            max_tokens=700,
        )

        print(
            "DEBUG: Bridge Gemini response received"
        )

    except Exception as e:

        print("\n========== BRIDGE GEMINI ERROR ==========")
        print(
            "Exception type:",
            type(e).__name__,
        )
        print(
            "Exception:",
            repr(e),
        )
        print(
            "Model:",
            repr(model),
        )
        print(
            "API key configured:",
            bool(
                os.getenv(
                    "GEMINI_API_KEY"
                )
            ),
        )
        print(
            "=========================================\n"
        )

        raise

    return response.choices[0].message.content


# ---------------------------------------------------------
# Query Cognee
# ---------------------------------------------------------

async def query_teaching(
    mood: dict | str,
    dataset_name: str = "teachings",
    top_k: int = 5,
) -> dict:
    """
    Query the Cognee knowledge base for teachings relevant to the
    user's current mood.

    Runs two Cognee searches:
      - GRAPH_COMPLETION: a reasoned, synthesized answer that
        draws on entity/relationship connections in the graph
        (used as "graph_answers").
      - CHUNKS: the actual raw text chunks that back that answer,
        pulled straight from the ingested PDFs (used as
        "raw_excerpts").

    NOTE: this function is now async because cognee.search()
    is async. Callers must `await query_teaching(...)`.
    """

    if isinstance(mood, dict):
        mood_label = mood.get("label", "")
    else:
        mood_label = str(mood)

    if not mood_label:
        return {
            "graph_answers": [],
            "raw_excerpts": [],
        }

    query = (
        f"What do the teachings in this knowledge base say about "
        f"experiencing and moving through {mood_label}? "
        "Include any guidance, reframes, or practices mentioned."
    )

    print("\n========== COGNEE QUERY START ==========")
    print("Mood label:", mood_label)
    print("Query:", query)

    graph_answers: list[str] = []
    raw_excerpts: list[str] = []

    # -----------------------------------------------------
    # 1. Reasoned graph completion
    # -----------------------------------------------------
    try:
        graph_results = await cognee.search(
            query_text=query,
            query_type=SearchType.GRAPH_COMPLETION,
            datasets=[dataset_name],
        )

        for item in graph_results or []:
            if isinstance(item, str):
                graph_answers.append(item)
            elif isinstance(item, dict):
                text = (
                    item.get("text")
                    or item.get("answer")
                    or item.get("content")
                )
                if text:
                    graph_answers.append(str(text))
            else:
                graph_answers.append(str(item))

        graph_answers = graph_answers[:top_k]

        print(
            "DEBUG: Cognee graph_answers retrieved =",
            len(graph_answers),
        )

    except Exception as e:
        print("DEBUG: Cognee GRAPH_COMPLETION search failed:", repr(e))

    # -----------------------------------------------------
    # 2. Raw supporting excerpts / chunks
    # -----------------------------------------------------
    try:
        chunk_results = await cognee.search(
            query_text=query,
            query_type=SearchType.CHUNKS,
            datasets=[dataset_name],
        )

        for item in chunk_results or []:
            if isinstance(item, str):
                raw_excerpts.append(item)
            elif isinstance(item, dict):
                text = (
                    item.get("text")
                    or item.get("chunk")
                    or item.get("content")
                )
                if text:
                    raw_excerpts.append(str(text))
            else:
                raw_excerpts.append(str(item))

        raw_excerpts = raw_excerpts[:top_k]

        print(
            "DEBUG: Cognee raw_excerpts retrieved =",
            len(raw_excerpts),
        )

    except Exception as e:
        print("DEBUG: Cognee CHUNKS search failed:", repr(e))

    print("========== COGNEE QUERY END ==========\n")

    return {
        "graph_answers": graph_answers,
        "raw_excerpts": raw_excerpts,
    }


# ---------------------------------------------------------
# Ingest PDF library
# ---------------------------------------------------------

async def ingest_pdf_library(
    dataset_name: str = "teachings",
) -> dict:

    """
    Scans PDF_DIR for PDF files, adds them to Cognee,
    and runs cognify() to extract entity/relationship
    knowledge graphs.
    """

    if not PDF_DIR.exists():

        raise FileNotFoundError(
            f"PDF directory not found at: {PDF_DIR}"
        )

    pdf_files = list(
        PDF_DIR.glob("*.pdf")
    )

    if not pdf_files:

        raise FileNotFoundError(
            "No PDF files found inside: "
            f"{PDF_DIR}"
        )

    file_paths = [
        str(pdf)
        for pdf in pdf_files
    ]

    print(
        "Ingesting",
        len(file_paths),
        "PDF files..."
    )

    # Add PDFs
    await cognee.add(
        file_paths,
        dataset_name=dataset_name,
    )

    # Build knowledge graph and vector indices
    await cognee.cognify(
        dataset_name=dataset_name,
    )

    return {
        "dataset": dataset_name,
        "files_ingested": len(file_paths),
        "paths": file_paths,
    }

async def ingest_pdf_library(dataset_name: str = "teachings"):
    target_dir = PDF_DIR.resolve()

    # Match all PDF files in the target directory
    pdf_files = list(target_dir.glob("*.pdf"))

    if not pdf_files:
        return f"No PDFs found in {target_dir} to ingest."

    # Convert absolute Path objects to string paths
    file_paths = [str(f) for f in pdf_files]

    # 1. Add PDF files to Cognee
    await cognee.add(file_paths, dataset_name=dataset_name)

    # 2. Cognify (build graph)
    await cognee.cognify(dataset_name=dataset_name)

    return f"Successfully ingested {len(file_paths)} PDF file(s) into dataset '{dataset_name}'."