#!/usr/bin/env python3
"""Online, non-blocking, WAL-safe SQLite database backup procedure for STEM RADAR.

Uses SQLite's native online backup API (sqlite3.Connection.backup) to safely
create a consistent snapshot of the database while the Telegram bot and FastAPI
services continue reading and writing concurrently.
"""

import argparse
import gzip
import logging
import shutil
import sqlite3
import sys
import time
from pathlib import Path

# Ensure repository root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

try:
    from app.config import settings

    DEFAULT_DB_PATH = Path(settings.database_url.replace("sqlite+aiosqlite:///", ""))
except Exception:
    DEFAULT_DB_PATH = BASE_DIR / "data" / "stem_radar.db"

DEFAULT_BACKUP_DIR = BASE_DIR / "data" / "backups"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("stem_radar.backup")


def perform_online_backup(
    db_path: Path,
    backup_dir: Path,
    compress: bool = True,
    keep_count: int = 7,
) -> Path:
    """Execute a consistent, WAL-safe online backup of the SQLite database.

    Args:
        db_path: Absolute or relative path to the live SQLite database file.
        backup_dir: Directory where backup snapshots will be stored.
        compress: Whether to gzip-compress the resulting backup file.
        keep_count: Maximum number of recent backups to retain.

    Returns:
        Path to the finalized backup file.
    """
    if not db_path.exists():
        raise FileNotFoundError(f"Source database not found at: {db_path}")

    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    temp_backup_path = backup_dir / f"stem_radar_backup_{timestamp}.db"

    logger.info("Initiating online backup for '%s'...", db_path)
    start_time = time.time()

    # Step 1: Execute page-by-page online backup using SQLite native backup API
    src_conn = sqlite3.connect(str(db_path), timeout=10.0)
    dest_conn = sqlite3.connect(str(temp_backup_path))

    try:
        # SQLite's backup() safely reads both .db and .db-wal transaction logs
        with dest_conn:
            src_conn.backup(dest_conn, pages=250, sleep=0.01)
        logger.info("Page copy complete. Verifying integrity of backup snapshot...")

        # Step 2: Verify integrity check on destination snapshot
        cursor = dest_conn.cursor()
        cursor.execute("PRAGMA integrity_check")
        status = cursor.fetchone()
        if not status or status[0] != "ok":
            raise RuntimeError(f"Integrity check failed on backup snapshot: {status}")
        cursor.close()
        logger.info("Integrity check passed ('ok').")
    finally:
        dest_conn.close()
        src_conn.close()

    final_path = temp_backup_path

    # Step 3: Optional gzip compression
    if compress:
        compressed_path = backup_dir / f"stem_radar_backup_{timestamp}.db.gz"
        logger.info("Compressing backup snapshot with gzip...")
        with open(temp_backup_path, "rb") as f_in, gzip.open(compressed_path, "wb", compresslevel=6) as f_out:
            shutil.copyfileobj(f_in, f_out)
        temp_backup_path.unlink()  # Remove uncompressed temp copy
        final_path = compressed_path

    elapsed = time.time() - start_time
    src_size_mb = db_path.stat().st_size / (1024 * 1024)
    dest_size_mb = final_path.stat().st_size / (1024 * 1024)

    logger.info(
        "Backup successfully finalized in %.2fs. Source: %.2f MB -> Backup: %.2f MB ('%s')",
        elapsed,
        src_size_mb,
        dest_size_mb,
        final_path.name,
    )

    # Step 4: Rotate backups (prune older than keep_count)
    rotate_backups(backup_dir, keep_count)

    return final_path


def rotate_backups(backup_dir: Path, keep_count: int) -> None:
    """Retain only the most recent keep_count backups, pruning older snapshots."""
    if keep_count <= 0:
        return

    backups = sorted(
        [p for p in backup_dir.glob("stem_radar_backup_*") if p.is_file()],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    if len(backups) > keep_count:
        to_delete = backups[keep_count:]
        for old_backup in to_delete:
            try:
                old_backup.unlink()
                logger.info("Pruned old backup snapshot: '%s'", old_backup.name)
            except Exception as exc:
                logger.warning("Failed to delete old backup '%s': %s", old_backup.name, exc)


def main() -> int:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description="WAL-safe online SQLite backup procedure for STEM RADAR.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=DEFAULT_DB_PATH,
        help="Path to live database file.",
    )
    parser.add_argument(
        "--backup-dir",
        type=Path,
        default=DEFAULT_BACKUP_DIR,
        help="Directory to store backup files.",
    )
    parser.add_argument(
        "--keep",
        type=int,
        default=7,
        help="Number of recent backups to keep.",
    )
    parser.add_argument(
        "--no-compress",
        action="store_true",
        help="Disable gzip compression.",
    )

    args = parser.parse_args()

    try:
        perform_online_backup(
            db_path=args.db_path,
            backup_dir=args.backup_dir,
            compress=not args.no_compress,
            keep_count=args.keep,
        )
        return 0
    except Exception as exc:
        logger.error("Database backup operation failed: %s", exc, exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
