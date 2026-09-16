import os

from dotenv import load_dotenv
from box_sdk_gen import (
    BoxClient,
    BoxCCGAuth,
    CCGConfig,
)

load_dotenv()


def get_box_client() -> BoxClient:
    """Authenticate as the application's Service Account using CCG.

    Client Credentials Grant is the recommended auth method for
    server-to-server automations where no end user is present.
    """
    config = CCGConfig(
        client_id=os.getenv("BOX_CLIENT_ID"),
        client_secret=os.getenv("BOX_CLIENT_SECRET"),
        enterprise_id=os.getenv("BOX_ENTERPRISE_ID"),
    )
    auth = BoxCCGAuth(config=config)
    return BoxClient(auth=auth)
