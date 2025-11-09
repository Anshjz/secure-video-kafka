from cryptography.fernet import Fernet
import os

def load_key(file_path="secret.key"):
    """Load or generate a global Fernet key (optional)."""
    if not os.path.exists(file_path):
        key = Fernet.generate_key()
        with open(file_path, "wb") as f:
            f.write(key)
    else:
        with open(file_path, "rb") as f:
            key = f.read()
    return key

# Optional global fernet (not used per-video)
fernet_global = Fernet(load_key())

def encrypt_file(input_file: str, output_file: str, fernet, chunk_size=1024*1024):
    """Encrypt file in chunks using the provided Fernet instance."""
    with open(input_file, "rb") as fin, open(output_file, "wb") as fout:
        while True:
            chunk = fin.read(chunk_size)
            if not chunk:
                break
            encrypted_chunk = fernet.encrypt(chunk)
            fout.write(len(encrypted_chunk).to_bytes(4, "big"))
            fout.write(encrypted_chunk)
    return output_file

def decrypt_file(input_file: str, output_file: str, fernet):
    """Decrypt file in chunks using the provided Fernet instance."""
    with open(input_file, "rb") as fin, open(output_file, "wb") as fout:
        while True:
            size_bytes = fin.read(4)
            if not size_bytes:
                break
            chunk_size = int.from_bytes(size_bytes, "big")
            encrypted_chunk = fin.read(chunk_size)
            decrypted_chunk = fernet.decrypt(encrypted_chunk)
            fout.write(decrypted_chunk)
    return output_file
