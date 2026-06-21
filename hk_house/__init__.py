"""HK-House: Hong Kong property price data pipelines.

Each source has an independent pipeline (fetch -> parse -> transform) that
emits records in the shared base schema defined in `hk_house.models.base`.
"""

__version__ = "0.1.0"
