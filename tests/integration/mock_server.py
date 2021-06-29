import signal
import subprocess as sp
import time
import logging
import shutil

import pytest
import requests
import psycopg2
import redis

_proxy_bypass = {
    "http": None,
    "https": None,
}


def start_service(service_name, host, port):
    moto_svr_path = shutil.which("moto_server")
    args = [moto_svr_path, service_name, "-H", host, "-p", str(port)]
    process = sp.Popen(args, stdin=sp.PIPE, stdout=sp.PIPE, stderr=sp.PIPE)
    url = f"http://{host}:{port}"

    for i in range(0, 30):
        output = process.poll()
        if output is not None:
            logging.info(f"moto_server exited status {output}")
            stdout, stderr = process.communicate()
            logging.info(f"moto_server stdout: {stdout}")
            logging.info(f"moto_server stderr: {stderr}")
            pytest.fail(f"Can not start service: {service_name}")

        try:
            # we need to bypass the proxies due to monkeypatches
            requests.get(url, timeout=5, proxies=_proxy_bypass)
            break
        except requests.exceptions.ConnectionError:
            time.sleep(0.5)
    else:
        stop_process(process)  # pytest.fail doesn't call stop_process
        pytest.fail(f"Can not start service: {service_name}")

    return process


def stop_process(process):
    try:
        process.send_signal(signal.SIGTERM)
        process.communicate(timeout=20)
    except sp.TimeoutExpired:
        process.kill()
        outs, errors = process.communicate(timeout=20)
        exit_code = process.returncode
        msg = f"Child process finished {exit_code} not in clean way: {outs} {errors}"
        raise RuntimeError(msg)


def wait_postgres_server(dsn):
    for i in range(0, 30):
        try:
            conn = psycopg2.connect(dsn)
            conn.close()
            return
        except Exception as e:
            logging.debug(f"PostgreSQL unavailable yet: {e}")
            time.sleep(1)
    else:
        pytest.fail("Couldn't reach PostgreSQL server")


def wait_redis_server(hostname, host_port):
    for i in range(0, 30):
        try:
            conn = redis.Redis(hostname, host_port)
            conn.close()
            return
        except Exception as e:
            logging.debug(f"Redis unavailable yet: {e}")
            time.sleep(1)
    else:
        pytest.fail("Couldn't reach Redis server")
