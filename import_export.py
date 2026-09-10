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
import sys
import tempfile
from typing import Optional

from models import get_session


# ----- MODEL REGISTRY -----
# [Add or remove tables here as your app grows]
def get_exportable_models() -> list:
    """Returns a list of (model_class, model_name) tuples for CSV export."""
    from models import Cases, Agents, Rooms, Evidence, Persons, Notes

    return [
        (Cases, "CASES"),
        (Agents, "AGENTS"),
        (Rooms, "ROOMS"),
        (Evidence, "EVIDENDCE"),
        (Persons, "PERSONS"),
        (Notes, "NOTES")
    ]


def get_all_models() -> dict:
    """Returns ALL models including UploadedFiles for import."""
    from models import (
        Cases,
        Agents,
        Rooms,
        Evidence,
        Persons,
        Notes,
        UploadedFiles,
    )

    return {
        "CASES": Cases,
        "AGENTS": Agents,
        "ROOMS": Rooms,
        "EVIDENCE": Evidence,
        "PERSONS": Persons,
        "NOTES": Notes,
        "FILES": UploadedFiles
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


def export_vector_to_csv(password: Optional[str] = None) -> None:
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
            multi_line=True,
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
                multi_line=True,
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
                if uf.FILEDATA:
                    # Sanitize filename
                    safe_name = uf.FILENAME or f"file_{uf.Z_PK}"
                    safe_name = safe_name.replace("/", "_").replace("\\", "_")
                    file_path = files_dir / safe_name

                    with open(file_path, "wb") as f:
                        f.write(uf.FILEDATA)

                    sha256_hash = hashlib.sha256(uf.FILEDATA).hexdigest()

                    files_list.append(
                        {
                            "FILENAME": safe_name,
                            "FILESIZE": uf.FILESIZE or len(uf.FILEDATA),
                            "FILEHASH": sha256_hash
                        }
                    )

                    num_files += 1

    except Exception as err:
        ui.notify(
            f"Error exporting files → {err}",
            multi_line=True,
            type="warning",
            timeout=0,
            position="center",
            close_button="OK",
        )

    print(f"DEBUG: zip_path = {zip_path}")

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
            multi_line=True,
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
        f"Saved to: {export_dir}",
        multi_line=True,
        timeout=0,
        position="bottom",
        close_button="OK",
    )


def export_vector_to_json(password: Optional[str] = None):
    """Exports ALL database tables into ONE .json file.

    If a password is provided, the .json is placed inside an
    AES-256 encrypted .zip with the same naming convention.

    Saves to ~/<case-number>_<datetime>_saved_results.json
    """
    from models import UploadedFiles

    folder_name = get_case_info_for_folder_name()
    if not folder_name:
        return

    home_dir = Path.home()
    desktop_dir = home_dir / "Desktop"

    # ----- Build the complete data structure -----
    all_data = {
        "export_metadata": {
            "export_date": datetime.now().isoformat(),
            "format_version": "1.0",
            "case_folder": folder_name,
        },
        "tables": {},
    }

    total_records = 0

    # ----- Case tables → JSON -----
    for model_class, table_name in get_exportable_models():

        columns = get_column_names(model_class)

        try:
            with get_session() as session:
                records = session.query(model_class).all()

                table_rows = []
                for record in records:
                    row = {}
                    for col in columns:
                        value = getattr(record, col)
                        if isinstance(value, datetime):
                            row[col] = value.isoformat()
                        elif isinstance(value, bytes):
                            # Binary BLOBs encoded as base64 text
                            import base64

                            row[col] = base64.b64encode(value).decode("ascii")
                        elif isinstance(value, bool):
                            row[col] = value
                        else:
                            row[col] = value
                    table_rows.append(row)

                all_data["tables"][table_name] = {
                    "record_count": len(table_rows),
                    "records": table_rows,
                }
                total_records += len(table_rows)

        except Exception as err:
            ui.notify(
                f"Error exporting {table_name} → {err}",
                multi_line=True,
                type="negative",
                timeout=0,
                position="center",
                close_button="OK",
            )
            return

    # ----- Uploaded files → base64 inside the JSON -----
    import base64

    files_list = []
    try:
        with get_session() as session:
            for uf in session.query(UploadedFiles).all():
                if uf.FILEDATA:
                    safe_name = (
                        (uf.FILENAME or f"file_{uf.Z_PK}")
                        .replace("/", "_")
                        .replace("\\", "_")
                    )
                    files_list.append(
                        {
                            "FILENAME": safe_name,
                            "FILESIZE": uf.FILESIZE or len(uf.FILEDATA),
                            "FILEMIMETYPE": uf.FILEMIMETYPE or "application/octet-stream",
                            "FILEDATA_b64": base64.b64encode(uf.FILEDATA).decode("ascii"),
                        }
                    )
    except Exception as err:
        ui.notify(
            f"Error exporting files → {err}",
            type="warning",
            timeout=5000,
            position="center",
            close_button="OK",
        )

    all_data["files"] = {
        "record_count": len(files_list),
        "records": files_list,
    }

    # ----- Write the .json file -----
    json_path = desktop_dir / f"{folder_name}.json"
    try:
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(all_data, f, indent=4, ensure_ascii=False)
    except OSError as err:
        ui.notify(
            f"Error writing JSON → {err}",
            multi_line=True,
            type="negative",
            timeout=5000,
            position="center",
            close_button="OK",
        )
        return

    # ----- Optional: encrypt the .json inside a .zip -----
    final_path = json_path
    if password:
        zip_path = desktop_dir / f"{folder_name}.json.zip"
        try:
            with pyzipper.AESZipFile(
                zip_path,
                "w",
                compression=pyzipper.ZIP_DEFLATED,
                encryption=pyzipper.WZ_AES,
            ) as zf:
                zf.setpassword(password.encode("utf-8"))
                zf.setencryption(pyzipper.WZ_AES, nbits=256)
                zf.write(json_path, arcname=json_path.name)

            json_path.unlink()  # Remove the plain .json
            final_path = zip_path
        except Exception as err:
            ui.notify(
                f"Error creating encrypted zip → {err}",
                multi_line=True,
                type="negative",
                timeout=0,
                position="center",
                close_button="OK",
            )
            return

    ui.notify(
        f"JSON export complete! \n"
        f"Total records: {total_records} \n"
        f"Files embedded: {len(files_list)} \n"
        f"Saved to: {final_path}",
        multi_line=True,
        timeout=0,
        position="bottom",
        close_button="OK",
    )


# ----- IMPORT FUNCTION -----


def import_vector_from_csv(
        zip_path: str,
        password: Optional[str] = None
) -> None:
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
                    f"Failed to decrypt ZIP file → {err}. \n"
                    "Check your password and try again.",
                    multi_line=True,
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
            multi_line=True,
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
                multi_line=True,
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
                            FILENAME=file_path.name,
                            FILEDATA=file_data,
                            FILESIZE=len(file_data),
                            FILEMIMETYPE="application/octet-stream",
                            FILEUPLOADEDBY="import",
                        )
                        session.add(new_file)
                        files_imported += 1

        except Exception as err:
            ui.notify(
                f"Error importing files → {err}",
                multi_line=True,
                type="warning",
                timeout=0,
                position="center",
                close_button="OK",
            )

    # ----- Clean up temporary directory -----
    shutil.rmtree(temp_dir, ignore_errors=True)

    # ----- Success notification -----
    ui.notify(
        f"Import complete! \n"
        f"Tables: {', '.join(imported_tables)} \n"
        f"Files: {files_imported} \n"
        f"Total records: {total_records}",
        multi_line=True,
        timeout=0,
        position="bottom",
        close_button="OK",
    )


def import_vector_from_json(source: str, password: Optional[str] = None):
    """Imports all tables from a single VECTOR .json export file.

    Accepts a .json file directly, or an encrypted .zip containing one.

    Clears existing data before importing.
    """
    import base64
    import tempfile
    from sqlalchemy import Boolean, DateTime, Integer, Float

    source_path = Path(source)
    if not source_path.exists():
        ui.notify(
            f"{source_path.name} File not found.", type="negative")
        return

    temp_dir_to_clean = None

    # ----- If a zip was given, extract it first -----
    if source_path.suffix.lower() == ".zip":
        temp_dir = Path(tempfile.mkdtemp(prefix="vector_json_import_"))
        temp_dir_to_clean = temp_dir
        try:
            with pyzipper.AESZipFile(source_path, "r") as zf:
                if password:
                    zf.setpassword(password.encode("utf-8"))
                zf.extractall(temp_dir)
        except RuntimeError:
            ui.notify(
                "Failed to decrypt — check your password.",
                type="negative",
                timeout=0,
                position="center",
                close_button="OK",
            )
            shutil.rmtree(temp_dir, ignore_errors=True)
            return

        json_files = list(temp_dir.rglob("*.json"))
        if not json_files:
            ui.notify(
                "No .json file found inside the archive.",
                type="negative",
                timeout=0,
                position="center",
                close_button="OK",
            )
            shutil.rmtree(temp_dir, ignore_errors=True)
            return
        source_path = json_files[0]

    try:
        with open(source_path, "r", encoding="utf-8") as f:
            all_data = json.load(f)
    except (json.JSONDecodeError, OSError) as err:
        ui.notify(
            f"Error reading JSON file → {err}",
            multi_line=True,
            type="negative",
            timeout=0,
            position="center",
            close_button="OK",
        )
        if temp_dir_to_clean:
            shutil.rmtree(temp_dir_to_clean, ignore_errors=True)
        return

    # ----- Validate format -----
    if "tables" not in all_data:
        ui.notify(
            "Not a valid VECTOR JSON export (missing 'tables' key).",
            type="negative",
            timeout=0,
            position="center",
            close_button="OK",
        )
        if temp_dir_to_clean:
            shutil.rmtree(temp_dir_to_clean, ignore_errors=True)
        return

    def json_to_value(value, column):
        """Converts a JSON value back to the right Python type."""
        if value is None:
            if column.nullable:
                return None
            if isinstance(column.type, Boolean):
                return False
            return ""
        col_type = column.type
        if isinstance(col_type, Boolean):
            if isinstance(value, bool):
                return value
            return str(value).lower() in ("true", "1", "yes", "t")
        elif isinstance(col_type, (Integer, Float)):
            return value
        elif isinstance(col_type, DateTime):
            try:
                return datetime.fromisoformat(str(value))
            except (ValueError, TypeError):
                return None
        else:
            # Detect base64-encoded BLOBs heuristically: they are long
            # ASCII strings stored by export_vector_to_csv_json
            if isinstance(value, str) and len(value) > 0:
                try:
                    import base64

                    decoded = base64.b64decode(value, validate=True)
                    # Heuristic: only treat as binary if mostly non-text
                    if (
                        decoded[:4] not in (b"[BIN", b"")
                        and not value.isprintable() is False
                    ):
                        return decoded
                except Exception:
                    pass
            return value

    models = get_all_models()
    imported_tables = []
    total_records = 0

    # ----- Import each table -----
    for table_name, table_payload in all_data["tables"].items():
        if table_name not in models:
            print(f"Skipping unknown table: {table_name}")
            continue

        model_class = models[table_name]
        records = table_payload.get("records", [])
        columns = {col.name: col for col in model_class.__table__.columns}

        try:
            with get_session() as session:
                session.query(model_class).delete()

                for rec in records:
                    record_data = {}
                    for col_name, col_obj in columns.items():
                        if col_name == "Z_PK":
                            continue  # Let autoincrement reassign
                        raw = rec.get(col_name)
                        record_data[col_name] = json_to_value(raw, col_obj)

                    session.add(model_class(**record_data))

            with get_session() as session:
                count = session.query(models[table_name]).count()

            imported_tables.append(f"{table_name} ({count})")
            total_records += count

        except Exception as err:
            ui.notify(
                f"Error importing {table_name} → {err}",
                multi_line=True,
                type="negative",
                timeout=0,
                position="center",
                close_button="OK",
            )
            if temp_dir_to_clean:
                shutil.rmtree(temp_dir_to_clean, ignore_errors=True)
            return

    # ----- Import uploaded files -----
    from models import UploadedFiles

    files_imported = 0

    files_payload = all_data.get("files", {})
    if files_payload.get("records"):
        try:
            with get_session() as session:
                session.query(UploadedFiles).delete()

                for rec in files_payload["records"]:
                    file_bytes = base64.b64decode(rec["FILEDATA_b64"])
                    session.add(
                        UploadedFiles(
                            FILENAME=rec["FILENAME"],
                            FILEDATA=FILEDATA if False else file_bytes,
                            FILESIZE=rec.get("FILESIZE") or len(file_bytes),
                            FILEMIMETYPE=rec.get(
                                "FILEMIMETYPE",
                                "application/octet-stream"
                            ),
                            FILEUPLOADEDBY="json-import",
                        )
                    )
                    files_imported_count = (
                        files_imported_count + 1
                        if "files_imported_count" in dir()
                        else 1
                    )

            files_imported = len(files_payload["records"])

        except Exception as err:
            ui.notify(
                f"Error importing files → {err}",
                multi_line=True,
                type="warning",
                timeout=0,
                position="center",
                close_button="OK",
            )
            files_imported = 0
    else:
        files_imported = 0

    # ----- Cleanup & success -----
    if temp_dir_to_clean:
        shutil.rmtree(temp_dir_to_clean, ignore_errors=True)

    ui.notify(
        f"JSON import complete! \n"
        f"Tables: {', '.join(imported_tables)} \n"
        f"Files: {files_imported} \n"
        f"Total records: {total_records}",
        multi_line=True,
        timeout=0,
        position="bottom",
        close_button="OK",
    )
