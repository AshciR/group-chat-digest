# Chat Nuff Bot
This is a Telegram bot that summarizes chats. It can give you the
gist of the last N messages within the chat.

## Building the image
Use the following command to build the image
```shell
docker build . -t <tag-the-image>
```

## How to run
You can run the application as a docker containers with the following.
```shell
docker run 
-e TELEGRAM_API_KEY=<key> \ 
-e OPENAI_API_KEY=sk-<key> \ 
-p 80:80 \ 
<docker-image>
```

##  Redis image
`docker run -p 6379:6379 --name some-redis-1 -d redis:7.2.4-alpine`