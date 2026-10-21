# Runaway Agent Monitoring System

## Project Overview

This project is a runtime monitoring layer designed to detect and restrict suspicious behavior in AI agents. It monitors agent actions before they reach the tools and helps prevent repeated actions, loops, excessive tool calls, and lack of progress.

## Problem Statement

AI agents can get stuck repeating actions, executing loops, or making unnecessary tool calls. This can waste time and computational resources. Our system monitors these behaviors and restricts suspicious actions before they are executed.

## Goal

To build a monitoring layer that detects runaway agent behavior, controls risky actions, and records decisions for evaluation.

## System Architecture

The system follows this workflow:

`Simulated Agent → Action Gateway → Monitoring Detectors → Risk Engine → Controller → Mock Tools`

The Event Logger stores action details, risk scores, decisions, and reasons in an SQLite database.

## Working Principle

1. **Action Gateway:** Intercepts every proposed action before it reaches a tool and coordinates the monitoring process.

2. **Repetition Detector:** Detects identical actions repeated beyond a configured limit by comparing their type, target, and arguments.

3. **Cycle Detector:** Identifies repeating sequences of actions, such as reading a file and undoing the action repeatedly.

4. **Frequency Detector:** Detects excessive tool calls within a specified time window.

5. **Semantic Similarity Detector:** Uses TF-IDF and cosine similarity to identify actions with highly similar text arguments, even when their wording differs.

6. **Progress Monitor:** Tracks whether actions produce meaningful progress and flags consecutive actions that fail to advance the task.

7. **Risk Engine:** Combines detector risk scores and records reasons for suspicious behavior. The current overall risk score is the maximum individual detector score.

8. **Controller:** Uses the risk score and detection reasons to decide whether to allow, block, pause, or throttle an action.

9. **Event Logger:** Stores action details, results, risk scores, decisions, and reasons in an SQLite database for inspection and evaluation.

## Project Structure

```text
os_project/
├── agent/
│   └── simulated_agent.py
├── gateway/
│   └── action_gateway.py
├── monitor/
│   ├── repetition_detector.py
│   ├── cycle_detector.py
│   ├── frequency_detector.py
│   ├── progress_monitor.py
│   └── semantic_detector.py
├── tests/
│   └── test_gateway.py
├── controller.py
├── risk_engine.py
├── mock_tools.py
├── event_logger.py
├── event_schema.py
├── run.py
└── monitor.db
```

## Setup and Installation

**Requirements:** Python 3.14.4 and pip.

1. Clone the repository and move into the project directory.

2. Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

3. Install the required libraries:

```bash
pip install pandas numpy scikit-learn
```

If a `requirements.txt` file is available, use `pip install -r requirements.txt` instead.

## Running the Project

Run a scenario using:

```bash
python run.py --scenario normal --db normal.db
```

Available scenarios:

```bash
python run.py --scenario repetitive --db repetitive.db
python run.py --scenario cyclic --db cyclic.db
python run.py --scenario frequency --db frequency.db
python run.py --scenario semantic --db semantic.db
python run.py --scenario progress --db progress.db
```

Run the unit tests:

```bash
python -m unittest discover -s tests -v
```

## Implementation

The current prototype has demonstrated the following behaviors:

- **Normal task:** Actions are allowed and the task completes.
- **Repetitive behavior:** Repeated searches beyond the configured limit are blocked.
- **Cyclic behavior:** Repeating action sequences are detected and blocked.
- **Excessive frequency:** Actions exceeding the configured time-window limit are restricted.
- **Semantic similarity:** Highly similar search requests are detected and restricted.
- **Lack of progress:** Consecutive actions without meaningful progress can trigger restrictions.
- **Event logging:** Action results, risk scores, decisions, and reasons are stored in SQLite.

## Evaluation and Results

The system was evaluated using six scenarios: normal, repetitive, cyclic, frequency, semantic similarity, and lack of progress.

### Evaluation Metrics

- **Detection Accuracy:** Percentage of actions correctly classified.
- **False Positive Rate:** Percentage of normal actions incorrectly flagged.
- **Detection Latency:** Average time from scenario start to first detection.
- **Actions Prevented:** Number of actions rejected by the gateway.
- **Computational Overhead:** Estimated additional processing time introduced by the gateway.

### Results

| Metric | Result |
|---|---:|
| Detection Accuracy | 100.00% |
| False Positive Rate | 0.00% |
| Detection Latency | 25.8188 ms |
| Actions Prevented | 9 |
| Average Gateway Latency | 8.8825 ms |
| Estimated Computational Overhead | 8.8800 ms |

### Scenario Results

| Scenario | Correct | Prevented |
|---|---:|---:|
| Normal | 3/3 | 0 |
| Repetitive | 5/5 | 2 |
| Cyclic | 6/6 | 3 |
| Frequency | 7/7 | 2 |
| Semantic | 2/2 | 1 |
| Progress | 4/4 | 1 |
| **Total** | **27/27** | **9** |

All nine unit tests passed using `python -m unittest discover -s tests -v`.

### Limitations

These results are from controlled scenarios using a simulated agent and mock tools. The accuracy and false positive rate apply only to the tested actions. Computational overhead is an estimate, and further testing with real agents and tools is required.