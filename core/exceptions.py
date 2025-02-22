class ZTFMError(Exception):
    pass

class TokenValidationError(ZTFMError):
    pass

class PolicyPropagationError(ZTFMError):
    pass

class SidecarProvisioningError(ZTFMError):
    pass

class CacheConsistencyError(ZTFMError):
    pass