"""Content-generation eval harness for the LinkedIn wedge.

Runs the Writer agent against a fixed seed set, scores drafts via an
LLM-as-judge, and compares aggregate scores to a committed baseline.

See README.md for invocation.
"""
