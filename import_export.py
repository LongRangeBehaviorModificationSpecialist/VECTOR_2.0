#!/usr/bin/env python3

"""
import_export.py

Database export and import functionality.

Import: Restores tables from CSV files and file BLOBs from disk.
Export: Saves all tables to CSV files and file BLOBs to disk.
"""

import csv
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
from nicegui import ui
from pathlib import Path
import pyzipper
import re
import shutil
import tempfile
from typing import Optional

from failures import explain, log
from program.config import Config
from models import (
    LEGACY_COLUMN_NAMES,
    LEGACY_TABLE_NAMES,
    Cases,
    get_session,
    normalise_legacy_dates,
    record_audit,
)
from utils import CONFIRM_TIMEOUT, WARN_TIMEOUT, ZERO_TIMEOUT


@dataclass
class ExportResult:
    zip_path: Path
    message: str


# ----- MODEL REGISTRY -----
# [Add or remove tables here as the app grows]
def get_exportable_models() -> list:
    """Returns a list of (model_class, model_name) tuples for CSV export."""
    from models import (
        Cases,
        Agents,
        Rooms,
        Evidence,
        Persons,
        Notes,
        AuditLog,
    )

    return [
        (Cases, "CASES"),
        (Agents, "AGENTS"),
        (Rooms, "ROOMS"),
        (Evidence, "EVIDENCE"),
        (Persons, "PERSONS"),
        (Notes, "NOTES"),
        # The audit trail travels with the case: an export that drops it
        # cannot answer what changed after collection.
        (AuditLog, "AUDIT"),
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
        "FILES": UploadedFiles,
    }



# ----- Names used by older exports -----
# Exports made before the column renames use lowercase table names and
# the old column spellings, and upstream's exports write the evidence
# table as "EVIDENDCE". All of them are read as the table they meant.
_TABLE_ALIASES = {
    **LEGACY_TABLE_NAMES,
    "EVIDENDCE": "EVIDENCE",
}

# Keys describing each attachment in the manifest and the JSON export.
_FILE_ENTRY_ALIASES = {
    "file_name": "FILENAME",
    "file_size": "FILESIZE",
    "file_mime_type": "FILEMIMETYPE",
    "mime_type": "FILEMIMETYPE",
    "uploaded_by": "FILEUPLOADEDBY",
    "hash_at_ingest": "FILESHA256",
    "hashed_at": "FILEHASHEDDATETIME",
    "FILEHASHEDAT": "FILEHASHEDDATETIME",
    "file_hash": "FILEHASH",
    "matches_ingest_hash": "FILEHASHMATCHES",
    "data_base64": "FILEDATA_b64",
}

def same_hash(first, second) -> bool:
    """Whether two SHA-256 digests are the same digest.

    Hex is not case-sensitive: VECTOR now writes digests in capitals,
    and every attachment collected before that was recorded in lower
    case. Compared as text, each of those would read as altered.
    """
    return (first or "").strip().upper() == (second or "").strip().upper()


def hash_file(path: Path, chunk_size: int = 65536) -> str:
    """Streamed SHA-256 of a file's contents."""
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            hasher.update(chunk)
    return hasher.hexdigest().upper()


def canonical_table_name(name: str) -> str:
    """Maps any table name an export has used onto today's."""
    name = str(name)
    return _TABLE_ALIASES.get(name, name.upper())


def canonical_row(table_name: str, row: dict) -> dict:
    """Renames legacy column names in one exported row."""
    renames = LEGACY_COLUMN_NAMES.get(table_name, {})
    return {renames.get(key, key): value for key, value in row.items()}


def canonical_file_entry(entry: dict) -> dict:
    """Renames legacy keys in one attachment's manifest entry."""
    return {
        _FILE_ENTRY_ALIASES.get(key, key): value
        for key, value in entry.items()
    }


# ----- Unpacking an import, within limits -----
# An import used to unpack the whole archive before looking at it: a ZIP
# of under 2 KB unpacked a 1 MB file VECTOR never reads, and one made to
# unpack to gigabytes could fill the disk. Only the files an import
# reads are unpacked now, and unpacking stops at a limit on entries and
# on bytes, counted as they are written -- a ZIP can say anything about
# its own sizes.

class ArchiveTooLarge(ValueError):
    """An archive past the import limits. Nothing has been imported."""


def _member_path(dest: Path, name: str) -> Optional[Path]:
    """Where an entry unpacks to, or None for a name that would leave
    dest (an absolute path, a drive, "..")."""
    if name.startswith(("/", "\\")):
        return None
    parts = [part for part in name.replace("\\", "/").split("/")
             if part not in ("", ".")]
    if not parts or any(part == ".." or ":" in part for part in parts):
        return None
    return dest.joinpath(*parts)


def _is_csv_import_member(name: str) -> bool:
    """A file the CSV import reads: a table, the manifest, an attachment."""
    parts = name.replace("\\", "/").lower().split("/")
    return (
        parts[-1].endswith(".csv")
        or parts[-1] == "export_manifest.json"
        or "files" in parts[:-1]
    )


def _is_json_import_member(name: str) -> bool:
    """A file the JSON import reads: the export itself."""
    return name.lower().endswith(".json")


def _extract_wanted(archive, dest: Path, wanted) -> None:
    """Unpacks the entries wanted(name) accepts into dest, within the
    limits. Raises ArchiveTooLarge past them; RuntimeError for a wrong or
    missing password, as extractall did."""
    limit = Config.MAX_IMPORT_EXPANDED_BYTES
    infos = archive.infolist()
    if len(infos) > Config.MAX_IMPORT_ENTRIES:
        raise ArchiveTooLarge(
            f"It holds {len(infos):,} entries; an import may hold at most "
            f"{Config.MAX_IMPORT_ENTRIES:,}."
        )
    chosen = [info for info in infos
              if not info.is_dir() and wanted(info.filename)]
    too_big = (
        f"It unpacks to more than {limit // (1024 * 1024):,} MB, the most "
        "an import may unpack to (VECTOR_MAX_IMPORT_EXPANDED_MB)."
    )
    if sum(info.file_size for info in chosen) > limit:
        raise ArchiveTooLarge(too_big)

    written = 0
    for info in chosen:
        target = _member_path(dest, info.filename)
        if target is None:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        with archive.open(info) as source, open(target, "wb") as out:
            while True:
                chunk = source.read(1024 * 1024)
                if not chunk:
                    break
                written += len(chunk)
                if written > limit:
                    raise ArchiveTooLarge(too_big)
                out.write(chunk)


def _refuse_large_archive(err: ArchiveTooLarge) -> None:
    ui.notify(
        "Nothing was imported, and the case on this computer is "
        f"unchanged: this file is larger than an import may be.\n\n{err}",
        multi_line=True,
        classes="multi-line-notification",
        type="warning",
        timeout=ZERO_TIMEOUT,
        position="center",
        close_button="OK",
    )


def _report_failure(message: str, err: BaseException) -> None:
    """Explains a failed export or import on screen, and logs the detail."""
    log.error("%s", message, exc_info=err)
    ui.notify(
        f"{message}\n\n{explain(err)}",
        multi_line=True,
        classes="multi-line-notification",
        type="warning",
        timeout=ZERO_TIMEOUT,
        position="center",
        close_button="OK",
    )


def _clear_case_tables(session) -> None:
    """Empties every case table, inside the import's own transaction.

    An import replaces the whole case. Clearing only the tables an export
    happened to contain kept whatever it lacked -- the previous case's
    attachments, for one, when the archive had none.
    """
    for model_class in get_all_models().values():
        session.query(model_class).delete()


# ----- Staging -----
# Exports are built in the system temp folder and handed to the browser as
# a download, so the file reaches whichever device asked for it -- a tablet
# on `--lan` included -- and no copy is left on the host's Desktop. Imports
# arrive the same way, as an upload. Neither is needed once the download or
# the import has happened, so anything left for over an hour is removed.
#
# The two folders an import unpacks into are on the list as well
# ("vector_import_" also covers the uploads). Each holds the whole case,
# photographs included, unencrypted even when the export was not; an
# import that failed part-way used to leave one behind for good, under a
# name this clean-up did not recognise.
STAGING_PREFIXES = ("vector_export_", "vector_import_", "vector_json_import_")
# Set value to 1 hour (3,600 seconds)
STAGING_MAX_AGE_SECONDS = 60 * 60


def new_staging_dir(prefix: str) -> Path:
    """A fresh private folder in the system temp directory."""
    return Path(tempfile.mkdtemp(prefix=prefix))


def remove_stale_staging(
        max_age_seconds: int = STAGING_MAX_AGE_SECONDS,
) -> int:
    """Deletes staging folders older than max_age_seconds.

    Returns how many were removed. A folder still in use -- a large
    download in progress on Windows -- cannot be deleted, and is left for
    the next pass.
    """
    import time

    cutoff = time.time() - max_age_seconds
    removed = 0
    for entry in Path(tempfile.gettempdir()).iterdir():
        if not entry.name.startswith(STAGING_PREFIXES):
            continue
        try:
            if entry.is_dir() and entry.stat().st_mtime < cutoff:
                shutil.rmtree(entry)
                removed += 1
        except OSError:
            continue
    return removed


def _unique_archive_name(name: str, used: set) -> str:
    """A name no other attachment in this archive has taken.

    Two attachments can share a name -- two photographs both called
    photo.jpg -- and written into one folder the second overwrote the
    first, so one was lost from the export. Compared without regard to
    case, since Windows treats Photo.jpg and photo.jpg as one file.
    """
    stem, suffix = Path(name).stem, Path(name).suffix
    candidate = name
    counter = 2
    while candidate.lower() in used:
        candidate = f"{stem} ({counter}){suffix}"
        counter += 1
    used.add(candidate.lower())
    return candidate


# ----- HELPER FUNCTIONS -----

def get_case_info_for_folder_name() -> str:
    """Builds the folder name from the active case info."""
    from models import Cases

    with get_session() as session:
        case = session.query(Cases).first()
        if not case:
            ui.notify(
                "No case found. Cannot export data.",
                type="warning",
                timeout=WARN_TIMEOUT,
                position="center",
                close_button="OK",
            )
            return ""

        case_number = safe_file_name(case.CASENUMBER or "UNKNOWN")
        begin_dt = case.CASEDATETIMEBEGIN or "UNKNOWN"

        # Format the datetime
        if hasattr(begin_dt, "strftime"):
            dt_str = begin_dt.strftime("%Y-%m-%d_%H%M%S")
        else:
            # Sanitize the string
            dt_str = safe_file_name(
                str(begin_dt)
                .replace(":", "")
                .replace(" ", "_")
                .replace("/", "")
            )
        return f"{case_number}_{dt_str}_saved_results"


_NOT_IN_FILE_NAMES = re.compile(r'[<>:"/\\|?*\x00-\x1f\s]+')


def safe_file_name(text: str) -> str:
    """Text made fit to be part of a file name on Windows as well.

    The case number names the export. One holding a character Windows
    refuses -- "26:1234", "ICAC?26" -- stopped the export at the end of
    the day with "Could not start the export". Those characters, and
    spaces, become underscores, and any left at either end go -- with
    trailing dots, which Windows also refuses.
    """
    cleaned = _NOT_IN_FILE_NAMES.sub("_", str(text)).strip("_. ")
    return cleaned or "UNKNOWN"


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
    from sqlalchemy import Boolean, DateTime, Integer, Float, String

    col_type = column.type

    if value == "" or value is None:
        # A CSV cell cannot tell empty text from no value at all. A required
        # text column gets its "" back: a room saved without agents holds ""
        # there, and turning it into None failed the whole import. Anything
        # else gets None, as before.
        if not column.nullable and isinstance(col_type, String):
            return ""
        return None

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


# ----- CSV EXPORT FUNCTION -----

def export_vector_to_csv(
        password: Optional[str] = None,
        destination: Optional[Path] = None,
) -> Optional[ExportResult]:
    """Exports every table to CSV, with every attachment, as one ZIP.

    Returns the finished archive's path, or None if the export failed.
    The archive is written to `destination` -- a fresh staging folder when
    none is given, for the caller to hand to the browser as a download.
    The CSVs are assembled in a separate staging folder that is removed
    afterwards, so no unencrypted copy of the case is left behind.
    """
    from models import UploadedFiles

    # ----- Build folder name -----
    folder_name = get_case_info_for_folder_name()

    if not folder_name:
        return None

    remove_stale_staging()
    destination = (
        Path(destination) if destination else new_staging_dir("vector_export_")
    )
    work_dir = new_staging_dir(prefix="vector_export_")

    # ----- Assemble the archive's contents before zipping -----
    export_dir = work_dir / folder_name
    files_dir = export_dir / "files"
    zip_path = destination / f"{folder_name}.zip"

    try:
        export_dir.mkdir(parents=True, exist_ok=True)
        files_dir.mkdir(parents=True, exist_ok=True)
    except OSError as err:
        _report_failure(
            "Could not start the export. Nothing was downloaded.",
            err
        )
        shutil.rmtree(work_dir, ignore_errors=True)
        return None

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
                    writer.writerow(columns)  # Write the header row
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
            _report_failure(
                f"The export stopped while reading {table_name}. "
                "Nothing was downloaded.",
                err,
            )
            shutil.rmtree(work_dir, ignore_errors=True)
            return None

    # ----- Export uploaded files -----
    files_list = []
    num_files = 0
    integrity_failures = []
    used_names = set()

    try:
        with get_session() as session:
            uploaded_files = session.query(UploadedFiles).all()
            for uf in uploaded_files:
                if uf.FILEDATA:
                    # Sanitize filename
                    safe_name = uf.FILENAME or f"file_{uf.Z_PK}"
                    safe_name = safe_name.replace("/", "_").replace("\\", "_")
                    archive_name = _unique_archive_name(safe_name, used_names)
                    file_path = files_dir / archive_name

                    with open(file_path, "wb") as f:
                        f.write(uf.FILEDATA)

                    sha256_hash = (
                        hashlib.sha256(uf.FILEDATA).hexdigest().upper()
                    )

                    # The hash taken when the file was collected is the
                    # one that matters. Recomputing here only certifies
                    # the copy, so compare the two and say so if they
                    # disagree.
                    recorded = uf.FILESHA256 or ""
                    verified = (not recorded) or same_hash(
                        recorded, sha256_hash
                    )
                    if not verified:
                        integrity_failures.append(archive_name)

                    # FILENAME, FILESIZE and FILEHASH are the keys
                    # upstream's manifest uses; the rest carry the
                    # collection record this branch adds. FILEARCHIVENAME
                    # is the file's name inside the archive, which differs
                    # from FILENAME when two attachments shared a name.
                    files_list.append(
                        {
                            "FILENAME": safe_name,
                            "FILEARCHIVENAME": archive_name,
                            "FILESIZE": uf.FILESIZE or len(uf.FILEDATA),
                            "FILEHASH": sha256_hash,
                            "FILESHA256": recorded or None,
                            "FILEHASHEDDATETIME": uf.FILEHASHEDDATETIME or None,
                            "FILEMIMETYPE": uf.FILEMIMETYPE or "",
                            "FILEUPLOADEDBY": uf.FILEUPLOADEDBY or "",
                            "FILEHASHMATCHES": verified,
                        }
                    )

                    num_files += 1

                # Let go of this attachment's bytes before the next is
                # read. The session keeps what it has loaded, so without
                # this every photograph in the case was held in memory
                # at once.
                session.expire(uf, ["FILEDATA"])

    except Exception as err:
        # Carrying on would hand over an export without its attachments,
        # under a message saying it was complete.
        _report_failure(
            "The export stopped while copying the attachments. Nothing "
            "was downloaded.",
            err,
        )
        shutil.rmtree(work_dir, ignore_errors=True)
        return None

    # ----- Write a manifest file -----
    manifest = {
        "export_date": datetime.now().isoformat(),
        "case_file": zip_path.name,
        "tables": [
            {
                "name": table_name,
                "records": count,
                "sha256": hash_file(export_dir / f"{table_name}.csv"),
            }
            for table_name, count in exported_tables.items()
        ],
        "total_records": total_records,
        "files": files_list,
        "total_files": num_files,
        "integrity_failures": integrity_failures,
        "encrypted": password is not None and len(password) > 0,
    }

    if integrity_failures:
        ui.notify(
            "WARNING -- these attachments no longer match the SHA-256 "
            "recorded when they were collected:\n\n"
            + "\n".join(integrity_failures)
            + "\n\nThe export still completed. Investigate before relying "
            "on these files.",
            multi_line=True,
            classes="multi-line-notification",
            type="warning",
            timeout=ZERO_TIMEOUT,
            position="center",
            close_button="OK",
        )

    manifest_path = export_dir / "export_manifest.json"

    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=4)

    # ----- Create the ZIP file -----
    try:
        with get_session() as session:
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
        _report_failure(
            "Could not create the ZIP file. Nothing was exported.",
            err,
        )
        shutil.rmtree(work_dir, ignore_errors=True)
        return None

    try:
        with get_session() as session:
            case = session.query(Cases).order_by(Cases.Z_PK).first()

            record_audit(
                session,
                action="EXPORT",
                table_name="(all case tables)",
                summary=f"Exported CSV data for Case No. {case.CASENUMBER}",
                after={
                    "destination": str(zip_path.name),
                    "date/time": manifest.get("export_date", "unknown"),
                    "records": total_records,
                    "files": num_files,
                    "integrity_failures": integrity_failures,
                    "encrypted": password is not None and len(password) > 0,
                }
            )
    except Exception as err:
        # Named the audit record through a "stage" set inside the try, so
        # a failure before it was set raised again here; and printed the
        # raw error to the console rather than logging it.
        _report_failure(
            "The CSV export was made but could not be recorded in the "
            "audit trail, so it was not handed over. Nothing was "
            "downloaded.",
            err,
        )
        shutil.rmtree(work_dir, ignore_errors=True)
        return None

    # Delete the staging directory
    shutil.rmtree(work_dir, ignore_errors=True)

    def entry_word(count: int) -> str:
        return "entry" if count == 1 else "entries"

    enc_text = " (AES-256 encrypted)" if password else ""

    table_lines = "\n".join(
        f"{n} ({c} {entry_word(c)})" for n, c in exported_tables.items()
    )

    message = (
        f"Exporting data to CSV{enc_text}...\n\n"
        f"Tables :\n\n{table_lines}\n\n"
        f"Output will be named :  {zip_path.name}"
    )

    return ExportResult(zip_path=zip_path, message=message)


# ----- CSV IMPORT FUNCTION -----

def import_vector_from_csv(
        zip_path: str,
        password: Optional[str] = None,
) -> None:
    """Imports database tables from a .zip file.

    If the zip is encrypted, decrypts it with the provided password.

    Clears existing data before importing.
    """

    zip_file = Path(zip_path)

    if not zip_file.exists():
        ui.notify(
            "ZIP file not found.",
            type="warning",
            timeout=WARN_TIMEOUT,
            position="center",
            close_button="OK",
        )
        return

    if zip_file.suffix.lower() != ".zip":
        ui.notify(
            "Please select a .zip file.",
            type="warning",
            timeout=WARN_TIMEOUT,
            position="center",
            close_button="OK",
        )
        return

    # ----- Extract the zip to a temporary directory -----
    temp_dir = Path(tempfile.mkdtemp(prefix="vector_import_"))
    try:
        _import_csv_archive(zip_file, password, temp_dir)
    finally:
        # However the import ended -- finished, refused, or stopped by
        # something nobody foresaw -- the unpacked case goes.
        shutil.rmtree(temp_dir, ignore_errors=True)


# ----- Checked before anything is cleared -----
# An import replaces the whole case, so a file that would put less in its
# place is refused while the case is still there: a file holding no case,
# a table cut short, a photograph the export listed and the archive lost,
# a file altered since export. A JSON file with an empty table list used
# to clear the case and report success, and an archive missing a listed
# photograph imported without it.

def _refuse_import(problems: list) -> None:
    """Says why a file was not imported. Nothing has been changed."""
    ui.notify(
        "Nothing was imported, and the case on this computer is "
        "unchanged: this file failed its integrity checks.\n\n"
        + "\n\n".join(problems),
        multi_line=True,
        classes="multi-line-notification",
        type="warning",
        timeout=ZERO_TIMEOUT,
        position="center",
        close_button="OK",
    )


def _one_case(count: int) -> list:
    if count == 1:
        return []
    if count == 0:
        return ["It holds no case."]
    return [f"It holds {count} cases; VECTOR holds one at a time."]


def _csv_rows(path: Path) -> int:
    with open(path, "r", newline="", encoding="utf-8") as handle:
        return sum(1 for _row in csv.DictReader(handle))


def _check_csv_archive(import_dir: Path, found_tables: list, manifest: dict) -> list:
    """What is wrong with an unpacked CSV archive, or [] when nothing is.

    An archive without a manifest, or whose manifest lists no files, is
    from before files were listed: its attachments cannot be checked, and
    the import says so afterwards, as it always has.
    """
    tables = {name: path for name, _model, path in found_tables}
    problems = _one_case(_csv_rows(tables["CASES"]) if "CASES" in tables else 0)

    # Every table the manifest lists, with the rows it had.
    for entry in manifest.get("tables") or []:
        if not isinstance(entry, dict) or not entry.get("name"):
            continue
        name = canonical_table_name(entry["name"])
        if name not in get_all_models():
            continue
        if name not in tables:
            problems.append(f"Its {entry['name']} table is missing.")
            continue
        listed = entry.get("records")
        found = _csv_rows(tables[name])
        if isinstance(listed, int) and found != listed:
            problems.append(
                f"Its {entry['name']} table should hold {listed} rows and "
                f"holds {found}."
            )

    # The attachments: exactly those listed, each as it was exported.
    listed_files = manifest.get("files")
    if not isinstance(listed_files, list):
        return problems
    names, expected = [], {}
    for entry in listed_files:
        if not isinstance(entry, dict):
            continue
        entry = canonical_file_entry(entry)
        name = entry.get("FILEARCHIVENAME") or entry.get("FILENAME")
        if name:
            names.append(name)
            expected[name] = entry.get("FILEHASH")
    files_dir = import_dir / "files"
    present = (
        {path.name: path for path in files_dir.iterdir() if path.is_file()}
        if files_dir.is_dir() else {}
    )
    listed_once = list(dict.fromkeys(names))
    missing = [name for name in listed_once if name not in present]
    altered = [
        name for name in listed_once
        if name in present and expected[name]
        and not same_hash(expected[name], hash_file(present[name]))
    ]
    unlisted = sorted(name for name in present if name not in expected)
    twice = sorted({name for name in names if names.count(name) > 1})
    if missing:
        problems.append(
            "Files its manifest lists that are not in the archive:\n"
            + "\n".join(missing)
        )
    if altered:
        problems.append(
            "Files whose contents do not match the manifest hash:\n"
            + "\n".join(altered)
        )
    if unlisted:
        problems.append(
            "Files in the archive that its manifest does not list:\n"
            + "\n".join(unlisted)
        )
    if twice:
        problems.append(
            "Files its manifest lists twice:\n" + "\n".join(twice)
        )
    return problems


def _check_json_export(payload: dict) -> tuple:
    """What is wrong with a JSON export, and its attachments decoded.

    Returns (problems, [(entry, bytes), ...]); problems is [] when the
    file can replace the case.
    """
    import base64
    import binascii

    tables = payload.get("tables")
    if not isinstance(tables, dict):
        return ["Its list of tables is damaged."], []

    problems = []
    case_count = 0
    for raw_name, table_data in tables.items():
        name = canonical_table_name(raw_name)
        if name not in get_all_models():
            # The audit trail is exported but never restored.
            continue
        records = (
            table_data.get("records") if isinstance(table_data, dict) else None
        )
        if not isinstance(records, list) or not all(
            isinstance(record, dict) for record in records
        ):
            problems.append(f"Its {raw_name} table is damaged.")
            continue
        listed = table_data.get("record_count")
        if isinstance(listed, int) and listed != len(records):
            problems.append(
                f"Its {raw_name} table should hold {listed} records and "
                f"holds {len(records)}."
            )
        if name == "CASES":
            case_count = len(records)
    problems = _one_case(case_count) + problems

    # A 1.0 export held a bare list. Upstream's layout, and 1.1, wrap it
    # as {"record_count": n, "records": [...]}.
    entries = payload.get("files", [])
    if isinstance(entries, dict):
        listed = entries.get("record_count")
        entries = entries.get("records", [])
        if isinstance(listed, int) and isinstance(entries, list) and (
            listed != len(entries)
        ):
            problems.append(
                f"It should hold {listed} attachments and holds "
                f"{len(entries)}."
            )
    if not isinstance(entries, list):
        return problems + ["Its list of attachments is damaged."], []

    decoded, altered = [], []
    for raw_entry in entries:
        if not isinstance(raw_entry, dict):
            problems.append("An attachment in it is damaged.")
            continue
        entry = canonical_file_entry(raw_entry)
        name = entry.get("FILENAME") or "(unnamed)"
        try:
            data = base64.b64decode(entry.get("FILEDATA_b64", ""), validate=True)
        except (binascii.Error, ValueError, TypeError):
            problems.append(f"The attachment {name} is damaged.")
            continue
        expected = entry.get("FILEHASH")
        if expected and not same_hash(
            expected, hashlib.sha256(data).hexdigest()
        ):
            altered.append(name)
        decoded.append((entry, data))
    if altered:
        problems.append(
            "These attachments do not match the hash recorded in the file:\n"
            + "\n".join(altered)
        )
    return problems, decoded


def _import_csv_archive(
        zip_file: Path,
        password: Optional[str],
        temp_dir: Path,
) -> None:
    """The CSV import itself, unpacking into temp_dir, which the caller
    removes however this ends."""
    try:
        if password:
            # ----- Decrypt and extract -----
            try:
                with pyzipper.AESZipFile(zip_file, "r") as zf:
                    zf.setpassword(password.encode("utf-8"))
                    _extract_wanted(zf, temp_dir, _is_csv_import_member)
            except RuntimeError as err:
                ui.notify(
                    f"Failed to decrypt ZIP file → {err}.\n"
                    "Check your password and try again.",
                    type="warning",
                    timeout=WARN_TIMEOUT,
                    position="center",
                    close_button="OK",
                )
                return
        else:
            # ----- Extract without password -----
            try:
                with pyzipper.AESZipFile(zip_file, "r") as zf:
                    _extract_wanted(zf, temp_dir, _is_csv_import_member)
            except RuntimeError:
                # This zip requires a password
                ui.notify(
                    "This ZIP file is encrypted. Please provide a password.",
                    type="warning",
                    timeout=WARN_TIMEOUT,
                    position="center",
                    close_button="OK",
                )
                return

    except ArchiveTooLarge as err:
        _refuse_large_archive(err)
        return
    except Exception as err:
        _report_failure(
            "Could not open that file. Nothing was imported, and the case "
            "is unchanged.",
            err,
        )
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
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
            if not isinstance(manifest, dict):
                raise ValueError("the manifest is not a VECTOR manifest")
        except (OSError, UnicodeDecodeError, ValueError) as err:
            # A damaged file, or not a VECTOR export. This used to stop
            # the import with no message at all.
            _report_failure(
                "That file's export_manifest.json could not be read, so "
                "it cannot be imported. Nothing was imported, and the "
                "case is unchanged.",
                err,
            )
            return
        print(
            f"Importing from export dated: "
            f"{manifest.get('export_date', 'unknown')}"
        )
    else:
        manifest = {}

    # ----- Verify CSV files exist -----
    models = get_all_models()
    found_tables = []

    # Matched from the files present rather than looked up by today's
    # names, so an archive using an older or misspelled table name still
    # imports.
    for csv_path in sorted(import_dir.glob("*.csv")):
        table_name = canonical_table_name(csv_path.stem)
        model_class = models.get(table_name)
        if model_class is not None:
            found_tables.append((table_name, model_class, csv_path))

    if not found_tables:
        ui.notify(
            "No CSV files found in the selected ZIP archive.",
            type="warning",
            timeout=WARN_TIMEOUT,
            position="center",
            close_button="OK",
        )
        return

    problems = _check_csv_archive(import_dir, found_tables, manifest)
    if problems:
        _refuse_import(problems)
        return

    # ----- Replace the case, all or nothing -----
    # Every table, the attachments and the audit record go in one
    # transaction. Each table used to be replaced in a transaction of its
    # own, so a failure part-way left a case that was half the old one and
    # half the new, under a message naming only the table that failed.
    from models import UploadedFiles

    files_dir = import_dir / "files"
    imported_tables = []
    total_records = 0
    files_imported = 0

    # The manifest records a SHA-256 per file. Verify against it rather
    # than trusting the archive, and carry the original provenance back
    # instead of stamping every file "import" / octet-stream.
    manifest_files = {}
    for entry in manifest.get("files", []):
        if isinstance(entry, dict):
            entry = canonical_file_entry(entry)
            # Keyed by the name inside the archive. Archives from before
            # FILEARCHIVENAME, and upstream's, only have FILENAME.
            archive_name = (
                entry.get("FILEARCHIVENAME") or entry.get("FILENAME")
            )
            if archive_name:
                manifest_files[archive_name] = entry

    hash_mismatches = []
    unlisted_files = []
    stage = "the case"

    try:
        with get_session() as session:
            _clear_case_tables(session)

            for table_name, model_class, csv_path in found_tables:
                stage = table_name
                columns = get_column_names(model_class)
                column_objects = (
                    {col.name: col for col in model_class.__table__.columns}
                )
                count = 0

                with open(csv_path, "r", newline="", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        row = canonical_row(table_name, row)
                        record_data = {}
                        for col_name in columns:
                            if col_name in row:
                                raw_value = row[col_name]
                                # Skip binary columns
                                if raw_value == "[BINARY_DATA]":
                                    continue
                                record_data[col_name] = deserialize_value(
                                    raw_value,
                                    column_objects[col_name],
                                )
                        # Preserve original IDs for relational integrity
                        # (don't delete the id field — keep it)
                        session.add(model_class(**record_data))
                        count += 1

                # Flushed table by table, so a bad row is reported against
                # the table it is in.
                session.flush()
                imported_tables.append(f"{table_name} ({count})")
                total_records += count

            stage = "the attachments"
            if files_dir.exists():
                session.query(UploadedFiles).delete()
                for file_path in sorted(files_dir.iterdir()):
                    if not file_path.is_file():
                        continue

                    with open(file_path, "rb") as f:
                        file_data = f.read()

                    actual_hash = hashlib.sha256(file_data).hexdigest().upper()
                    entry = manifest_files.get(file_path.name)

                    if entry is None:
                        unlisted_files.append(file_path.name)
                    else:
                        expected = entry.get("FILEHASH")
                        if expected and not same_hash(expected, actual_hash):
                            hash_mismatches.append(file_path.name)

                    details = entry or {}
                    new_file = UploadedFiles(
                        FILENAME=details.get("FILENAME") or file_path.name,
                        FILEDATA=file_data,
                        FILESIZE=len(file_data),
                        FILEMIMETYPE=(
                            details.get("FILEMIMETYPE")
                            or "application/octet-stream"
                        ),
                        FILEUPLOADEDBY=(
                            details.get("FILEUPLOADEDBY") or "import"
                        ),
                        FILESHA256=details.get("FILESHA256") or actual_hash,
                        FILEHASHEDDATETIME=details.get("FILEHASHEDDATETIME"),
                    )
                    session.add(new_file)
                    files_imported += 1
                session.flush()

            stage = "the audit record"
            record_audit(
                session,
                action="IMPORT",
                table_name="(all case tables)",
                summary=f"{total_records} rows, {files_imported} files",
                after={
                    "source": str(zip_file),
                    "exported": manifest.get("export_date", "unknown"),
                    "hash_mismatches": hash_mismatches,
                    "files_not_in_manifest": unlisted_files,
                },
            )

    except Exception as err:
        _report_failure(
            "Nothing was imported and the case is unchanged. The problem "
            f"was in {stage}.",
            err,
        )
        return

    if hash_mismatches or unlisted_files:
        problems = []
        if hash_mismatches:
            problems.append(
                "Files whose contents do not match the manifest hash:\n"
                + "\n".join(hash_mismatches)
            )
        if unlisted_files:
            problems.append(
                "Files present in the archive but absent from the "
                "manifest:\n" + "\n".join(unlisted_files)
            )
        ui.notify(
            "WARNING — this archive failed integrity checks.\n\n"
            + "\n\n".join(problems)
            + "\n\nThe import completed and has been recorded in the "
            "audit trail. Treat these files as unverified.",
            multi_line=True,
            classes="multi-line-notification",
            type="warning",
            timeout=ZERO_TIMEOUT,
            position="center",
            close_button="OK",
        )

    # An archive from before the date format changed would otherwise be
    # scrambled the first time someone edits a case time or a birth date.
    normalise_legacy_dates()

    table_lines = " | ".join(imported_tables)

    # ----- Success notification -----
    ui.notify(
        f"Data import complete!\n\n"
        f"Tables :  {table_lines}\n\n"
        f"Total records :  {total_records}\n\n"
        f"Files :  {files_imported}",
        multi_line=True,
        classes="multi-line-notification",
        timeout=CONFIRM_TIMEOUT,
        position="bottom",
        close_button="OK",
    )


# ----- JSON EXPORT / IMPORT -----
# A second format alongside the CSV archive: one file rather than a
# folder, with attachments embedded, so a case can be handed to another
# tool or another system as a single artifact.
#
# The SHA-256 recorded at collection travels with each attachment and is
# checked on the way back in, the audit trail is included in the export
# and an import is itself recorded, and the file is staged in a temp
# directory rather than written to the Desktop in the clear and then
# encrypted afterwards.
#
# The layout follows upstream's -- capitalised table names, attachments
# under files.records with the bytes in FILEDATA_b64 -- and the importer
# still reads this branch's earlier 1.0 layout.

JSON_FORMAT_VERSION = "1.2"


def _row_to_json(record, columns: list) -> dict:
    """Converts one row to JSON-safe values."""
    import base64

    row = {}
    for name in columns:
        value = getattr(record, name)
        if isinstance(value, datetime):
            row[name] = value.isoformat()
        elif isinstance(value, (bytes, bytearray)):
            row[name] = base64.b64encode(bytes(value)).decode("ascii")
        else:
            row[name] = value
    return row


def _json_to_value(value, column):
    """Converts a JSON value back to the column's Python type."""
    import base64
    from sqlalchemy import Boolean, DateTime, Float, Integer, LargeBinary

    if value is None:
        return None

    column_type = column.type

    if isinstance(column_type, LargeBinary):
        return base64.b64decode(value)

    if isinstance(column_type, Boolean):
        if isinstance(value, bool):
            return value
        return str(value).lower() in ("true", "1", "yes", "t")

    if isinstance(column_type, Integer):
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    if isinstance(column_type, Float):
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    if isinstance(column_type, DateTime):
        try:
            return datetime.fromisoformat(str(value))
        except (TypeError, ValueError):
            return None

    return value


# ----- JSON EXPORT FUNCTION -----

def export_vector_to_json(
        password: Optional[str] = None,
        destination: Optional[Path] = None,
) -> Optional[ExportResult]:
    """Exports the whole case to a single JSON file.

    Attachments are embedded as base64 alongside the SHA-256 recorded
    when they were collected, so the file is self-contained and its
    contents can be checked on the way back in.

    With a password the JSON is sealed in an AES-256 zip. Returns the
    finished file's path, or None if the export failed. It is written to
    `destination` -- a fresh staging folder when none is given, for the
    caller to hand to the browser as a download.
    """
    from models import UploadedFiles

    folder_name = get_case_info_for_folder_name()
    if not folder_name:
        return None

    payload = {
        "export_metadata": {
            "export_date": datetime.now().isoformat(),
            "format_version": JSON_FORMAT_VERSION,
            "case_folder": folder_name,
            "application": "VECTOR",
        },
        "tables": {},
        "files": {
            "record_count": 0,
            "records": []
        },
    }

    total_records = 0

    for model_class, table_name in get_exportable_models():
        columns = get_column_names(model_class)
        try:
            with get_session() as session:
                rows = [
                    _row_to_json(record, columns)
                    for record in session.query(model_class).all()
                ]
        except Exception as err:
            _report_failure(
                f"The export stopped while reading {table_name}. "
                "Nothing was downloaded.",
                err,
            )
            return None

        payload["tables"][table_name] = {
            "record_count": len(rows),
            "records": rows,
        }
        total_records += len(rows)

    # ----- Attachments, with their collection hashes -----
    import base64

    integrity_failures = []
    try:
        with get_session() as session:
            for uploaded in session.query(UploadedFiles).all():
                if not uploaded.FILEDATA:
                    continue

                current_hash = (
                    hashlib.sha256(uploaded.FILEDATA).hexdigest().upper()
                )
                recorded = uploaded.FILESHA256 or ""
                matches = (not recorded) or same_hash(
                    recorded, current_hash
                )
                if not matches:
                    integrity_failures.append(
                        uploaded.FILENAME or "(unnamed)"
                    )

                payload["files"]["records"].append(
                    {
                        "FILENAME": uploaded.FILENAME,
                        "FILESIZE": uploaded.FILESIZE,
                        "FILEMIMETYPE": uploaded.FILEMIMETYPE,
                        "FILEUPLOADEDBY": uploaded.FILEUPLOADEDBY,
                        "FILESHA256": recorded or None,
                        "FILEHASHEDDATETIME": uploaded.FILEHASHEDDATETIME,
                        "FILEHASH": current_hash,
                        "FILEHASHMATCHES": matches,
                        "FILEDATA_b64": base64.b64encode(
                            uploaded.FILEDATA
                        ).decode("ascii"),
                    }
                )
    except Exception as err:
        # Carrying on would hand over an export without its attachments,
        # under a message saying it was complete.
        _report_failure(
            "The export stopped while adding the attachments. Nothing "
            "was downloaded.",
            err,
        )
        return None

    file_records = payload["files"]["records"]
    payload["files"]["record_count"] = len(file_records)
    payload["export_metadata"]["total_records"] = total_records
    payload["export_metadata"]["total_files"] = len(file_records)
    payload["export_metadata"]["integrity_failures"] = integrity_failures

    if integrity_failures:
        ui.notify(
            "WARNING: these attachments no longer match the SHA-256 "
            "recorded when they were collected:\n"
            + "\n".join(integrity_failures)
            + "\nThe export still completed. Investigate before relying "
            "on these files.",
            multi_line=True,
            classes="multi-line-notification",
            type="warning",
            timeout=ZERO_TIMEOUT,
            position="center",
            close_button="OK",
        )

    # ----- Write it, staging in a temp directory -----
    remove_stale_staging()
    destination = (
        Path(destination) if destination else new_staging_dir("vector_export_")
    )
    work_dir = new_staging_dir("vector_export_")
    staged_json = work_dir / f"{folder_name}.json"

    try:
        with open(staged_json, "w", encoding="utf-8") as handle:
            json.dump(
                payload,
                handle,
                indent=4,
                ensure_ascii=False,
                default=str,
            )

        if password:
            final_path = destination / f"{folder_name}.json.zip"
            with pyzipper.AESZipFile(
                final_path,
                "w",
                compression=pyzipper.ZIP_DEFLATED,
                encryption=pyzipper.WZ_AES,
            ) as archive:
                archive.setpassword(password.encode("utf-8"))
                archive.setencryption(pyzipper.WZ_AES, nbits=256)
                archive.write(staged_json, arcname=staged_json.name)
        else:
            final_path = destination / staged_json.name
            shutil.copy2(staged_json, final_path)

    except Exception as err:
        _report_failure(
            "Could not write the JSON export. Nothing was downloaded.",
            err)
        return None
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)

    try:
        with get_session() as session:
            case = session.query(Cases).order_by(Cases.Z_PK).first()

            record_audit(
                session,
                action="EXPORT",
                table_name="(all case tables)",
                summary=f"Exported JSON data for Case No. {case.CASENUMBER}",
                after={
                    "destination": str(final_path.name),
                    "date/time": payload.get("export_metadata", {}).get(
                        "export_date",
                        "unknown",
                    ),
                    "format_version": payload.get("export_metadata", {}).get(
                        "format_version",
                        "unknown",
                    ),
                    "records": total_records,
                    "files": len(file_records),
                    "integrity_failures": integrity_failures,
                    "encrypted": password is not None and len(password) > 0,
                }
            )
    except Exception as err:
        # Named the audit record through a "stage" set inside the try, so
        # a failure before it was set raised again here; and printed the
        # raw error to the console rather than logging it.
        _report_failure(
            "The JSON export was made but could not be recorded in the "
            "audit trail, so it was not handed over. Nothing was "
            "downloaded.",
            err,
        )
        return None

    encrypted_note = " (AES-256 encrypted)" if password else ""

    message = (
        f"Exporting data to JSON{encrypted_note}...\n"
        f"Total records :  {total_records}\n"
        f"Attachments embedded :  {len(file_records)}\n"
        f"Output will be named :  {final_path.name}"
    )

    return ExportResult(zip_path=final_path, message=message)


# ----- JSON IMPORT FUNCTION -----

def import_vector_from_json(
        source: str,
        password: Optional[str] = None,
) -> None:
    """Restores a case from a JSON export, replacing what is loaded.

    Accepts the .json directly or the encrypted .json.zip. Attachments
    are checked against the hash recorded in the file, and the import
    itself is written to the audit trail -- which is never overwritten
    by the one in the export, so the receiving machine keeps its own
    history.
    """
    source_path = Path(str(source).strip("\"'"))
    if not source_path.exists():
        ui.notify(
            f"{source_path.name} not found.",
            type="warning",
            timeout=WARN_TIMEOUT,
            position="center",
            close_button="OK",
        )
        return

    staging = (
        Path(tempfile.mkdtemp(prefix="vector_json_import_"))
        if source_path.suffix.lower() == ".zip" else None
    )
    try:
        _import_json_file(source, source_path, password, staging)
    finally:
        # However the import ended, the unwrapped case goes.
        if staging is not None:
            shutil.rmtree(staging, ignore_errors=True)


def _import_json_file(
        source: str,
        source_path: Path,
        password: Optional[str],
        staging: Optional[Path],
) -> None:
    """The JSON import itself. An archive is unwrapped into staging,
    which the caller removes however this ends."""
    from models import UploadedFiles

    # ----- Unwrap an encrypted archive -----
    if staging is not None:
        try:
            with pyzipper.AESZipFile(source_path, "r") as archive:
                if password:
                    archive.setpassword(password.encode("utf-8"))
                _extract_wanted(archive, staging, _is_json_import_member)
        except ArchiveTooLarge as err:
            _refuse_large_archive(err)
            return
        except RuntimeError:
            ui.notify(
                "Could not open that archive. If it is encrypted, check "
                "the password.",
                type="warning",
                timeout=WARN_TIMEOUT,
                position="center",
                close_button="OK",
            )
            return
        except Exception as err:
            # A damaged archive: a bad checksum, a broken entry.
            _report_failure(
                "Could not open that archive; it may be damaged. Nothing "
                "was imported, and the case is unchanged.",
                err,
            )
            return

        candidates = list(staging.rglob("*.json"))
        if not candidates:
            ui.notify(
                "No .json file inside that archive.",
                type="warning",
                timeout=WARN_TIMEOUT,
                position="center",
                close_button="OK",
            )
            return
        source_path = candidates[0]

    try:
        with open(source_path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (json.JSONDecodeError, OSError, UnicodeDecodeError) as err:
        ui.notify(
            f"Could not read that file → {err}.",
            type="warning",
            timeout=WARN_TIMEOUT,
            position="center",
            close_button="OK",
        )
        return

    if not isinstance(payload, dict) or "tables" not in payload:
        ui.notify(
            "That is not a VECTOR JSON export - it has no 'tables' "
            "section.",
            type="warning",
            timeout=WARN_TIMEOUT,
            position="center",
            close_button="OK",
        )
        return

    problems, attachments = _check_json_export(payload)
    if problems:
        _refuse_import(problems)
        return

    models_by_name = get_all_models()
    imported = []
    total_records = 0
    files_imported = 0
    stage = "the case"

    # ----- Replace the case, all or nothing -----
    # One transaction, as in the CSV import, so a failure leaves the case
    # exactly as it was.
    try:
        with get_session() as session:
            _clear_case_tables(session)

            for raw_name, table_data in payload["tables"].items():
                table_name = canonical_table_name(raw_name)
                model_class = models_by_name.get(table_name)
                if model_class is None:
                    # The audit trail is exported but never restored over
                    # the local one; anything else unknown is skipped.
                    continue
                stage = table_name

                column_objects = {
                    column.name: column
                    for column in model_class.__table__.columns
                }
                records = table_data.get("records", [])
                for row in records:
                    values = {
                        name: _json_to_value(value, column_objects[name])
                        for name, value in canonical_row(
                            table_name, row
                        ).items()
                        if name in column_objects
                    }
                    session.add(model_class(**values))

                # Flushed table by table, so a bad row is reported against
                # the table it is in.
                session.flush()
                imported.append(f"{table_name} ({len(records)})")
                total_records += len(records)

            stage = "the attachments"
            session.query(UploadedFiles).delete()
            for entry, raw in attachments:
                actual_hash = hashlib.sha256(raw).hexdigest().upper()
                session.add(
                    UploadedFiles(
                        FILENAME=entry.get("FILENAME") or "imported",
                        FILEDATA=raw,
                        FILESIZE=entry.get("FILESIZE") or len(raw),
                        FILEMIMETYPE=(
                            entry.get("FILEMIMETYPE")
                            or "application/octet-stream"
                        ),
                        FILEUPLOADEDBY=(
                            entry.get("FILEUPLOADEDBY") or "import"
                        ),
                        FILESHA256=entry.get("FILESHA256") or actual_hash,
                        FILEHASHEDDATETIME=entry.get("FILEHASHEDDATETIME"),
                    )
                )
                files_imported += 1
            session.flush()

            stage = "the audit record"
            record_audit(
                session,
                action="IMPORT",
                table_name="(all case tables)",
                summary=f"JSON: {total_records} rows, {files_imported} files",
                after={
                    "source": str(source),
                    "exported": payload.get("export_metadata", {}).get(
                        "export_date",
                        "unknown",
                    ),
                    "format_version": payload.get("export_metadata", {}).get(
                        "format_version",
                        "unknown",
                    ),
                },
            )

    except Exception as err:
        _report_failure(
            "Nothing was imported, and the case is unchanged. The problem "
            f"was in {stage}.",
            err,
        )
        return

    normalise_legacy_dates()

    tables = " | ".join(imported)

    ui.notify(
        f"Data import complete.\n\n"
        f"Tables :  {tables}\n\n"
        f"Total records :  {total_records}\n\n"
        f"Files :  {files_imported}",
        multi_line=True,
        classes="multi-line-notification",
        timeout=CONFIRM_TIMEOUT,
        position="bottom",
        close_button="OK",
    )


def needs_password(path) -> bool:
    """Whether an exported file is sealed with a password.

    Read from the archive itself -- each entry in a ZIP records whether it
    is encrypted -- so nobody has to remember, or guess, before importing.
    """
    candidate = Path(path)
    if candidate.suffix.lower() != ".zip":
        return False
    try:
        with pyzipper.AESZipFile(candidate, "r") as archive:
            return any(info.flag_bits & 0x1 for info in archive.infolist())
    except Exception:
        # Anything unreadable is left to the importer, which opens it and
        # says what is wrong with it.
        return False


def looks_like_json_export(path: str) -> bool:
    """Whether a file is a JSON export rather than the CSV archive.

    Both formats can arrive as a .zip, so the suffix alone does not
    settle it. An encrypted archive cannot be read without the password,
    but its entry names are still listed, which is enough.

    Anything unreadable falls back to False -- the CSV reader gives the
    clearer message when handed something it does not recognise.
    """
    candidate = Path(str(path).strip("\"'"))

    if candidate.suffix.lower() == ".json":
        return True

    if candidate.suffix.lower() != ".zip":
        return False

    try:
        with pyzipper.AESZipFile(candidate, "r") as archive:
            names = [name.lower() for name in archive.namelist()]
    except Exception:
        # Anything unreadable is not a JSON export. The CSV importer then
        # opens it, and says what is wrong with it.
        return False

    has_json = any(name.endswith(".json") for name in names)
    has_csv = any(name.endswith(".csv") for name in names)

    # The CSV archive also carries export_manifest.json, so a JSON
    # export is the one with JSON and no CSVs.
    return has_json and not has_csv
