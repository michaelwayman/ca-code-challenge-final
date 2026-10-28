R16.1 | pass | libs/pyproject.toml exists with [project] name = "cauth", version = "0.1.0" (libs/pyproject.toml:6-7)
R16.2 | fail | not executed: `python -m venv`, `pip`, `python -m build` and `docker run` all denied by permission mode this session; wheel build + clean-venv install unverified
R16.3 | fail | no service Dockerfiles or requirements files exist in the repo (git ls-files has no Dockerfile/requirements*.txt; docker-compose.yml and Makefile do not reference cauth/libs); see NEEDS
R16.4 | pass | libs/src/cauth/ids.py:6-9 deterministic_uuid(audience, source_id) = uuid5(uuid5(URL_NS, audience), str(source_id)); exported via `from cauth import deterministic_uuid` (used in libs/tests/test_ids.py:3)
R16.5 | fail | test present (libs/tests/test_ids.py:6-12 pins wp_user/1 and wp_user/2 to fixed UUIDs, asserts wp_user/1 != other/1) but not executed: pytest/docker denied by permission mode this session
