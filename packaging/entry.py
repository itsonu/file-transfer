"""PyInstaller entry point for the standalone Open Transfer executable."""

from open_transfer.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
