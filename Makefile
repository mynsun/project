build:
	docker build -t streamlit-app .

run:
	docker run -it -d --name streamlit-container -p 8501:8501 \
		-v $(PWD):/app \
		streamlit-app

exec:
	docker exec -it streamlit-container /bin/bash

ps:
	docker ps -a

img:
	docker images

rm:
	docker rm -f $$(docker ps -aq)

rmi:
	docker rmi -f $$(docker images -q)
