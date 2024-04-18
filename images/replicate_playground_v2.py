import base64
from typing import Optional
from pydantic import BaseModel, Field
from enum import Enum
import requests
import replicate


class PlaygroundV2Sampler(Enum):
    DDIM = "DDIM"
    DPM_SOLVER_MULTISTEP = "DPMSolverMultistep"
    K_EULER = "K_EULER"
    K_EULER_ANCESTRAL = "K_EULER_ANCESTRAL"
    HEUN_DISCRETE = "HeunDiscrete"
    PNDM = "PNDM"
    KARRAS_DPM = "KarrasDPM"

    @staticmethod
    def from_string_with_default(sampler_name: str) -> "PlaygroundV2Sampler":
        opts = {
            "DDIM": PlaygroundV2Sampler.DDIM,
            "DPMSolverMultistep": PlaygroundV2Sampler.DPM_SOLVER_MULTISTEP,
            "K_EULER": PlaygroundV2Sampler.K_EULER,
            "K_EULER_ANCESTRAL": PlaygroundV2Sampler.K_EULER_ANCESTRAL,
            "HeunDiscrete": PlaygroundV2Sampler.HEUN_DISCRETE,
            "PNDM": PlaygroundV2Sampler.PNDM,
            "KarrasDPM": PlaygroundV2Sampler.KARRAS_DPM
        }
        try:
            return opts[sampler_name]
        except KeyError:
            return PlaygroundV2Sampler.KARRAS_DPM


class PlaygroundV2Params(BaseModel):
    prompt: str = Field(
        ...,
        description="(prompt): A detailed, thorough, and vivid description of the image to be generate with a minimum of 20 words.",
    )
    negative_prompt = Field(
        "ugly, deformed, noisy, blurry, distorted",
        description="(negative_prompt): Optional negative prompt for classifier-free guidance. Used to prevent the model from producing certain types of content.",
    )
    cfg_scale: float = Field(
        ...,
        description="(cfg_scale): Influences how strongly your generation is guided to match your prompt.",
        # mininum and maximum
        ge=1,
        le=10,
    )
    sampler: PlaygroundV2Sampler = Field(
        ...,
        description="(sampler) Choose which sampler we want to denoise our generation with.",
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


def get_image_for_prompt(params: PlaygroundV2Params, seed: Optional[int] = None):
    output = replicate.run(
        # "playgroundai/playground-v2-1024px-aesthetic:42fe626e41cc811eaf02c94b892774839268ce1994ea778eba97103fe1ef51b8",
        # "lucataco/dpo-sdxl:d41d041f711763cfa9d34f81c9f64da035ae25dbc44ca4e3cea5e89f9f44d724",
        "lucataco/open-dalle-v1.1:1c7d4c8dec39c7306df7794b28419078cb9d18b9213ab1c21fdc46a1deca0144",
        input={
            "width": 1344,
            "height": 768,
            "prompt": params.prompt,
            "scheduler": params.sampler.value,
            "guidance_scale": params.cfg_scale,
            "apply_watermark": False,
            "negative_prompt": params.negative_prompt,
            "num_inference_steps": 50,

            # Unfortunately the safety checker flags everything
            # "disable_safety_checker": True,

            # dpo only
            # "refine": "expert_ensemble_refiner",
            # "high_noise_frac": 0.8,
            # "refine_steps": 50
        },
    )

    # download the image and encode it as a base64 string
    r = requests.get(output[0], stream=True).content
    return base64.b64encode(r).decode("utf-8")

if __name__ == '__main__':
    print(PlaygroundV2Params.schema_json(indent=2))
