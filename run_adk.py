#!/usr/bin/env python3
"""
Entry point for the google.adk agent integration.

Runs a predefined mock scenario through the ADK monitoring stack without
making any live LLM calls (no GOOGLE_API_KEY required).

Usage:
    python run_adk.py --scenario normal
    python run_adk.py --scenario repetitive
    python run_adk.py --scenario cyclic

Environment variables (optional for live mode):
    GOOGLE_API_KEY  — Gemini API key for real LLM calls
    GOOGLE_MODEL    — Model ID (default: gemini-2.5-flash)
    TRACES_FILE     — OTel trace output file (default: traces.jsonl)
    MONITOR_DB      — SQLite event log path (default: adk_monitor.db)
"""
import argparse

from adk_agent.runaway_agent import run_mock_scenario


def main():
    parser = argparse.ArgumentParser(
        description="ADK Runaway Detection Agent — Mock Demo"
    )
    parser.add_argument(
        "--scenario",
        choices=["normal", "repetitive", "cyclic"],
        default="normal",
        help="Scenario to run (default: normal)",
    )
    args = parser.parse_args()
    run_mock_scenario(args.scenario)


if __name__ == "__main__":
    main()
