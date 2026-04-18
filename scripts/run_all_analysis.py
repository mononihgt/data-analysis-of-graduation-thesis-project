from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
LOG_DIR = ROOT / "results" / "run_all_analysis"
PROC_SCRIPTS = [
    "proc1_eptask_learning_analysis.py",
    "proc2_sptask_rt_analysis.py",
    "proc3_djtask_accuracy_analysis.py",
    "proc4_pdtask_analysis.py",
    "proc5_cttask_position_analysis.py",
    "proc6_mrtask_reconstruction_analysis.py",
]


@dataclass
class RunResult:
    script_name: str
    return_code: int
    duration_seconds: float
    log_path: Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run proc1-proc6 analysis scripts in parallel.",
    )
    parser.add_argument(
        "--jobs",
        type=int,
        default=len(PROC_SCRIPTS),
        help="Number of scripts to run concurrently. Default: all proc scripts.",
    )
    parser.add_argument(
        "--python",
        default=sys.executable,
        help="Python executable used to run analysis scripts. Default: current interpreter.",
    )
    return parser.parse_args()


def run_one_script(script_name: str, python_bin: str) -> RunResult:
    script_path = SCRIPTS_DIR / script_name
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / f"{script_path.stem}.log"

    env = os.environ.copy()
    env.setdefault("PYTHONUNBUFFERED", "1")

    started_at = time.perf_counter()
    with log_path.open("w", encoding="utf-8") as log_file:
        log_file.write(f"$ {python_bin} {script_path}\n\n")
        log_file.flush()
        process = subprocess.run(
            [python_bin, str(script_path)],
            cwd=str(ROOT),
            env=env,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
    duration_seconds = time.perf_counter() - started_at
    return RunResult(
        script_name=script_name,
        return_code=process.returncode,
        duration_seconds=duration_seconds,
        log_path=log_path,
    )


def print_summary(results: list[RunResult]) -> int:
    failed = [result for result in results if result.return_code != 0]
    print("\nRun summary")
    print("===========")
    for result in sorted(results, key=lambda item: item.script_name):
        status = "OK" if result.return_code == 0 else f"FAIL ({result.return_code})"
        print(
            f"- {result.script_name}: {status}, "
            f"{result.duration_seconds:.1f}s, log={result.log_path}"
        )

    if failed:
        print(f"\n{len(failed)} script(s) failed.")
        return 1

    print("\nAll analysis scripts completed successfully.")
    return 0


def main() -> int:
    args = parse_args()
    jobs = max(1, min(args.jobs, len(PROC_SCRIPTS)))
    print(f"Running {len(PROC_SCRIPTS)} analysis scripts with {jobs} parallel worker(s).")
    print(f"Logs: {LOG_DIR}")

    results: list[RunResult] = []
    with ThreadPoolExecutor(max_workers=jobs) as executor:
        future_map = {
            executor.submit(run_one_script, script_name, args.python): script_name
            for script_name in PROC_SCRIPTS
        }
        for future in as_completed(future_map):
            result = future.result()
            results.append(result)
            status = "OK" if result.return_code == 0 else f"FAIL ({result.return_code})"
            print(f"[{status}] {result.script_name} in {result.duration_seconds:.1f}s")

    return print_summary(results)


if __name__ == "__main__":
    raise SystemExit(main())
