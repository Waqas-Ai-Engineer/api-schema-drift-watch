"""api-schema-drift-watch: detect schema drift in JSON API responses."""
from .schema import infer_schema, merge_schemas
from .diff import diff_schemas, Change

__all__ = ["infer_schema", "merge_schemas", "diff_schemas", "Change"]
__version__ = "1.0.0"
