"""
Six-layer encryption system with AEAD and Encrypt-then-MAC modes.
"""

import logging
import json
import base64
import struct
from typing import Dict, List, Tuple, Optional
from io import BytesIO

from cryptography.hazmat.primitives.ciphers.aead import AESGCM, ChaCha20Poly1305
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import hashes, hmac
from cryptography.hazmat.backends import default_backend
from argon2.low_level import hash_secret_raw, Type

from .utils import secure_random_bytes

logger = logging.getLogger(__name__)


ARGON2_TIME_COST = 3
ARGON2_MEMORY_COST = 65536
ARGON2_PARALLELISM = 4
ARGON2_HASH_LEN = 32
ARGON2_SALT_LEN = 16


class EncryptionLayer:
    """Base class for encryption layers."""
    
    def __init__(self, key: bytes):
        self.key = key
        
    def encrypt(self, data: bytes) -> Tuple[bytes, Dict]:
        raise NotImplementedError
        
    def decrypt(self, data: bytes, metadata: Dict) -> bytes:
        raise NotImplementedError


class AESGCMLayer(EncryptionLayer):
    """AES-256-GCM AEAD encryption layer."""
    
    def encrypt(self, data: bytes) -> Tuple[bytes, Dict]:
        nonce = secure_random_bytes(12)
        aesgcm = AESGCM(self.key)
        ciphertext = aesgcm.encrypt(nonce, data, None)
        
        metadata = {
            'algorithm': 'AES-256-GCM',
            'nonce': base64.b64encode(nonce).decode('ascii')
        }
        
        return ciphertext, metadata
    
    def decrypt(self, data: bytes, metadata: Dict) -> bytes:
        nonce = base64.b64decode(metadata['nonce'])
        aesgcm = AESGCM(self.key)
        return aesgcm.decrypt(nonce, data, None)


class ChaCha20Poly1305Layer(EncryptionLayer):
    """ChaCha20-Poly1305 AEAD encryption layer."""
    
    def encrypt(self, data: bytes) -> Tuple[bytes, Dict]:
        nonce = secure_random_bytes(12)
        chacha = ChaCha20Poly1305(self.key)
        ciphertext = chacha.encrypt(nonce, data, None)
        
        metadata = {
            'algorithm': 'ChaCha20-Poly1305',
            'nonce': base64.b64encode(nonce).decode('ascii')
        }
        
        return ciphertext, metadata
    
    def decrypt(self, data: bytes, metadata: Dict) -> bytes:
        nonce = base64.b64decode(metadata['nonce'])
        chacha = ChaCha20Poly1305(self.key)
        return chacha.decrypt(nonce, data, None)


class AESCBCHMACLayer(EncryptionLayer):
    """AES-256-CBC with HMAC-SHA256 (Encrypt-then-MAC) layer."""
    
    def encrypt(self, data: bytes) -> Tuple[bytes, Dict]:
        iv = secure_random_bytes(16)
        
        cipher = Cipher(algorithms.AES(self.key[:32]), modes.CBC(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        
        padding_length = 16 - (len(data) % 16)
        padded_data = data + bytes([padding_length]) * padding_length
        
        ciphertext = encryptor.update(padded_data) + encryptor.finalize()
        
        h = hmac.HMAC(self.key[32:], hashes.SHA256(), backend=default_backend())
        h.update(iv + ciphertext)
        tag = h.finalize()
        
        metadata = {
            'algorithm': 'AES-256-CBC-HMAC-SHA256',
            'iv': base64.b64encode(iv).decode('ascii'),
            'tag': base64.b64encode(tag).decode('ascii')
        }
        
        return ciphertext, metadata
    
    def decrypt(self, data: bytes, metadata: Dict) -> bytes:
        iv = base64.b64decode(metadata['iv'])
        expected_tag = base64.b64decode(metadata['tag'])
        
        h = hmac.HMAC(self.key[32:], hashes.SHA256(), backend=default_backend())
        h.update(iv + data)
        h.verify(expected_tag)
        
        cipher = Cipher(algorithms.AES(self.key[:32]), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        
        padded_data = decryptor.update(data) + decryptor.finalize()
        
        padding_length = padded_data[-1]
        return padded_data[:-padding_length]


class AESCTRHMACLayer(EncryptionLayer):
    """AES-256-CTR with HMAC-SHA256 (Encrypt-then-MAC) layer."""
    
    def encrypt(self, data: bytes) -> Tuple[bytes, Dict]:
        nonce = secure_random_bytes(16)
        
        cipher = Cipher(algorithms.AES(self.key[:32]), modes.CTR(nonce), backend=default_backend())
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(data) + encryptor.finalize()
        
        h = hmac.HMAC(self.key[32:], hashes.SHA256(), backend=default_backend())
        h.update(nonce + ciphertext)
        tag = h.finalize()
        
        metadata = {
            'algorithm': 'AES-256-CTR-HMAC-SHA256',
            'nonce': base64.b64encode(nonce).decode('ascii'),
            'tag': base64.b64encode(tag).decode('ascii')
        }
        
        return ciphertext, metadata
    
    def decrypt(self, data: bytes, metadata: Dict) -> bytes:
        nonce = base64.b64decode(metadata['nonce'])
        expected_tag = base64.b64decode(metadata['tag'])
        
        h = hmac.HMAC(self.key[32:], hashes.SHA256(), backend=default_backend())
        h.update(nonce + data)
        h.verify(expected_tag)
        
        cipher = Cipher(algorithms.AES(self.key[:32]), modes.CTR(nonce), backend=default_backend())
        decryptor = cipher.decryptor()
        plaintext = decryptor.update(data) + decryptor.finalize()
        
        return plaintext


def derive_keys_from_passphrase(passphrase: str, salt: bytes, num_keys: int = 6, key_size: int = 64) -> List[bytes]:
    """
    Derive multiple encryption keys from a passphrase using Argon2id.
    
    Args:
        passphrase: User passphrase
        salt: Salt for key derivation
        num_keys: Number of keys to derive
        key_size: Size of each key in bytes
        
    Returns:
        List of derived keys
    """
    master_key = hash_secret_raw(
        secret=passphrase.encode('utf-8'),
        salt=salt,
        time_cost=ARGON2_TIME_COST,
        memory_cost=ARGON2_MEMORY_COST,
        parallelism=ARGON2_PARALLELISM,
        hash_len=key_size * num_keys,
        type=Type.ID
    )
    
    keys = [master_key[i*key_size:(i+1)*key_size] for i in range(num_keys)]
    return keys


def create_encryption_layers(keys: List[bytes]) -> List[EncryptionLayer]:
    """
    Create six encryption layers with the provided keys.
    
    Args:
        keys: List of 6 keys (each 64 bytes)
        
    Returns:
        List of encryption layer objects
    """
    if len(keys) != 6:
        raise ValueError("Expected 6 keys for 6 encryption layers")
    
    return [
        AESGCMLayer(keys[0][:32]),
        ChaCha20Poly1305Layer(keys[1][:32]),
        AESCBCHMACLayer(keys[2]),
        AESCTRHMACLayer(keys[3]),
        ChaCha20Poly1305Layer(keys[4][:32]),
        AESGCMLayer(keys[5][:32])
    ]


def encrypt_multilayer(data: bytes, passphrase: str) -> Tuple[bytes, Dict]:
    """
    Encrypt data through six layers of encryption.
    
    Args:
        data: Data to encrypt
        passphrase: User passphrase
        
    Returns:
        Tuple of (encrypted_data, key_metadata)
    """
    logger.info("Starting six-layer encryption")
    
    kdf_salt = secure_random_bytes(ARGON2_SALT_LEN)
    keys = derive_keys_from_passphrase(passphrase, kdf_salt, num_keys=6, key_size=64)
    
    layers = create_encryption_layers(keys)
    
    encrypted_data = data
    layer_metadata = []
    
    for i, layer in enumerate(layers):
        encrypted_data, metadata = layer.encrypt(encrypted_data)
        layer_metadata.append(metadata)
        logger.debug(f"Layer {i+1}/{len(layers)}: {metadata['algorithm']} - encrypted {len(encrypted_data)} bytes")
    
    key_metadata = {
        'version': '1.0',
        'kdf': {
            'algorithm': 'Argon2id',
            'salt': base64.b64encode(kdf_salt).decode('ascii'),
            'time_cost': ARGON2_TIME_COST,
            'memory_cost': ARGON2_MEMORY_COST,
            'parallelism': ARGON2_PARALLELISM
        },
        'layers': layer_metadata
    }
    
    logger.info(f"Six-layer encryption complete: {len(data)} -> {len(encrypted_data)} bytes")
    
    return encrypted_data, key_metadata


def decrypt_multilayer(data: bytes, key_metadata: Dict, passphrase: str) -> bytes:
    """
    Decrypt data by removing six layers of encryption in reverse order.
    
    Args:
        data: Encrypted data
        key_metadata: Metadata from keys.json
        passphrase: User passphrase
        
    Returns:
        Decrypted data
        
    Raises:
        Exception: If any AEAD tag or HMAC verification fails
    """
    logger.info("Starting six-layer decryption")
    
    kdf_salt = base64.b64decode(key_metadata['kdf']['salt'])
    keys = derive_keys_from_passphrase(passphrase, kdf_salt, num_keys=6, key_size=64)
    
    layers = create_encryption_layers(keys)
    
    decrypted_data = data
    layer_metadata = key_metadata['layers']
    
    for i in range(len(layers) - 1, -1, -1):
        metadata = layer_metadata[i]
        decrypted_data = layers[i].decrypt(decrypted_data, metadata)
        logger.debug(f"Layer {len(layers)-i}/{len(layers)}: {metadata['algorithm']} - decrypted {len(decrypted_data)} bytes")
    
    logger.info(f"Six-layer decryption complete: {len(data)} -> {len(decrypted_data)} bytes")
    
    return decrypted_data
