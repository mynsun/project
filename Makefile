.PHONY: build run stop logs clean push

STREAMLIT_IMAGE_FULL_NAME = mynsunxx/streamlitapp:latest
FASTAPI_IMAGE_FULL_NAME = mynsunxx/fastapi-backend:latest

build:
	docker-compose build

run:
	docker-compose up -d

stop:
	docker-compose down

logs:
	docker-compose logs -f

clean:
	docker-compose down --rmi all --volumes
	docker system prune -a -f || true # 사용하지 않는 Docker 데이터도 강제로 정리

push: build
	docker push $(STREAMLIT_IMAGE_FULL_NAME)
	docker push $(FASTAPI_IMAGE_FULL_NAME)
