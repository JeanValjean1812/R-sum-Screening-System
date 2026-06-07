"""Document parsing components (résumés and job descriptions)."""

from parsers.jd_parser import JDParser, JDRequirements
from parsers.resume_parser import ResumeParser

__all__ = ["ResumeParser", "JDParser", "JDRequirements"]
