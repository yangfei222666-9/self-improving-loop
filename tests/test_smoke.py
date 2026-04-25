"""
Smoke tests — verify imports, basic instantiation, and core execution path.
These are intentionally minimal; the full 17-test suite lives in the parent
TaijiOS repo and is being ported here in follow-up PRs.
"""
import json
import multiprocessing
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from self_improving_loop import (
    SelfImprovingLoop,
    AutoRollback,
    AdaptiveThreshold,
    ConfigAdapter,
    JsonlTraceStore,
    SQLiteTraceStore,
    TelegramNotifier,
    YijingEvolutionStrategy,
    __version__,
)
from self_improving_loop.yijing import identify_hexagram, score_lines
from self_improving_loop.notifier import _encode_for_stdout


def _append_traces_worker(args):
    traces_file, worker_id, count = args
    store = JsonlTraceStore(traces_file)
    for i in range(count):
        store.append({
            "agent_id": f"worker-{worker_id}",
            "task": f"task-{i}",
            "success": True,
            "duration_sec": 0.0,
            "timestamp": datetime.now().isoformat(),
        })


def test_version_is_set():
    assert __version__
    assert __version__.count(".") >= 1  # at least major.minor


def test_imports_resolve():
    # If any of these blow up, the package is broken at install-time
    assert SelfImprovingLoop
    assert ConfigAdapter
    assert JsonlTraceStore
    assert SQLiteTraceStore
    assert YijingEvolutionStrategy
    assert AutoRollback
    assert AdaptiveThreshold
    assert TelegramNotifier


def test_loop_instantiates_with_tempdir(tmp_path: Path):
    loop = SelfImprovingLoop(data_dir=str(tmp_path))
    assert loop.data_dir == tmp_path
    assert loop.state_file.parent == tmp_path
    assert loop.storage == "jsonl"
    assert loop.auto_rollback is not None
    assert loop.adaptive_threshold is not None
    assert loop.notifier is not None
    # alias exposed to README-facing users
    assert loop.rollback is loop.auto_rollback


def test_track_alias_records_success(tmp_path: Path):
    loop = SelfImprovingLoop(data_dir=str(tmp_path))
    result = loop.track(
        agent_id="alias-agent",
        task="alias task",
        execute_fn=lambda: "ok",
    )

    assert result["success"] is True
    assert result["result"] == "ok"


def test_loop_supports_sqlite_trace_storage(tmp_path: Path):
    loop = SelfImprovingLoop(data_dir=str(tmp_path), storage="sqlite")
    assert loop.storage == "sqlite"
    assert loop.trace_db_file.exists()

    result = loop.execute_with_improvement(
        agent_id="sqlite-agent",
        task="sqlite-backed trace",
        execute_fn=lambda: {"ok": True},
    )

    assert result["success"] is True
    rows = loop._load_traces("sqlite-agent")
    assert len(rows) == 1
    assert rows[0]["task"] == "sqlite-backed trace"


def test_loop_rejects_unknown_trace_storage(tmp_path: Path):
    with pytest.raises(ValueError, match="storage must be"):
        SelfImprovingLoop(data_dir=str(tmp_path), storage="yaml")


def test_strategy_alias_is_preferred_entrypoint(tmp_path: Path):
    class Strategy:
        def analyze(self, agent_id, traces, before_metrics):
            return None

    strategy = Strategy()
    loop = SelfImprovingLoop(data_dir=str(tmp_path), strategy=strategy)
    assert loop.improvement_strategy is strategy


def test_strategy_alias_rejects_duplicate_strategy_args(tmp_path: Path):
    class Strategy:
        pass

    with pytest.raises(ValueError, match="either strategy or improvement_strategy"):
        SelfImprovingLoop(
            data_dir=str(tmp_path),
            strategy=Strategy(),
            improvement_strategy=Strategy(),
        )


def test_improvement_strategy_hook_applies_and_records_backup(tmp_path: Path):
    class Strategy:
        def __init__(self):
            self.applied = []

        def current_config(self, agent_id):
            return {"timeout_sec": 30}

        def analyze(self, agent_id, traces, before_metrics):
            return {"timeout_sec": 45}

        def apply(self, agent_id, config_patch):
            self.applied.append((agent_id, config_patch))
            return True

    strategy = Strategy()
    loop = SelfImprovingLoop(data_dir=str(tmp_path), improvement_strategy=strategy)
    loop.adaptive_threshold.set_manual_threshold(
        "strategy-agent",
        failure_threshold=1,
        analysis_window_hours=24,
        cooldown_hours=0,
    )

    def bad():
        raise ValueError("boom")

    result = loop.execute_with_improvement(
        agent_id="strategy-agent",
        task="will trigger strategy",
        execute_fn=bad,
    )

    assert result["improvement_triggered"] is True
    assert result["improvement_applied"] == 1
    assert strategy.applied == [("strategy-agent", {"timeout_sec": 45})]
    assert "strategy-agent" in loop.state["backups"]


def test_config_adapter_applies_and_restores_real_config(tmp_path: Path):
    class Strategy:
        def __init__(self):
            self.proposed = False

        def analyze(self, agent_id, traces, before_metrics):
            if self.proposed:
                return None
            self.proposed = True
            return {"mode": "broken"}

    class Adapter:
        def __init__(self):
            self.config = {"mode": "baseline", "timeout_sec": 30}
            self.restored = False

        def get_config(self, agent_id):
            return dict(self.config)

        def apply_config(self, agent_id, config_patch):
            self.config.update(config_patch)
            return True

        def rollback_config(self, agent_id, backup_config):
            self.config = dict(backup_config)
            self.restored = True

    adapter = Adapter()
    loop = SelfImprovingLoop(
        data_dir=str(tmp_path),
        improvement_strategy=Strategy(),
        config_adapter=adapter,
    )
    loop.adaptive_threshold.set_manual_threshold(
        "adapter-agent",
        failure_threshold=1,
        analysis_window_hours=24,
        cooldown_hours=0,
        is_critical=True,
    )

    def agent_call():
        if adapter.config["mode"] == "broken":
            raise RuntimeError("bad config")
        return {"ok": True}

    loop.execute_with_improvement(
        agent_id="adapter-agent",
        task="baseline pass",
        execute_fn=agent_call,
    )
    loop.execute_with_improvement(
        agent_id="adapter-agent",
        task="seed failure",
        execute_fn=lambda: (_ for _ in ()).throw(RuntimeError("seed")),
    )
    assert adapter.config["mode"] == "broken"

    loop.adaptive_threshold.set_manual_threshold(
        "adapter-agent",
        failure_threshold=999,
        analysis_window_hours=24,
        cooldown_hours=0,
        is_critical=True,
    )

    rollback_result = None
    for i in range(10):
        result = loop.execute_with_improvement(
            agent_id="adapter-agent",
            task=f"post-patch regression {i}",
            execute_fn=agent_call,
        )
        if result["rollback_executed"]:
            rollback_result = result["rollback_executed"]
            break

    assert rollback_result is not None
    assert rollback_result["success"] is True
    assert rollback_result["restore_applied"] is True
    assert rollback_result["restore_source"] == "config_adapter"
    assert adapter.restored is True
    assert adapter.config == {"mode": "baseline", "timeout_sec": 30}


def test_execute_with_improvement_records_success(tmp_path: Path):
    loop = SelfImprovingLoop(data_dir=str(tmp_path))
    result = loop.execute_with_improvement(
        agent_id="smoke-agent",
        task="trivial task",
        execute_fn=lambda: {"ok": True},
    )
    assert result["success"] is True
    assert result["result"] == {"ok": True}
    assert result["error"] is None
    assert result["duration_sec"] >= 0
    assert result["improvement_triggered"] is False  # single success, no trigger
    assert result["rollback_executed"] is None

    # Trace file should have been written
    traces_file = tmp_path / "traces.jsonl"
    assert traces_file.exists()
    lines = traces_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    row = json.loads(lines[0])
    assert row["agent_id"] == "smoke-agent"
    assert row["success"] is True


def test_trace_store_process_safe_append(tmp_path: Path):
    traces_file = tmp_path / "traces.jsonl"
    workers = 4
    per_worker = 20
    ctx = multiprocessing.get_context("spawn")

    with ctx.Pool(processes=workers) as pool:
        pool.map(
            _append_traces_worker,
            [(str(traces_file), worker_id, per_worker) for worker_id in range(workers)],
        )

    rows = JsonlTraceStore(traces_file).load()
    assert len(rows) == workers * per_worker
    assert all(row["success"] is True for row in rows)


def test_trace_store_skips_corrupt_jsonl_lines(tmp_path: Path):
    traces_file = tmp_path / "traces.jsonl"
    traces_file.write_text(
        "\n".join([
            '{"agent_id": "ok", "success": true, "timestamp": "2026-04-25T00:00:00"}',
            "{not-json",
            '{"agent_id": "ok", "success": false, "timestamp": "2026-04-25T00:00:01"}',
        ]) + "\n",
        encoding="utf-8",
    )

    rows = JsonlTraceStore(traces_file).load(agent_id="ok")
    assert len(rows) == 2


def test_sqlite_trace_store_round_trip_and_agent_filter(tmp_path: Path):
    db_path = tmp_path / "traces.sqlite3"
    store = SQLiteTraceStore(db_path)
    store.append({
        "agent_id": "a",
        "task": "first",
        "success": True,
        "timestamp": "2026-04-25T00:00:00",
    })
    store.append({
        "agent_id": "b",
        "task": "second",
        "success": False,
        "timestamp": "2026-04-25T00:00:01",
    })

    assert [row["task"] for row in store.load()] == ["first", "second"]
    assert [row["task"] for row in store.load(agent_id="b")] == ["second"]


def test_yijing_identifies_core_hexagram_from_six_lines():
    lines = score_lines([
        {
            "agent_id": "strong",
            "task": "ok",
            "success": True,
            "duration_sec": 0.01,
            "timestamp": "2026-04-25T00:00:00",
        }
        for _ in range(4)
    ], {"success_rate": 1.0, "avg_duration_sec": 0.01, "consecutive_failures": 0})
    state = identify_hexagram(lines)
    assert state.binary == "111111"
    assert state.name == "qian"
    assert state.moving_lines == ()


def test_yijing_strategy_returns_bounded_policy_patch():
    strategy = YijingEvolutionStrategy(latency_target_sec=1.0)
    patch = strategy.analyze(
        agent_id="route-agent",
        traces=[
            {
                "agent_id": "route-agent",
                "task": "route",
                "success": False,
                "duration_sec": 2.0,
                "error": "provider route schema handoff sync quota error",
                "context": {"route_ok": False, "handoff_ok": False, "budget": "quota"},
                "timestamp": "2026-04-25T00:00:00",
            }
        ],
        before_metrics={
            "success_rate": 0.0,
            "avg_duration_sec": 2.0,
            "total_tasks": 1,
            "consecutive_failures": 3,
        },
    )
    assert patch["strategy_source"] == "yijing_hexagram_state_machine"
    assert patch["hexagram"]["binary"] == "000000"
    assert patch["hexagram"]["name"] == "kun"
    assert patch["policy_action"] == "conserve_and_rollback_bias"
    assert patch["auto_apply_enabled"] is False
    assert len(patch["dimensions"]) == 6


def test_cli_version_outputs_version(capsys):
    from self_improving_loop.cli import main

    assert main(["--version"]) == 0
    captured = capsys.readouterr()
    assert "self-improving-loop 0.1.0" in captured.out


def test_execute_with_improvement_captures_failure(tmp_path: Path):
    loop = SelfImprovingLoop(data_dir=str(tmp_path))

    def bad():
        raise ValueError("boom")

    result = loop.execute_with_improvement(
        agent_id="fail-agent",
        task="will fail",
        execute_fn=bad,
    )
    assert result["success"] is False
    assert "boom" in (result["error"] or "")


def test_adaptive_threshold_returns_tuple(tmp_path: Path):
    t = AdaptiveThreshold(str(tmp_path))
    failure, window, cooldown = t.get_threshold("some-agent", task_history=[])
    # all three should be positive integers
    assert isinstance(failure, int) and failure > 0
    assert isinstance(window, int) and window > 0
    assert isinstance(cooldown, int) and cooldown > 0


def test_manual_threshold_overrides_adaptive(tmp_path: Path):
    t = AdaptiveThreshold(str(tmp_path))
    t.set_manual_threshold(
        "critical-agent",
        failure_threshold=1,
        analysis_window_hours=12,
        cooldown_hours=1,
        is_critical=True,
    )
    failure, window, cooldown = t.get_threshold("critical-agent", task_history=[])
    assert failure == 1
    assert window == 12
    assert cooldown == 1


def test_notifier_default_is_noninvasive(capsys, tmp_path: Path):
    # Default stub should never raise and should be replaceable.
    loop = SelfImprovingLoop(data_dir=str(tmp_path))
    loop.notifier.notify_improvement(
        agent_id="x", improvements_applied=1, details={"k": "v"}
    )
    # stub prints to stdout; we just assert it didn't crash
    captured = capsys.readouterr()
    assert "x" in captured.out or captured.out == ""  # either format is fine


def test_notifier_stdout_encoding_fallback_handles_windows_cp1252():
    text = _encode_for_stdout("🔧 自动改进 • ok", encoding="cp1252")
    text.encode("cp1252")
    assert "ok" in text


def test_custom_notifier_subclass_is_honored(tmp_path: Path):
    received = []

    class MyNotifier(TelegramNotifier):
        def _send_message(self, message, priority="normal"):
            received.append((priority, message))

    loop = SelfImprovingLoop(data_dir=str(tmp_path), notifier=MyNotifier())
    loop.notifier.notify_improvement(
        agent_id="custom", improvements_applied=2, details=None
    )
    assert len(received) == 1
    priority, message = received[0]
    assert priority in ("normal", "high")
    assert "custom" in message


def test_get_improvement_stats_empty(tmp_path: Path):
    loop = SelfImprovingLoop(data_dir=str(tmp_path))
    stats = loop.get_improvement_stats()
    assert isinstance(stats, dict)
    # Just assert the shape; keys will be zero/empty
    assert "total_improvements" in stats or "total_rollbacks" in stats or stats == {}


def test_auto_rollback_history_is_empty_for_new_agent(tmp_path: Path):
    r = AutoRollback(str(tmp_path))
    history = r.get_rollback_history("never-seen-agent")
    assert isinstance(history, list)
    assert len(history) == 0
