"""One collector per provider. Add new ones to ALL."""

from .aws import AWS
from .azure import Azure
from .exoscale import Exoscale
from .hetzner import Hetzner
from .lyceum import Lyceum
from .nebius import Nebius
from .ovhcloud import OVHcloud
from .runpod import RunPod
from .scaleway import Scaleway
from .seeweb import Seeweb
from .verda import Verda

_ORDER = (Scaleway, OVHcloud, Hetzner, Verda, Exoscale, Nebius, Lyceum, Seeweb, AWS, Azure, RunPod)
ALL = {c.provider: c for c in _ORDER}
