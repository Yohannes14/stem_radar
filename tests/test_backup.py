"""Tests for scripts/backup_db.py: WAL-safe SQLite online backup procedure."""

import gzip
import sqlite3

import pytest

from scripts.backup_db import perform_online_backup, rotate_backups


@pytest.fixture
def sample_sqlite_db(tmp_path):
    """Create a temporary SQLite database with WAL mode and sample records."""
    db_file = tmp_path / "live_test.db"
    conn = sqlite3.connect(str(db_file))
    cursor = conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("CREATE TABLE test_data (id INTEGER PRIMARY KEY, title TEXT)")
    for i in range(10):
        cursor.execute("INSERT INTO test_data (title) VALUES (?)", (f"Item {i}",))
    conn.commit()
    conn.close()
    return db_file


def test_perform_online_backup_compressed(sample_sqlite_db, tmp_path):
    """Verify online backup successfully creates a verified, gzipped snapshot."""
    backup_dir = tmp_path / "backups"

    backup_file = perform_online_backup(
        db_path=sample_sqlite_db,
        backup_dir=backup_dir,
        compress=True,
        keep_count=5,
    )

    assert backup_file.exists()
    assert backup_file.name.endswith(".db.gz")

    # Decompress and verify database contents
    decompressed_path = tmp_path / "decompressed.db"
    with gzip.open(backup_file, "rb") as f_in, open(decompressed_path, "wb") as f_out:
        f_out.write(f_in.read())

    dest_conn = sqlite3.connect(str(decompressed_path))
    cursor = dest_conn.cursor()
    cursor.execute("PRAGMA integrity_check")
    status = cursor.fetchone()
    assert status[0] == "ok"

    cursor.execute("SELECT COUNT(*) FROM test_data")
    count = cursor.fetchone()[0]
    assert count == 10
    dest_conn.close()


def test_perform_online_backup_uncompressed(sample_sqlite_db, tmp_path):
    """Verify online backup with compression disabled produces raw SQLite database."""
    backup_dir = tmp_path / "backups"

    backup_file = perform_online_backup(
        db_path=sample_sqlite_db,
        backup_dir=backup_dir,
        compress=False,
        keep_count=5,
    )

    assert backup_file.exists()
    assert backup_file.name.endswith(".db")
    assert not backup_file.name.endswith(".gz")

    dest_conn = sqlite3.connect(str(backup_file))
    cursor = dest_conn.cursor()
    cursor.execute("PRAGMA integrity_check")
    assert cursor.fetchone()[0] == "ok"
    dest_conn.close()


def test_rotate_backups(tmp_path):
    """Verify rotate_backups prunes old files exceeding keep_count."""
    backup_dir = tmp_path / "rotation_test"
    backup_dir.mkdir(parents=True)

    # Create 5 dummy backup files
    created_files = []
    for i in range(5):
        f = backup_dir / f"stem_radar_backup_20261116_10000{i}.db.gz"
        f.write_text(f"dummy data {i}")
        created_files.append(f)

    # Keep only the 3 most recent
    rotate_backups(backup_dir, keep_count=3)

    remaining = sorted(list(backup_dir.glob("stem_radar_backup_*")))
    assert len(remaining) == 3


def test_backup_nonexistent_source_raises_error(tmp_path):
    """Verify trying to backup non-existent database file raises FileNotFoundError."""
    non_existent = tmp_path / "does_not_exist.db"
    backup_dir = tmp_path / "backups"

    with pytest.raises(FileNotFoundError):
        perform_online_backup(
            db_path=non_existent,
            backup_dir=backup_dir,
            compress=True,
        )
