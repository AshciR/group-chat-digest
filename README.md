# Chat Nuff Bot
This is a Telegram bot that summarizes chats. It can give you the
gist of the last N messages within the chat.

## Requisites
- Docker
- Python 3.12+

## How to run
1. Create a `.env` file based on `.env.template`. 
2. Fill in the API keys as required. Use your own keys, or ask the maintainers.
3. (Optional) Configure encryption settings (see Security section below).

### A. Using uv
It's suggested to use the python build tool, [uv](https://docs.astral.sh/uv/).
Installation guides can be found on their site.

After uv is installed, you run the following:
1. Initialize the virtual environment and download the dependencies
`uv sync`
2. Run the application
`docker-compose up -d`
3. Stop the application
`docker-compose down`

### B. Spinning Docker up manually
You can run the application as a docker containers with the following.
```shell
docker-compose up -d --build 
```

This will build the images for you then run them in a detached mode.
If you do not need to build the images, you can use the following command.
```shell
docker-compose up -d
```

## Building only the app image
Use the following command to build the image
```shell
docker build . -t <tag-the-image>
```

### C. Running from PyCharm
1. Create a run config using `main.py`
2. Set an LOCAL env variable (optional)
3. Start the Redis database locally `docker-compose up -d redis`
4. Run `main.py`

## Testing
This project contains tests. We use Pytest for the testing framework.
Tests can be run 2 ways:

### A. Using uv
`uv run pytest -n auto tests --spec`

This runs tests with pytest in parallel mode.

### B. Using Pytest directly
`pytest -n auto tests --spec`

Runs Pytest in a parallel mode. Note: We create atom tests that facilitate this.
Meaning, our practice is not writing tests that share state, or depending on
the results from other tests.

## Security

### Message Encryption

The bot supports application-level encryption for message content stored in Redis:

- **Encryption Library**: Uses `cryptography` library with Fernet symmetric encryption
- **What's Encrypted**: Only message content (PII data) - metadata remains unencrypted for functionality
- **Backward Compatibility**: Handles both encrypted and unencrypted messages during migration

### Setup Encryption

1. **Generate an encryption key**:
   ```shell
   uv run python generate_encryption_key.py
   ```

2. **Configure environment variables** in your `.env` file:
   ```
   ENCRYPTION_ENABLED=True
   ENCRYPTION_KEY=<generated-key-from-step-1>
   ```

3. **Deploy safely**:
   - Configure the encryption key
   - Enable encryption with `ENCRYPTION_ENABLED=True`

## Notes
The application requires a Redis cache to store messages.
`docker-compose up -d` will spin up a cache for you. But if you
decide to use a different version, you'll have to get 
the images from Redis' official Docker hub.
