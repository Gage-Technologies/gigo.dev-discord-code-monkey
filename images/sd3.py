import base64
from email.mime import base
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, validator
from requests_toolbelt.multipart.encoder import MultipartEncoder
import requests
import os

class AspectRatio(Enum):
    AS_1_1 = "1:1"
    AS_16_9 = "16:9"
    AS_21_9 = "21:9"
    AS_2_3 = "2:3"
    AS_3_2 = "3:2"
    AS_4_3 = "4:5"
    AS_5_4 = "5:4"
    AS_9_16 = "9:16"
    AS_9_21 = "9:21"
    

    @staticmethod
    def from_string_with_default(style_preset: str) -> "AspectRatio":
        opts = {
            "1:1": AspectRatio.AS_1_1,
            "16:9": AspectRatio.AS_16_9,
            "21:9": AspectRatio.AS_21_9,
            "2:3": AspectRatio.AS_2_3,
            "3:2": AspectRatio.AS_3_2,
            "4:5": AspectRatio.AS_4_3,
            "5:4": AspectRatio.AS_5_4,
            "9:16": AspectRatio.AS_9_16,
            "9:21": AspectRatio.AS_9_21,
        }
        try:
            return opts[style_preset]
        except KeyError:
            return AspectRatio.AS_16_9


class SD3Params(BaseModel):
    prompt: str = Field(..., description="The description of the image to generate.")
    aspect_ratio: AspectRatio = Field(default=AspectRatio.AS_16_9, description="Aspect ratio of the generated image.")
    edit_last_image: bool = Field(default=False, description="Whether the prior image should be used as a starting point and the prompt edits applied to it.")
    strength: float = Field(0.35, description="Strength of the prior image influence when edit_last_image is True.", ge=0, le=1)
    animate: bool = Field(False, description="Whether to animate the image into a short video.")
    motion_cfg_scale: float = Field(
        2.5,
        description="Influences how strongly the animation will match the original image. Higher values allow the animation to deviate more whereas lowe values keep the animation more consistent.",
        ge=0,
        le=10
    )
    

def get_image_for_prompt(
    params: SD3Params, seed: Optional[int] = None, last_img: Optional[str] = None
) -> Optional[str]:
    fields = {
        'prompt': params.prompt,
        'mode': "image-to-image" if last_img is not None else "text-to-image",
        'model': "sd3",
        'output_format': 'png',
    }
    if seed is not None:
        fields['seed'] = str(seed)
    if last_img is not None:
        print("######### including last image")
        fields['image'] = ("input.png", base64.b64decode(last_img), 'image/png')
        fields['strength'] = str(params.strength)
    else:
        fields['aspect_ratio'] = params.aspect_ratio.value

    
    m = MultipartEncoder(fields=fields)


    response = requests.post(
        "https://api.stability.ai/v2beta/stable-image/generate/sd3", 
        headers={
            'Authorization': f'Bearer {os.environ.get("SD_KEY")}',
            'Accept': 'application/json',
            'Content-Type': m.content_type,
        }, 
        data=m
    )
    if response.status_code == 200:
        return response.json()["image"]
    elif response.status_code == 403:
        # handle innapropriate content
        return "<|IAC|>"
    else:
        raise Exception(f"Error in API call: {response.text}")


if __name__ == "__main__":
    params = SD3Params(
        prompt="A man standing on a beauitiful mountain at sunset",
        mode="text-to-image",
        aspect_ratio="16:9",
        output_format="png"
    )
    with open("output_image.png", "rb") as f:
        last_img = base64.b64encode(f.read()).decode()
    result = get_image_for_prompt(params, last_img=last_img)
    with open("output_image2.png", "wb") as f:
        f.write(base64.b64decode(result))
    print("Image generated successfully.")