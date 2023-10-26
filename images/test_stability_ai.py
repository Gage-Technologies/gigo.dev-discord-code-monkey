import base64

import yaml

from images.stablility_ai import get_image_for_prompt

with open("../config.yml") as f:
    cfg = yaml.load(f, Loader=yaml.FullLoader)


def test_get_image_for_prompt():
    img = get_image_for_prompt("build a chat with openai in golang", cfg["stability_key"])
    assert img is not None

    with open("/tmp/test-stable-ai.png", "w+b") as f:
        f.write(base64.b64decode(img))
