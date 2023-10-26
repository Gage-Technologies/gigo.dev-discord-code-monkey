import base64

from images.sd_web_ui import get_image_for_prompt


def test_get_image_for_prompt():
    img = get_image_for_prompt("thumbnail for a programming article with the title: build a cgat with openai in golang", "test")
    assert img is not None

    with open("/tmp/test-web-ui.jpg", "wb") as f:
        f.write(base64.b64decode(img))
