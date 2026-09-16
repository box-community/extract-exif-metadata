import time

from box_sdk_gen import BoxClient
from box_sdk_gen.networking.fetch_options import FetchOptions, ResponseFormat
from box_sdk_gen.schemas.file_full import FileFullRepresentationsEntriesStatusStateField


def list_representations(client: BoxClient, file_id: str) -> None:
    """Fetch and print all available representations for a file."""
    file = client.files.get_file_by_id(
        file_id,
        fields=["representations"],
    )
    entries = file.representations.entries

    print("Representations for file", file_id)
    print("-" * 50)
    for rep in entries:
        dims = rep.properties.dimensions if rep.properties and rep.properties.dimensions else ""
        dims_str = f"  |  dimensions: {dims}" if dims else ""
        print(f"  type: {rep.representation}{dims_str}")


def fetch_representation(
    client: BoxClient,
    file_id: str,
    rep_hint: str,
    asset_path: str = "",
    max_wait_seconds: int = 30,
    poll_interval: int = 3,
) -> bytes | None:
    """Request a representation and return its bytes once Box has generated it.

    `embedded_metadata` is on-demand. A `none` state means generation has not
    started — hitting the info URL queues it. The SDK does not poll for you.
    """
    file = client.files.get_file_by_id(
        file_id,
        fields=["representations"],
        x_rep_hints=rep_hint,
    )
    entries = file.representations.entries

    rep = entries[0]
    state = rep.status.state
    state_str = state.value if state else "unknown"
    url_template = rep.content.url_template
    print(f"state: {state_str}  |  url_template: {url_template}")

    if state == FileFullRepresentationsEntriesStatusStateField.NONE:
        print("State is 'none' - triggering generation via info URL...")
        if rep.info and rep.info.url:
            client.make_request(
                FetchOptions(
                    url=rep.info.url,
                    method="GET",
                    response_format=ResponseFormat.NO_CONTENT,
                )
            )
        state = FileFullRepresentationsEntriesStatusStateField.PENDING

    elapsed = 0
    while state == FileFullRepresentationsEntriesStatusStateField.PENDING:
        if elapsed >= max_wait_seconds:
            print(f"Timed out after {max_wait_seconds}s waiting for representation.")
            return None
        print(f"  State is 'pending' - waiting {poll_interval}s... (elapsed: {elapsed}s)")
        time.sleep(poll_interval)
        elapsed += poll_interval
        file = client.files.get_file_by_id(
            file_id,
            fields=["representations"],
            x_rep_hints=rep_hint,
        )
        entries = file.representations.entries
        rep = entries[0]
        state = rep.status.state if rep.status else None

    ready_states = {
        FileFullRepresentationsEntriesStatusStateField.SUCCESS,
        FileFullRepresentationsEntriesStatusStateField.VIEWABLE,
    }
    if state not in ready_states:
        print(f"Representation ended in unexpected state: {state}")
        return None

    url_template = rep.content.url_template
    download_url = url_template.replace("{+asset_path}", asset_path)
    response = client.make_request(
        FetchOptions(
            url=download_url,
            method="GET",
            response_format=ResponseFormat.BINARY,
            follow_redirects=True,
        )
    )
    return response.content.read()
