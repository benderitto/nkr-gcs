"""Coalesce robot-state changes into non-blocking popup notifications."""

from .model.robot_model import MODE_NAMES


class RobotStateNotifier:
    def __init__(self, popup, robot=None, schedule=None):
        self.popup = popup
        self._previous = self._snapshot(robot) if robot is not None else None
        self._pending = []
        self._schedule = schedule or self._qt_schedule

    def update(self, robot) -> None:
        current = self._snapshot(robot)
        if self._previous is None:
            self._previous = current
            return
        old_mode, old_armed, old_estop = self._previous
        self._previous = current
        mode, armed, estop = current
        if current == (old_mode, old_armed, old_estop):
            return

        # E-stop activation supersedes all normal-state notifications.
        if estop and not old_estop:
            self._pending.clear()
            self._show("E-STOP ACTIVE", 3000)
            return
        messages = []
        if old_estop and not estop:
            messages.append(("E-STOP CLEARED", 1500))
        if armed != old_armed:
            messages.append(("ROBOT ARMED" if armed else "ROBOT DISARMED", 1500))
        if mode != old_mode and mode in MODE_NAMES:
            messages.append((f"DRIVE MODE: {MODE_NAMES[mode]}", 1500))
        self._enqueue(messages)

    def _enqueue(self, messages) -> None:
        if not messages:
            return
        if self._pending:
            self._pending.extend(messages)
            return
        first, *rest = messages
        self._pending = rest
        self._show(*first)

    def _show(self, text: str, timeout_ms: int) -> None:
        self.popup.show_message(text, timeout_ms)
        if self._pending:
            self._schedule(timeout_ms, self._show_next)

    def _show_next(self) -> None:
        if not self._pending:
            return
        message = self._pending.pop(0)
        self._show(*message)

    @staticmethod
    def _snapshot(robot):
        return robot.active_mode, robot.armed, robot.estop

    @staticmethod
    def _qt_schedule(timeout_ms, callback) -> None:
        # Local import keeps protocol/network tests independent of PySide6.
        from PySide6.QtCore import QTimer
        QTimer.singleShot(timeout_ms, callback)
