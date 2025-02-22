import asyncio
import hashlib
import json
import time
from typing import Dict, List
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from ..core.models import Token

class TokenCache:
    """Implements Algorithm 2: Distributed Token Validation"""
    
    def __init__(self, num_shards: int, validation_key: rsa.RSAPublicKey):
        self.num_shards = num_shards
        self.shards: List[Dict[str, Token]] = [{} for _ in range(num_shards)]
        self.validation_key = validation_key
        self.miss_count = 0
        self.total_count = 0
        
    async def validate_token(self, token: Token) -> bool:
        
        self.total_count += 1
        
        # Get shard using consistent hashing
        shard_id = self._get_shard_id(token.id)
        shard = self.shards[shard_id]
        
        # Check cache
        if token.id in shard:
            cached_token = shard[token.id]
            
            # Check expiration
            if time.time() - cached_token.issued_at > cached_token.ttl:
                del shard[token.id]
            else:
                return True
                
        self.miss_count += 1
        valid = await self._validate_token_signature(token)
        
        if valid:
            shard[token.id] = token
            
        return valid
        
    def get_hit_rate(self) -> float:
        """Calculate cache hit rate (Equation 5)"""
        if self.total_count == 0:
            return 1.0
        return 1 - (self.miss_count / self.total_count)
        
    async def _validate_token_signature(self, token: Token) -> bool:
        
        try:
            # Create signature message
            message = json.dumps({
                "id": token.id,
                "claims": token.claims,
                "issued_at": token.issued_at
            }).encode()
            
            
            self.validation_key.verify(
                token.signature,
                message,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            return True
            
        except Exception:
            return False
            
    def _get_shard_id(self, token_id: str) -> int:
       
        hash_val = int(hashlib.sha256(token_id.encode()).hexdigest(), 16)
        return hash_val % self.num_shards