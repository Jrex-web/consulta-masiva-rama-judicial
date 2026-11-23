import os
import sys
from streamlit.web import cli as stcli


def resolve_path(path: str) -> str:
    if getattr(sys, "frozen", False):
        exe_dir = os.path.dirname(sys.executable)
        external_file = os.path.join(exe_dir, path)
        if os.path.exists(external_file):
            return external_file
        return os.path.join(sys._MEIPASS, path)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), path)


if __name__ == "__main__":
    # Prevent Streamlit logging crashes when --windowed sets stdout/stderr to None
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w")

    if getattr(sys, "frozen", False):
        sys.path.insert(0, os.path.dirname(sys.executable))

    app_path = resolve_path("app.py")
    sys.argv = [
        "streamlit",
        "run",
        app_path,
        "--global.developmentMode=false",
        "--server.headless=false",
    ]
    sys.exit(stcli.main())
