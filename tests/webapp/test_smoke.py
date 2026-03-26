from dataclasses import dataclass

import pytest
import requests

from matanyone2.webapp.smoke import poll_jobs
from matanyone2.webapp.smoke import wait_for_server


@dataclass
class _FakeResponse:
    status_code: int
    payload: dict

    def json(self):
        return self.payload


class _FakeSession:
    def __init__(self, responses):
        self._responses = responses

    def get(self, url, timeout):
        response = self._responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def test_wait_for_server_retries_until_ready():
    session = _FakeSession(
        [
            requests.RequestException("not ready"),
            _FakeResponse(503, {}),
            _FakeResponse(200, {}),
        ]
    )
    sleep_calls = []
    monotonic_values = iter([0.0, 0.05, 0.10, 0.15])

    wait_for_server(
        session,
        "http://127.0.0.1:8010",
        timeout_seconds=1.0,
        poll_interval_seconds=0.1,
        sleep=sleep_calls.append,
        monotonic=lambda: next(monotonic_values),
    )

    assert sleep_calls == [0.1, 0.1]


def test_poll_jobs_tracks_queued_follow_up_job():
    session = _FakeSession(
        [
            _FakeResponse(200, {"job_id": "job-1", "status": "running"}),
            _FakeResponse(200, {"job_id": "job-2", "status": "queued"}),
            _FakeResponse(200, {"job_id": "job-1", "status": "completed"}),
            _FakeResponse(200, {"job_id": "job-2", "status": "running"}),
            _FakeResponse(200, {"job_id": "job-1", "status": "completed"}),
            _FakeResponse(200, {"job_id": "job-2", "status": "completed"}),
        ]
    )
    sleep_calls = []
    monotonic_values = iter([0.0, 0.1, 0.2, 0.3])

    statuses = poll_jobs(
        session,
        "http://127.0.0.1:8010",
        ["job-1", "job-2"],
        timeout_seconds=5.0,
        poll_interval_seconds=0.25,
        sleep=sleep_calls.append,
        monotonic=lambda: next(monotonic_values),
    )

    assert statuses["job-1"]["status"] == "completed"
    assert statuses["job-2"]["status"] == "completed"
    assert sleep_calls == [0.25, 0.25]


def test_poll_jobs_requires_follow_up_job_to_queue():
    session = _FakeSession(
        [
            _FakeResponse(200, {"job_id": "job-1", "status": "running"}),
            _FakeResponse(200, {"job_id": "job-2", "status": "running"}),
            _FakeResponse(200, {"job_id": "job-1", "status": "completed"}),
            _FakeResponse(200, {"job_id": "job-2", "status": "completed"}),
        ]
    )
    monotonic_values = iter([0.0, 0.1, 0.2])

    with pytest.raises(AssertionError, match="never entered queued status"):
        poll_jobs(
            session,
            "http://127.0.0.1:8010",
            ["job-1", "job-2"],
            timeout_seconds=5.0,
            poll_interval_seconds=0.25,
            sleep=lambda _: None,
            monotonic=lambda: next(monotonic_values),
        )


def test_poll_jobs_retries_transient_connection_errors():
    session = _FakeSession(
        [
            _FakeResponse(200, {"job_id": "job-1", "status": "running"}),
            _FakeResponse(200, {"job_id": "job-2", "status": "queued"}),
            requests.RequestException("connection reset"),
            _FakeResponse(200, {"job_id": "job-1", "status": "completed"}),
            _FakeResponse(200, {"job_id": "job-2", "status": "completed"}),
        ]
    )
    sleep_calls = []
    monotonic_values = iter([0.0, 0.1, 0.2, 0.3])

    statuses = poll_jobs(
        session,
        "http://127.0.0.1:8010",
        ["job-1", "job-2"],
        timeout_seconds=5.0,
        poll_interval_seconds=0.25,
        sleep=sleep_calls.append,
        monotonic=lambda: next(monotonic_values),
    )

    assert statuses["job-1"]["status"] == "completed"
    assert statuses["job-2"]["status"] == "completed"
    assert sleep_calls == [0.25, 0.25]
