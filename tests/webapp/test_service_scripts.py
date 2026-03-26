from pathlib import Path
import json
import subprocess
import time


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"


def _run_powershell_script(script_name: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(SCRIPTS_DIR / script_name),
            *args,
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_start_script_dry_run_outputs_expected_commands(tmp_path):
    service_root = tmp_path / "service"

    result = _run_powershell_script(
        "start_internal_webapp.ps1",
        "-ServiceRoot",
        str(service_root),
        "-Port",
        "8123",
        "-DryRun",
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)

    assert payload["status"] == "dry_run"
    assert payload["python_path"].endswith(r".venv\Scripts\python.exe")
    assert payload["base_url"] == "http://127.0.0.1:8123"
    assert payload["webapp_args"] == [
        "-m",
        "uvicorn",
        "scripts.run_internal_webapp:app",
        "--host",
        "127.0.0.1",
        "--port",
        "8123",
    ]
    assert payload["worker_args"] == ["scripts/run_internal_worker.py"]


def test_check_script_reports_not_running_when_state_file_missing(tmp_path):
    service_root = tmp_path / "service"

    result = _run_powershell_script(
        "check_internal_webapp.ps1",
        "-ServiceRoot",
        str(service_root),
    )

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["status"] == "not_running"
    assert payload["state_file"].endswith("service.json")


def test_stop_script_dry_run_is_noop_without_state_file(tmp_path):
    service_root = tmp_path / "service"

    result = _run_powershell_script(
        "stop_internal_webapp.ps1",
        "-ServiceRoot",
        str(service_root),
        "-DryRun",
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "not_running"
    assert payload["service_root"] == str(service_root)


def test_stop_script_waits_for_processes_to_exit(tmp_path):
    service_root = tmp_path / "service"
    service_root.mkdir(parents=True, exist_ok=True)
    state_file = service_root / "service.json"
    proc_one = subprocess.Popen(
        ["powershell", "-NoProfile", "-Command", "Start-Sleep -Seconds 60"]
    )
    proc_two = subprocess.Popen(
        ["powershell", "-NoProfile", "-Command", "Start-Sleep -Seconds 60"]
    )
    try:
        state_file.write_text(
            json.dumps(
                {
                    "webapp_pid": proc_one.pid,
                    "worker_pid": proc_two.pid,
                }
            ),
            encoding="utf-8",
        )

        result = _run_powershell_script(
            "stop_internal_webapp.ps1",
            "-ServiceRoot",
            str(service_root),
        )

        assert result.returncode == 0, result.stderr
        payload = json.loads(result.stdout)
        assert payload["status"] == "stopped"

        for _ in range(10):
            if proc_one.poll() is not None and proc_two.poll() is not None:
                break
            time.sleep(0.2)

        assert proc_one.poll() is not None
        assert proc_two.poll() is not None
        assert not state_file.exists()
    finally:
        proc_one.kill()
        proc_two.kill()


def test_start_script_and_check_script_report_running_state(tmp_path):
    service_root = tmp_path / "service"
    port = "8137"

    start_result = _run_powershell_script(
        "start_internal_webapp.ps1",
        "-ServiceRoot",
        str(service_root),
        "-Port",
        port,
    )

    assert start_result.returncode == 0, start_result.stderr
    start_payload = json.loads(start_result.stdout)
    assert start_payload["status"] == "started"

    try:
        check_payload = None
        check_result = None
        for _ in range(20):
            check_result = _run_powershell_script(
                "check_internal_webapp.ps1",
                "-ServiceRoot",
                str(service_root),
                "-Port",
                port,
            )
            check_payload = json.loads(check_result.stdout)
            if check_result.returncode == 0 and check_payload["status"] == "running":
                break
            time.sleep(0.5)

        assert check_result is not None
        assert check_result.returncode == 0, check_result.stderr
        assert check_payload is not None
        assert check_payload["status"] == "running"
        assert check_payload["http_status"] == 200

        time.sleep(1.5)
        stable_result = _run_powershell_script(
            "check_internal_webapp.ps1",
            "-ServiceRoot",
            str(service_root),
            "-Port",
            port,
        )
        stable_payload = json.loads(stable_result.stdout)

        assert stable_result.returncode == 0, stable_result.stderr
        assert stable_payload["status"] == "running"
        assert stable_payload["http_status"] == 200
    finally:
        _run_powershell_script(
            "stop_internal_webapp.ps1",
            "-ServiceRoot",
            str(service_root),
            "-Port",
            port,
        )


def test_stop_script_cleans_up_started_service_processes(tmp_path):
    service_root = tmp_path / "service"
    port = "8138"

    start_result = _run_powershell_script(
        "start_internal_webapp.ps1",
        "-ServiceRoot",
        str(service_root),
        "-Port",
        port,
    )

    assert start_result.returncode == 0, start_result.stderr

    try:
        for _ in range(20):
            check_result = _run_powershell_script(
                "check_internal_webapp.ps1",
                "-ServiceRoot",
                str(service_root),
                "-Port",
                port,
            )
            if check_result.returncode == 0:
                break
            time.sleep(0.5)

        stop_result = _run_powershell_script(
            "stop_internal_webapp.ps1",
            "-ServiceRoot",
            str(service_root),
            "-Port",
            port,
        )
        dry_run_result = _run_powershell_script(
            "stop_internal_webapp.ps1",
            "-ServiceRoot",
            str(service_root),
            "-Port",
            port,
            "-DryRun",
        )

        assert stop_result.returncode == 0, stop_result.stderr
        assert dry_run_result.returncode == 0, dry_run_result.stderr
        assert json.loads(dry_run_result.stdout)["status"] == "not_running"
    finally:
        _run_powershell_script(
            "stop_internal_webapp.ps1",
            "-ServiceRoot",
            str(service_root),
            "-Port",
            port,
        )
