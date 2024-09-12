import base64
from typing import Optional
from pydantic import BaseModel, Field
from enum import Enum
import requests
import replicate

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
            "2:3": AspectRatio.AS_2_3,
            "3:2": AspectRatio.AS_3_2,
            "4:5": AspectRatio.AS_4_3,
            "5:4": AspectRatio.AS_5_4,
            "9:16": AspectRatio.AS_9_16,
        }
        try:
            return opts[style_preset]
        except KeyError:
            return AspectRatio.AS_16_9


class FluxParams(BaseModel):
    prompt: str = Field(
        ...,
        description="(prompt): A detailed, thorough, and vivid description of the image to be generate with a minimum of 20 words.",
    )
    cfg_scale: float = Field(
        ...,
        description="(cfg_scale): Controls the balance between adherence to the text prompt and image quality/diversity. Higher values make the output more closely match the prompt but may reduce overall image quality. Lower values allow for more creative freedom but might produce results less relevant to the prompt.",
        # mininum and maximum
        ge=2,
        le=5,
    )
    interval: int = Field(
        1,
        description="(interval): Interval is a setting that increases the variance in possible outputs letting the model be a tad more dynamic in what outputs it may produce in terms of composition, color, detail, and prompt interpretation. Setting this value low will ensure strong prompt following with more consistent outputs, setting it higher will produce more dynamic or varied outputs.",
        ge=1,
        le=5,
    )
    aspect_ratio: AspectRatio = Field(
        AspectRatio.AS_16_9,
        description="(aspect_ratio): The aspect ratio of the generated image."
    )
    animate: bool = Field(
        False, description="(animate): Generated an animated version of the image."
    )
    motion_cfg_scale: float = Field(
        2.5,
        description="(motion_cfg_scale): Influences how strongly the animation will match the original image. Higher values allow the animation to deviate more whereas lowe values keep the animation more consistent.",
        ge=0,
        le=10,
    )


def get_image_for_prompt(params: FluxParams, seed: Optional[int] = None):
    output = replicate.run(
        "black-forest-labs/flux-pro",
        input={
            "steps": 30,
            "prompt": params.prompt,
            "guidance": params.cfg_scale,
            "interval": params.interval,
            "aspect_ratio": params.aspect_ratio.value,
            "safety_tolerance": 3,
            "seed": seed,
        },
    )

    # download the image and encode it as a base64 string
    r = requests.get(output, stream=True).content
    return base64.b64encode(r).decode("utf-8")

if __name__ == '__main__':
    print(FluxParams.schema_json(indent=2))
