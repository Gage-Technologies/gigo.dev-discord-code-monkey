
docker:
	docker build --tag=gigodev/code-monkey .

docker-push:
	docker push gigodev/code-monkey
