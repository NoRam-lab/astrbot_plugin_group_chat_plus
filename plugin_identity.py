"""Shared identity constants for the local-signed Group Chat Plus build."""

PLUGIN_PACKAGE_NAME = "astrbot_plugin_group_chat_plus"
PLUGIN_LOCAL_NAME = "noram_group_chat_plus"
PLUGIN_LEGACY_NAME = "noram"
PLUGIN_DATA_NAME = PLUGIN_LEGACY_NAME
PLUGIN_REPO_URL = ""


def get_legacy_plugin_data_dir(star_tools):
    """Return the legacy data dir while tolerating older test doubles."""
    try:
        return star_tools.get_data_dir(PLUGIN_DATA_NAME)
    except TypeError:
        return star_tools.get_data_dir()
