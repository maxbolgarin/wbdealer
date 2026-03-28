send-envs:
	scp .env deploy@ci.scanorbit.cloud:/home/deploy/wbdealer

deploy:
	gitb pull
	docker compose up -d --build