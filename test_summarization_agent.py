"""
Local Test Script for Summarization Agent

Tests the summarization agent locally using existing documents from Databricks.
Mimics the Streamlit app flow: fetch PDFs → select one → run agent → display results
"""

import sys
from databricks import sql
import os
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from agents.summarization.graph import run_summarization

# Load environment variables
load_dotenv()

# Databricks configuration
DATABRICKS_HOST = os.getenv("DATABRICKS_HOST").replace("https://", "")
DATABRICKS_TOKEN = os.getenv("DATABRICKS_TOKEN")
DATABRICKS_WAREHOUSE_ID = os.getenv("SQL_WAREHOUSE_ID")
CATALOG_NAME = "heineken_test_workspace"
SCHEMA_NAME = "nextlevel-rag"


def query_pdf_registry(limit=20):
    """
    Query pdf_registry table for completed PDFs (same as Streamlit app)

    Returns:
        list: List of PDF dicts
    """
    try:
        with sql.connect(
            server_hostname=DATABRICKS_HOST,
            http_path=f"/sql/1.0/warehouses/{DATABRICKS_WAREHOUSE_ID}",
            access_token=DATABRICKS_TOKEN
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute(f"""
                    SELECT
                        pdf_id,
                        pdf_name,
                        processing_status,
                        upload_date,
                        processed_date
                    FROM {CATALOG_NAME}.`{SCHEMA_NAME}`.pdf_registery
                    WHERE processing_status = 'completed'
                    ORDER BY upload_date DESC
                    LIMIT {limit}
                """)

                columns = [desc[0] for desc in cursor.description]
                results = []

                for row in cursor.fetchall():
                    results.append(dict(zip(columns, row)))

                return results

    except Exception as e:
        print(f"Error querying PDFs: {e}")
        return []


def load_chunks_for_pdf(pdf_id):
    """
    Load chunks from chunks_embedded table for a specific PDF

    Args:
        pdf_id: PDF identifier

    Returns:
        list: List of chunk dicts [{chunk_id, text, page_number}, ...]
    """
    try:
        with sql.connect(
            server_hostname=DATABRICKS_HOST,
            http_path=f"/sql/1.0/warehouses/{DATABRICKS_WAREHOUSE_ID}",
            access_token=DATABRICKS_TOKEN
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute(f"""
                    SELECT
                        chunk_id,
                        text,
                        page_number,
                        chunk_index
                    FROM {CATALOG_NAME}.`{SCHEMA_NAME}`.chunks_embedded
                    WHERE pdf_id = '{pdf_id}'
                    ORDER BY page_number, chunk_index
                """)

                chunks = []
                for row in cursor.fetchall():
                    chunks.append({
                        "chunk_id": row[0],
                        "text": row[1],
                        "page_number": row[2]
                    })

                return chunks

    except Exception as e:
        print(f"Error loading chunks: {e}")
        return []


def main():
    """Main test function"""

    print("=" * 80)
    print("SUMMARIZATION AGENT - LOCAL TEST")
    print("=" * 80)

    # Step 1: Fetch completed PDFs
    print("\nFetching completed PDFs from Databricks...")
    pdfs = query_pdf_registry(limit=10)

    if not pdfs:
        print("No completed PDFs found. Upload and process a PDF first.")
        return

    print(f"Found {len(pdfs)} completed PDFs:\n")

    # Display PDFs
    for i, pdf in enumerate(pdfs, 1):
        print(f"{i}. {pdf['pdf_name']}")
        print(f"   ID: {pdf['pdf_id']}")
        print(f"   Uploaded: {pdf['upload_date']}")
        print()

    # Step 2: Select a PDF (auto-select first one for testing)
    selection = 0  # Auto-select first PDF
    selected_pdf = pdfs[selection]

    print(f"\nAuto-selected: {selected_pdf['pdf_name']}")
    print(f"   PDF ID: {selected_pdf['pdf_id']}")

    # Step 3: Load chunks
    print(f"\nLoading chunks for PDF...")
    chunks = load_chunks_for_pdf(selected_pdf['pdf_id'])

    if not chunks:
        print("No chunks found for this PDF")
        return

    total_pages = len(set(c["page_number"] for c in chunks))
    print(f"Loaded {len(chunks)} chunks from {total_pages} pages")

    # Step 4: Choose summary type (auto-select technical)
    summary_type = "technical"  # Auto-select technical summary
    print(f"\nSummary type: {summary_type}")

    print(f"\nGenerating {summary_type} summary...")

    # Step 5: Run summarization agent
    print("\n" + "=" * 80)
    print(f"RUNNING SUMMARIZATION AGENT ({summary_type.upper()})")
    print("=" * 80)
    print("This may take a few minutes depending on document size...\n")

    try:
        result = run_summarization(
            pdf_id=selected_pdf['pdf_id'],
            pdf_name=selected_pdf['pdf_name'],
            chunks=chunks,
            summary_type=summary_type,
            total_pages=total_pages,
            total_chunks=len(chunks)
        )

        # Step 6: Display results
        print("\n" + "=" * 80)
        print("SUMMARIZATION COMPLETE")
        print("=" * 80)

        print(f"\nProcessing time: {result['processing_time']:.2f} seconds")
        print(f"Batches processed: {result['current_batch']}")
        print(f"Iterations: {result['iteration']}")
        print(f"Key topics: {', '.join(result['key_topics'])}")

        if result.get('error_message'):
            print(f"\nWarning: {result['error_message']}")

        print("\n" + "=" * 80)
        print("FINAL SUMMARY:")
        print("=" * 80)
        print(result['final_summary'])
        print("=" * 80)

        # Step 7: Save to file (auto-save)
        filename = f"summary_{selected_pdf['pdf_name']}_{summary_type}.txt"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"PDF: {selected_pdf['pdf_name']}\n")
            f.write(f"Type: {summary_type}\n")
            f.write(f"Processing time: {result['processing_time']:.2f}s\n")
            f.write(f"Key topics: {', '.join(result['key_topics'])}\n")
            f.write("\n" + "=" * 80 + "\n")
            f.write(result['final_summary'])

        print(f"\nSaved to: {filename}")

    except Exception as e:
        print(f"\nError running summarization: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
