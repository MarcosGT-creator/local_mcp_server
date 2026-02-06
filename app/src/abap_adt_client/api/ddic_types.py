"""
Common DDIC object type definitions and mappings.
"""
from typing import Literal, get_args

# Data Preview Object Types (only CDS and DDIC/Tables support data preview)
DDIC_OBJECT_TYPES = Literal[
    "cds",    # CDS Views - support data preview
    "ddic",   # Transparent tables - support data preview
]

# Get all valid type strings for validation
VALID_DDIC_TYPES = get_args(DDIC_OBJECT_TYPES)
