import io
import logging
import os
import time

import cv2
import numpy as np
from PIL import Image

log = logging.getLogger(__name__)


def _change_image_memory(path: str, file_size: int = 2**20) -> cv2.typing.MatLike:
    """
    Tries to match the image memory to a specific file size.

    :param path: (str) Path to the image
    :param file_size: (int) Size of the file in bytes
    :return: (np.ndarray) rescaled version of the image
    """
    image = cv2.imread(path)
    if image is None:
        raise ValueError(f'Error reading image: {path}')

    height, width = image.shape[:2]
    log.info('Got image for change_memory with size = %d x %d', width, height)

    original_memory = os.stat(path).st_size
    original_bytes_per_pixel = original_memory / np.prod(image.shape[:2])
    log.debug('Original image size = %d, bytes per pixel = %.2f', original_memory, original_bytes_per_pixel)

    new_bytes_per_pixel = original_bytes_per_pixel * (file_size / original_memory)
    new_bytes_ratio = np.sqrt(new_bytes_per_pixel / original_bytes_per_pixel)
    new_width, new_height = int(new_bytes_ratio * width), int(new_bytes_ratio * height)

    # handle max w/h
    if new_height > 2560:
        ratio = new_height / 2560
        new_height = int(new_height / ratio)
        new_width = int(new_width / ratio)
    if new_width > 2560:
        ratio = new_width / 2560
        new_height = int(new_height / ratio)
        new_width = int(new_width / ratio)

    log.debug('Resized to %d x %d', new_width, new_height)
    return cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_CUBIC)


def _get_size_of_image(image: cv2.typing.MatLike) -> int:
    # Encode into memory and get size
    buffer = io.BytesIO()
    image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))  # Fix BGR to RGB
    image.save(buffer, format='PNG')
    return buffer.getbuffer().nbytes


def _save_image(image: cv2.typing.MatLike, path: str) -> None:
    image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))  # Fix BGR to RGB
    with open(path, 'wb') as f:
        image.save(f, format='PNG')


def limit_image_memory(path: str, max_file_size: int, delta: float = 0.05, step_limit: int = 10) -> str:
    """
    Reduces an image to the required max file size.

    :param step_limit: Max steps count
    :param path: (str) Path to the original (unchanged) image.
    :param max_file_size: (int) maximum size of the image
    :param delta: (float) maximum allowed variation from the max file size.
        This is a value between 0 and 1, relatively to the max file size.
    :return: an image path to the limited image.
    """
    start_time = time.perf_counter()
    max_file_size *= 1 - delta
    max_deviation_percentage = delta
    new_image = None

    current_memory = new_memory = os.stat(path).st_size
    ratio = 1
    steps = 0
    prev_memory = new_memory  # Add tracking for memory change

    while abs(1 - max_file_size / new_memory) > max_deviation_percentage:
        new_image = _change_image_memory(path, file_size=int(max_file_size * ratio))
        new_memory = _get_size_of_image(new_image)
        log.info('Calculated new size of image after resize = %d', new_memory)
        ratio *= max_file_size / new_memory
        steps += 1

        if abs(new_memory - prev_memory) < 10:  # Prevent endless looping
            log.warning('Image resizing has reached its limit of precision.')
            break

        prev_memory = new_memory

        if steps > step_limit:
            break

    log.info(
        'Resized image from %.2f MB to %.2f MB in %i steps. Time taken: %5.3f seconds',
        current_memory / 2**20,
        new_memory / 2**20,
        steps,
        time.perf_counter() - start_time,
    )

    if new_image is not None:
        _save_image(new_image, path)
    return path
