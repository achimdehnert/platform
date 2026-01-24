from __future__ import annotations

import asyncio
import time
from typing import Any

from ..clients.env_client import EnvClient
from ..clients.ssh_client import SSHClient
from ..settings import settings


async def bfagent_deploy_web(
    image_tag: str,
    host: str | None = None,
    project_dir: str = "/opt/bfagent-app",
    compose_file: str = "docker-compose.prod.yml",
    env_file: str = ".env.prod",
    service: str = "bfagent-web",
    image_repo: str = "ghcr.io/achimdehnert/bfagent/bfagent-web",
    verify_url: str = "https://bfagent.iil.pet/login/",
    expect_http_status: int = 200,
    pull: bool = True,
    recreate: bool = True,
) -> dict[str, Any]:
    ssh = SSHClient(host=host or settings.ssh_host)
    env = EnvClient(ssh)

    compose_file_path = f"{project_dir}/{compose_file}"
    env_file_path = f"{project_dir}/{env_file}"

    try:
        await ssh.connect()

        await env.set_env_var(env_file_path, "BFAgent_IMAGE_TAG", image_tag)

        image_ref = f"{image_repo}:{image_tag}"
        pull_output = ""
        if pull:
            pull_output = await ssh.run_checked(f"docker pull {image_ref}")

        compose_pull_output = ""
        if pull:
            stdout, stderr, exit_code = await ssh.run(
                f"docker compose -f {compose_file_path} --env-file {env_file_path} pull {service}",
                timeout=600,
            )
            compose_pull_output = stdout or stderr
            if exit_code != 0:
                return {
                    "success": False,
                    "error": "compose pull failed",
                    "exit_code": exit_code,
                    "output": compose_pull_output,
                    "image": image_ref,
                    "env_file": env_file_path,
                }

        up_cmd = (
            f"docker compose -f {compose_file_path} --env-file {env_file_path} up -d"
            f" --no-deps{' --force-recreate' if recreate else ''} {service}"
        )
        up_stdout, up_stderr, up_exit = await ssh.run(up_cmd, timeout=600)
        up_output = up_stdout or up_stderr
        if up_exit != 0:
            return {
                "success": False,
                "error": "compose up failed",
                "exit_code": up_exit,
                "output": up_output,
                "image": image_ref,
                "env_file": env_file_path,
            }

        # Healthcheck can legitimately return 502/503 during container warmup.
        # Retry a bit to avoid false negatives.
        http_code = -1
        code_exit = -1
        attempts = 0
        t0 = time.monotonic()
        for attempt in range(1, 31):  # ~60s total (30 * 2s)
            attempts = attempt
            code_out, code_err, code_exit = await ssh.run(
                f"curl -s -o /dev/null -w '%{{http_code}}' {verify_url}",
                timeout=60,
            )
            http_code_str = (code_out or "").strip()
            http_code = int(http_code_str) if http_code_str.isdigit() else -1
            if code_exit == 0 and http_code == expect_http_status:
                break
            await asyncio.sleep(2)

        elapsed_s = round(time.monotonic() - t0, 2)

        ok = code_exit == 0 and http_code == expect_http_status

        result: dict[str, Any] = {
            "success": ok,
            "tool_version": "bfagent_deploy_web@2025-12-15a",
            "image": image_ref,
            "env_file": env_file_path,
            "compose_file": compose_file_path,
            "service": service,
            "pull_output": pull_output,
            "compose_pull_output": compose_pull_output,
            "up_output": up_output,
            "verify_url": verify_url,
            "http_status": http_code,
            "expected_http_status": expect_http_status,
            "healthcheck_attempts": attempts,
            "healthcheck_elapsed_s": elapsed_s,
        }

        if not ok:
            ps_stdout, ps_stderr, ps_exit = await ssh.run(
                f"docker compose -f {compose_file_path} --env-file {env_file_path} ps",
                timeout=60,
            )
            result["compose_ps"] = ps_stdout or ps_stderr
            result["compose_ps_exit"] = ps_exit

            caddy_logs_cmd = f"docker compose -f {compose_file_path} --env-file {env_file_path} logs --tail 200 caddy"
            caddy_out, caddy_err, caddy_exit = await ssh.run(caddy_logs_cmd, timeout=120)
            result["caddy_logs_cmd"] = caddy_logs_cmd
            result["caddy_logs_exit"] = caddy_exit
            result["caddy_logs_tail"] = caddy_out or caddy_err

            logs_cmd = f"docker compose -f {compose_file_path} --env-file {env_file_path} logs --tail 200 {service}"
            logs_stdout, logs_stderr, logs_exit = await ssh.run(logs_cmd, timeout=120)
            result["logs_cmd"] = logs_cmd
            result["logs_exit"] = logs_exit
            result["logs_tail"] = logs_stdout or logs_stderr

            cid_cmd = f"docker compose -f {compose_file_path} --env-file {env_file_path} ps -q {service}"
            cid_out, cid_err, cid_exit = await ssh.run(cid_cmd, timeout=30)
            cid = (cid_out or "").strip()
            result["container_id"] = cid
            result["container_id_exit"] = cid_exit
            if cid_exit == 0 and cid:
                inspect_cmd = f"docker inspect --format='{{{{json .State}}}}' {cid}"
                ins_out, ins_err, ins_exit = await ssh.run(inspect_cmd, timeout=30)
                result["inspect_cmd"] = inspect_cmd
                result["inspect_exit"] = ins_exit
                result["inspect_state"] = (ins_out or ins_err).strip()

        return result
    finally:
        await ssh.disconnect()
