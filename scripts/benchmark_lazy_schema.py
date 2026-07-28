#!/usr/bin/env python3
"""Benchmark SchemaOrg init cost across the whole test library.

Discovers every ``tests/test_data/**/*.testhtml`` fixture (same set the
unittest suite uses) and prints a short aggregated summary by default.

Usage (from repo root, with .venv active):

    python scripts/benchmark_lazy_schema.py
    python scripts/benchmark_lazy_schema.py --repeat 5 --warmup 1
    python scripts/benchmark_lazy_schema.py --verbose
    python scripts/benchmark_lazy_schema.py --limit 50
"""

from __future__ import annotations

import argparse
import statistics
import sys
import time
import tracemalloc
import warnings
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable
from unittest import mock

from recipe_scrapers import scrape_html
from recipe_scrapers._schemaorg import SchemaOrg

ROOT = Path(__file__).resolve().parents[1]
TEST_DATA = ROOT / "tests" / "test_data"

OPS = (
    "A_construct",
    "B_title",
    "C_common",
    "D_first_schema",
    "E_to_json",
)


@dataclass
class OpStat:
    medians_ms: list[float] = field(default_factory=list)
    schema_counts: list[int] = field(default_factory=list)


@dataclass(frozen=True)
class Fixture:
    host: str
    path: Path
    size: int

    @property
    def name(self) -> str:
        return f"{self.host}/{self.path.name}"


def _discover_fixtures() -> list[Fixture]:
    fixtures: list[Fixture] = []
    for host_dir in sorted(p for p in TEST_DATA.iterdir() if p.is_dir()):
        for html_path in sorted(host_dir.glob("*.testhtml")):
            fixtures.append(Fixture(host_dir.name, html_path, html_path.stat().st_size))
    return fixtures


def _median(values: list[float]) -> float:
    return statistics.median(values) if values else 0.0


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(
        len(ordered) - 1,
        max(0, int(round((pct / 100) * (len(ordered) - 1)))),
    )
    return ordered[index]


def _fmt_duration(seconds: float) -> str:
    seconds = max(0, int(seconds))
    minutes, secs = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:d}:{secs:02d}"


def _render_progress(done: int, total: int, started: float, label: str) -> None:
    width = 28
    fraction = 0 if total == 0 else done / total
    filled = int(width * fraction)
    bar = "#" * filled + "-" * (width - filled)
    elapsed = time.perf_counter() - started
    rate = done / elapsed if elapsed > 0 and done else 0.0
    remaining = (total - done) / rate if rate else 0.0
    suffix = label[:36].ljust(36)
    line = (
        f"\r[{bar}] {done}/{total} {100 * fraction:5.1f}%  "
        f"elapsed {_fmt_duration(elapsed)}  eta {_fmt_duration(remaining)}  {suffix}"
    )
    print(line, end="", file=sys.stderr, flush=True)
    if done >= total:
        print(file=sys.stderr, flush=True)


def _run_timed(
    operation: Callable[[], object], repeat: int, warmup: int
) -> list[float]:
    for _ in range(warmup):
        try:
            operation()
        except Exception:
            pass
    samples: list[float] = []
    for _ in range(repeat):
        start = time.perf_counter()
        try:
            operation()
        except Exception:
            pass
        samples.append(time.perf_counter() - start)
    return samples


def _count_schema_constructions(operation: Callable[[], object]) -> int:
    counter: Counter = Counter()
    real_init: Callable[..., object] = SchemaOrg.__init__

    def tracked_init(
        self: object, page_data: object, *args: object, **kwargs: object
    ) -> object:
        counter["calls"] += 1
        return real_init(self, page_data, *args, **kwargs)

    with mock.patch.object(SchemaOrg, "__init__", tracked_init):
        try:
            operation()
        except Exception:
            pass
    return counter["calls"]


def _peak_memory_before_schema(html: str, url: str) -> int | None:
    tracemalloc.start()
    try:
        scraper = scrape_html(html, org_url=url)
        try:
            scraper.title()
        except Exception:
            pass
        materialized = "schema" in scraper.__dict__
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    return None if materialized else peak


def _ops(html: str, url: str) -> dict[str, Callable[[], object]]:
    return {
        "A_construct": lambda: scrape_html(html, org_url=url),
        "B_title": lambda: scrape_html(html, org_url=url).title(),
        "C_common": lambda: (
            (s := scrape_html(html, org_url=url)).title(),
            s.ingredients(),
            s.instructions_list(),
        ),
        "D_first_schema": lambda: scrape_html(html, org_url=url).schema,
        "E_to_json": lambda: scrape_html(html, org_url=url).to_json(),
    }


def _fmt_ms(value: float) -> str:
    return f"{value:7.2f}ms"


def _fmt_mib(value: float) -> str:
    return f"{value:.2f} MiB"


def _summarize_op(name: str, stat: OpStat) -> str:
    medians = stat.medians_ms
    skipped = sum(1 for n in stat.schema_counts if n == 0)
    total = len(stat.schema_counts) or 1
    return (
        f"  {name:16}  p50={_fmt_ms(_median(medians))}  "
        f"p95={_fmt_ms(_percentile(medians, 95))}  "
        f"schema_skipped={skipped}/{total} ({100 * skipped / total:5.1f}%)"
    )


def _subset_summary(
    label: str, indices: list[int], stats: dict[str, OpStat]
) -> list[str]:
    if not indices:
        return [f"{label}: 0 fixtures"]
    lines = [f"{label}: {len(indices)} fixtures"]
    for op in OPS:
        medians = [stats[op].medians_ms[i] for i in indices]
        counts = [stats[op].schema_counts[i] for i in indices]
        skipped = sum(1 for n in counts if n == 0)
        lines.append(
            f"  {op:16}  p50={_fmt_ms(_median(medians))}  "
            f"p95={_fmt_ms(_percentile(medians, 95))}  "
            f"schema_skipped={skipped}/{len(indices)}"
        )
    return lines


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeat", type=int, default=3, help="Timed iterations per op")
    parser.add_argument(
        "--warmup", type=int, default=1, help="Warmup iterations per op"
    )
    parser.add_argument("--limit", type=int, default=0, help="Cap fixtures (0 = all)")
    parser.add_argument(
        "--large-kb",
        type=int,
        default=1024,
        help="Fixture size threshold for the large subset (KiB)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Also print per-fixture rows",
    )
    args = parser.parse_args()

    warnings.filterwarnings("ignore")

    fixtures = _discover_fixtures()
    if args.limit:
        fixtures = fixtures[: args.limit]

    total = len(fixtures)
    print(
        f"Benchmarking {total} fixtures "
        f"(repeat={args.repeat}, warmup={args.warmup})...",
        file=sys.stderr,
        flush=True,
    )

    stats: dict[str, OpStat] = {op: OpStat() for op in OPS}
    peak_before_schema: list[int] = []
    html_only_indices: list[int] = []
    large_indices: list[int] = []
    large_bytes = args.large_kb * 1024
    started = time.perf_counter()

    if args.verbose:
        print(f"{'fixture':48} {'op':16} {'median_ms':>10} {'schema_n':>8}")

    for index, fixture in enumerate(fixtures):
        _render_progress(index, total, started, fixture.name)
        html = fixture.path.read_text(encoding="utf-8")
        url = fixture.host
        ops = _ops(html, url)

        for op_name, operation in ops.items():
            samples = _run_timed(operation, repeat=args.repeat, warmup=args.warmup)
            schema_n = _count_schema_constructions(operation)
            median_ms = _median(samples) * 1000
            stats[op_name].medians_ms.append(median_ms)
            stats[op_name].schema_counts.append(schema_n)
            if args.verbose:
                print(
                    f"{fixture.name:48} {op_name:16} "
                    f"{median_ms:10.2f} {schema_n:8d}"
                )

        # HTML-only: common fields completed without constructing SchemaOrg.
        if stats["C_common"].schema_counts[-1] == 0:
            html_only_indices.append(index)
            peak = _peak_memory_before_schema(html, url)
            if peak is not None:
                peak_before_schema.append(peak)

        if fixture.size >= large_bytes:
            large_indices.append(index)

    _render_progress(total, total, started, "done")

    construct_skipped = sum(1 for n in stats["A_construct"].schema_counts if n == 0)
    mode = (
        "lazy"
        if construct_skipped > len(fixtures) / 2
        else "eager" if fixtures else "unknown"
    )

    lines = [
        "Lazy SchemaOrg library benchmark",
        (
            f"mode={mode}  fixtures={len(fixtures)}  "
            f"repeat={args.repeat}  warmup={args.warmup}"
        ),
        "",
        "Overall (per-fixture median -> library p50/p95):",
    ]
    for op in OPS:
        lines.append(_summarize_op(op, stats[op]))

    lines.append("")
    lines.extend(
        _subset_summary(
            "HTML-only subset (C_common schema_n=0)", html_only_indices, stats
        )
    )
    lines.append("")
    lines.extend(
        _subset_summary(
            f"Large subset (html >= {args.large_kb} KiB)",
            large_indices,
            stats,
        )
    )

    lines.append("")
    if peak_before_schema:
        peaks_mib = [p / (1024 * 1024) for p in peak_before_schema]
        lines.append(
            "Peak memory before schema (HTML-only title path): "
            f"p50={_fmt_mib(_median(peaks_mib))}  "
            f"p95={_fmt_mib(_percentile(peaks_mib, 95))}  "
            f"n={len(peaks_mib)}"
        )
    else:
        lines.append(
            "Peak memory before schema: n/a "
            "(schema already materialized on title path for all fixtures)"
        )

    print("\n".join(lines))


if __name__ == "__main__":
    main()
