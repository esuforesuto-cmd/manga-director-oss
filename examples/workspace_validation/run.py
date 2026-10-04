"""Render safe workspace and declared-dependency diagnostics."""

from pathlib import Path

from manga_director.production import DevelopmentDiagnostics

if __name__ == "__main__":
    print(DevelopmentDiagnostics(Path(__file__).resolve().parents[2]).report().to_markdown())
