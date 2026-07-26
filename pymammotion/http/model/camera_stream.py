from dataclasses import dataclass, field

from mashumaro.mixins.orjson import DataClassORJSONMixin


@dataclass
class Camera(DataClassORJSONMixin):
    """Single camera entry within a stream subscription response."""

    cameraId: int = 0
    token: str = ""


@dataclass
class StreamSubscriptionResponse(DataClassORJSONMixin):
    """Agora stream details returned by either Mammotion FPV API generation.

    The legacy ``/stream/subscription`` response omits the encryption, region,
    licence, and remaining-time fields added by ``/stream/token``.  Defaults
    keep both response shapes compatible with the same HA-facing model.
    """

    appid: str = ""
    openEncrypt: int = 0
    cameras: list[Camera] = field(default_factory=list)
    channelName: str = ""
    areaCode: str = ""
    token: str = ""
    uid: int = 0
    license: str | None = None
    availableTime: int | None = None


@dataclass
class VideoResourceResponse(DataClassORJSONMixin):
    """Video resource usage and availability data returned for a device."""

    id: str
    deviceId: str
    deviceName: str
    cycleType: int
    usageYearMonth: str
    totalTime: int
    availableTime: int
