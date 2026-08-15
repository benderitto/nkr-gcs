from nkr_gcs.model.robot_model import RobotModel
from nkr_gcs.robot_state_notifier import RobotStateNotifier


class Popup:
    def __init__(self):
        self.messages = []

    def show_message(self, text, timeout_ms):
        self.messages.append((text, timeout_ms))


def test_notifier_emits_once_and_queues_armed_before_mode():
    robot = RobotModel()
    popup = Popup()
    callbacks = []
    notifier = RobotStateNotifier(popup, robot, lambda delay, fn: callbacks.append(fn))
    robot.armed = True
    robot.active_mode = 2
    notifier.update(robot)
    assert popup.messages == [("ROBOT ARMED", 1500)]
    callbacks.pop()()
    assert popup.messages[-1] == ("DRIVE MODE: TANK", 1500)
    notifier.update(robot)
    assert len(popup.messages) == 2


def test_estop_activation_has_priority_over_other_changes():
    robot = RobotModel()
    popup = Popup()
    notifier = RobotStateNotifier(popup, robot, lambda *_: None)
    robot.armed = True
    robot.active_mode = 3
    robot.estop = True
    notifier.update(robot)
    assert popup.messages == [("E-STOP ACTIVE", 3000)]
