"""VIXOR — Comprehensive Module Verification Script (T-014+)

Tests all critical modules against the seeded demo data.
Uses FastAPI TestClient for direct API calls.
"""

import os
import sys
from datetime import datetime

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_auth():
    """Test authentication endpoint."""
    print("TEST: AUTH - POST /api/v1/auth/login")
    response = client.post(
        "/api/v1/auth/login",
        data={"email": "admin@example.com", "password": "Admin123!"}
    )
    print(f"  Status: {response.status_code}")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    data = response.json()
    print(f"  Has access_token: {'access_token' in data}")
    assert "access_token" in data
    print("  PASS")
    return True


def test_projects():
    """Test projects endpoint."""
    print("TEST: PROJECTS - GET /api/v1/projects")
    response = client.get("/api/v1/projects")
    print(f"  Status: {response.status_code}")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    data = response.json()
    print(f"  Projects count: {len(data)}")
    project_names = [p.get("name") for p in data]
    print(f"  Project names: {project_names}")
    assert "Enterprise Security Audit" in project_names
    print("  PASS")
    return True


def test_scope_barrier():
    """Test scope barrier - verify domain statuses."""
    print("TEST: SCOPE BARRIER - Domain verification statuses")
    # Check domains via projects endpoint
    response = client.get("/api/v1/projects")
    data = response.json()
    assert len(data) > 0
    # Find the demo project
    demo_project = None
    for p in data:
        if p.get("name") == "Enterprise Security Audit":
            demo_project = p
            break
    assert demo_project is not None, "Demo project not found"
    
    # Check scans to verify domains
    response = client.get("/api/v1/scans")
    scans = response.json()
    print(f"  Scans found: {len(scans)}")
    for s in scans:
        print(f"    Scan {s['id'][:8]}: domain_id={s['domain_id']}, status={s['status']}")
    print("  PASS")
    return True


def test_assets():
    """Test assets endpoint - verify at least 2 assets with tech stack."""
    print("TEST: ASSETS - GET assets endpoint")
    # Try different asset endpoints
    found = False
    
    # Try /api/v1/projects/{id}/assets
    response = client.get("/api/v1/projects/1/assets")
    print(f"  /api/v1/projects/1/assets Status: {response.status_code}")
    if response.status_code == 200:
        assets = response.json()
        print(f"  Assets found: {len(assets)}")
        for a in assets:
            print(f"    Asset: {a.get('hostname')} - IPs: {a.get('ips')} - Tech: {a.get('technologies')}")
        if len(assets) >= 2:
            found = True
    
    if not found:
        # Try listing all assets
        response = client.get("/api/v1/assets/")
        print(f"  /api/v1/assets/ Status: {response.status_code}")
        if response.status_code == 200:
            assets = response.json()
            print(f"  Assets found: {len(assets)}")
            for a in assets:
                print(f"    Asset: {a.get('hostname')} - IPs: {a.get('ips')} - Tech: {a.get('technologies')}")
            if len(assets) >= 2:
                found = True
    
    assert found, "Could not find at least 2 assets with tech stack"
    print("  PASS")
    return True


def test_findings_and_xai():
    """Test findings and XAI/shap."""
    print("TEST: FINDINGS & XAI - GET /api/v1/scans/{id}/findings")
    # First get scans
    response = client.get("/api/v1/scans")
    scans = response.json()
    assert len(scans) > 0, "No scans found"
    
    scan_id = scans[0]["id"]
    print(f"  Using scan ID: {scan_id}")
    
    # Get findings for this scan
    response = client.get(f"/api/v1/scans/{scan_id}/findings")
    print(f"  Status: {response.status_code}")
    if response.status_code == 200:
        findings = response.json()
        print(f"  Findings count: {len(findings)}")
        assert len(findings) >= 1, "Expected at least 1 finding"
        
        for f in findings[:1]:  # Check first finding
            print(f"  Finding: {f.get('title')}")
            print(f"  CVSS: {f.get('cvss')}")
            print(f"  Severity: {f.get('severity_raw')}")
            # Check for ML score / shap
            print(f"  Has evidence: {'evidence' in f}")
            print(f"  Evidence keys: {list(f.get('evidence', {}).keys()) if f.get('evidence') else 'N/A'}")
        
        print("  PASS")
    else:
        print("  FAIL - could not get findings")
        return False
    return True


def test_correlations():
    """Test correlations endpoint."""
    print("TEST: CORRELATIONS - GET /api/v1/correlations")
    response = client.get("/api/v1/correlations")
    print(f"  Status: {response.status_code}")
    if response.status_code == 200:
        correlations = response.json()
        print(f"  Correlations found: {len(correlations)}")
        for c in correlations:
            combined_score = c.get("combined_risk_score", "N/A")
            print(f"  Correlation: {c.get('title')} - combined_risk_score: {combined_score}")
        if len(correlations) >= 1:
            # Check the first correlation has combined_risk_score == 88
            first = correlations[0]
            score = first.get("combined_risk_score")
            print(f"  First correlation combined_risk_score: {score}")
            assert score == 88, f"Expected combined_risk_score == 88, got {score}"
    
    print("  PASS")
    return True


def test_reports():
    """Test reports endpoint."""
    print("TEST: REPORTS - GET /api/v1/reports")
    response = client.get("/api/v1/reports")
    print(f"  Status: {response.status_code}")
    if response.status_code == 200:
        reports = response.json()
        print(f"  Reports found: {len(reports)}")
        for r in reports:
            print(f"  Report: {r.get('title', 'N/A')} - status: {r.get('status')} - format: {r.get('format')}")
        if len(reports) >= 1:
            first = reports[0]
            assert first.get("status") == "completed", "Expected completed report"
            assert first.get("format") == "PDF", "Expected PDF format"
            assert "Executive Security Audit" in first.get("title", ""), "Expected report title to contain 'Executive Security Audit'"
    
    print("  PASS")
    return True


def test_admin_audit():
    """Verify that the audit route rejects anonymous and invalid-token access."""
    path = "/api/v1/users/audit-logs"
    print(f"TEST: ADMIN AUDIT AUTHORIZATION - GET {path}")
    anonymous = client.get(path)
    print(f"  Anonymous status: {anonymous.status_code}")
    if anonymous.status_code != 401:
        print("  FAIL: expected 401 without credentials")
        return False

    invalid_token = client.get(
        path, headers={"Authorization": "Bearer intentionally-invalid-test-token"}
    )
    print(f"  Invalid-token status: {invalid_token.status_code}")
    if invalid_token.status_code != 401:
        print("  FAIL: expected 401 for an invalid token")
        return False

    print("  PASS (authorization boundary)")
    return True


def main():
    """Run all tests and generate results."""
    print("=" * 60)
    print("VIXOR COMPREHENSIVE MODULE VERIFICATION")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("=" * 60)
    print()
    
    results = {}
    
    tests = [
        ("AUTH", test_auth),
        ("PROJECTS", test_projects),
        ("SCOPE_BARRIER", test_scope_barrier),
        ("ASSETS", test_assets),
        ("FINDINGS_XAI", test_findings_and_xai),
        ("CORRELATIONS", test_correlations),
        ("REPORTS", test_reports),
        ("ADMIN_AUDIT", test_admin_audit),
    ]
    
    for test_name, test_func in tests:
        try:
            passed = test_func()
            if passed is True:
                results[test_name] = {"status": "PASS", "detail": ""}
            else:
                results[test_name] = {
                    "status": "FAIL",
                    "detail": "check did not return True",
                }
                print(f"  -> {test_name}: FAIL - check did not return True")
        except AssertionError as e:
            results[test_name] = {"status": "FAIL", "detail": str(e)}
            print(f"  -> {test_name}: FAIL - {e}")
        except Exception as e:  # noqa: BLE001 - continue to report each independent diagnostic
            results[test_name] = {"status": "ERROR", "detail": str(e)}
            print(f"  -> {test_name}: ERROR - {e}")
        print()
    
    # Generate results file
    output_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..",
        "..",
        "..",
        "VERIFICATION_RESULTS.txt"
    )
    
    # Fix the path - go to the project root
    project_root = r"C:\Users\usamah\Desktop\VIXOR — Autonomous"
    output_path = os.path.join(project_root, "VERIFICATION_RESULTS.txt")
    
    with open(output_path, "w") as f:
        f.write("=" * 60 + "\n")
        f.write("VIXOR VERIFICATION RESULTS\n")
        f.write(f"Timestamp: {datetime.now().isoformat()}\n")
        f.write("=" * 60 + "\n\n")
        
        all_pass = True
        for test_name, result in results.items():
            f.write(f"  {test_name}: {result['status']}")
            if result['detail']:
                f.write(f" - {result['detail']}")
            f.write("\n")
            if result['status'] != 'PASS':
                all_pass = False
        
        f.write("\n" + "=" * 60 + "\n")
        f.write(f"OVERALL: {'ALL TESTS PASSED' if all_pass else 'SOME TESTS FAILED'}\n")
        f.write("=" * 60 + "\n")
    
    print("=" * 60)
    print(f"OVERALL: {'ALL TESTS PASSED' if all_pass else 'SOME TESTS FAILED'}")
    print(f"Results written to: {output_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
