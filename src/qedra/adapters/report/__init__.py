"""Report renderers: turn a Report into JSON, Markdown, or console output."""

from qedra.adapters.report.json_report import to_json
from qedra.adapters.report.markdown import to_markdown

__all__ = ["to_json", "to_markdown"]
