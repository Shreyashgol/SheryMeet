"""ORM model package.

Importing every model here ensures they are all registered on `Base.metadata`
(so Alembic autogenerate and `create_all` see the full schema) and that
relationship forward references (`"Job"`, `"Summary"`, …) resolve.
"""

from app.database.base import Base
from app.models.action_item import ActionItem
from app.models.job import Job
from app.models.processing_log import ProcessingLog
from app.models.summary import Summary
from app.models.transcript import Transcript

__all__ = ["Base", "Job", "Transcript", "Summary", "ActionItem", "ProcessingLog"]
