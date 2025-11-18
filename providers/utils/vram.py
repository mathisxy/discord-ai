import asyncio
import logging
import time

import pynvml

def check_free_vram(required_gb:float=8):
    pynvml.nvmlInit()
    handle = pynvml.nvmlDeviceGetHandleByIndex(0)  # Nur GPU 0
    info = pynvml.nvmlDeviceGetMemoryInfo(handle)
    free_gb = info.free / 1024**3
    if free_gb < required_gb:
        logging.warning(f"NOT Enough VRAM: {free_gb:.2f} GB free, {required_gb} GB required")
        raise RuntimeError(f"Not enough VRAM: {free_gb:.2f} GB free, {required_gb} GB required")
    logging.info(f"Enough VRAM: {free_gb:.2f} GB free, {required_gb} GB required")

async def wait_for_vram(required_gb:float=8, timeout:float=20, interval:float=1):

    logging.info("Waiting for VRAM")

    start = time.time()

    while True:
        try:
            check_free_vram(required_gb=required_gb)
            break
        except RuntimeError as e:
            if (time.time() - start) >= timeout:
                logging.exception(f"Wait for vram timeout: {timeout}s, interval: {interval}")
                raise TimeoutError(f"Timeout: {e}")
            else:
                await asyncio.sleep(interval)