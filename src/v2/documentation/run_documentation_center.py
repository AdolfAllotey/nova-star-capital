from src.v2.documentation.indexing.masterbook_indexer import build_index
from src.v2.documentation.analysis.coverage_engine import build_coverage
from src.v2.documentation.analysis.health_engine import build_health
from src.v2.documentation.reporting.documentation_center_report import main as center_report
from src.v2.documentation.reporting.documentation_quality_issues import main as quality_report


def run_once():
    build_index()
    build_coverage()
    build_health()
    center_report()
    quality_report()


def main():
    # First pass updates generated reports.
    run_once()

    # Second pass re-indexes those generated reports after metadata has been written.
    run_once()


if __name__ == "__main__":
    main()
