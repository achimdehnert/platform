# ADR-058 Testing Check — patch for tools/repo_checker.py
#
# INSERT this function before check_repo() in repo_checker.py,
# then add check_testing() call inside check_repo().
#
# In check_repo(), after check_django_config line, add:
#   report.results.extend(check_testing(repo_path, config))


def check_testing(repo_path, config):
    """Check ADR-058 testing infrastructure compliance."""
    from pathlib import Path
    results = []
    cat = "testing"

    tests_candidates = [repo_path / "tests", repo_path / "src" / "tests"]
    tests_dir = next((p for p in tests_candidates if p.exists()), None)

    if tests_dir is None:
        results.append(CheckResult(
            cat, "tests_dir", Severity.WARNING,
            "No tests/ directory found",
        ))
        return results

    results.append(CheckResult(
        cat, "tests_dir", Severity.OK,
        f"{tests_dir.relative_to(repo_path)} exists",
    ))

    conftest = tests_dir / "conftest.py"
    if not conftest.exists():
        results.append(CheckResult(
            cat, "conftest", Severity.WARNING,
            "tests/conftest.py missing",
            str(conftest),
        ))
    else:
        content = read_file(conftest)
        if content and "platform_context.testing" in content:
            results.append(CheckResult(
                cat, "conftest_platform", Severity.OK,
                "conftest.py imports platform_context.testing",
                str(conftest),
            ))
        else:
            results.append(CheckResult(
                cat, "conftest_platform", Severity.WARNING,
                "conftest.py does not import platform_context.testing"
                " (ADR-058)",
                str(conftest),
            ))

    test_auth = tests_dir / "test_auth.py"
    if not test_auth.exists():
        results.append(CheckResult(
            cat, "test_auth", Severity.WARNING,
            "tests/test_auth.py missing — auth/access control tests"
            " required (ADR-058 A2)",
            str(test_auth),
        ))
    else:
        content = read_file(test_auth)
        if content and "assert_login_required" in content:
            results.append(CheckResult(
                cat, "test_auth", Severity.OK,
                "test_auth.py uses assert_login_required",
                str(test_auth),
            ))
        else:
            results.append(CheckResult(
                cat, "test_auth", Severity.WARNING,
                "test_auth.py exists but does not use assert_login_required",
                str(test_auth),
            ))

    req_test_candidates = [
        repo_path / "requirements-test.txt",
        repo_path / "requirements" / "test.txt",
        repo_path / "requirements" / "dev.txt",
    ]
    req_test = next((p for p in req_test_candidates if p.exists()), None)
    if req_test is None:
        results.append(CheckResult(
            cat, "requirements_test", Severity.WARNING,
            "No requirements-test.txt found (ADR-058)",
        ))
    else:
        content = read_file(req_test)
        if content and "platform-context" in content:
            results.append(CheckResult(
                cat, "requirements_platform", Severity.OK,
                "platform-context[testing] in"
                f" {req_test.relative_to(repo_path)}",
                str(req_test),
            ))
        else:
            results.append(CheckResult(
                cat, "requirements_platform", Severity.WARNING,
                f"{req_test.relative_to(repo_path)}"
                " missing platform-context[testing] (ADR-058)",
                str(req_test),
            ))

    pyproject = repo_path / "pyproject.toml"
    if pyproject.exists():
        content = read_file(pyproject)
        if content and "pytest.ini_options" in content:
            results.append(CheckResult(
                cat, "pytest_config", Severity.OK,
                "pyproject.toml has [tool.pytest.ini_options]",
                str(pyproject),
            ))
        else:
            results.append(CheckResult(
                cat, "pytest_config", Severity.WARNING,
                "pyproject.toml missing [tool.pytest.ini_options]",
                str(pyproject),
            ))

    return results
