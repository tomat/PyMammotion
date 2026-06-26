from collections.abc import Iterable
from dataclasses import dataclass, field

from mashumaro.mixins.orjson import DataClassORJSONMixin

from pymammotion.http.model.http import ErrorInfo


@dataclass
class DeviceErrors(DataClassORJSONMixin):
    """Active error codes and their associated timestamps reported by the device."""

    err_code_list: list[int] = field(default_factory=list)
    err_code_list_time: list[int] = field(default_factory=list)
    error_codes: dict[str, ErrorInfo] = field(default_factory=dict)

    def set_error_pairs(self, codes: list[int], timestamps: list[int]) -> None:
        """Store reported errors with known active codes first.

        Mammotion devices can report several concurrent error slots. Some slots
        contain internal/debug codes which are not present in the public error
        metadata. Consumers that only surface the first error should see a known
        actionable error before an unmapped internal code.
        """
        pairs = self.prioritized_error_pairs(zip(codes, timestamps, strict=False))
        self.err_code_list[:] = [code for code, _timestamp in pairs]
        self.err_code_list_time[:] = [timestamp for _code, timestamp in pairs]

    def prioritized_error_pairs(self, pairs: Iterable[tuple[int, int]]) -> list[tuple[int, int]]:
        """Return error pairs ordered as known active, unknown active, inactive."""
        indexed_pairs: list[tuple[int, int, int, int]] = []
        for index, pair in enumerate(pairs):
            code, timestamp = pair
            code = int(code)
            timestamp = int(timestamp)
            abs_code = abs(code)
            if abs_code == 0:
                priority = 2
            elif str(abs_code) in self.error_codes:
                priority = 0
            else:
                priority = 1
            indexed_pairs.append((priority, index, code, timestamp))

        return [
            (code, timestamp)
            for _priority, _index, code, timestamp in sorted(indexed_pairs)
        ]

    def error_pair(self, number: int = 1) -> tuple[int, int] | None:
        """Return the nth prioritized active error pair, using 1-based numbering."""
        if number < 1:
            return None

        active_pairs = [
            pair
            for pair in self.prioritized_error_pairs(
                zip(self.err_code_list, self.err_code_list_time, strict=False)
            )
            if abs(pair[0]) != 0
        ]
        try:
            return active_pairs[number - 1]
        except IndexError:
            return None
