import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile


ui_directory = Path(__file__).resolve().parent
tests_directory = ui_directory.parent
repository_root = ui_directory.parents[3]
operator_state = ui_directory / ".auth" / "operator.json"
arguments = list(sys.argv[1:])
run_performance = "--performance" in arguments
if run_performance:
    arguments.remove("--performance")

if not operator_state.is_file():
    raise SystemExit(f"Missing operator storage state: {operator_state}")
if stat.S_IMODE(operator_state.stat().st_mode) != 0o600:
    raise SystemExit("operator.json must have permissions 0600")

with tempfile.TemporaryDirectory(prefix="cc018-ui-") as temporary_directory:
    isolated_root = Path(temporary_directory)
    shutil.copy2(ui_directory / "conftest.py", isolated_root / "conftest.py")
    shutil.copy2(
        ui_directory / "test_workspace_baseline.py",
        isolated_root / "test_workspace_baseline.py",
    )
    test_file = isolated_root / "test_workspace_baseline.py"
    if run_performance:
        test_file = isolated_root / "test_performance_baseline.py"
        shutil.copy2(
            ui_directory / "test_performance_baseline.py",
            test_file,
        )
    fixture_directory = isolated_root / "fixtures"
    fixture_directory.mkdir()
    shutil.copy2(
        tests_directory / "fixtures" / "orm_helpers.py",
        fixture_directory / "orm_helpers.py",
    )
    auth_directory = isolated_root / ".auth"
    auth_directory.mkdir()
    isolated_state = auth_directory / "operator.json"
    shutil.copy2(operator_state, isolated_state)
    os.chmod(isolated_state, 0o600)

    environment = os.environ.copy()
    environment["CC018_EVIDENCE_DIR"] = str(ui_directory / "evidence")
    existing_pythonpath = environment.get("PYTHONPATH")
    environment["PYTHONPATH"] = os.pathsep.join(
        value for value in (str(isolated_root), existing_pythonpath) if value
    )
    command = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        "-c",
        str(repository_root / "pytest.ini"),
        str(test_file),
        *arguments,
    ]
    raise SystemExit(
        subprocess.run(command, cwd=repository_root, env=environment).returncode
    )
