"""server/app.py — OpenEnv multi-mode deployment entry point."""
import os
from app import app  # Flask app instance

__all__ = ["app", "main"]


def main():
    """Entry point for `server` console script."""
    port = int(os.environ.get("PORT", 7860))
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)


if __name__ == "__main__":
    main()
