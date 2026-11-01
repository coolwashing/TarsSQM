from app.models.attachment import SysAttachment
from app.models.main_data import SqmSupplier, SqmProject, SqmPart
from app.models.sqm_quality import SqmPartDev, SqmQualityIssue
from app.models.ctq import SqmCtq
from app.models.kb import SqmKbDoc

__all__ = [
    "SysAttachment",
    "SqmSupplier",
    "SqmProject",
    "SqmPart",
    "SqmPartDev",
    "SqmQualityIssue",
    "SqmCtq",
    "SqmKbDoc"
]
