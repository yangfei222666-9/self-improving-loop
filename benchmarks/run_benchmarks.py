"""
Self-Improving Loop 性能基准测试

测试不同场景下的性能表现，生成性能报告。
"""

import sys
import time
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from self_improving_loop import SelfImprovingLoop


class Benchmark:
    def __init__(self):
        self.results = []
        self.temp_dir = Path(tempfile.mkdtemp(prefix="benchmark_"))

    def cleanup(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def run(self, name, fn, iterations=100):
        """运行基准测试"""
        print(f"\n{'='*60}")
        print(f"Benchmark: {name}")
        print(f"Iterations: {iterations}")
        print(f"{'='*60}")

        # 预热
        for _ in range(min(10, iterations // 10)):
            fn()

        # 测试
        times = []
        for i in range(iterations):
            start = time.perf_counter()
            fn()
            duration = time.perf_counter() - start
            times.append(duration)

            if (i + 1) % (iterations // 10) == 0:
                print(f"Progress: {i+1}/{iterations}")

        # 统计
        avg = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)
        p50 = sorted(times)[len(times) // 2]
        p95 = sorted(times)[int(len(times) * 0.95)]
        p99 = sorted(times)[int(len(times) * 0.99)]

        result = {
            "name": name,
            "iterations": iterations,
            "avg_ms": avg * 1000,
            "min_ms": min_time * 1000,
            "max_ms": max_time * 1000,
            "p50_ms": p50 * 1000,
            "p95_ms": p95 * 1000,
            "p99_ms": p99 * 1000,
            "throughput": 1 / avg,
        }

        self.results.append(result)

        print(f"\nResults:")
        print(f"  Avg: {result['avg_ms']:.2f}ms")
        print(f"  Min: {result['min_ms']:.2f}ms")
        print(f"  Max: {result['max_ms']:.2f}ms")
        print(f"  P50: {result['p50_ms']:.2f}ms")
        print(f"  P95: {result['p95_ms']:.2f}ms")
        print(f"  P99: {result['p99_ms']:.2f}ms")
        print(f"  Throughput: {result['throughput']:.0f} ops/sec")

        return result

    def save_report(self, filename="benchmark_report.json"):
        """保存性能报告"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "python_version": sys.version,
            "results": self.results,
        }

        report_path = Path(__file__).parent / filename
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        print(f"\n{'='*60}")
        print(f"Report saved to: {report_path}")
        print(f"{'='*60}")


def main():
    bench = Benchmark()

    try:
        # Benchmark 1: 基础任务执行
        loop = SelfImprovingLoop(data_dir=str(bench.temp_dir / "basic"))

        def basic_task():
            return loop.execute_with_improvement(
                agent_id="bench-basic",
                task="基础任务",
                execute_fn=lambda: {"ok": True}
            )

        bench.run("Basic Task Execution", basic_task, iterations=1000)

        # Benchmark 2: 带上下文的任务
        def task_with_context():
            return loop.execute_with_improvement(
                agent_id="bench-context",
                task="带上下文任务",
                execute_fn=lambda: {"result": 42},
                context={"input": 21, "operation": "multiply"}
            )

        bench.run("Task with Context", task_with_context, iterations=1000)

        # Benchmark 3: 失败任务
        counter = {"value": 0}

        def failing_task():
            counter["value"] += 1
            return loop.execute_with_improvement(
                agent_id="bench-fail",
                task=f"失败任务 {counter['value']}",
                execute_fn=lambda: 1 / 0
            )

        bench.run("Failing Task", failing_task, iterations=100)

        # Benchmark 4: 并发执行
        def concurrent_task():
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = [
                    executor.submit(
                        loop.execute_with_improvement,
                        agent_id=f"bench-concurrent-{i % 5}",
                        task=f"并发任务 {i}",
                        execute_fn=lambda: {"ok": True}
                    )
                    for i in range(50)
                ]
                return [f.result() for f in futures]

        bench.run("Concurrent Execution (50 tasks)", concurrent_task, iterations=10)

        # Benchmark 5: 大数据量
        def large_data_task():
            return loop.execute_with_improvement(
                agent_id="bench-large",
                task="大数据任务",
                execute_fn=lambda: {"data": "x" * 10000}
            )

        bench.run("Large Data Task", large_data_task, iterations=100)

        # Benchmark 6: 统计查询
        def stats_query():
            return loop.get_improvement_stats("bench-basic")

        bench.run("Stats Query", stats_query, iterations=1000)

        # 保存报告
        bench.save_report()

        # 打印总结
        print(f"\n{'='*60}")
        print("Summary")
        print(f"{'='*60}")
        for result in bench.results:
            print(f"{result['name']:40} {result['avg_ms']:8.2f}ms  {result['throughput']:8.0f} ops/sec")

    finally:
        bench.cleanup()


if __name__ == "__main__":
    main()
