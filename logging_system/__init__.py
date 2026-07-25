"""
gesturedrive.logging_system
=============================
Centralized structured logging subsystem.

Usage (in any module)
---------------------
    from logging_system.logger_factory import LoggerFactory
    logger = LoggerFactory.get(__name__)
    logger.info("Ready.")
"""
