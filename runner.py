"""
runner.py — Arranca checker.py y main.py con delay.
Reinicia cualquiera de los dos si se cae.
"""

import subprocess
import time
import logging
import sys
import os

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [RUNNER] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

DELAY_BETWEEN_STARTS = 20   # segundos entre checker y main
HEALTH_CHECK_INTERVAL = 30  # cada cuántos segundos verificar que sigan vivos


def start(script):
    logging.info(f"Arrancando {script}...")
    proc = subprocess.Popen(
        [sys.executable, "-u", script],
        stdout=sys.stdout,
        stderr=sys.stderr,
        env=os.environ.copy()
    )
    logging.info(f"{script} corriendo (PID {proc.pid})")
    return proc


if __name__ == "__main__":
    logging.info("=" * 60)
    logging.info("Reddit-Airtable Bot iniciando...")

    # 1. Checker primero
    checker = start("checker.py")

    logging.info(f"Esperando {DELAY_BETWEEN_STARTS}s antes de arrancar scraper...")
    time.sleep(DELAY_BETWEEN_STARTS)

    # 2. Scraper principal
    scraper = start("main.py")

    # 3. Loop de salud
    while True:
        time.sleep(HEALTH_CHECK_INTERVAL)

        if checker.poll() is not None:
            logging.warning("⚠️  checker.py terminó. Reiniciando...")
            checker = start("checker.py")

        if scraper.poll() is not None:
            logging.warning("⚠️  main.py terminó. Reiniciando...")
            scraper = start("main.py")
