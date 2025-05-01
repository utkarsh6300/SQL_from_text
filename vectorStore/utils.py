import hashlib

def deterministic_uuid(data: str) -> str:
    """
    Generate a deterministic UUID based on input data using SHA-256.
    
    Args:
        data (str): Input string to generate UUID from
        
    Returns:
        str: A deterministic UUID-like string (first 32 chars of SHA-256 hex)
    """
    return hashlib.sha256(data.encode()).hexdigest()[:32]