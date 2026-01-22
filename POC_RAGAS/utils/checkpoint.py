"""Checkpoint management for RAGAS evaluation runs."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from POC_RAGAS.config import CONFIG


def get_checkpoint_path(run_id: str) -> Path:
    """Generate checkpoint file path with run_id."""
    CONFIG.checkpoint_dir.mkdir(parents=True, exist_ok=True)
    return CONFIG.checkpoint_dir / f"checkpoint_{run_id}.json"


def save_checkpoint(
    run_id: str,
    config: Dict[str, Any],
    samples: List[Dict[str, Any]],
    failed: List[Dict[str, Any]],
    total_questions: int,
    completed_questions: int,
) -> Path:
    """Save current progress to checkpoint file."""
    checkpoint_path = get_checkpoint_path(run_id)
    
    checkpoint_data = {
        "run_id": run_id,
        "timestamp": datetime.utcnow().isoformat(),
        "config": config,
        "progress": {
            "total_questions": total_questions,
            "completed_questions": completed_questions,
            "failed_questions": len(failed),
            "last_checkpoint": datetime.utcnow().isoformat(),
        },
        "samples": samples,
        "failed": failed,
    }
    
    checkpoint_path.write_text(json.dumps(checkpoint_data, indent=2))
    return checkpoint_path


def find_all_checkpoints() -> List[Dict[str, Any]]:
    """Find all checkpoint files and return their metadata."""
    if not CONFIG.checkpoint_dir.exists():
        return []
    
    checkpoints = []
    for checkpoint_file in CONFIG.checkpoint_dir.glob("checkpoint_*.json"):
        try:
            data = json.loads(checkpoint_file.read_text())
            checkpoints.append({
                "path": checkpoint_file,
                "run_id": data.get("run_id", ""),
                "timestamp": data.get("timestamp", ""),
                "completed_questions": data.get("progress", {}).get("completed_questions", 0),
                "data": data,
            })
        except (json.JSONDecodeError, KeyError):
            continue
    
    return checkpoints


def load_latest_checkpoint() -> Optional[Dict[str, Any]]:
    """
    Automatically find and load the checkpoint with the most progress.
    
    Returns:
        Checkpoint data dict if found, None otherwise.
    """
    checkpoints = find_all_checkpoints()
    if not checkpoints:
        return None
    
    # Find checkpoint with highest completed_questions count
    best_checkpoint = max(
        checkpoints,
        key=lambda c: (
            c["completed_questions"],  # Primary: most progress
            c["timestamp"],  # Secondary: most recent if tied
        ),
    )
    
    return best_checkpoint["data"]


def load_checkpoint_from_path(checkpoint_path: Path) -> Optional[Dict[str, Any]]:
    """
    Load checkpoint from a specific file path.
    
    Args:
        checkpoint_path: Path to checkpoint file (can be relative or absolute).
    
    Returns:
        Checkpoint data dict if found and valid, None otherwise.
    """
    # Handle relative paths - check in checkpoint_dir first, then try as-is
    if not checkpoint_path.is_absolute():
        # Try in checkpoint directory
        checkpoint_file = CONFIG.checkpoint_dir / checkpoint_path
        if not checkpoint_file.exists():
            # Try as absolute path from checkpoint_dir
            checkpoint_file = checkpoint_path
    else:
        checkpoint_file = checkpoint_path
    
    if not checkpoint_file.exists():
        return None
    
    try:
        data = json.loads(checkpoint_file.read_text())
        return data
    except (json.JSONDecodeError, IOError):
        return None


def should_checkpoint(completed_count: int, interval: int = None) -> bool:
    """Determine if checkpoint should be saved (every N questions)."""
    if interval is None:
        interval = CONFIG.checkpoint_interval
    return completed_count > 0 and completed_count % interval == 0
