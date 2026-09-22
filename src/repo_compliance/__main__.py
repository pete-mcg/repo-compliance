"""Run the repository compliance checker as a module."""

import sys

from repo_compliance.app import main

if __name__ == "__main__":
    sys.exit(main())
