import base64
import dotenv

import yaml

from images.replicate_playground_v2 import PlaygroundV2Params, PlaygroundV2Sampler, get_image_for_prompt

dotenv.load_dotenv("./.env")


def test_pg_connection():
    img = get_image_for_prompt(PlaygroundV2Params(
        prompt="gorilla riding a skateboard",
        sampler=PlaygroundV2Sampler.DDIM,
        cfg_scale=10
    ), 42069)
    assert img is not None

    with open("/tmp/test-stable-ai.png", "w+b") as f:
        f.write(base64.b64decode(img))


if __name__ == "__main__":
    test_pg_connection()
