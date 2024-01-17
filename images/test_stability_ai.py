import base64
import dotenv

import yaml

from images.stablility_ai import SDXLParams, SDXLSampler, get_image_for_prompt, generate_video_from_image

dotenv.load_dotenv("./.env")


def test_stability_connection():
    img = get_image_for_prompt(SDXLParams(
        prompt="gorilla riding a skateboard",
        sampler=SDXLSampler.K_DPMPP_2M,
        cfg_scale=10
    ), 42069)
    assert img is not None

    with open("/tmp/test-stable-ai.png", "w+b") as f:
        f.write(base64.b64decode(img))

    vid = generate_video_from_image(img, 42069, 2.5, 40)
    assert vid is not None

    with open("/tmp/test-stable-ai.mp4", "w+b") as f:
        f.write(base64.b64decode(vid))


if __name__ == "__main__":
    test_stability_connection()
