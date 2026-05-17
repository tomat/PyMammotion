"""sys.toapp_* status packets update cached report_data."""

from __future__ import annotations

from pymammotion.data.model.device import MowerDevice
from pymammotion.data.model.report_info import LocationData
from pymammotion.device.state_reducer import MowerStateReducer
from pymammotion.proto import LubaMsg, MctlSys, SysBatUp, SysMowInfo, SysWorkState


def test_toapp_batinfo_updates_battery_on_copied_report_data() -> None:
    reducer = MowerStateReducer()
    current = MowerDevice(name="Yuka-Test")
    current.report_data.dev.battery_val = 35
    current.report_data.dev.sys_status = 7

    msg = LubaMsg(sys=MctlSys(toapp_batinfo=SysBatUp(bat_val=74)))
    updated = reducer.apply(current, msg)

    assert updated.report_data is not current.report_data
    assert updated.report_data.dev is not current.report_data.dev
    assert updated.report_data.dev.battery_val == 74
    assert updated.report_data.dev.sys_status == 7
    assert current.report_data.dev.battery_val == 35


def test_toapp_work_state_updates_device_state_charge_and_hashes() -> None:
    reducer = MowerStateReducer()
    current = MowerDevice(name="Yuka-Test")
    current.report_data.dev.sys_status = 3
    current.report_data.dev.charge_state = 1
    current.report_data.work.path_hash = 111
    current.report_data.locations = [LocationData(bol_hash=222)]

    msg = LubaMsg(
        sys=MctlSys(
            toapp_work_state=SysWorkState(
                device_state=5,
                charge_state=2,
                cm_hash=333,
                path_hash=444,
            )
        )
    )
    updated = reducer.apply(current, msg)

    assert updated.report_data is not current.report_data
    assert updated.report_data.dev.sys_status == 5
    assert updated.report_data.dev.charge_state == 2
    assert updated.report_data.work.path_hash == 444
    assert updated.report_data.locations[0].bol_hash == 333
    assert current.report_data.dev.sys_status == 3
    assert current.report_data.dev.charge_state == 1
    assert current.report_data.work.path_hash == 111
    assert current.report_data.locations[0].bol_hash == 222


def test_toapp_mow_info_updates_app_visible_mow_info() -> None:
    reducer = MowerStateReducer()
    current = MowerDevice(name="Yuka-Test")
    current.report_data.dev.sys_status = 3
    current.report_data.dev.battery_val = 35
    current.report_data.dev.charge_state = 1
    current.report_data.work.knife_height = 45
    current.report_data.rtk.status = 1
    current.report_data.rtk.gps_stars = 12

    msg = LubaMsg(
        sys=MctlSys(
            toapp_mow_info=SysMowInfo(
                device_state=6,
                bat_val=88,
                knife_height=65,
                rt_kstatus=4,
                rt_kstars=21,
            )
        )
    )
    updated = reducer.apply(current, msg)

    assert updated.report_data is not current.report_data
    assert updated.report_data.dev.sys_status == 6
    assert updated.report_data.dev.battery_val == 88
    assert updated.report_data.dev.charge_state == 1
    assert updated.report_data.work.knife_height == 65
    assert updated.report_data.rtk.status == 4
    assert updated.report_data.rtk.gps_stars == 21
    assert current.report_data.dev.sys_status == 3
    assert current.report_data.dev.battery_val == 35
    assert current.report_data.work.knife_height == 45
