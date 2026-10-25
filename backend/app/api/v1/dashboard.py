"""VIXOR — Dashboard API endpoints.

GET /dashboard/summary - Summary stats (ownership-checked via projects).
GET /dashboard/trends - Trend data (ownership-checked via projects).
"""

from fastapi import APIRouter, Depends

from app.core.rbac import RequireViewer

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get(
    "/summary",
    response_model=dict,
    summary="Dashboard summary stats (ownership-checked)",
)
async def get_dashboard_summary(
    current_user: dict = Depends(RequireViewer),
):
    from app.deps import get_db as get_db_dep

    db = get_db_dep()

    from app.models.asset import Asset
    from app.models.finding import Finding
    from app.models.project import Project
    from app.models.scan import Scan

    user_id = current_user.get("user_id")
    user_role = current_user.get("role", "viewer")

    # Build base query with ownership filter
    if user_role == "admin":
        project_filter = None
    else:
        project_filter = Project.owner_id == user_id

    # Count projects
    if project_filter is not None:
        total_projects = db.query(Project).filter(project_filter).count()
    else:
        total_projects = db.query(Project).count()

    # Count domains
    from app.models.domain import Domain

    if project_filter is not None:
        total_domains = (
            db.query(Domain)
            .join(Project, Domain.project_id == Project.id)
            .filter(project_filter)
            .count()
        )
    else:
        total_domains = db.query(Domain).count()

    # Count assets
    if project_filter is not None:
        total_assets = (
            db.query(Asset)
            .join(Domain, Asset.domain_id == Domain.id)
            .join(Project, Domain.project_id == Project.id)
            .filter(project_filter)
            .count()
        )
    else:
        total_assets = db.query(Asset).count()

    # Count scans
    if project_filter is not None:
        total_scans = (
            db.query(Scan)
            .join(Project, Scan.project_id == Project.id)
            .filter(project_filter)
            .count()
        )
    else:
        total_scans = db.query(Scan).count()

    # Count findings by severity
    if project_filter is not None:
        findings_query = (
            db.query(Finding)
            .join(Scan, Finding.scan_id == Scan.id)
            .join(Project, Scan.project_id == Project.id)
            .filter(project_filter)
        )
    else:
        findings_query = db.query(Finding)

    critical = findings_query.filter(Finding.severity_raw == "critical").count()
    high = findings_query.filter(Finding.severity_raw == "high").count()
    medium = findings_query.filter(Finding.severity_raw == "medium").count()
    low = findings_query.filter(Finding.severity_raw == "low").count()

    db.close()

    return {
        "total_projects": total_projects,
        "total_domains": total_domains,
        "total_assets": total_assets,
        "total_scans": total_scans,
        "total_findings": critical + high + medium + low,
        "critical_findings": critical,
        "high_findings": high,
        "medium_findings": medium,
        "low_findings": low,
        "open_findings": critical + high + medium + low,
    }


@router.get(
    "/trends",
    response_model=dict,
    summary="Dashboard trend data (ownership-checked)",
)
async def get_dashboard_trends(
    current_user: dict = Depends(RequireViewer),
):
    from app.deps import get_db as get_db_dep

    db = get_db_dep()

    from app.models.project import Project
    from app.models.scan import Scan

    user_id = current_user.get("user_id")
    user_role = current_user.get("role", "viewer")

    if user_role == "admin":
        project_filter = None
    else:
        project_filter = Project.owner_id == user_id

    if project_filter is not None:
        scans = (
            db.query(Scan)
            .join(Project, Scan.project_id == Project.id)
            .filter(project_filter)
            .all()
        )
    else:
        scans = db.query(Scan).all()

    db.close()

    # Group scans by date
    from collections import defaultdict

    trends: dict[str, int] = defaultdict(int)
    for scan in scans:
        if scan.created_at:
            date_str = scan.created_at.strftime("%Y-%m-%d")
            trends[date_str] += 1

    return {
        "trends": [
            {"date": date, "count": count} for date, count in sorted(trends.items())
        ],
    }
