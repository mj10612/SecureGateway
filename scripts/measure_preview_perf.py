"""Benchmark runner for masking preview input latency and scaling (#342)."""

import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from threading import Thread
import time

PROSE_PARAGRAPH = (
    "2026년 11월 보안 감사 보고서: 김철수 수석 엔지니어(chulsoo.kim@secure-tech.co.kr)는 판교 데이터센터 서버(192.168.1.100)의 "
    "방산 레이더 radome 모듈과 전술 데이터 링크(tactical data link) 시스템 연결 상태를 점검했습니다. "
    "프로젝트 Alpha 진행률은 95%이며, 암호화 키는 vault-sec-9921에 안전하게 보관되어 있습니다. "
    "향후 유지보수 계획은 서울 본사 회의실에서 매주 화요일 14시에 논의될 예정입니다.\n"
)

CODE_SNIPPET = (
    "def handle_secure_packet(packet_id: int, host_ip: str = '192.168.1.1', user_email: str = 'admin@corp.internal') -> dict:\n"
    "    '''Process encrypted payload from host_ip for user_email.'''\n"
    "    secret_token = 'SEC_KEY_88291_ALPHA'\n"
    "    logger.info(f'Processing packet {packet_id} for {user_email} at {host_ip}')\n"
    "    if packet_id > 500:\n"
    "        return {'status': 'success', 'dest': host_ip, 'token': secret_token}\n"
    "    return {'status': 'pending', 'host': host_ip}\n\n"
)


def make_payload(base_text: str, target_bytes: int) -> str:
    encoded = base_text.encode("utf-8")
    repeat_count = target_bytes // len(encoded) + 1
    repeated = base_text * repeat_count
    byte_data = repeated.encode("utf-8")[:target_bytes]
    decoded = byte_data.decode("utf-8", errors="ignore")
    current_bytes = len(decoded.encode("utf-8"))
    if current_bytes < target_bytes:
        decoded += " " * (target_bytes - current_bytes)
    assert len(decoded.encode("utf-8")) == target_bytes
    return decoded


def run_single(size_bytes: int, kind: str, with_coverage: bool) -> None:
    cov = None
    if with_coverage:
        import coverage

        cov = coverage.Coverage()
        cov.start()

    from secure_gateway.admin_preview import _execute_preview, create_preview_session, derive_spans
    from secure_gateway.gateway import PrivacyGateway

    base_snippet = PROSE_PARAGRAPH if kind == "prose" else CODE_SNIPPET
    mode = "prose" if kind == "prose" else "code"
    text = make_payload(base_snippet, size_bytes)

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        state_dir = tmp_path / "sessions"
        audit_path = tmp_path / "logs.sqlite3"
        gateway = PrivacyGateway(
            ("127.0.0.1", 0),
            "token",
            upstreams={"claude": "http://127.0.0.1:1"},
            state_dir=state_dir,
            audit_path=audit_path,
        )
        server_thread = Thread(target=gateway.serve_forever, daemon=True)
        server_thread.start()

        try:
            # Measure mask only
            t0 = time.perf_counter()
            session = create_preview_session(gateway, natural_language="auto")
            if mode == "code":
                masked = session.mask(text, code=True, language="python")
            else:
                masked = session.mask(text, code=False, language="auto")
            mask_s = time.perf_counter() - t0

            # Measure derive_spans only
            t1 = time.perf_counter()
            uncertain, spans = derive_spans(session, text, masked)
            derive_s = time.perf_counter() - t1

            # Measure full _execute_preview
            t2 = time.perf_counter()
            _ = _execute_preview(
                gateway, text, mode, language="auto", code_language="python" if mode == "code" else None
            )
            total_s = time.perf_counter() - t2

            result = {
                "status": "ok",
                "bytes": size_bytes,
                "kind": kind,
                "with_coverage": with_coverage,
                "mask_s": round(mask_s, 4),
                "derive_s": round(derive_s, 4),
                "total_s": round(total_s, 4),
                "spans_count": len(spans),
                "uncertain": uncertain,
            }
            print(f"RESULT_JSON:{json.dumps(result)}", flush=True)
        finally:
            gateway.shutdown()
            server_thread.join(2)
            gateway.server_close()

    if cov:
        cov.stop()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--single", action="store_true")
    parser.add_argument("--size", type=int, default=16 * 1024)
    parser.add_argument("--kind", choices=["prose", "code"], default="prose")
    parser.add_argument("--coverage", action="store_true")
    args = parser.parse_args()

    if args.single:
        run_single(args.size, args.kind, args.coverage)
        return

    # Benchmark orchestration
    phase1_sizes = [
        (16 * 1024, "16 KiB"),
        (64 * 1024, "64 KiB"),
        (128 * 1024, "128 KiB"),
        (256 * 1024, "256 KiB"),
    ]

    all_results = []
    print("=== STARTING PREVIEW LATENCY BENCHMARKS (Timeout: 60s per test) ===", flush=True)

    for cov_flag in [False, True]:
        cov_label = "WITH coverage" if cov_flag else "WITHOUT coverage"
        print(f"\n--- Running {cov_label} ---", flush=True)
        max_256_time = 0.0
        for size_bytes, size_label in phase1_sizes:
            for kind in ["prose", "code"]:
                cmd = [
                    sys.executable,
                    str(Path(__file__).resolve()),
                    "--single",
                    "--size",
                    str(size_bytes),
                    "--kind",
                    kind,
                ]
                if cov_flag:
                    cmd.append("--coverage")

                print(f"Testing {size_label} {kind} ({cov_label})... ", end="", flush=True)
                t_start = time.perf_counter()
                try:
                    p = subprocess.run(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        timeout=60,
                        cwd=str(Path(__file__).resolve().parents[1]),
                    )
                    elapsed = time.perf_counter() - t_start
                    if p.returncode != 0:
                        print(f"FAILED (code {p.returncode}) in {elapsed:.2f}s", flush=True)
                        if p.stderr:
                            print(p.stderr, flush=True)
                        all_results.append({
                            "size": size_label,
                            "bytes": size_bytes,
                            "kind": kind,
                            "coverage": cov_flag,
                            "status": "error",
                            "elapsed": elapsed,
                        })
                    else:
                        out_line = next(
                            (line for line in p.stdout.splitlines() if line.startswith("RESULT_JSON:")), None
                        )
                        if out_line:
                            data = json.loads(out_line[len("RESULT_JSON:") :])
                            print(
                                f"OK: total={data['total_s']:.3f}s (mask={data['mask_s']:.3f}s, derive={data['derive_s']:.3f}s, spans={data['spans_count']})",
                                flush=True,
                            )
                            all_results.append(data)
                            if size_bytes == 256 * 1024:
                                max_256_time = max(max_256_time, data["total_s"])
                        else:
                            print(f"OK (no json) in {elapsed:.2f}s", flush=True)
                except subprocess.TimeoutExpired:
                    print("TIMED OUT (>60s)", flush=True)
                    all_results.append({
                        "size": size_label,
                        "bytes": size_bytes,
                        "kind": kind,
                        "coverage": cov_flag,
                        "status": "timed_out",
                        "elapsed": 60.0,
                    })
                    if size_bytes == 256 * 1024:
                        max_256_time = 60.0

        # Now check if 256 KiB finished well inside the 10s deadline (< 5.0 s)
        print(f"\nSlowest 256 KiB under {cov_label}: {max_256_time:.2f}s", flush=True)
        if max_256_time < 5.0:
            print("256 KiB completed well inside deadline (< 5s), evaluating 512 KiB and 1 MiB...", flush=True)
            for size_bytes, size_label in [(512 * 1024, "512 KiB"), (1024 * 1024, "1 MiB")]:
                for kind in ["prose", "code"]:
                    cmd = [
                        sys.executable,
                        str(Path(__file__).resolve()),
                        "--single",
                        "--size",
                        str(size_bytes),
                        "--kind",
                        kind,
                    ]
                    if cov_flag:
                        cmd.append("--coverage")

                    print(f"Testing {size_label} {kind} ({cov_label})... ", end="", flush=True)
                    t_start = time.perf_counter()
                    try:
                        p = subprocess.run(
                            cmd,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            text=True,
                            timeout=60,
                            cwd=str(Path(__file__).resolve().parents[1]),
                        )
                        elapsed = time.perf_counter() - t_start
                        if p.returncode != 0:
                            print(f"FAILED (code {p.returncode}) in {elapsed:.2f}s", flush=True)
                        else:
                            out_line = next(
                                (line for line in p.stdout.splitlines() if line.startswith("RESULT_JSON:")), None
                            )
                            if out_line:
                                data = json.loads(out_line[len("RESULT_JSON:") :])
                                print(
                                    f"OK: total={data['total_s']:.3f}s (mask={data['mask_s']:.3f}s, derive={data['derive_s']:.3f}s, spans={data['spans_count']})",
                                    flush=True,
                                )
                                all_results.append(data)
                    except subprocess.TimeoutExpired:
                        print("TIMED OUT (>60s)", flush=True)
                        all_results.append({
                            "size": size_label,
                            "bytes": size_bytes,
                            "kind": kind,
                            "coverage": cov_flag,
                            "status": "timed_out",
                            "elapsed": 60.0,
                        })
        else:
            print(f"256 KiB was {max_256_time:.2f}s (>= 5s); skipping 512 KiB / 1 MiB under {cov_label} as instructed.", flush=True)

    # Print summary
    print("\n=== COMPLETE BENCHMARK SUMMARY ===", flush=True)
    print(json.dumps(all_results, indent=2), flush=True)


if __name__ == "__main__":
    main()
