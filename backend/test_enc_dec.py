from encryption_utils import encrypt_file, decrypt_file
import os

filename = "sample-mp4-file-small.mp4"
enc_path = f"uploads/{filename}.enc"
dec_path = f"uploads/decrypted_{filename}"

# Encrypt
encrypt_file(f"uploads/{filename}", enc_path)

# Decrypt
decrypt_file(enc_path, dec_path)

print("✅ Encryption-Decryption test completed successfully!")
print("Check the decrypted file in uploads folder.")
