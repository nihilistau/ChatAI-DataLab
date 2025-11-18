"""One-off helper to (re)generate the hypothesis control notebook."""
# @tag: kitchen,scripts,notebook-factory

from __future__ import annotations

import json
import textwrap
from pathlib import Path


def as_lines(text: str) -> list[str]:
    text = textwrap.dedent(text).strip("\n")
    return [f"{line}\n" for line in text.splitlines()]


def md_cell(text: str) -> dict:
    return {
        "cell_type": "markdown",
        "metadata": {"language": "markdown"},
        "source": as_lines(text),
    }


def code_cell(text: str) -> dict:
    return {
        "cell_type": "code",
        "metadata": {"language": "python"},
        "execution_count": None,
        "outputs": [],
        "source": as_lines(text),
    }


cells = [
    md_cell(
        """
        # Hypothesis Workflow Control Lab

        All-in-one environment dedicated to designing, validating, and steering hypotheses inside ChatAI · DataLab.
        """
    ),
    md_cell(
        """
        ### Title Panel · Mission & Scope

        **Flow:** Manage every step from hypothesis ideation → experiment design → execution telemetry → decision logs without leaving this notebook.

        **Usage**

        - Pin hypotheses you care about, tag them, and set expectations for the tests that must validate them.
        - Use the experiment designer to add tests, compose combined experiments, and simulate or log real runs.
        - Monitor Tail/Ops logs directly from the notebook so the control surface stays in sync with the front-end Ops Deck.

        **Hints**

        - Press the refresh buttons on each panel after running real automation so that live metrics (votes, pass rates, ops logs) stay aligned.
        - The voting + decision matrix panel helps you choose which hypothesis to materialize in the TestLab environment.
        - Every action emits a change-log entry so you always know “how many changes” have happened in this working session.
        """
    ),
    md_cell(
        """
        ### Layout & Modules

        1. **Meta grid** — top cards report hypothesis counts, pass rates, votes, change-log volume, and captured data points.
        2. **Flow explainer** — a narrative panel that details what inputs you have, what actions are available, and how to interpret outputs.
        3. **Experiment designer** — create, combine, and run tests (manually or via simulation) while keeping an audit of their states.
        4. **Decision + voting matrix** — compare confidence, votes, and data volume before deciding which hypothesis to promote.
        5. **Interactive data wall** — sliders and toggles to visualize relationships (e.g., votes vs. pass rate, latency trends, data volume per stage).
        6. **Ops/Tail console** — pulls the same `/api/tail-log` feed used by the Ops Deck so both surfaces share the latest actions.
        """
    ),
    code_cell(
        """
        import os
        import random
        import statistics
        from dataclasses import dataclass, field
        from datetime import datetime
        from typing import Dict, List, Optional
        from uuid import uuid4

        import numpy as np
        import pandas as pd
        import plotly.express as px
        import ipywidgets as widgets
        from IPython.display import HTML, clear_output, display

        pd.options.display.float_format = "{:,.2f}".format

        try:
            import requests
        except ImportError:
            requests = None

        THEME_STYLES = \"\"\"
        <style>
        :root {
            --lab-bg: #05060d;
            --lab-panel: #0b1020;
            --lab-panel-alt: #10172b;
            --lab-border: #1c2340;
            --lab-accent: #9d7bff;
            --lab-lime: #b5f36a;
            --lab-amber: #ffb347;
            --lab-salmon: #ff9ca8;
            --lab-text: #f0f4ff;
        }

        .lab-panel {
            background: var(--lab-panel);
            border: 1px solid var(--lab-border);
            border-radius: 18px;
            padding: 1.15rem 1.35rem;
            color: var(--lab-text);
            box-shadow: inset 0 0 35px rgba(0, 0, 0, 0.35);
        }

        .lab-panel h3, .lab-panel h4 {
            margin-top: 0;
        }

        .meta-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
            gap: 0.9rem;
        }

        .stat-card {
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: 14px;
            padding: 0.9rem 1rem;
            background: rgba(8, 12, 24, 0.75);
        }

        .stat-card h4 {
            margin: 0;
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 0.2em;
            color: var(--lab-amber);
        }

        .stat-card p {
            margin: 0.35rem 0 0;
            font-size: 1.65rem;
            font-weight: 600;
        }

        .lab-table {
            border-collapse: collapse;
            width: 100%;
        }

        .lab-table th, .lab-table td {
            border: 1px solid rgba(255, 255, 255, 0.08);
            padding: 0.45rem 0.65rem;
            font-size: 0.9rem;
        }

        .lab-table th {
            text-transform: uppercase;
            letter-spacing: 0.15em;
            font-size: 0.75rem;
            color: var(--lab-amber);
        }

        .ops-log-entry {
            border-bottom: 1px solid rgba(255, 255, 255, 0.08);
            padding: 0.35rem 0;
            font-family: \"JetBrains Mono\", \"Fira Code\", monospace;
        }

        .vote-pill {
            display: inline-flex;
            align-items: center;
            gap: 0.4rem;
            border: 1px solid rgba(255, 255, 255, 0.18);
            border-radius: 999px;
            padding: 0.15rem 0.75rem;
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 0.2em;
        }
        </style>
        \"\"\"

        display(HTML(THEME_STYLES))
        """
    ),
    code_cell(
        """
        def slugify(value: str, prefix: str = "hyp") -> str:
            base = "".join(ch.lower() if ch.isalnum() else "-" for ch in value).strip("-")
            base = "-".join(part for part in base.split("-") if part)
            token = base or f"{prefix}-{uuid4().hex[:4]}"
            return token

        @dataclass
        class Hypothesis:
            key: str
            title: str
            objective: str
            owner: str = "shared"
            tags: List[str] = field(default_factory=list)
            confidence: float = 0.5
            votes: int = 0
            stage: str = "ideation"
            data_points: int = 0

        @dataclass
        class TestCase:
            key: str
            hypothesis_key: str
            name: str
            description: str
            metric: str
            target: float
            stage: str = "lab"
            owner: str = "shared"
            weight: float = 1.0
            last_run: Optional[datetime] = None
            status: str = "pending"

        @dataclass
        class TestRun:
            run_id: str
            test_key: str
            hypothesis_key: str
            value: float
            status: str
            notes: str
            sample_size: int
            created_at: datetime

        class HypothesisRegistry:
            def __init__(
                self,
                hypotheses: Optional[List[Hypothesis]] = None,
                tests: Optional[List[TestCase]] = None,
                runs: Optional[List[TestRun]] = None,
            ) -> None:
                self.hypotheses: Dict[str, Hypothesis] = {}
                self.tests: Dict[str, TestCase] = {}
                self.runs: List[TestRun] = []
                self.changelog: List[tuple[datetime, str]] = []
                if hypotheses:
                    for hyp in hypotheses:
                        self.hypotheses[hyp.key] = hyp
                        self.record_change(f"seeded hypothesis · {hyp.title}")
                if tests:
                    for test in tests:
                        self.tests[test.key] = test
                        self.record_change(f"seeded test · {test.name}")
                if runs:
                    for run in runs:
                        self.runs.append(run)
                self.recalculate_confidence()

            def record_change(self, message: str) -> None:
                self.changelog.append((datetime.utcnow(), message))
                if len(self.changelog) > 200:
                    self.changelog = self.changelog[-200:]

            def recalculate_confidence(self) -> None:
                grouped: Dict[str, List[bool]] = {}
                for run in self.runs:
                    grouped.setdefault(run.hypothesis_key, []).append(run.status == "pass")
                for key, hyp in self.hypotheses.items():
                    verdicts = grouped.get(key, [])
                    hyp.confidence = round(0.35 + 0.55 * (sum(verdicts) / len(verdicts)), 3) if verdicts else hyp.confidence
                    hyp.data_points = sum(r.sample_size for r in self.runs if r.hypothesis_key == key)

            def add_hypothesis(self, title: str, objective: str, owner: str = "shared", tags: Optional[List[str]] = None) -> Hypothesis:
                key = slugify(title)
                if key in self.hypotheses:
                    key = f"{key}-{len(self.hypotheses)}"
                hyp = Hypothesis(key=key, title=title, objective=objective, owner=owner, tags=tags or [])
                self.hypotheses[key] = hyp
                self.record_change(f"added hypothesis · {title}")
                return hyp

            def add_test(
                self,
                hypothesis_key: str,
                name: str,
                description: str,
                metric: str,
                target: float,
                stage: str = "lab",
                owner: str = "shared",
                weight: float = 1.0,
            ) -> TestCase:
                key = slugify(name, prefix="test")
                if key in self.tests:
                    key = f"{key}-{len(self.tests)}"
                test = TestCase(
                    key=key,
                    hypothesis_key=hypothesis_key,
                    name=name,
                    description=description,
                    metric=metric,
                    target=target,
                    stage=stage,
                    owner=owner,
                    weight=weight,
                )
                self.tests[key] = test
                self.record_change(f"added test · {name}")
                return test

            def log_run(self, test_key: str, value: float, notes: str = "", sample_size: int = 120) -> TestRun:
                test = self.tests[test_key]
                status = "pass" if value >= test.target else "fail"
                run = TestRun(
                    run_id=f"run-{uuid4().hex[:6]}",
                    test_key=test.key,
                    hypothesis_key=test.hypothesis_key,
                    value=float(value),
                    status=status,
                    notes=notes or "manual entry",
                    sample_size=int(sample_size),
                    created_at=datetime.utcnow(),
                )
                self.runs.append(run)
                test.last_run = run.created_at
                test.status = status
                self.record_change(f"{test.name} {status} @ {run.value:.2f}")
                self.recalculate_confidence()
                return run

            def simulate_run(self, test_key: str, intensity: float = 1.0, jitter: float = 0.08) -> TestRun:
                test = self.tests[test_key]
                centered = test.target * random.uniform(0.92, 1.08) * intensity
                noise = random.gauss(0, test.target * jitter)
                value = max(centered + noise, 0)
                notes = f"simulated · intensity={intensity:.2f}"
                sample = random.randint(60, 240)
                return self.log_run(test_key=test_key, value=value, notes=notes, sample_size=sample)

            def tests_frame(self) -> pd.DataFrame:
                rows = []
                for test in self.tests.values():
                    runs = [run for run in self.runs if run.test_key == test.key]
                    pass_rate = sum(run.status == "pass" for run in runs) / len(runs) if runs else 0
                    avg_value = statistics.mean(run.value for run in runs) if runs else None
                    rows.append(
                        {
                            "hypothesis_key": test.hypothesis_key,
                            "hypothesis": self.hypotheses[test.hypothesis_key].title,
                            "test_key": test.key,
                            "test": test.name,
                            "metric": test.metric,
                            "target": test.target,
                            "stage": test.stage,
                            "owner": test.owner,
                            "last_run": test.last_run.isoformat() if test.last_run else None,
                            "status": test.status,
                            "pass_rate": round(pass_rate, 3),
                            "avg_value": round(avg_value, 3) if avg_value is not None else None,
                            "data_points": sum(run.sample_size for run in runs),
                            "run_count": len(runs),
                        }
                    )
                return pd.DataFrame(rows)

            def hypotheses_frame(self) -> pd.DataFrame:
                df = self.tests_frame()
                rows = []
                for hyp in self.hypotheses.values():
                    subset = df[df["hypothesis_key"] == hyp.key]
                    pass_rate = subset["pass_rate"].mean() if not subset.empty else 0
                    run_count = subset["run_count"].sum() if not subset.empty else 0
                    rows.append(
                        {
                            "key": hyp.key,
                            "title": hyp.title,
                            "stage": hyp.stage,
                            "objective": hyp.objective,
                            "tags": ", ".join(hyp.tags),
                            "confidence": hyp.confidence,
                            "votes": hyp.votes,
                            "data_points": hyp.data_points,
                            "avg_pass_rate": round(pass_rate, 3),
                            "run_count": run_count,
                        }
                    )
                return pd.DataFrame(rows)

            def results_frame(self) -> pd.DataFrame:
                rows = [
                    {
                        "run_id": run.run_id,
                        "test_key": run.test_key,
                        "hypothesis_key": run.hypothesis_key,
                        "value": run.value,
                        "status": run.status,
                        "notes": run.notes,
                        "sample_size": run.sample_size,
                        "created_at": run.created_at,
                        "delta_vs_target": run.value - self.tests[run.test_key].target,
                    }
                    for run in self.runs
                ]
                return pd.DataFrame(rows)

            def metrics(self) -> Dict[str, float]:
                tests_df = self.tests_frame()
                hyp_df = self.hypotheses_frame()
                return {
                    "hypotheses": len(self.hypotheses),
                    "tests": len(self.tests),
                    "active_tests": int((tests_df["status"] == "pass").sum()) if not tests_df.empty else 0,
                    "avg_confidence": float(hyp_df["confidence"].mean()) if not hyp_df.empty else 0,
                    "votes": int(hyp_df["votes"].sum()) if not hyp_df.empty else 0,
                    "data_points": int(hyp_df["data_points"].sum()) if not hyp_df.empty else 0,
                    "changes": len(self.changelog),
                    "runs": len(self.runs),
                }

            def combine_tests(self, test_keys: List[str]) -> pd.DataFrame:
                df = self.tests_frame()
                subset = df[df["test_key"].isin(test_keys)]
                if subset.empty:
                    return pd.DataFrame()
                combo = (
                    subset.groupby(["hypothesis", "stage"])
                    .agg(
                        pass_rate=("pass_rate", "mean"),
                        avg_target=("target", "mean"),
                        avg_value=("avg_value", "mean"),
                        total_runs=("run_count", "sum"),
                        total_points=("data_points", "sum"),
                    )
                    .reset_index()
                )
                combo["delta_vs_target"] = combo["avg_value"] - combo["avg_target"]
                return combo

            def cast_vote(self, hypothesis_key: str, votes: int) -> None:
                hyp = self.hypotheses[hypothesis_key]
                hyp.votes += votes
                self.record_change(f"votes +{votes} → {hyp.title}")
        """
    ),
    code_cell(
        """
        # Seed data using the existing ChatAI canvas hypotheses.
        sample_hypotheses = [
            Hypothesis(
                key="hyp-pause-density",
                title="Pause density telemetry",
                objective="Correlate typing pauses with downstream prompt quality shifts",
                owner="insights",
                tags=["telemetry", "latency"],
                confidence=0.55,
                votes=3,
                stage="analysis",
                data_points=1480,
            ),
            Hypothesis(
                key="hyp-token-priming",
                title="Token priming uplift",
                objective="Front-load clear intent to cut clarification turns by 20%",
                owner="shared",
                tags=["prompting", "efficiency"],
                confidence=0.61,
                votes=5,
                stage="design",
                data_points=990,
            ),
            Hypothesis(
                key="hyp-ops-memory",
                title="Ops deck memory",
                objective="Blend ops log context into TailLog feed for faster incident triage",
                owner="ops",
                tags=["ops", "observability"],
                confidence=0.48,
                votes=2,
                stage="ideation",
                data_points=420,
            ),
        ]

        sample_tests = [
            TestCase(
                key="test-pause-density",
                hypothesis_key="hyp-pause-density",
                name="Pause cluster detection",
                description="Detect meaningful pause clusters within 2s windows",
                metric="precision",
                target=0.78,
                stage="lab",
                owner="instrumentation",
            ),
            TestCase(
                key="test-pause-quality",
                hypothesis_key="hyp-pause-density",
                name="Quality delta tracking",
                description="Relate pause clusters to quality score deltas",
                metric="pearson_r",
                target=0.52,
                stage="analysis",
            ),
            TestCase(
                key="test-token-priming",
                hypothesis_key="hyp-token-priming",
                name="Prompt priming drop",
                description="Measure clarification drop after priming",
                metric="clarity_delta",
                target=0.2,
                stage="pilot",
            ),
            TestCase(
                key="test-ops-tail",
                hypothesis_key="hyp-ops-memory",
                name="Ops log surfacing",
                description="Surface ops events inside TailLog",
                metric="triage_time",
                target=12,
                stage="ideation",
            ),
        ]

        registry = HypothesisRegistry(sample_hypotheses, sample_tests)
        rng = np.random.default_rng(42)
        for test in sample_tests:
            for _ in range(rng.integers(2, 6)):
                jitter = rng.uniform(0.9, 1.15)
                value = float(np.round(test.target * jitter, 3))
                registry.log_run(
                    test_key=test.key,
                    value=value,
                    notes="seeded import",
                    sample_size=int(rng.integers(80, 220)),
                )
        """
    ),
    code_cell(
        """
        # Build the interactive control surface.
        OPS_API_BASE = os.environ.get("CHATAI_LAB_API", os.environ.get("CHATAI_API_BASE_URL", "http://localhost:8000"))

        def fetch_tail_log(limit: int = 12):
            fallback = [
                {
                    "message": "Tail log endpoint unavailable. Using notebook change-log instead.",
                    "source": "notebook",
                    "createdAt": datetime.utcnow().isoformat(),
                }
            ]
            if requests is None:
                return fallback
            try:
                response = requests.get(
                    f"{OPS_API_BASE.rstrip('/')}/api/tail-log",
                    params={"limit": limit},
                    timeout=3.5,
                )
                response.raise_for_status()
                return response.json()
            except Exception as exc:
                fallback[0]["message"] = f"Tail log unavailable ({exc})"
                return fallback

        def make_stat_card(label: str, value: str, hint: str, accent: str) -> widgets.HTML:
            return widgets.HTML(
                value=f'''
                <div class="stat-card">
                    <h4 style="color:{accent}">{label}</h4>
                    <p>{value}</p>
                    <small>{hint}</small>
                </div>
                '''
            )

        def format_dataframe(df: pd.DataFrame, empty_message: str) -> widgets.HTML:
            if df.empty:
                return widgets.HTML(value=f"<div class='lab-panel'><em>{empty_message}</em></div>")
            return widgets.HTML(value=df.to_html(index=False, classes="lab-table"))

        stats_box = widgets.HBox(layout=widgets.Layout(justify_content="space-between"))
        hypothesis_table_out = widgets.Output()
        test_table_out = widgets.Output()
        combine_output = widgets.Output()
        ops_log_out = widgets.Output(layout=widgets.Layout(max_height="240px", overflow_y="auto"))
        change_log_out = widgets.Output(layout=widgets.Layout(max_height="200px", overflow_y="auto"))
        plot_output = widgets.Output()
        vote_status = widgets.HTML()
        flow_panel = widgets.HTML(
            value='''
            <div class="lab-panel">
                <h3>Workflow explainer</h3>
                <p>This workspace keeps hypotheses, tests, telemetry, and decisions together. Start at the top meta grid, design or import tests, run or simulate them, then use the voting matrix to choose which hypothesis graduates into the dedicated TestLab environment.</p>
                <ul>
                    <li><strong>Inputs</strong>: hypotheses, experiment definitions, live ops/tail logs, telemetry tables.</li>
                    <li><strong>Actions</strong>: create/edit tests, combine runs, run simulations, cast votes, refresh ops context.</li>
                    <li><strong>Outputs</strong>: decision matrix, aggregated pass rates, live data volume, change-log trail.</li>
                </ul>
            </div>
            '''
        )

        hyp_title_input = widgets.Text(description="Title", placeholder="Latency clusters → quality")
        hyp_objective_input = widgets.Textarea(description="Objective", rows=3)
        hyp_tags_input = widgets.Text(description="Tags", placeholder="comma,separated")
        add_hyp_button = widgets.Button(description="Add hypothesis", button_style="success", icon="plus")

        test_parent_dropdown = widgets.Dropdown(options=[], description="Hypothesis")
        test_name_input = widgets.Text(description="Test name")
        test_metric_input = widgets.Text(description="Metric", placeholder="precision")
        test_target_input = widgets.FloatText(description="Target")
        test_desc_input = widgets.Textarea(description="Description", rows=2)
        test_stage_dropdown = widgets.Dropdown(options=[("Ideation", "ideation"), ("Lab", "lab"), ("Pilot", "pilot"), ("Analysis", "analysis")], description="Stage")
        add_test_button = widgets.Button(description="Add test", button_style="info", icon="flask")

        run_test_dropdown = widgets.Dropdown(options=[], description="Test")
        run_intensity_slider = widgets.FloatSlider(description="Intensity", min=0.8, max=1.2, step=0.05, value=1.0)
        run_jitter_slider = widgets.FloatSlider(description="Jitter", min=0.01, max=0.25, step=0.01, value=0.08)
        run_button = widgets.Button(description="Run simulation", button_style="warning", icon="play")

        vote_dropdown = widgets.Dropdown(options=[], description="Hypothesis")
        vote_slider = widgets.IntSlider(description="Votes", min=1, max=5, value=1)
        vote_button = widgets.Button(description="Cast votes", button_style="primary", icon="check")

        combine_select = widgets.SelectMultiple(options=[], description="Tests", layout=widgets.Layout(width="320px", height="200px"))
        combine_button = widgets.Button(description="Combine & analyze", icon="link", button_style="info")

        viz_chart_selector = widgets.ToggleButtons(
            options=[
                ("Pass rate vs votes", "pass-votes"),
                ("Latency trend", "latency"),
                ("Data volume", "volume"),
            ],
            description="Graph",
        )
        viz_min_runs = widgets.IntSlider(description="Min runs", min=1, max=8, value=2)

        ops_refresh_button = widgets.Button(description="Refresh tail log", icon="refresh", button_style="info")

        def refresh_options():
            hyp_options = [(hyp.title, hyp.key) for hyp in registry.hypotheses.values()]
            test_options = [(test.name, test.key) for test in registry.tests.values()]
            if not hyp_options:
                hyp_options = [("—", "")]
            test_parent_dropdown.options = hyp_options
            vote_dropdown.options = hyp_options
            run_test_dropdown.options = test_options or [("—", "")]
            combine_select.options = test_options or []

        def refresh_stats():
            stats = registry.metrics()
            cards = [
                make_stat_card("Hypotheses", f"{stats['hypotheses']}", "tracked", "#9d7bff"),
                make_stat_card("Tests", f"{stats['tests']}", "in catalog", "#7af5a5"),
                make_stat_card("Runs", f"{stats['runs']}", "executed", "#ffb347"),
                make_stat_card("Votes", f"{stats['votes']}", "total", "#ff9ca8"),
                make_stat_card("Confidence", f"{stats['avg_confidence']:.2f}", "avg", "#7dd3fc"),
                make_stat_card("Data pts", f"{stats['data_points']}", "captured", "#f472b6"),
                make_stat_card("Changes", f"{stats['changes']}", "this session", "#c4b5fd"),
            ]
            stats_box.children = cards

        def refresh_tables():
            with hypothesis_table_out:
                clear_output(wait=True)
                display(format_dataframe(registry.hypotheses_frame(), "No hypotheses yet."))
            with test_table_out:
                clear_output(wait=True)
                display(format_dataframe(registry.tests_frame(), "Add a test to populate this table."))
            with change_log_out:
                clear_output(wait=True)
                for ts, message in reversed(registry.changelog[-6:]):
                    display(widgets.HTML(value=f"<div class='ops-log-entry'><strong>{ts.strftime('%H:%M:%S')}</strong> · {message}</div>"))

        def refresh_plot(*_):
            df = registry.tests_frame()
            if df.empty:
                with plot_output:
                    clear_output(wait=True)
                    display(widgets.HTML(value="<em>No test data yet.</em>"))
                    return
            summary = registry.hypotheses_frame()
            if viz_chart_selector.value == "pass-votes":
                fig = px.scatter(
                    summary,
                    x="votes",
                    y="avg_pass_rate",
                    size="data_points",
                    color="confidence",
                    hover_name="title",
                    title="Votes vs pass rate (bubble size = data volume)",
                    range_y=[0, 1],
                    template="plotly_dark",
                )
            elif viz_chart_selector.value == "latency":
                results = registry.results_frame()
                filtered = results.groupby("test_key").filter(lambda grp: len(grp) >= viz_min_runs.value)
                if filtered.empty:
                    fig = px.scatter(title="Not enough runs for latency trend")
                else:
                    fig = px.line(
                        filtered,
                        x="created_at",
                        y="value",
                        color="test_key",
                        title="Metric trend over time",
                        template="plotly_dark",
                    )
            else:
                summary = registry.tests_frame()
                fig = px.bar(
                    summary,
                    x="test",
                    y="data_points",
                    color="stage",
                    title="Data volume per test",
                    template="plotly_dark",
                )
            with plot_output:
                clear_output(wait=True)
                fig.show()

        def refresh_ops_log(*_):
            entries = fetch_tail_log(limit=15)
            with ops_log_out:
                clear_output(wait=True)
                for entry in entries:
                    created = entry.get("createdAt") or entry.get("created_at")
                    try:
                        timestamp = datetime.fromisoformat(str(created).replace("Z", ""))
                        stamp = timestamp.strftime("%H:%M:%S")
                    except Exception:
                        stamp = "—"
                    display(
                        widgets.HTML(
                            value=f"<div class='ops-log-entry'><strong>{stamp}</strong> [{entry.get('source','ops')}] {entry.get('message')}</div>"
                        )
                    )

        def handle_add_hypothesis(_):
            if not hyp_title_input.value or not hyp_objective_input.value:
                return
            tags = [tag.strip() for tag in hyp_tags_input.value.split(",") if tag.strip()]
            registry.add_hypothesis(hyp_title_input.value, hyp_objective_input.value, tags=tags)
            hyp_title_input.value = ""
            hyp_objective_input.value = ""
            hyp_tags_input.value = ""
            refresh_options()
            refresh_stats()
            refresh_tables()

        def handle_add_test(_):
            if not test_parent_dropdown.value or not test_name_input.value:
                return
            registry.add_test(
                hypothesis_key=test_parent_dropdown.value,
                name=test_name_input.value,
                description=test_desc_input.value,
                metric=test_metric_input.value or "metric",
                target=test_target_input.value or 0.0,
                stage=test_stage_dropdown.value,
            )
            test_name_input.value = ""
            test_metric_input.value = ""
            test_target_input.value = 0.0
            test_desc_input.value = ""
            refresh_options()
            refresh_tables()

        def handle_run_test(_):
            if not run_test_dropdown.value:
                return
            registry.simulate_run(
                run_test_dropdown.value,
                intensity=run_intensity_slider.value,
                jitter=run_jitter_slider.value,
            )
            refresh_stats()
            refresh_tables()
            refresh_plot()

        def handle_vote(_):
            if not vote_dropdown.value:
                return
            registry.cast_vote(vote_dropdown.value, vote_slider.value)
            vote_status.value = f"<div class='vote-pill'>Votes applied · +{vote_slider.value}</div>"
            refresh_stats()
            refresh_tables()
            refresh_plot()

        def handle_combine(_):
            selected = list(combine_select.value)
            combo = registry.combine_tests(selected)
            with combine_output:
                clear_output(wait=True)
                if combo.empty:
                    display(widgets.HTML(value="<em>Select at least one test.</em>"))
                else:
                    display(format_dataframe(combo, ""))

        add_hyp_button.on_click(handle_add_hypothesis)
        add_test_button.on_click(handle_add_test)
        run_button.on_click(handle_run_test)
        vote_button.on_click(handle_vote)
        combine_button.on_click(handle_combine)
        viz_chart_selector.observe(refresh_plot, names="value")
        viz_min_runs.observe(refresh_plot, names="value")
        ops_refresh_button.on_click(refresh_ops_log)

        refresh_options()
        refresh_stats()
        refresh_tables()
        refresh_plot()
        refresh_ops_log()

        hypothesis_panel = widgets.VBox(
            [
                widgets.HTML(value="<h3>Hypothesis registry</h3>"),
                hypothesis_table_out,
                widgets.HBox([hyp_title_input, hyp_tags_input]),
                hyp_objective_input,
                add_hyp_button,
            ],
            layout=widgets.Layout(width="48%"),
        )

        test_panel = widgets.VBox(
            [
                widgets.HTML(value="<h3>Experiment designer</h3>"),
                test_table_out,
                test_parent_dropdown,
                test_name_input,
                widgets.HBox([test_metric_input, test_target_input]),
                test_desc_input,
                test_stage_dropdown,
                add_test_button,
            ],
            layout=widgets.Layout(width="48%"),
        )

        run_panel = widgets.VBox(
            [
                widgets.HTML(value="<h3>Run & monitor tests</h3>"),
                widgets.HBox([run_test_dropdown, run_intensity_slider, run_jitter_slider]),
                run_button,
                widgets.HTML(value="<h4>Combined / cross-reference</h4>"),
                combine_select,
                combine_button,
                combine_output,
            ]
        )

        voting_panel = widgets.VBox(
            [
                widgets.HTML(value="<h3>Voting + decision matrix</h3>"),
                vote_dropdown,
                vote_slider,
                vote_button,
                vote_status,
                widgets.HTML(value="<h4>Recent changes</h4>"),
                change_log_out,
            ]
        )

        viz_panel = widgets.VBox(
            [
                widgets.HTML(value="<h3>Interactive data wall</h3>"),
                widgets.HBox([viz_chart_selector, viz_min_runs]),
                plot_output,
            ]
        )

        ops_panel = widgets.VBox(
            [
                widgets.HTML(value="<h3>Ops / Tail console</h3>"),
                ops_refresh_button,
                ops_log_out,
            ]
        )

        dashboard = widgets.VBox(
            [
                widgets.HTML(value="<div class='lab-panel'><h3>Meta grid</h3></div>"),
                stats_box,
                flow_panel,
                widgets.HBox([hypothesis_panel, test_panel], layout=widgets.Layout(justify_content="space-between")),
                widgets.HBox([run_panel, voting_panel], layout=widgets.Layout(justify_content="space-between")),
                viz_panel,
                ops_panel,
            ],
            layout=widgets.Layout(gap="1.5rem"),
        )

        display(dashboard)
        """
    ),
]

notebook = {
    "cells": cells,
    "metadata": {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3",
        },
        "language_info": {
            "name": "python",
            "version": "3.10",
        },
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}

def main() -> None:
    target = Path("d:/Files/Code 3/ChatAI-DataLab/datalab/notebooks/hypothesis_control.ipynb")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(notebook, indent=2))


if __name__ == "__main__":
    main()
