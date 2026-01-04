#!/usr/bin/env python3
"""Entry point for PyInstaller bundled executable.

This script exists to avoid relative import issues when running as a bundled executable.
PyInstaller needs to run the module as a package, not as a standalone script.
"""

if __name__ == "__main__":
    from mtg_core.api.server import main

    main()
