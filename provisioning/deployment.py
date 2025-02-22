import asyncio
from ztfm.core.models import FunctionInstance
from ztfm.provisioning.sidecar import SidecarManager

class DeploymentManager:
    def __init__(self, sidecar_manager: SidecarManager):
        self.sidecar_manager = sidecar_manager

    async def deploy_function(self, function_instance: FunctionInstance, node: str):
        if not self._has_sidecar(function_instance.id):
            await self.sidecar_manager.provision_sidecar(function_instance.id, node)
        print(f"Deployed function {function_instance.id} on node {node}")

    def _has_sidecar(self, function_instance_id: str) -> bool:
        return f"sidecar_{function_instance_id}" in self.sidecar_manager.sidecars