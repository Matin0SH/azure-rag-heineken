"""
Utility functions for summarization agent.

Includes helpers for saving intermediate results, logging, etc.
"""

import json
import os
from datetime import datetime
from typing import Dict, Any


def save_stage_results(stage_name: str, state: Dict[str, Any], output_folder: str = "outputs/summarization"):
    """
    Save stage results to JSON file for inspection.

    Args:
        stage_name: Name of the stage (e.g., "regroup_pages", "map_extract")
        state: Current state dict
        output_folder: Base output folder (default: outputs/summarization)

    Creates:
        outputs/summarization/{stage_name}_{timestamp}.json
    """

    # Create output folder if doesn't exist
    os.makedirs(output_folder, exist_ok=True)

    # Create filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(output_folder, f"{stage_name}_{timestamp}.json")

    # Prepare data to save (filter out large/unnecessary fields)
    save_data = {
        "stage": stage_name,
        "timestamp": timestamp,
        "pdf_id": state.get("pdf_id"),
        "pdf_name": state.get("pdf_name"),
        "summary_type": state.get("summary_type"),
        "total_pages": state.get("total_pages"),
        "total_chunks": state.get("total_chunks"),
        "total_batches": state.get("total_batches"),
    }

    # Add stage-specific data
    if stage_name == "regroup_pages":
        save_data["pages_count"] = len(state.get("pages", []))
        save_data["sample_pages"] = state.get("pages", [])[:2]  # First 2 pages as sample

    elif stage_name == "create_batches":
        save_data["batches_count"] = len(state.get("batches", []))
        save_data["sample_batches"] = [
            {
                "batch_id": b["batch_id"],
                "pages_count": len(b.get("pages", []))
            }
            for b in state.get("batches", [])[:3]  # First 3 batches
        ]

    elif stage_name == "map_extract":
        extractions = state.get("batch_extractions", [])
        save_data["extractions_count"] = len(extractions)
        save_data["sample_extractions"] = extractions[:2]  # First 2 extractions

    elif stage_name == "reduce_combine":
        save_data["reduce_levels_count"] = len(state.get("reduce_levels", []))
        save_data["reduce_levels_sizes"] = [len(level) for level in state.get("reduce_levels", [])]
        save_data["final_summary_length"] = len(state.get("final_summary", ""))
        save_data["final_summary_preview"] = state.get("final_summary", "")[:500]  # First 500 chars

    elif stage_name == "extract_topics":
        save_data["key_topics"] = state.get("key_topics", [])
        save_data["final_summary_length"] = len(state.get("final_summary", ""))

    # Add processing metadata
    save_data["processing_time"] = state.get("processing_time", 0.0)
    save_data["error_message"] = state.get("error_message")

    # Save to file
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(save_data, f, indent=2, ensure_ascii=False)

    print(f"💾 Saved {stage_name} results to {filename}")

    return filename
