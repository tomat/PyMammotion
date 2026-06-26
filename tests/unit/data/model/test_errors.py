from __future__ import annotations

from typing import cast

from pymammotion.data.model.errors import DeviceErrors
from pymammotion.http.model.http import ErrorInfo


def _known_errors(*codes: int) -> dict[str, ErrorInfo]:
    return cast(dict[str, ErrorInfo], {str(code): object() for code in codes})


def test_known_active_error_is_selected_before_unknown_error() -> None:
    errors = DeviceErrors(
        err_code_list=[8000033, 1203, 1215],
        err_code_list_time=[100, 200, 300],
        error_codes=_known_errors(1203),
    )

    assert errors.error_pair() == (1203, 200)
    assert errors.error_pair(2) == (8000033, 100)


def test_zero_slots_are_not_selected_as_active_errors() -> None:
    errors = DeviceErrors(
        err_code_list=[0, 8000033, 0],
        err_code_list_time=[0, 100, 0],
        error_codes={},
    )

    assert errors.error_pair() == (8000033, 100)
    assert errors.error_pair(2) is None


def test_set_error_pairs_keeps_timestamps_matched_after_prioritizing() -> None:
    errors = DeviceErrors(error_codes=_known_errors(1203))

    errors.set_error_pairs([8000033, 1203, 0], [100, 200, 0])

    assert errors.err_code_list == [1203, 8000033, 0]
    assert errors.err_code_list_time == [200, 100, 0]
