import asyncio
import logging
import subprocess
import sys

from quart import Blueprint, jsonify

from ..broadcast import broadcast_stats
from ..stats_service import real_time_stats
from .system_routes import _cleanup_bot

github_bp = Blueprint("dashboard_github", __name__)


async def run_git_command(*args):
    """Run a git command and return stdout, stderr, and return code."""
    try:
        process = await asyncio.create_subprocess_exec(
            "git", *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd="."
        )
        stdout, stderr = await process.communicate()
        return {
            "stdout": stdout.decode().strip(),
            "stderr": stderr.decode().strip(),
            "returncode": process.returncode
        }
    except Exception as e:
        logging.error(f"Error running git command: {e}")
        return {
            "stdout": "",
            "stderr": str(e),
            "returncode": 1
        }


@github_bp.route("/api/github/status")
async def api_github_status():
    """Get current git status including commit hash, branch, and uncommitted changes."""
    try:
        # Get current commit hash (full and short)
        result = await run_git_command("rev-parse", "HEAD")
        if result["returncode"] != 0:
            return jsonify({"error": "Failed to get current commit"}), 500
        current_commit = result["stdout"]

        result = await run_git_command("rev-parse", "--short=7", "HEAD")
        if result["returncode"] != 0:
            return jsonify({"error": "Failed to get short commit"}), 500
        current_commit_short = result["stdout"]

        # Get current branch
        result = await run_git_command("rev-parse", "--abbrev-ref", "HEAD")
        if result["returncode"] != 0:
            return jsonify({"error": "Failed to get current branch"}), 500
        current_branch = result["stdout"]

        # Check for uncommitted changes
        result = await run_git_command("status", "--porcelain")
        has_uncommitted_changes = len(result["stdout"]) > 0

        # Get remote URL
        result = await run_git_command("config", "--get", "remote.origin.url")
        remote_url = result["stdout"] if result["returncode"] == 0 else ""

        return jsonify({
            "current_commit": current_commit,
            "current_commit_short": current_commit_short,
            "current_branch": current_branch,
            "has_uncommitted_changes": has_uncommitted_changes,
            "remote_url": remote_url
        })
    except Exception as e:
        logging.error(f"Error getting git status: {e}")
        return jsonify({"error": str(e)}), 500


@github_bp.route("/api/github/check-updates")
async def api_github_check_updates():
    """Check for available updates from origin/main."""
    try:
        # Get current commit
        result = await run_git_command("rev-parse", "HEAD")
        if result["returncode"] != 0:
            return jsonify({"error": "Failed to get current commit"}), 500
        current_commit = result["stdout"]

        result = await run_git_command("rev-parse", "--short=7", "HEAD")
        if result["returncode"] != 0:
            return jsonify({"error": "Failed to get short commit"}), 500
        current_commit_short = result["stdout"]

        # Fetch from remote
        result = await run_git_command("fetch", "origin", "main")
        if result["returncode"] != 0:
            return jsonify({"error": f"Failed to fetch from remote: {result['stderr']}"}), 500

        # Get latest commit from origin/main
        result = await run_git_command("rev-parse", "origin/main")
        if result["returncode"] != 0:
            return jsonify({"error": "Failed to get remote commit"}), 500
        latest_commit = result["stdout"]

        result = await run_git_command("rev-parse", "--short=7", "origin/main")
        if result["returncode"] != 0:
            return jsonify({"error": "Failed to get short remote commit"}), 500
        latest_commit_short = result["stdout"]

        # Check if already up to date
        if current_commit == latest_commit:
            return jsonify({
                "updates_available": False,
                "current_commit": current_commit,
                "current_commit_short": current_commit_short,
                "latest_commit": latest_commit,
                "latest_commit_short": latest_commit_short,
                "commits_behind": 0,
                "commit_log": []
            })

        # Get number of commits behind
        result = await run_git_command("rev-list", "--count", f"HEAD..origin/main")
        commits_behind = int(result["stdout"]) if result["returncode"] == 0 else 0

        # Get commit log
        result = await run_git_command(
            "log",
            "--pretty=format:%H|%an|%aI|%s",
            f"HEAD..origin/main"
        )

        commit_log = []
        if result["returncode"] == 0 and result["stdout"]:
            for line in result["stdout"].split("\n"):
                if line.strip():
                    parts = line.split("|", 3)
                    if len(parts) == 4:
                        commit_log.append({
                            "hash": parts[0][:7],  # Short hash
                            "author": parts[1],
                            "date": parts[2],
                            "message": parts[3]
                        })

        return jsonify({
            "updates_available": True,
            "current_commit": current_commit,
            "current_commit_short": current_commit_short,
            "latest_commit": latest_commit,
            "latest_commit_short": latest_commit_short,
            "commits_behind": commits_behind,
            "commit_log": commit_log
        })
    except Exception as e:
        logging.error(f"Error checking for updates: {e}")
        return jsonify({"error": str(e)}), 500


@github_bp.route("/api/github/update", methods=["POST"])
async def api_github_update():
    """Pull from origin/main and restart the bot."""
    try:
        real_time_stats.add_event_log("GitHub update requested via dashboard", "system")
        await broadcast_stats()

        # Schedule the update and restart as an async task
        asyncio.create_task(_perform_update_and_restart())

        return jsonify({"success": True, "message": "Update and restart initiated"})
    except Exception as e:
        logging.error(f"Error initiating update: {e}")
        return jsonify({"error": str(e)}), 500


async def _perform_update_and_restart():
    """Perform git pull and restart the bot."""
    try:
        # Wait for the response to send
        await asyncio.sleep(1)

        logging.info("Starting update and restart...")

        # Attempt git pull (log result but continue even if it fails)
        try:
            result = await run_git_command("pull", "origin", "main")
            if result["returncode"] == 0:
                logging.info(f"Git pull successful: {result['stdout']}")
            else:
                logging.warning(f"Git pull failed: {result['stderr']} - continuing with restart")
        except Exception as e:
            logging.warning(f"Git pull error: {e} - continuing with restart")

        # Perform cleanup
        await _cleanup_bot()

        # Wait for everything to settle
        await asyncio.sleep(1)

        # Restart the process
        logging.info("Executing restart...")
        subprocess.Popen([sys.executable] + sys.argv)
        logging.info("New process started, exiting...")
        sys.exit(0)

    except Exception as e:
        logging.error(f"Error during update and restart: {e}")
        # Still attempt to restart even if cleanup fails (recovery mechanism)
        subprocess.Popen([sys.executable] + sys.argv)
        sys.exit(1)
