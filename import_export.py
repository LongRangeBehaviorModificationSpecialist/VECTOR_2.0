#!/usr/bin/env python3

"""
import_export.py — Database export and import functionality.

Import: Restores tables from CSV files and file BLOBs from disk.
Export: Saves all tables to CSV files and file BLOBs to disk.
"""

import csv
from datetime import datetime
import hashlib
import json
from nicegui import ui
from pathlib import Path
import pyzipper
import shutil
import tempfile
from typing import Optional

from models import get_session


# ----- MODEL REGISTRY -----
# [Add or remove tables here as your app grows]
def get_exportable_models() -> list:
    """Returns a list of (model_class, model_name) tuples for CSV export."""
    from models import Cases, Agents, Rooms, Evidence, Persons, Notes

    return [
        (Cases, "cases"),
        (Agents, "agents"),
        (Rooms, "rooms"),
        (Evidence, "evidence"),
        (Persons, "persons"),
        (Notes, "notes")
    ]


def get_all_models() -> dict:
    """Returns ALL models including UploadedFiles for import."""
    from models import Cases, Agents, Rooms, Evidence, Persons, Notes, UploadedFiles

    return {
        "cases": Cases,
        "agents": Agents,
        "rooms": Rooms,
        "evidence": Evidence,
        "persons": Persons,
        "notes": Notes,
        "uploaded_files": UploadedFiles
    }


# ----- HELPER FUNCTIONS -----

def get_case_info_for_folder_name() -> str:
    """Builds the folder name from the active case info."""
    from models import Cases

    with get_session() as session:
        case = session.query(Cases).first()
        if not case:
            ui.notify(
                "No case found. Cannot export data.",
                type="negative",
                timeout=0,
                position="center",
                close_button="OK",
            )
            return ""

        case_number = (
            (case.CASENUMBER or "UNKNOWN")
            .replace("/", "_")
            .replace("\\", "_")
            .replace(" ", "_")
        )

        begin_dt = case.CASEDATETIMEBEGIN or "UNKNOWN"

        # Format the datetime
        if hasattr(begin_dt, "strftime"):
            dt_str = begin_dt.strftime("%Y-%m-%d_%H%M%S")
        else:
            # Sanitize the string
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


def deserialize_value(value: str, column) -> str:
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


# ----- EXPORT FUNCTION -----


def export_database(password: Optional[str] = None) -> None:
    """Exports all database tables to CSV files and file BLOBs to disk.

    Saves to ~/Desktop/<case-number>_<datetime>_saved_results/
    """
    from models import UploadedFiles

    # ----- Build folder name -----
    folder_name = get_case_info_for_folder_name()

    if not folder_name:
        return

    home_dir = Path.home()
    desktop_dir = home_dir / "Desktop"

    # ----- Create temporary dir for export before zipping -----
    export_dir = desktop_dir / folder_name
    files_dir = export_dir / "files"
    zip_path = desktop_dir / f"{folder_name}.zip"

    try:
        export_dir.mkdir(parents=True, exist_ok=True)
        files_dir.mkdir(parents=True, exist_ok=True)
    except OSError as err:
        ui.notify(
            f"Error creating export directory → {err}",
            type="negative",
            timeout=0,
            position="center",
            close_button="OK",
        )
        return

    # ----- Export each table to CSV -----
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

        except Exception as err:
            ui.notify(
                f"Error exporting {table_name} → {err}",
                type="negative",
                timeout=0,
                position="center",
                close_button="OK",
            )
            return

    # ----- Export uploaded files -----
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

                    sha256_hash = hashlib.sha256(uf.file_data).hexdigest()

                    files_list.append(
                        {
                            "file_name": safe_name,
                            "file_size": uf.file_size or len(uf.file_data),
                            "file_hash": sha256_hash
                        }
                    )

                    num_files += 1

    except Exception as err:
        ui.notify(
            f"Error exporting files → {err}",
            type="warning",
            timeout=0,
            position="center",
            close_button="OK",
        )

    # ----- Write a manifest file -----
    manifest = {
        "export_date": datetime.now().isoformat(),
        "case_file": str(zip_path),
        "tables": [
            {"name": table_name, "records": count}
            for table_name, count in exported_tables.items()
        ],
        "total_records": total_records,
        "files": files_list,
        "total_files": num_files,
        "encrypted": password is not None and len(password) > 0,
    }

    manifest_path = export_dir / "export_manifest.json"

    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=4)

    # ----- Create the ZIP file -----
    try:
        if password:
            with pyzipper.AESZipFile(
                zip_path,
                "w",
                compression=pyzipper.ZIP_DEFLATED,
                encryption=pyzipper.WZ_AES
            ) as zf:

                zf.setpassword(password.encode("utf-8"))
                zf.setencryption(pyzipper.WZ_AES, nbits=256)

                # Walk the export directory and add all files
                for file_path in export_dir.rglob("*"):
                    if file_path.is_file():
                        arcname = file_path.relative_to(export_dir)
                        zf.write(file_path, arcname)
        else:
            # ----- Unencrypted ZIP -----
            with pyzipper.AESZipFile(
                zip_path,
                "w",
                compression=pyzipper.ZIP_DEFLATED
            ) as zf:
                for file_path in export_dir.rglob("*"):
                    if file_path.is_file():
                        arcname = file_path.relative_to(export_dir)
                        zf.write(file_path, arcname)

    except Exception as err:
        ui.notify(
            f"Error creating zip file → {err}",
            type="negative",
            timeout=0,
            position="center",
            close_button="OK",
        )
        shutil.rmtree(export_dir, ignore_errors=True)
        return

    # ----- Delete the temporary directory -----
    shutil.rmtree(export_dir, ignore_errors=True)

    enc_text = " (AES-256 encrypted)" if password else ""

    # ----- Success notification -----
    ui.notify(
        f"Export complete!{enc_text}\n"
        f"Tables: {', '.join(f'{n} ({c})' for n, c in exported_tables.items())}\n"
        f"Files: {num_files}\n"
        f"Saved to: {zip_path}",
        timeout=0,
        position="bottom",
        close_button="OK",
    )

    # Also show in terminal
    print(f"\n{'='*60}")
    print(f"  EXPORT COMPLETE")
    print(f"  Location: {zip_path}")
    print(f"  Tables: {exported_tables}")
    print(f"  Total records: {total_records}")
    print(f"  Files exported: {num_files}")
    print(f"{'='*60}\n")


# ----- IMPORT FUNCTION -----


def import_database(zip_path: str, password: Optional[str] = None) -> None:
    """Imports database tables from a .zip file.

    If the zip is encrypted, decrypts it with the provided password.

    Clears existing data before importing.
    """

    zip_file = Path(zip_path)

    if not zip_file.exists():
        ui.notify(
            "ZIP file not found.",
            type="negative",
            timeout=0,
            position="center",
            close_button="OK",
        )
        return

    if not zip_file.suffix == ".zip":
        ui.notify(
            "Please select a .zip file.",
            type="warning",
            timeout=0,
            position="center",
            close_button="OK",
        )
        return

    # ----- Extract the zip to a temporary directory -----
    temp_dir = Path(tempfile.mkdtemp(prefix="vector_import_"))

    try:
        if password:
            # ----- Decrypt and extract -----
            try:
                with pyzipper.AESZipFile(zip_file, "r") as zf:
                    zf.setpassword(password.encode("utf-8"))
                    zf.extractall(temp_dir)
            except RuntimeError as err:
                ui.notify(
                    f"Failed to decrypt ZIP file → {err}.\n"
                    "Check your password and try again.",
                    type="negative",
                    timeout=0,
                    position="center",
                    close_button="OK",
                )
                shutil.rmtree(temp_dir, ignore_errors=True)
                return
        else:

            # ----- Extract without password -----
            try:
                with pyzipper.AESZipFile(zip_file, "r") as zf:
                    zf.extractall(temp_dir)
            except RuntimeError:
                # This zip requires a password
                ui.notify(
                    "This ZIP file is encrypted. Please provide a password.",
                    type="warning",
                    timeout=0,
                    position="center",
                    close_button="OK",
                )
                shutil.rmtree(temp_dir, ignore_errors=True)
                return

    except Exception as err:
        ui.notify(
            f"Error extracting ZIP → {err}",
            type="negative",
            timeout=0,
            position="center",
            close_button="OK",
        )
        shutil.rmtree(temp_dir, ignore_errors=True)
        return

    # ----- Check for manifest -----
    manifest_path = temp_dir / "export_manifest.json"

    # If manifest not at root, look for it in subdirectories
    if not manifest_path.exists():
        manifests = list(temp_dir.rglob("export_manifest.json"))
        if manifests:
            manifest_path = manifests[0]
            # Set the import directory to the folder containing the manifest
            import_dir = manifest_path.parent
        else:
            import_dir = temp_dir
    else:
        import_dir = temp_dir

    if manifest_path.exists():
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        print(
            f"Importing from export dated: "
            f"{manifest.get('export_date', 'unknown')}"
        )
    else:
        manifest = {}

    # ----- Verify CSV files exist -----
    models = get_all_models()
    found_tables = []

    for table_name, model_class in models.items():
        csv_path = import_dir / f"{table_name}.csv"

        if csv_path.exists():
            found_tables.append((table_name, model_class, csv_path))

    if not found_tables:
        ui.notify(
            "No CSV files found in the selected ZIP archive.",
            type="negative",
            timeout=0,
            position="center",
            close_button="OK",
        )
        shutil.rmtree(temp_dir, ignore_errors=True)
        return

    # ----- Import each table -----
    imported_tables = []
    total_records = 0

    for table_name, model_class, csv_path in found_tables:
        columns = get_column_names(model_class)
        column_objects = (
            {col.name: col for col in model_class.__table__.columns}
        )

        try:
            with get_session() as session:
                # ----- Clear existing data -----
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
                                    raw_value,
                                    column_objects[col_name],
                                )
                        # Preserve original IDs for relational integrity
                        # (don't delete the id field — keep it)
                        new_record = model_class(**record_data)
                        session.add(new_record)

            # Count imported records
            with get_session() as session:
                count = session.query(model_class).count()

            imported_tables.append(f"{table_name} ({count})")
            total_records += count

        except Exception as err:
            ui.notify(
                f"Error importing {table_name} → {err}",
                type="negative",
                timeout=0,
                position="center",
                close_button="OK",
            )
            shutil.rmtree(temp_dir, ignore_errors=True)
            return

    # ----- Import files -----
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
                            file_mime_type="application/octet-stream",
                            uploaded_by="import",
                        )
                        session.add(new_file)
                        files_imported += 1

        except Exception as err:
            ui.notify(
                f"Error importing files → {err}",
                type="warning",
                timeout=0,
                position="center",
                close_button="OK",
            )

    # ----- Clean up temporary directory -----
    shutil.rmtree(temp_dir, ignore_errors=True)

    # ----- Success notification -----
    ui.notify(
        f"Import complete!\n"
        f"Tables: {', '.join(imported_tables)}\n"
        f"Files: {files_imported}\n"
        f"Total records: {total_records}",
        timeout=0,
        position="bottom",
        close_button="OK",
    )

    print(f"\n{'='*60}")
    print(f"  IMPORT COMPLETE")
    print(f"  Tables: {imported_tables}")
    print(f"  Total records: {total_records}")
    print(f"  Files imported: {files_imported}")
    print(f"{'='*60}\n")
