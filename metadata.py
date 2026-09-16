import json
from datetime import datetime, timezone

from box_sdk_gen import (
    BoxAPIError,
    BoxClient,
    CreateFileMetadataByIdScope,
    UpdateFileMetadataByIdRequestBody,
    UpdateFileMetadataByIdRequestBodyOpField,
    UpdateFileMetadataByIdScope,
)

# Maps Box metadata template field key -> (JSON path, type).
# Types: "date" | "number" | "text"
# [0] refers to the first element of the top-level array.
EMBEDDED_METADATA_FIELD_MAP = {
    "datetime": ("[0].EXIF.DateTimeOriginal", "date"),
    "cameraMake": ("[0].EXIF.Make", "text"),
    "imageWidth": ("[0].File.ImageWidth", "number"),
    "imageHeight": ("[0].File.ImageHeight", "number"),
    "iso": ("[0].EXIF.ISO", "number"),
    "colorProfile": ("[0].ICC_Profile.ProfileDescription", "text"),
    "rights": ("[0].XMP.Rights", "text"),
    "creator": ("[0].XMP.Creator", "text"),
}


def _coerce(value, field_type: str):
    """Convert a raw JSON value to the type expected by the Box metadata template."""
    if field_type == "number":
        return float(value) if "." in str(value) else int(value)
    if field_type == "date":
        # EXIF dates look like "2023:01:15 12:34:56" — Box expects RFC 3339.
        try:
            dt = datetime.strptime(str(value), "%Y:%m:%d %H:%M:%S")
            return dt.replace(tzinfo=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            return str(value)
    return str(value)


def _resolve_path(data, path: str):
    """Walk a dotted path like '[0].EXIF.DateTimeOriginal' into nested data."""
    for part in path.split("."):
        if part.startswith("[") and part.endswith("]"):
            try:
                data = data[int(part[1:-1])]
            except (IndexError, TypeError, ValueError):
                return None
        else:
            if not isinstance(data, dict):
                return None
            data = data.get(part)
        if data is None:
            return None
    return data


def apply_embedded_metadata_to_template(
    client: BoxClient,
    file_id: str,
    embedded_metadata_bytes: bytes,
    template_key: str,
) -> None:
    """Parse embedded_metadata JSON, map fields, and write an enterprise instance.

    Missing fields are omitted. If no mapped fields are present, skip the write.
    Creating metadata only succeeds the first time; on 409 the function JSON-Patch
    updates with op ``add`` so re-runs still succeed when a file omits some fields.
    """
    embedded_metadata = json.loads(embedded_metadata_bytes.decode("utf-8"))
    fields = {}
    for template_field, (path, field_type) in EMBEDDED_METADATA_FIELD_MAP.items():
        value = _resolve_path(embedded_metadata, path)
        if value is not None:
            fields[template_field] = _coerce(value, field_type)
    print(f"Extracted {len(fields)} of {len(EMBEDDED_METADATA_FIELD_MAP)} fields:")
    for k, v in fields.items():
        print(f"  {k}: {v!r} ({type(v).__name__})")
    if not fields:
        print(f"No mapped fields on file {file_id}; skipping metadata write")
        return

    try:
        client.file_metadata.create_file_metadata_by_id(
            file_id=file_id,
            scope=CreateFileMetadataByIdScope.ENTERPRISE,
            template_key=template_key,
            request_body=fields,
        )
        print(f"Metadata created: {template_key} on file {file_id}")
    except BoxAPIError as error:
        if error.response_info.status_code != 409:
            raise
        client.file_metadata.update_file_metadata_by_id(
            file_id=file_id,
            scope=UpdateFileMetadataByIdScope.ENTERPRISE,
            template_key=template_key,
            request_body=[
                UpdateFileMetadataByIdRequestBody(
                    op=UpdateFileMetadataByIdRequestBodyOpField.ADD,
                    path=f"/{key}",
                    value=value,
                )
                for key, value in fields.items()
            ],
        )
        print(f"Metadata updated: {template_key} on file {file_id}")
