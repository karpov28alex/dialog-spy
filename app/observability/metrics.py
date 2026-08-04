from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from threading import Lock


@dataclass(slots=True)
class RuntimeMetrics:
    requests_total: dict[tuple[str, str, int], int] = field(
        default_factory=lambda: defaultdict(int)
    )
    request_duration_seconds_sum: dict[tuple[str, str], float] = field(
        default_factory=lambda: defaultdict(float)
    )
    request_duration_seconds_count: dict[tuple[str, str], int] = field(
        default_factory=lambda: defaultdict(int)
    )
    _lock: Lock = field(default_factory=Lock)

    def observe_http(
        self,
        *,
        method: str,
        route: str,
        status_code: int,
        duration_seconds: float,
    ) -> None:
        key = (method, route)
        with self._lock:
            self.requests_total[(method, route, status_code)] += 1
            self.request_duration_seconds_sum[key] += duration_seconds
            self.request_duration_seconds_count[key] += 1

    def render_prometheus(self) -> str:
        lines = [
            "# HELP dialog_spy_http_requests_total Total HTTP requests.",
            "# TYPE dialog_spy_http_requests_total counter",
        ]
        with self._lock:
            for (method, route, status), value in sorted(self.requests_total.items()):
                labels = _labels(method=method, route=route, status=str(status))
                lines.append(f"dialog_spy_http_requests_total{{{labels}}} {value}")

            lines.extend(
                [
                    "# HELP dialog_spy_http_request_duration_seconds HTTP request duration.",
                    "# TYPE dialog_spy_http_request_duration_seconds summary",
                ]
            )
            for (method, route), value in sorted(self.request_duration_seconds_sum.items()):
                labels = _labels(method=method, route=route)
                count = self.request_duration_seconds_count[(method, route)]
                lines.append(
                    "dialog_spy_http_request_duration_seconds_sum"
                    f"{{{labels}}} {value:.9f}"
                )
                lines.append(
                    "dialog_spy_http_request_duration_seconds_count"
                    f"{{{labels}}} {count}"
                )
        return "\n".join(lines) + "\n"


def _labels(**values: str) -> str:
    return ",".join(
        f'{key}="{value.replace(chr(92), chr(92) * 2).replace(chr(34), chr(92) + chr(34))}"'
        for key, value in values.items()
    )


runtime_metrics = RuntimeMetrics()
