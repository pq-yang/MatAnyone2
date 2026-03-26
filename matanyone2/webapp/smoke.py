from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
import argparse
import os
import subprocess
import sys
import time

from PIL import Image
import requests


TERMINAL_STATUSES = {
    "completed",
    "completed_with_warning",
    "failed",
    "interrupted",
}
SUCCESS_STATUSES = {"completed", "completed_with_warning"}


@dataclass(slots=True)
class SmokeResult:
    runtime_root: Path
    job_statuses: dict[str, dict]


def wait_for_server(
    session: requests.Session,
    base_url: str,
    *,
    timeout_seconds: float,
    poll_interval_seconds: float,
    sleep=time.sleep,
    monotonic=time.monotonic,
) -> None:
    deadline = monotonic() + timeout_seconds
    while True:
        try:
            response = session.get(f"{base_url}/", timeout=10)
            if response.status_code == 200:
                return
        except requests.RequestException:
            pass

        if monotonic() >= deadline:
            raise TimeoutError(f"webapp did not become ready: {base_url}")
        sleep(poll_interval_seconds)


def submit_job(
    session: requests.Session,
    base_url: str,
    video_path: Path,
    *,
    click_point: tuple[int, int] | None = None,
) -> str:
    with Path(video_path).open("rb") as source:
        upload_response = session.post(
            f"{base_url}/api/uploads",
            files={"video": (video_path.name, source, "video/mp4")},
            timeout=120,
        )
    upload_response.raise_for_status()
    upload_payload = upload_response.json()
    draft_id = upload_payload["draft_id"]

    template_response = session.get(
        f"{base_url}{upload_payload['template_frame_url']}",
        timeout=120,
    )
    template_response.raise_for_status()
    with Image.open(BytesIO(template_response.content)) as image:
        width, height = image.size
    if click_point is None:
        click_point = (width // 2, height // 2)

    click_response = session.post(
        f"{base_url}/api/drafts/{draft_id}/click",
        json={"x": click_point[0], "y": click_point[1], "positive": True},
        timeout=300,
    )
    click_response.raise_for_status()

    save_response = session.post(
        f"{base_url}/api/drafts/{draft_id}/masks",
        timeout=120,
    )
    save_response.raise_for_status()
    mask_name = save_response.json()["mask_name"]

    submit_response = session.post(
        f"{base_url}/api/drafts/{draft_id}/submit",
        json={
            "template_frame_index": 0,
            "selected_masks": [mask_name],
        },
        timeout=120,
    )
    submit_response.raise_for_status()
    return submit_response.json()["job_id"]


def poll_jobs(
    session: requests.Session,
    base_url: str,
    job_ids: list[str],
    *,
    timeout_seconds: float,
    poll_interval_seconds: float,
    sleep=time.sleep,
    monotonic=time.monotonic,
) -> dict[str, dict]:
    deadline = monotonic() + timeout_seconds
    statuses = {}
    queued_seen = {job_id: False for job_id in job_ids[1:]}

    while True:
        all_terminal = True
        retry_iteration = False
        for index, job_id in enumerate(job_ids):
            try:
                response = session.get(f"{base_url}/api/jobs/{job_id}", timeout=30)
            except requests.RequestException:
                retry_iteration = True
                all_terminal = False
                break
            if response.status_code >= 400:
                raise RuntimeError(f"failed to fetch status for {job_id}: {response.status_code}")
            payload = response.json()
            statuses[job_id] = payload
            status = payload["status"]
            if index > 0 and status == "queued":
                queued_seen[job_id] = True
            if status not in TERMINAL_STATUSES:
                all_terminal = False

        if retry_iteration:
            if monotonic() >= deadline:
                raise TimeoutError(f"jobs did not finish before timeout: {job_ids}")
            sleep(poll_interval_seconds)
            continue
        if all_terminal:
            break
        if monotonic() >= deadline:
            raise TimeoutError(f"jobs did not finish before timeout: {job_ids}")
        sleep(poll_interval_seconds)

    for job_id, seen in queued_seen.items():
        if not seen:
            raise AssertionError(f"job {job_id} never entered queued status")

    for job_id, payload in statuses.items():
        if payload["status"] not in SUCCESS_STATUSES:
            raise RuntimeError(f"job {job_id} ended with status {payload['status']}")
    return statuses


def build_service_env(runtime_root: Path, *, enable_prores: bool) -> dict[str, str]:
    runtime_root = Path(runtime_root)
    env = os.environ.copy()
    env["MATANYONE2_WEBAPP_RUNTIME_ROOT"] = str(runtime_root)
    env["MATANYONE2_WEBAPP_DATABASE_PATH"] = str(runtime_root / "jobs.db")
    env["MATANYONE2_WEBAPP_ENABLE_PRORES"] = "1" if enable_prores else "0"
    env["MATANYONE2_WEBAPP_SAM_MODEL_TYPE"] = env.get(
        "MATANYONE2_WEBAPP_SAM_MODEL_TYPE",
        "vit_h",
    )
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def start_services(
    *,
    project_root: Path,
    runtime_root: Path,
    port: int,
    enable_prores: bool,
    python_executable: Path | None = None,
) -> tuple[subprocess.Popen, subprocess.Popen]:
    runtime_root = Path(runtime_root)
    logs_dir = runtime_root / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    python_path = str(python_executable or sys.executable)
    env = build_service_env(runtime_root, enable_prores=enable_prores)

    webapp_stdout = (logs_dir / "webapp.out.log").open("w", encoding="utf-8")
    webapp_stderr = (logs_dir / "webapp.err.log").open("w", encoding="utf-8")
    worker_stdout = (logs_dir / "worker.out.log").open("w", encoding="utf-8")
    worker_stderr = (logs_dir / "worker.err.log").open("w", encoding="utf-8")

    webapp_process = subprocess.Popen(
        [
            python_path,
            "-m",
            "uvicorn",
            "scripts.run_internal_webapp:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        cwd=project_root,
        env=env,
        stdout=webapp_stdout,
        stderr=webapp_stderr,
    )
    worker_process = subprocess.Popen(
        [python_path, "scripts/run_internal_worker.py"],
        cwd=project_root,
        env=env,
        stdout=worker_stdout,
        stderr=worker_stderr,
    )
    return webapp_process, worker_process


def stop_process_tree(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return

    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=10)


def run_smoke(
    *,
    project_root: Path,
    video_path: Path,
    runtime_root: Path,
    port: int,
    copies: int,
    timeout_seconds: float,
    poll_interval_seconds: float,
    enable_prores: bool,
    python_executable: Path | None = None,
) -> SmokeResult:
    base_url = f"http://127.0.0.1:{port}"
    session = requests.Session()
    webapp_process, worker_process = start_services(
        project_root=project_root,
        runtime_root=runtime_root,
        port=port,
        enable_prores=enable_prores,
        python_executable=python_executable,
    )

    try:
        wait_for_server(
            session,
            base_url,
            timeout_seconds=60.0,
            poll_interval_seconds=1.0,
        )
        job_ids = [submit_job(session, base_url, video_path) for _ in range(copies)]
        statuses = poll_jobs(
            session,
            base_url,
            job_ids,
            timeout_seconds=timeout_seconds,
            poll_interval_seconds=poll_interval_seconds,
        )
        return SmokeResult(runtime_root=Path(runtime_root), job_statuses=statuses)
    finally:
        session.close()
        stop_process_tree(worker_process)
        stop_process_tree(webapp_process)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a queue smoke test for the internal webapp.")
    parser.add_argument(
        "--video",
        default="inputs/video/test-sample2.mp4",
        help="Path to the sample video used for smoke submission.",
    )
    parser.add_argument(
        "--runtime-root",
        default=None,
        help="Runtime directory used for this smoke run.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8010,
        help="Port used for the temporary webapp process.",
    )
    parser.add_argument(
        "--copies",
        type=int,
        default=2,
        help="How many jobs to submit back-to-back.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=900.0,
        help="Maximum total wait time for all jobs to finish.",
    )
    parser.add_argument(
        "--poll-interval-seconds",
        type=float,
        default=5.0,
        help="Polling interval for job status checks.",
    )
    parser.add_argument(
        "--disable-prores",
        action="store_true",
        help="Skip ProRes export during smoke.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    project_root = Path(__file__).resolve().parents[2]
    runtime_root = Path(args.runtime_root) if args.runtime_root else (
        project_root / "runtime" / f"smoke-{time.strftime('%Y%m%d-%H%M%S')}"
    )
    result = run_smoke(
        project_root=project_root,
        video_path=project_root / args.video,
        runtime_root=runtime_root,
        port=args.port,
        copies=args.copies,
        timeout_seconds=args.timeout_seconds,
        poll_interval_seconds=args.poll_interval_seconds,
        enable_prores=not args.disable_prores,
    )

    print(f"runtime_root={result.runtime_root}")
    for job_id, payload in result.job_statuses.items():
        print(f"{job_id} {payload['status']} {sorted(payload['artifacts'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
