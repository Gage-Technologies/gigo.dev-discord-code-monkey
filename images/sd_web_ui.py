import base64
import os
import random
import sys
import warnings
from io import BytesIO

import webuiapi

from typing import Optional

from PIL.Image import Image

API: Optional[webuiapi.WebUIApi] = None


def get_image_for_prompt(prompt: str, seed: Optional[int]) -> Optional[str]:
    global API
    if API is None:
        API = webuiapi.WebUIApi(
            host=os.environ.get("SD_LOCAL_API_URL"),
            key=os.environ.get("SD_KEY"),
            port=7860,
            steps=50,
        )

    if seed is None:
        seed = random.randint(0, 100000)

    result = API.txt2img(
        prompt=prompt,
        negative_prompt="ugly, out of frame",
        seed=seed,
        cfg_scale=7,
        width=768,
        height=768,
    )

    # Set up our warning to print to the console if the adult content classifier is tripped.
    # If adult content classifier is not tripped, save generated images.
    for resp in result.images:
        r: Image = resp
        buf = BytesIO()
        r.save(buf, format='jpeg')
        return base64.b64encode(buf.getbuffer()).decode()
