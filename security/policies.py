import asyncio
import json
import redis
from typing import Dict, List
from ztfm.utils.hlc import HybridLogicalClock

class Policy:
    def __init__(self, policy_id: str, constraint: str, version: int):
        self.id = policy_id
        self.constraint = constraint
        self.version = version

    def to_json(self):
        return json.dumps({"id": self.id, "constraint": self.constraint, "version": self.version})

    @staticmethod
    def from_json(data: str):
        obj = json.loads(data)
        return Policy(obj["id"], obj["constraint"], obj["version"])

class PolicyManager:
    def __init__(self, redis_host: str, redis_port: int, pubsub_channel: str):
        self.redis_client = redis.StrictRedis(host=redis_host, port=redis_port, decode_responses=True)
        self.pubsub = self.redis_client.pubsub()
        self.pubsub.subscribe(pubsub_channel)
        self.policies: Dict[str, Policy] = {}
        self.hlc = HybridLogicalClock()
        self.pubsub_channel = pubsub_channel

    async def update_policy(self, policy_id: str, constraint: str):
        new_version = self.hlc.now()
        new_policy = Policy(policy_id, constraint, new_version)
        self.redis_client.set(f"policy:{policy_id}", new_policy.to_json())
        await self._broadcast_policy(new_policy)

    async def _broadcast_policy(self, policy: Policy):
        self.redis_client.publish(self.pubsub_channel, policy.to_json())

    async def process_policy_updates(self):
        while True:
            message = self.pubsub.get_message(ignore_subscribe_messages=True)
            if message and message["type"] == "message":
                policy = Policy.from_json(message["data"])
                self._apply_policy_locally(policy)

    def _apply_policy_locally(self, policy: Policy):
        if policy.id not in self.policies or policy.version > self.policies[policy.id].version:
            self.policies[policy.id] = policy

    def verify_consistency(self, policy: Policy):
        current_policy = self.policies.get(policy.id)
        if current_policy and current_policy.version >= policy.version:
            return True
        return False

    def get_current_policies(self) -> List[Policy]:
        return sorted(self.policies.values(), key=lambda p: p.version)

if __name__ == "__main__":
    manager = PolicyManager(redis_host="localhost", redis_port=6379, pubsub_channel="policy_updates")
    asyncio.create_task(manager.process_policy_updates())

    loop = asyncio.get_event_loop()
    loop.run_until_complete(
        asyncio.gather(
            manager.update_policy("policy_1", "allow_read"),
            manager.update_policy("policy_2", "deny_write"),
            manager.update_policy("policy_1", "allow_write")
        )
    )

    current_policies = manager.get_current_policies()
    for policy in current_policies:
        print(f"Policy ID: {policy.id}, Constraint: {policy.constraint}, Version: {policy.version}")