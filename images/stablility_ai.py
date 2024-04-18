from enum import Enum
from io import BytesIO
import os
import base64
import random
import sys
import tempfile
import time
from pydantic import BaseModel, Field
import warnings
import requests
from stability_sdk import client
import http.client
from PIL import Image

import stability_sdk.interfaces.gooseai.generation.generation_pb2 as generation

from typing import Optional


API: Optional[client.StabilityInference] = None


class SDXLSampler(Enum):
    DDIM = "ddim"
    DDPM = "ddpm"
    K_EULER = "k_euler"
    # K_EULER_ANCESTRAL = "k_euler_ancestral"
    K_HEUN = "k_heun"
    K_DPM_2 = "k_dpm_2"
    # K_DPM_2_ANCESTRAL = "k_dpm_2_ancestral"
    K_LMS = "k_lms"
    # K_DPMPP_2S_ANCESTRAL = "k_dpmpp_2s_ancestral"
    K_DPMPP_2M = "k_dpmpp_2m"
    K_DPMPP_SDE = "k_dpmpp_sde"

    @staticmethod
    def from_string_with_default(sampler_name: str) -> "SDXLSampler":
        opts = {
            "ddim": SDXLSampler.DDIM,
            "ddpm": SDXLSampler.DDPM,
            "k_euler": SDXLSampler.K_EULER,
            # "k_euler_ancestral": SDXLSampler.K_EULER_ANCESTRAL,
            "k_heun": SDXLSampler.K_HEUN,
            "k_dpm_2": SDXLSampler.K_DPM_2,
            # "k_dpm_2_ancestral": SDXLSampler.K_DPM_2_ANCESTRAL,
            # "k_lms": SDXLSampler.K_LMS,
            # "k_dpmpp_2s_ancestral": SDXLSampler.K_DPMPP_2S_ANCESTRAL,
            "k_dpmpp_2m": SDXLSampler.K_DPMPP_2M,
            "k_dpmpp_sde": SDXLSampler.K_DPMPP_SDE,
        }
        try:
            return opts[sampler_name]
        except KeyError:
            return SDXLSampler.K_DPMPP_2M

    def to_pb(self):
        opts = {
            SDXLSampler.DDIM: generation.SAMPLER_DDIM,
            SDXLSampler.DDPM: generation.SAMPLER_DDPM,
            SDXLSampler.K_EULER: generation.SAMPLER_K_EULER,
            # SDXLSampler.K_EULER_ANCESTRAL: generation.SAMPLER_K_EULER_ANCESTRAL,
            SDXLSampler.K_HEUN: generation.SAMPLER_K_HEUN,
            SDXLSampler.K_DPM_2: generation.SAMPLER_K_DPM_2,
            # SDXLSampler.K_DPM_2_ANCESTRAL: generation.SAMPLER_K_DPM_2_ANCESTRAL,
            # SDXLSampler.K_LMS: generation.SAMPLER_K_LMS,
            # SDXLSampler.K_DPMPP_2S_ANCESTRAL: generation.SAMPLER_K_DPMPP_2S_ANCESTRAL,
            SDXLSampler.K_DPMPP_2M: generation.SAMPLER_K_DPMPP_2M,
            SDXLSampler.K_DPMPP_SDE: generation.SAMPLER_K_DPMPP_SDE,
        }
        return opts[self]


class SDXLStylePreset(Enum):
    # 3d-model analog-film anime cinematic comic-book digital-art enhance fantasy-art isometric line-art low-poly modeling-compound neon-punk origami photographic pixel-art tile-texture
    THREE_DMODEL = "3d-model"
    ANALOGFILM = "analog-film"
    ANIME = "anime"
    CINEMATIC = "cinematic"
    COMICBOOK = "comic-book"
    DIGITALART = "digital-art"
    ENHANCE = "enhance"
    FANTASYART = "fantasy-art"
    ISOMETRIC = "isometric"
    LINEART = "line-art"
    LOW_POLY = "low-poly"
    MODELINGCOMPOUND = "modeling-compound"
    NEONPUNK = "neon-punk"
    ORIGAMI = "origami"
    PHOTOGRAPHICAL = "photographic"
    PIXELART = "pixel-art"
    TILETEXTURE = "tile-texture"

    @staticmethod
    def from_string_with_default(style_preset: str) -> Optional["SDXLStylePreset"]:
        opts = {
            "3d-model": SDXLStylePreset.THREE_DMODEL,
            "analog-film": SDXLStylePreset.ANALOGFILM,
            "anime": SDXLStylePreset.ANIME,
            "cinematic": SDXLStylePreset.CINEMATIC,
            "comic-book": SDXLStylePreset.COMICBOOK,
            "digital-art": SDXLStylePreset.DIGITALART,
            "enhance": SDXLStylePreset.ENHANCE,
            "fantasy-art": SDXLStylePreset.FANTASYART,
            "isometric": SDXLStylePreset.ISOMETRIC,
            "line-art": SDXLStylePreset.LINEART,
            "low-poly": SDXLStylePreset.LOW_POLY,
            "modeling-compound": SDXLStylePreset.MODELINGCOMPOUND,
            "neon-punk": SDXLStylePreset.NEONPUNK,
            "origami": SDXLStylePreset.ORIGAMI,
            "photographic": SDXLStylePreset.PHOTOGRAPHICAL,
            "pixel-art": SDXLStylePreset.PIXELART,
            "tile-texture": SDXLStylePreset.TILETEXTURE,
        }
        try:
            return opts[style_preset]
        except KeyError:
            return None

    def to_pb(self) -> str:
        return self.value


class SDXLParams(BaseModel):
    prompt: str = Field(
        ...,
        description="A detailed, thorough, and vivid description of the image to be generate with a minimum of 20 words.",
    )
    guidance_scale: float = Field(
        ...,
        description="Influences how strongly your generation is guided to match your prompt.",
        # mininum and maximum
        ge=0,
        le=35,
    )
    sampler: SDXLSampler = Field(
        ...,
        description="Choose which sampler we want to denoise our generation with.",
    )
    preset: Optional[SDXLStylePreset] = Field(
        None,
        description="Choose a prebuilt set of styles that will be applied to your generated image.",
    )
    animate: bool = Field(False, description="Whether to animate the image into a short video.")
    motion_cfg_scale: float = Field(
        2.5,
        description="Influences how strongly the animation will match the original image. Higher values allow the animation to deviate more whereas lowe values keep the animation more consistent.",
        ge=0,
        le=10
    )


def get_image_for_prompt(
    params: SDXLParams, seed: Optional[int] = None
) -> Optional[str]:
    global API
    if API is None:
        API = client.StabilityInference(
            key=os.environ.get("SD_KEY"),  # API Key reference.
            verbose=True,  # Print debug messages.
            engine="stable-diffusion-xl-1024-v1-0",  # Set the engine to use for generation.
        )

    if seed is None:
        seed = random.randint(0, 100000)

    for i in range(3):
        try:
            answers = API.generate(
                prompt=params.prompt,
                seed=seed,
                steps=50,  # Amount of inference steps performed on image generation. Defaults to 30.
                cfg_scale=params.guidance_scale,  # Influences how strongly your generation is guided to match your prompt.
                # Setting this value higher increases the strength in which it tries to match your prompt.
                # Defaults to 7.0 if not specified.
                width=1344,  # Generation width, defaults to 512 if not included.
                height=768,  # Generation height, defaults to 512 if not included.
                samples=1,  # Number of images to generate, defaults to 1 if not included.
                sampler=params.sampler.to_pb(),  # Choose which sampler we want to denoise our generation with.
                # Defaults to k_dpmpp_2m if not specified. Clip Guidance only supports ancestral samplers.
                # (Available Samplers: ddim, plms, k_euler, k_euler_ancestral, k_heun, k_dpm_2, k_dpm_2_ancestral, k_dpmpp_2s_ancestral, k_lms, k_dpmpp_2m, k_dpmpp_sde)
                style_preset=None if params.preset is None else params.preset.to_pb(),
            )
            break
        except Exception as e:
            if i == 2:
                return None
            print(f"Failed to generate image for prompt: {e}", flush=True)
            continue

    # Set up our warning to print to the console if the adult content classifier is tripped.
    # If adult content classifier is not tripped, save generated images.
    for resp in answers:
        for artifact in resp.artifacts:
            if artifact.finish_reason == generation.FILTER:
                warnings.warn(
                    f"Your request activated the API's safety filters and could not be processed.\nPrompt: {params.json()}"
                    "Please modify the prompt and try again."
                )
                return "<|IAC|>"
            if artifact.type == generation.ARTIFACT_IMAGE:
                return base64.b64encode(artifact.binary).decode()


def generate_video_from_image(
    image: str, seed: int, cfg_scale: float
) -> str:
    """
    Generates a video from an image using the Stability.ai API.

    Args:
        api_key (str): Your API key for Stability.ai.
        image_path (str): The path to the image file.
        seed (int): The seed for the random number generator.
        cfg_scale (float): The configuration scale for the video generation.

    Returns:
        str: The response from the API as a string.
    """
    tfile = tempfile.mkstemp(suffix=".png")
    with open(tfile[1], "wb") as f:
        f.write(base64.b64decode(image))

    img = Image.open(tfile[1])
    img = img.resize((1024, 576))

    # Encode the file to png bytes
    img_bytes = BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)

    # Prepare the files and data for the multipart/form-data
    files = {"image": ("image.png", img_bytes.read(), "image/png")}
    data = {"seed": seed, "cfg_scale": cfg_scale + 0.0001, "motion_bucket_id": 127}

    # Setup headers
    headers = {"Authorization": f"Bearer {os.environ.get('SD_KEY')}"}

    # Make the request
    response = requests.post(
        "https://api.stability.ai/v2alpha/generation/image-to-video",
        headers=headers,
        files=files,
        data=data,
        timeout=60
    )

    if response.status_code != 200:
        raise Exception("failed to generate video: {}".format(response.text))

    # Get the API response
    id = response.json()["id"]

    print("video id:", id)

    headers["Accept"] = "application/json"

    # Poll the API on loop until our video is done generating
    while True:
        r = requests.get(
            f"https://api.stability.ai/v2alpha/generation/image-to-video/result/{id}", 
            headers=headers, 
            timeout=60
        )

        # Handle error
        if r.status_code >= 400:
            raise Exception(f"failed to retrieve video: {r.text}")

        # Loop for in progress
        if r.status_code == 202:
            time.sleep(3)
            continue

        return r.json()["video"]


if __name__ == "__main__":
    print(SDXLParams.schema_json(indent=2))
