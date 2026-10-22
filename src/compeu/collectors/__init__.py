"""One collector per provider. Add new ones to ALL."""

from .aws import AWS
from .azure import Azure
from .exoscale import Exoscale
from .hetzner import Hetzner
from .ionos import Ionos
from .koyeb import Koyeb
from .leafcloud import Leafcloud
from .lyceum import Lyceum
from .nebius import Nebius
from .ovhcloud import OVHcloud
from .runpod import RunPod
from .scaleway import Scaleway
from .seeweb import Seeweb
from .upcloud import UpCloud
from .verda import Verda

_ORDER = (
    Scaleway,
    OVHcloud,
    Hetzner,
    Verda,
    Exoscale,
    Nebius,
    Lyceum,
    Seeweb,
    UpCloud,
    Leafcloud,
    Ionos,
    Koyeb,
    AWS,
    Azure,
    RunPod,
)
ALL = {c.provider: c for c in _ORDER}
