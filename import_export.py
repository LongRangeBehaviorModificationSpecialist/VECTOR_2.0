#!/usr/bin/env python3

"""
export_import.py — Database export and import functionality.

Export: Saves all tables to CSV files and file BLOBs to disk.
Import: Restores tables from CSV files and file BLOBs from disk.
"""

import csv
import os
import json
from pathlib import Path
from datetime import datetime
from typing import Optional

from nicegui import ui

from models import get_session


# ─── MODEL REGISTRY ───
# [Add or remove tables here as your app grows]
def get_exportable_models():
    """Returns a list of (model_class, model_name) tuples for CSV export."""
    from models import Cases, Agents, Rooms, Evidence, Persons, Notes

    return [
        (Cases, "cases"),
        (Agents, "agents"),
        (Rooms, "rooms"),
        (Evidence, "evidence"),
        (Persons, "persons"),
        (Notes, "notes"),
    ]


def get_all_models():
    """Returns ALL models including UploadedFiles for import."""
    from models import Cases, Agents, Rooms, Evidence, Persons, Notes, UploadedFiles

    return {
        "cases": Cases,
        "agents": Agents,
        "rooms": Rooms,
        "evidence": Evidence,
        "persons": Persons,
        "notes": Notes,
        "uploaded_files": UploadedFiles,
    }


# ─── HELPER FUNCTIONS ───

def get_case_info_for_folder_name() -> str:
    """Builds the folder name from the active case info."""
    from models import Cases

    with get_session() as session:
        case = session.query(Cases).first()
        if not case:
            ui.notify("No case found. Cannot export.", type="negative")
            return ""

        case_number = (
            (case.case_number or "UNKNOWN")
            .replace("/", "_")
            .replace("\\", "_")
            .replace(" ", "_")
        )
        begin_dt = case.case_date_time_begin or "UNKNOWN"

        # Format the datetime
        if hasattr(begin_dt, "strftime"):
            dt_str = begin_dt.strftime("%Y%m%d_%H%M%S")
        else:
            # It's a string — sanitize it
            dt_str = (
                str(begin_dt)
                .replace(":", "")
                .replace(" ", "_")
                .replace("/", "")
            )

        return f"{case_number}_{dt_str}_saved_results"


def get_column_names(model_class) -> list:
    """Extracts column names from a SQLAlchemy model class."""
    return [col.name for col in model_class.__table__.columns]


def serialize_value(value) -> str:
    """Converts a database value to a CSV-safe string."""
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, bytes):
        # Skip binary data in CSV — handled separately
        return "[BINARY_DATA]"
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def deserialize_value(value: str, column):
    """Converts a CSV string back to the appropriate Python type."""
    from sqlalchemy import Boolean, DateTime, Integer, Float

    if value == "" or value is None:
        return None

    col_type = column.type

    if isinstance(col_type, Boolean):
        return value.lower() in ("true", "1", "yes", "t")
    elif isinstance(col_type, Integer):
        try:
            return int(value)
        except ValueError:
            return None
    elif isinstance(col_type, Float):
        try:
            return float(value)
        except ValueError:
            return None
    elif isinstance(col_type, DateTime):
        try:
            return datetime.fromisoformat(value)
        except (ValueError, TypeError):
            return None
    else:
        return value


# ─── EXPORT FUNCTION ───

def export_database():
    """Exports all database tables to CSV files and file BLOBs to disk.

    Saves to ~/case-number_datetime_saved_results/
    """
    from models import UploadedFiles

    # ─── Build folder name ───
    folder_name = get_case_info_for_folder_name()
    if not folder_name:
        return

    # ─── Create export directory ───
    home_dir = Path.home()
    export_dir = home_dir / folder_name
    files_dir = export_dir / "files"

    try:
        export_dir.mkdir(parents=True, exist_ok=True)
        files_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        ui.notify(
            f"Error creating export directory: {e}",
            type="negative",
            timeout=5000,
            position="center",
            close_button="OK",
        )
        return

    # ─── Export each table to CSV ───
    exported_tables = {}
    total_records = 0

    for model_class, table_name in get_exportable_models():
        columns = get_column_names(model_class)
        csv_path = export_dir / f"{table_name}.csv"

        try:
            with get_session() as session:
                records = session.query(model_class).all()

                with open(csv_path, "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow(columns)  # Header row

                    for record in records:
                        row = (
                            [
                                serialize_value(getattr(record, col))
                                for col in columns
                            ]
                        )
                        writer.writerow(row)

                count = len(records)
                total_records += count
                exported_tables[table_name] = count

        except Exception as e:
            ui.notify(
                f"Error exporting {table_name}: {e}", type="negative", timeout=5000
            )
            return

    # ─── Export uploaded files ───
    files_list = []
    num_files = 0
    try:
        with get_session() as session:
            uploaded_files = session.query(UploadedFiles).all()

            for uf in uploaded_files:
                if uf.file_data:
                    # Sanitize filename
                    safe_name = uf.file_name or f"file_{uf.id}"
                    safe_name = safe_name.replace("/", "_").replace("\\", "_")
                    file_path = files_dir / safe_name

                    with open(file_path, "wb") as f:
                        f.write(uf.file_data)

                    files_list.append(
                        {
                            "file_name": safe_name,
                            "file_size": uf.file_size or len(uf.file_data),
                        }
                    )

                    num_files += 1

    except Exception as e:
        ui.notify(f"Error exporting files: {e}", type="warning", timeout=5000)

    # ─── Write a manifest file ───
    manifest = {
        "export_date": datetime.now().isoformat(),
        "case_folder": folder_name,
        "tables": [
            {
                "name": table_name,
                "records": count
            }
            for table_name, count in exported_tables.items()
        ],
        "total_records": total_records,
        "files_exported": files_list,
        "export_path": str(export_dir),
    }

    manifest_path = export_dir / "export_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=4)

    # ─── Success notification ───
    ui.notify(
        f"Export complete!\n"
        f"Tables: {', '.join(exported_tables)}\n"
        f"Files: {num_files}\n"
        f"Saved to: {export_dir}",
        type="positive",
        timeout=0,
        close_button="OK",
    )

    # Also show in terminal
    print(f"\n{'='*60}")
    print(f"  EXPORT COMPLETE")
    print(f"  Location: {export_dir}")
    print(f"  Tables: {exported_tables}")
    print(f"  Total records: {total_records}")
    print(f"  Files exported: {num_files}")
    print(f"{'='*60}\n")


# ─── IMPORT FUNCTION ───

def import_database(import_dir: str):
    """
    Imports database tables from CSV files and file BLOBs from disk.
    Clears existing data before importing.
    """
    import_dir = Path(import_dir)

    if not import_dir.exists():
        ui.notify("Import directory not found.", type="negative")
        return

    # ─── Check for manifest ───
    manifest_path = import_dir / "export_manifest.json"
    if manifest_path.exists():
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        print(f"Importing from export dated: {manifest.get('export_date', 'unknown')}")
    else:
        manifest = {}

    # ─── Verify CSV files exist ───
    models = get_all_models()
    found_tables = []

    for table_name, model_class in models.items():
        csv_path = import_dir / f"{table_name}.csv"
        if csv_path.exists():
            found_tables.append((table_name, model_class, csv_path))

    if not found_tables:
        ui.notify("No CSV files found in the selected directory.", type="negative")
        return

    # ─── Import each table ───
    imported_tables = []
    total_records = 0

    for table_name, model_class, csv_path in found_tables:
        columns = get_column_names(model_class)
        column_objects = {col.name: col for col in model_class.__table__.columns}

        try:
            with get_session() as session:
                # Clear existing data
                session.query(model_class).delete()

                with open(csv_path, "r", newline="", encoding="utf-8") as f:
                    reader = csv.DictReader(f)

                    for row in reader:
                        record_data = {}
                        for col_name in columns:
                            if col_name in row:
                                raw_value = row[col_name]
                                if raw_value == "[BINARY_DATA]":
                                    continue  # Skip binary columns
                                record_data[col_name] = deserialize_value(
                                    raw_value, column_objects[col_name]
                                )

                        # Create new record (let autoincrement handle ID)
                        if "id" in record_data:
                            del record_data["id"]

                        new_record = model_class(**record_data)
                        session.add(new_record)

            # Count imported records
            with get_session() as session:
                count = session.query(model_class).count()

            imported_tables.append(f"{table_name} ({count})")
            total_records += count

        except Exception as e:
            ui.notify(
                f"Error importing {table_name}: {e}",
                type="negative",
                timeout=5000,
            )
            return

    # ─── Import files ───
    from models import UploadedFiles

    files_dir = import_dir / "files"
    files_imported = 0

    if files_dir.exists():
        try:
            with get_session() as session:
                session.query(UploadedFiles).delete()

                for file_path in files_dir.iterdir():
                    if file_path.is_file():
                        with open(file_path, "rb") as f:
                            file_data = f.read()

                        new_file = UploadedFiles(
                            file_name=file_path.name,
                            file_data=file_data,
                            file_size=len(file_data),
                            file_type="application/octet-stream",
                            uploaded_by="import",
                        )
                        session.add(new_file)
                        files_imported += 1

        except Exception as e:
            ui.notify(f"Error importing files: {e}", type="warning", timeout=5000)

    # ─── Success notification ───
    ui.notify(
        f"Import complete!\n"
        f"Tables: {', '.join(imported_tables)}\n"
        f"Files: {files_imported}\n"
        f"Total records: {total_records}",
        type="positive",
        timeout=0,
        close_button="OK",
    )

    print(f"\n{'='*60}")
    print(f"  IMPORT COMPLETE")
    print(f"  Tables: {imported_tables}")
    print(f"  Total records: {total_records}")
    print(f"  Files imported: {files_imported}")
    print(f"{'='*60}\n")
