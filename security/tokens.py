import hashlib
import asyncio
import aiohttp
from typing import Optional
from ztfm.cache.token_cache import TokenCache
from ztfm.utils.hashing import consistent_hash

class Token:
    """
    Represents a security token with an ID and Time-To-Live (TTL).
    """
    def __init__(self, token_id: str, ttl: int):
        self.id = token_id
        self.ttl = ttl  # Time-to-live in seconds

    def is_valid(self) -> bool:

        return True


class TokenValidator:
    def __init__(self, cache: TokenCache, fip_url: str):
        self.cache = cache
        self.fip_url = fip_url  # Federated Identity Provider (FIP) URL for remote validation

    async def validate_token(self, token: Token) -> bool:

        # Step 1: Compute the hash of the token ID
        key = self._hash_token_id(token.id)
        
        # Step 2: Find the appropriate node in the sharded Redis cluster
        node = self._find_virtual_node(key)
        
        # Step 3: Check if the token exists in the cache
        if await node.contains(token):
            return True  # Token is valid and found in the cache
        
        # Step 4: If not found, perform a remote validation
        if await self._validate_with_fip(token):
            # Add the token to the cache with its TTL
            await node.add(token, token.ttl)
            return True
        
        return False 

    def _hash_token_id(self, token_id: str) -> str:

        return hashlib.sha256(token_id.encode()).hexdigest()

    def _find_virtual_node(self, key: str):

        return consistent_hash(key, self.cache.get_cluster())

    async def _validate_with_fip(self, token: Token) -> bool:

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(self.fip_url, json={"token_id": token.id}) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("valid", False)
                    else:
                        print(f"Remote validation failed with status code {response.status}")
                        return False
            except Exception as e:
                print(f"Error during remote validation: {e}")
                return False


# Example usage:
if __name__ == "__main__":
    from ztfm.cache.token_cache import TokenCache

    cache = TokenCache()

    fip_url = "https://fip.localhost/validate"
    validator = TokenValidator(cache, fip_url)

    sample_token = Token(token_id="example_token_123", ttl=3600)


    loop = asyncio.get_event_loop()
    is_valid = loop.run_until_complete(validator.validate_token(sample_token))
    print(f"Token validation result: {is_valid}")