"""One collector per provider. Add new ones to ALL."""

from .aws import AWS
from .azure import Azure
from .exoscale import Exoscale
from .hetzner import Hetzner
from .ovhcloud import OVHcloud
from .runpod import RunPod
from .scaleway import Scaleway
from .verda import Verda

ALL = {c.provider: c for c in (Scaleway, OVHcloud, Hetzner, Verda, Exoscale, AWS, Azure, RunPod)}
