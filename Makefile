# Makefile
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

push:
	docker tag streamlit_app mynsunxx/streamlitapp:latest
	docker push mynsunxx/streamlitapp:latest
