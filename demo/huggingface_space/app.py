"""Streamlit demo for self-improving-loop.

This demo is intentionally local and deterministic. It shows the reliability
guard around a callable without calling an external model or provider.
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from self_improving_loop import SelfImprovingLoop

DATA_DIR = Path(".demo-traces")
AGENT_ID = "streamlit-demo-agent"


def _demo_call(task: str, should_fail: bool) -> dict:
    if should_fail:
        raise RuntimeError("simulated agent failure")
    return {
        "status": "ok",
        "handled_task": task,
        "external_model_called": False,
    }


st.set_page_config(
    page_title="self-improving-loop demo",
    layout="centered",
)

st.title("self-improving-loop")
st.caption("Regression guard for AI agents: trace, threshold, strategy, rollback evidence.")

task = st.text_area("Agent task", value="Answer a support ticket without regressing.")
should_fail = st.checkbox("Simulate a failing agent call")

if st.button("Run guard", type="primary"):
    loop = SelfImprovingLoop(data_dir=str(DATA_DIR), storage="sqlite")
    result = loop.track(
        agent_id=AGENT_ID,
        task=task,
        execute_fn=lambda: _demo_call(task, should_fail),
        context={
            "surface": "streamlit_demo",
            "external_model_called": False,
        },
    )
    stats = loop.get_improvement_stats(AGENT_ID)

    st.subheader("Execution result")
    st.json(result)

    st.subheader("Agent stats")
    st.json(stats)

    if result["success"]:
        st.success("Trace recorded. No external model call was made.")
    else:
        st.warning("Failure recorded honestly. The guard did not fake success.")
