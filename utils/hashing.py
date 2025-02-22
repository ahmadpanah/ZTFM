import hashlib

def consistent_hash(key: str, cluster: list) -> str:
    hash_value = int(hashlib.sha256(key.encode()).hexdigest(), 16)
    return cluster[hash_value % len(cluster)]