.PHONY: build run stop logs clean push

DOCKER_IMAGE_FULL_NAME = mynsunxx/streamlitapp:latest

build:
	docker-compose build

run:
	docker-compose up -d

stop:
	docker-compose down

logs:
	docker-compose logs -f

clean:
	docker system prune -a -f

push: build
	docker push $(DOCKER_IMAGE_FULL_NAME)
