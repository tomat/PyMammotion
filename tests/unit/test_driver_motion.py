from pymammotion.mammotion.commands.mammotion_command import MammotionCommand
from pymammotion.proto import DrvMotionCtrl, DrvMotionCtrlAck, LubaMsg, MctlDriver


def test_motion_command_includes_ble_channel() -> None:
    """Movement packets identify BLE as the control channel."""
    command = MammotionCommand(device_name="YUKA", user_account=123)

    message = LubaMsg.FromString(command.send_movement(linear_speed=250, angular_speed=0))

    assert message.driver is not None
    assert message.driver.todev_devmotion_ctrl == DrvMotionCtrl(
        set_linear_speed=250,
        set_angular_speed=0,
        channel=1,
    )
    assert message.driver.todev_devmotion_ctrl.SerializeToString() == bytes.fromhex("08fa011801")


def test_motion_ack_is_decoded() -> None:
    """Current firmware motion acknowledgements expose drop and delay data."""
    payload = LubaMsg(
        driver=MctlDriver(
            toapp_devmotion_ctrl_ack=DrvMotionCtrlAck(
                timestamp=123,
                is_drop=1,
                delay_ms=456,
            )
        )
    ).SerializeToString()

    message = LubaMsg.FromString(payload)

    assert message.driver is not None
    assert message.driver.toapp_devmotion_ctrl_ack == DrvMotionCtrlAck(
        timestamp=123,
        is_drop=1,
        delay_ms=456,
    )
