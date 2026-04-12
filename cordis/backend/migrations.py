from sqlalchemy import MetaData

from cordis.backend.config import build_config
from cordis.backend.models.base import DatabaseModel


def get_alembic_database_url() -> str:
    return build_config().database.sync_db_url


def get_alembic_target_metadata() -> MetaData:
    return DatabaseModel.metadata
