from encryption_utils import (
    generate_key,
    encrypt_message_content,
    decrypt_message_content,
    is_content_encrypted
)


def test_generate_key():
    # When: We generate an encryption key
    key = generate_key()
    
    # Then: It should be a valid base64 string
    assert isinstance(key, str)
    assert len(key) > 0
    # Fernet keys should be 44 characters when base64 encoded
    assert len(key) == 44


def test_encrypt_message_content_when_disabled(mocker):
    # Given: Encryption is disabled
    mocker.patch('encryption_utils.is_encryption_enabled', return_value=False)
    
    content = 'Test message content'
    
    # When: We try to encrypt content
    result = encrypt_message_content(content)
    
    # Then: The content should be unchanged
    assert result == content


def test_encrypt_message_content_when_enabled(mocker):
    # Given: Encryption is enabled with a valid key
    test_key = generate_key()
    mocker.patch('encryption_utils.is_encryption_enabled', return_value=True)
    mocker.patch('encryption_utils.get_encryption_key', return_value=test_key.encode())
    
    content = 'Test message content'
    
    # When: We encrypt content
    result = encrypt_message_content(content)
    
    # Then: The content should be encrypted
    assert result != content
    assert result.startswith('ENC:')
    assert result != 'Test message content'


def test_decrypt_message_content_unencrypted():
    # Given: Unencrypted content
    content = 'Test message content'
    
    # When: We try to decrypt it
    result = decrypt_message_content(content)
    
    # Then: The content should be unchanged
    assert result == content


def test_decrypt_message_content_encrypted(mocker):
    # Given: Encryption is enabled with a valid key
    test_key = generate_key()
    mocker.patch('encryption_utils.is_encryption_enabled', return_value=True)
    mocker.patch('encryption_utils.get_encryption_key', return_value=test_key.encode())
    
    original_content = 'Test message content'
    encrypted_content = encrypt_message_content(original_content)
    
    # When: We decrypt the encrypted content
    result = decrypt_message_content(encrypted_content)
    
    # Then: We should get back the original content
    assert result == original_content


def test_is_content_encrypted_unencrypted_content():
    # Given: Unencrypted content
    content = 'Test message content'
    
    # Then: Should be detected as unencrypted
    assert not is_content_encrypted(content)


def test_is_content_encrypted_encrypted_content():
    # Given: Encrypted content
    content = 'ENC:gAAAAABh5x2...'
    
    # Then: Should be detected as encrypted
    assert is_content_encrypted(content)