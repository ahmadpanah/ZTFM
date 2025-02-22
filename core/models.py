from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict
from datetime import datetime
from cryptography.x509 import Certificate
from cryptography.hazmat.primitives.asymmetric import rsa

class SidecarState(Enum):
    IDLE = "IDLE"
    PROVISIONING = "PROVISIONING"
    READY = "READY"

@dataclass
class Function:
    """Represents a serverless function instance"""
    id: str
    node: str
    port: int
    namespace: str
    resource_limits: Dict[str, str]
    env_vars: Dict[str, str]
    
@dataclass
class Sidecar:
    """Represents a security sidecar instance"""
    id: str
    state: SidecarState
    node: str
    port: int
    cert: Optional[Certificate] = None
    private_key: Optional[rsa.RSAPrivateKey] = None
    function_id: Optional[str] = None

@dataclass
class Token:
    """Represents an authentication token"""
    id: str
    ttl: int
    claims: Dict[str, any]
    signature: bytes
    issued_at: float

@dataclass
class Policy:
    """Represents a security policy"""
    id: str
    version: int
    constraint: str
    signature: bytes