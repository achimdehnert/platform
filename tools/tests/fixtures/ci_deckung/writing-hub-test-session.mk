# Fixture zu tools/tests/test_ci_deckung.py (platform#3845): Ziel `test-session`
# nachgebildet nach writing-hub/Makefile (Stand 2026-10-08). Container-Lebens-
# zyklus mit Shell-Schleife ueber \-Fortsetzungen und einem Make-Funktions-
# fragment `$(if ...)`. Zusaetzlich ein echtes Pruefziel `lint` als Gegenprobe.
TEST_PG_NAME := wh-test-pg
TEST_PG_PORT := 54329

test-session:
	@docker rm -f $(TEST_PG_NAME) >/dev/null 2>&1 || true
	@docker run -d --rm --name $(TEST_PG_NAME) \
		-e POSTGRES_USER=test_user -e POSTGRES_PASSWORD=test_pass -e POSTGRES_DB=test_db \
		-p $(TEST_PG_PORT):5432 postgres:16-alpine >/dev/null
	@for i in $$(seq 1 30); do \
		docker exec $(TEST_PG_NAME) pg_isready -U test_user >/dev/null 2>&1 && break; sleep 1; \
	done
	@set -e; trap 'docker stop $(TEST_PG_NAME) >/dev/null 2>&1 || true' EXIT; \
		$(TEST_ENV) \
		$(TEST_PYTEST) $(if $(K),-k "$(K)",) $(PYTEST_SEL)

lint:
	ruff check .
