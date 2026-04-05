from cordis import __version__

PACKAGE_NAME = "cordis"


def get_version_payload() -> dict[str, str]:
    return {"name": PACKAGE_NAME, "version": __version__}
