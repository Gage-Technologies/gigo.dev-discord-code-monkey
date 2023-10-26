import os
import base64
import random
import sys
import warnings
from stability_sdk import client
import stability_sdk.interfaces.gooseai.generation.generation_pb2 as generation

from typing import Optional


API: Optional[client.StabilityInference] = None


def get_image_for_prompt(
    prompt: str, seed: Optional[int] = None
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
                prompt=prompt,
                seed=seed,
                steps=50,  # Amount of inference steps performed on image generation. Defaults to 30.
                cfg_scale=7.0,  # Influences how strongly your generation is guided to match your prompt.
                # Setting this value higher increases the strength in which it tries to match your prompt.
                # Defaults to 7.0 if not specified.
                width=1344,  # Generation width, defaults to 512 if not included.
                height=768,  # Generation height, defaults to 512 if not included.
                samples=1,  # Number of images to generate, defaults to 1 if not included.
                sampler=generation.SAMPLER_K_DPMPP_2M  # Choose which sampler we want to denoise our generation with.
                # Defaults to k_dpmpp_2m if not specified. Clip Guidance only supports ancestral samplers.
                # (Available Samplers: ddim, plms, k_euler, k_euler_ancestral, k_heun, k_dpm_2, k_dpm_2_ancestral, k_dpmpp_2s_ancestral, k_lms, k_dpmpp_2m, k_dpmpp_sde)
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
                    f"Your request activated the API's safety filters and could not be processed.\nPrompt: {prompt}"
                    "Please modify the prompt and try again."
                )
                return "<|IAC|>"
            if artifact.type == generation.ARTIFACT_IMAGE:
                return base64.b64encode(artifact.binary).decode()
