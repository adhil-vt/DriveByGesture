"""
gesturedrive.config
====================
Configuration subsystem — TOML-based, with hot-reload support.

Hierarchy (highest priority first)
------------------------------------
1. CLI arguments
2. config/user/<username>.toml
3. config/default.toml
4. Hardcoded defaults in config/defaults.py
"""
