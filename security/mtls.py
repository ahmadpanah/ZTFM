import ssl
import asyncio
from typing import Optional
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend
from cryptography import x509
from cryptography.x509.oid import NameOID
import datetime

class MTLSManager:
    def __init__(self, ca_cert_path: str, ca_key_path: str):
        self.ca_cert_path = ca_cert_path
        self.ca_key_path = ca_key_path
        self.ca_cert, self.ca_key = self._load_ca_credentials()

    def _load_ca_credentials(self):
        with open(self.ca_cert_path, "rb") as cert_file:
            ca_cert = x509.load_pem_x509_certificate(cert_file.read(), default_backend())
        
        with open(self.ca_key_path, "rb") as key_file:
            ca_key = serialization.load_pem_private_key(
                key_file.read(),
                password=None,
                backend=default_backend()
            )
        
        return ca_cert, ca_key

    def generate_sidecar_credentials(self, sidecar_id: str):
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )

        csr = x509.CertificateSigningRequestBuilder().subject_name(
            x509.Name([
                x509.NameAttribute(NameOID.COMMON_NAME, sidecar_id),
            ])
        ).sign(private_key, hashes.SHA256(), default_backend())

        cert = x509.CertificateBuilder().subject_name(
            csr.subject
        ).issuer_name(
            self.ca_cert.subject
        ).public_key(
            csr.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.datetime.utcnow()
        ).not_valid_after(
            datetime.datetime.utcnow() + datetime.timedelta(days=365)
        ).add_extension(
            x509.BasicConstraints(ca=False, path_length=None), critical=True,
        ).sign(self.ca_key, hashes.SHA256(), default_backend())

        private_key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        )

        cert_pem = cert.public_bytes(serialization.Encoding.PEM)

        return private_key_pem, cert_pem

    async def perform_tls_handshake(self, sidecar_id: str, server_hostname: str):
        private_key_pem, cert_pem = self.generate_sidecar_credentials(sidecar_id)

        ssl_context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        ssl_context.load_verify_locations(cafile=self.ca_cert_path)
        ssl_context.load_cert_chain(
            certfile=cert_pem.decode(),
            keyfile=private_key_pem.decode()
        )
        ssl_context.check_hostname = True
        ssl_context.verify_mode = ssl.CERT_REQUIRED

        try:
            reader, writer = await asyncio.open_connection(
                server_hostname, 443, ssl=ssl_context
            )
            print(f"mTLS handshake successful for sidecar {sidecar_id}")
            writer.close()
            await writer.wait_closed()
            return True
        except Exception as e:
            print(f"mTLS handshake failed for sidecar {sidecar_id}: {e}")
            return False

if __name__ == "__main__":
    ca_cert_path = "path/to/ca_cert.pem"
    ca_key_path = "path/to/ca_key.pem"
    mtls_manager = MTLSManager(ca_cert_path, ca_key_path)

    sidecar_id = "sidecar_123"
    server_hostname = "example.com"

    loop = asyncio.get_event_loop()
    handshake_successful = loop.run_until_complete(
        mtls_manager.perform_tls_handshake(sidecar_id, server_hostname)
    )
    print(f"Handshake result: {handshake_successful}")
