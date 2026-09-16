import os

from dotenv import load_dotenv

from box_client import get_box_client
from metadata import apply_embedded_metadata_to_template
from representations import fetch_representation

load_dotenv()

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tiff", ".tif", ".heic", ".gif", ".webp"}


def process_folder_images(client, folder_id: str, template_key: str) -> None:
    """List image files in a folder, fetch embedded_metadata, and apply the template."""
    marker = None
    total = 0
    processed = 0

    while True:
        items = client.folders.get_folder_items(
            folder_id,
            fields=["id", "name", "type"],
            limit=100,
            marker=marker,
            usemarker=True,
        )

        for item in items.entries:
            if item.type != "file":
                continue
            ext = "." + item.name.rsplit(".", 1)[-1].lower() if "." in item.name else ""
            if ext not in IMAGE_EXTENSIONS:
                continue

            total += 1
            print(f"\nProcessing [{total}]: {item.name} (id: {item.id})")

            try:
                meta_bytes = fetch_representation(
                    client=client,
                    file_id=item.id,
                    rep_hint="[embedded_metadata]",
                    asset_path="",
                )
                if not meta_bytes:
                    continue

                apply_embedded_metadata_to_template(
                    client=client,
                    file_id=item.id,
                    embedded_metadata_bytes=meta_bytes,
                    template_key=template_key,
                )
                processed += 1
            except Exception as error:
                print(f"  Failed to process {item.name}: {error}")

        next_marker = getattr(items, "next_marker", None)
        if not next_marker:
            break
        marker = next_marker

    print(f"\nDone. Processed {processed} of {total} image(s) in folder {folder_id}.")


if __name__ == "__main__":
    client = get_box_client()
    process_folder_images(
        client,
        os.getenv("BOX_FOLDER_ID"),
        os.getenv("BOX_METADATA_TEMPLATE_KEY"),
    )
