.PHONY: run test test-ui install
run:      ## start the dashboard in the foreground
	python3 server.py
test:     ## backend tests (no extra dependencies)
	python3 -m unittest -v test_server test_agents
test-ui:  ## browser tests (needs: pip install playwright, and Chrome)
	python3 -m unittest -v test_ui
install:  ## install systemd user service
	./install.sh
