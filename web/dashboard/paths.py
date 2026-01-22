import os

WEB_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ROOT_DIR = os.path.abspath(os.path.join(WEB_DIR, ".."))
DATABASE_DIR = os.path.join(ROOT_DIR, "database")
REACT_BUILD_DIR = os.path.join(WEB_DIR, "frontend", "dist")
