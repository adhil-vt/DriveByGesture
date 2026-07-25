"""
gesturedrive.games
===================
Game plugin system.

OCP contract
------------
Adding support for a new game requires:
1. Creating a subpackage (e.g., games/need_for_speed/).
2. Implementing IGamePlugin in games/need_for_speed/plugin.py.
3. Registering in pyproject.toml entry points under "gesturedrive.games".

Zero changes to any existing code.
"""
