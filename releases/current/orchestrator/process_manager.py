"""Process lifecycle management for launched games."""
from __future__ import annotations
import logging
import os
import subprocess
from dataclasses import dataclass
from typing import Optional

import psutil

from manifest import GameEntry

LOGGER = logging.getLogger("orchestrator.process_manager")


@dataclass
class ProcessExit:
    """Information about a process exit event."""

    game_id: Optional[str]
    returncode: Optional[int]
    expected: bool


class ProcessManager:
    """Start and stop games as child processes."""

    def __init__(self) -> None:
        self._proc: Optional[psutil.Process] = None
        self._game: Optional[GameEntry] = None
        self._stopping: bool = False

    def is_running(self) -> bool:
        return self._proc is not None and self._proc.is_running()

    @property
    def current_game_id(self) -> Optional[str]:
        return self._game.id if self._game else None

    def start(self, game: GameEntry) -> None:
        if self.is_running():
            raise RuntimeError("a game is already running")

        env = os.environ.copy()
        env.update(game.env or {})
        cmd = [game.exec] + list(game.args or [])
        LOGGER.info("launching game", extra={"cmd": cmd, "game_id": game.id})
        try:
            proc = subprocess.Popen(
                cmd,
                cwd=game.workdir or None,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception as exc:
            LOGGER.exception("failed to start game %s", game.id)
            raise

        self._proc = psutil.Process(proc.pid)
        self._game = game
        self._stopping = False

    def stop(self, timeout_sec: float = 3.0) -> Optional[ProcessExit]:
        if self._proc is None:
            return None

        proc = self._proc
        game = self._game
        self._stopping = True
        LOGGER.info("stopping current game", extra={"game_id": game.id if game else None})
        try:
            if proc.is_running():
                for child in proc.children(recursive=True):
                    try:
                        child.terminate()
                    except Exception:
                        LOGGER.debug("failed terminating child", exc_info=True)
                try:
                    proc.terminate()
                except Exception:
                    LOGGER.debug("terminate failed", exc_info=True)
                gone, alive = psutil.wait_procs([proc], timeout=timeout_sec)
                if alive:
                    LOGGER.warning("force killing remaining process")
                    for p in alive:
                        try:
                            p.kill()
                        except Exception:
                            LOGGER.debug("kill failed", exc_info=True)
                        try:
                            p.wait(timeout=timeout_sec)
                        except Exception:
                            LOGGER.debug("wait on kill failed", exc_info=True)
        finally:
            returncode: Optional[int] = None
            try:
                returncode = proc.wait(timeout=0)
            except (psutil.TimeoutExpired, psutil.NoSuchProcess):
                returncode = None
            except psutil.Error:
                LOGGER.debug("wait returned psutil error", exc_info=True)
            self._proc = None
            self._game = None
            self._stopping = False
        return ProcessExit(game_id=game.id if game else None, returncode=returncode, expected=True)

    def poll_exit(self) -> Optional[ProcessExit]:
        if self._proc is None:
            return None

        proc = self._proc
        game = self._game
        try:
            returncode = proc.wait(timeout=0)
        except psutil.TimeoutExpired:
            return None
        except psutil.NoSuchProcess:
            returncode = proc.returncode
        except psutil.Error:
            LOGGER.debug("poll wait error", exc_info=True)
            returncode = None

        self._proc = None
        self._game = None
        expected = self._stopping
        self._stopping = False
        return ProcessExit(game_id=game.id if game else None, returncode=returncode, expected=expected)


__all__ = ["ProcessManager", "ProcessExit"]
