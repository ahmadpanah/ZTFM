import asyncio
from typing import Optional, Dict
from ..core.models import Function, Sidecar, SidecarState
from ..security.mtls import MTLSManager
from .deployment import DeploymentManager

class SidecarProvisioner:
    """Implements Algorithm 1: Dynamic Sidecar Provisioning"""
    
    def __init__(self, mtls_manager: MTLSManager, deployment_manager: DeploymentManager):
        self.sidecars: Dict[str, Sidecar] = {}
        self.functions: Dict[str, Function] = {}
        self.mtls_manager = mtls_manager
        self.deployment_manager = deployment_manager
        
    async def provision_sidecar(self, function: Function) -> Optional[Sidecar]:
        """Main sidecar provisioning workflow"""
        if self._has_sidecar(function.id):
            return None
            
        try:
            # Generate certificates
            cert, private_key = self.mtls_manager.generate_cert_pair()
            
            # Create sidecar
            sidecar = Sidecar(
                id=f"sidecar-{function.id}",
                state=SidecarState.IDLE,
                node=function.node,
                port=self._allocate_port(),
            )
            
            # Start provisioning
            sidecar.state = SidecarState.PROVISIONING
            
            # Deploy container
            success = await self.deployment_manager.deploy_sidecar(sidecar, function)
            if not success:
                return None
                
            # Configure networking
            if not await self.deployment_manager.setup_networking(sidecar, function):
                await self.deployment_manager.cleanup_deployment(sidecar)
                return None
                
            # Install certificates
            if not await self.deployment_manager.install_certificates(sidecar, cert, private_key):
                await self.deployment_manager.cleanup_deployment(sidecar)
                return None
                
            # Verify mTLS connection
            reader, writer = await self.mtls_manager.establish_connection(
                sidecar.node,
                sidecar.port,
                cert,
                private_key
            )
            
            # Test connection
            writer.write(b"VERIFY")
            await writer.drain()
            
            data = await reader.read(100)
            writer.close()
            await writer.wait_closed()
            
            if data != b"OK":
                await self.deployment_manager.cleanup_deployment(sidecar)
                return None
                
            # Mark sidecar as ready
            sidecar.state = SidecarState.READY
            sidecar.function_id = function.id
            sidecar.cert = cert
            sidecar.private_key = private_key
            
            self.sidecars[sidecar.id] = sidecar
            return sidecar
            
        except Exception as e:
            print(f"Sidecar provisioning failed: {e}")
            if sidecar:
                await self.deployment_manager.cleanup_deployment(sidecar)
            return None
            
    def _has_sidecar(self, function_id: str) -> bool:
        
        return any(s.function_id == function_id for s in self.sidecars.values())
        
    def _allocate_port(self) -> int:
        
        used_ports = {s.port for s in self.sidecars.values()}
        port = 8000
        while port in used_ports:
            port += 1
        return port