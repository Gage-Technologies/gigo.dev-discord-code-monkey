import base64
from http.cookies import SimpleCookie
import os
import time
from typing import Optional, List, Tuple, Union
from pydantic import BaseModel, Field
import requests
from requests_toolbelt import user_agent


class SunoParams(BaseModel):
    prompt: str = Field(..., description="The description of the song to generate. Be sure to describe the song genre and focus of the song. Max length of 200 characters")
    instrumental: bool = Field(False, description="Whether to generate an instrumental song with no lyrics.")


class Metadata(BaseModel):
    tags: Optional[Union[List[str], str]] = None
    prompt: str = ""
    gpt_description_prompt: str
    audio_prompt_id: Optional[str] = None
    history: Optional[List[str]] = None
    concat_history: Optional[List[str]] = None
    type: str
    duration: Optional[float] = None
    refund_credits: Optional[int] = None
    stream: bool
    error_type: Optional[str] = None
    error_message: Optional[str] = None

class Clip(BaseModel):
    id: str
    video_url: str = ""
    audio_url: str = ""
    image_url: Optional[str] = None
    image_large_url: Optional[str] = None
    is_video_pending: bool
    major_model_version: str
    model_name: str
    metadata: Metadata
    is_liked: bool
    user_id: str
    display_name: str
    handle: str
    is_handle_updated: bool
    is_trashed: bool
    reaction: Optional[str] = None
    created_at: str
    status: str
    title: str = ""
    play_count: int = 0
    upvote_count: int = 0
    is_public: bool

class SunoResponse(BaseModel):
    id: str
    clips: List[Clip]
    metadata: Metadata
    major_model_version: str
    status: str
    created_at: str
    batch_size: int



# {
#     "id": "e4aaf041-e3bc-40b5-a62d-d26dee9cfd73",
#     "clips": [
#         {
#             "id": "c43d5b93-1378-4d50-83d3-565f6c756a91",
#             "video_url": "",
#             "audio_url": "",
#             "image_url": null,
#             "image_large_url": null,
#             "is_video_pending": false,
#             "major_model_version": "v3",
#             "model_name": "chirp-v3",
#             "metadata": {
#                 "tags": null,
#                 "prompt": "",
#                 "gpt_description_prompt": "a song about gigo the code platform",
#                 "audio_prompt_id": null,
#                 "history": null,
#                 "concat_history": null,
#                 "type": "gen",
#                 "duration": null,
#                 "refund_credits": null,
#                 "stream": true,
#                 "error_type": null,
#                 "error_message": null
#             },
#             "is_liked": false,
#             "user_id": "10fe1369-3e46-4a3f-bc51-88a15e48ec8d",
#             "display_name": "IntenseScale895",
#             "handle": "intensescale895",
#             "is_handle_updated": false,
#             "is_trashed": false,
#             "reaction": null,
#             "created_at": "2024-04-19T18:04:02.858Z",
#             "status": "submitted",
#             "title": "",
#             "play_count": 0,
#             "upvote_count": 0,
#             "is_public": false
#         },
#         {
#             "id": "ac622979-83bb-4c83-9499-2cac14952771",
#             "video_url": "",
#             "audio_url": "",
#             "image_url": null,
#             "image_large_url": null,
#             "is_video_pending": false,
#             "major_model_version": "v3",
#             "model_name": "chirp-v3",
#             "metadata": {
#                 "tags": null,
#                 "prompt": "",
#                 "gpt_description_prompt": "a song about gigo the code platform",
#                 "audio_prompt_id": null,
#                 "history": null,
#                 "concat_history": null,
#                 "type": "gen",
#                 "duration": null,
#                 "refund_credits": null,
#                 "stream": true,
#                 "error_type": null,
#                 "error_message": null
#             },
#             "is_liked": false,
#             "user_id": "10fe1369-3e46-4a3f-bc51-88a15e48ec8d",
#             "display_name": "IntenseScale895",
#             "handle": "intensescale895",
#             "is_handle_updated": false,
#             "is_trashed": false,
#             "reaction": null,
#             "created_at": "2024-04-19T18:04:02.858Z",
#             "status": "submitted",
#             "title": "",
#             "play_count": 0,
#             "upvote_count": 0,
#             "is_public": false
#         }
#     ],
#     "metadata": {
#         "tags": null,
#         "prompt": "",
#         "gpt_description_prompt": "a song about gigo the code platform",
#         "audio_prompt_id": null,
#         "history": null,
#         "concat_history": null,
#         "type": "gen",
#         "duration": null,
#         "refund_credits": null,
#         "stream": true,
#         "error_type": null,
#         "error_message": null
#     },
#     "major_model_version": "v3",
#     "status": "running",
#     "created_at": "2024-04-19T18:04:02.848Z",
#     "batch_size": 2
# }

# {"gpt_description_prompt":"a song about gigo the code platform","mv":"chirp-v3-0","prompt":"","make_instrumental":false}
def generate_music(params: SunoParams) -> Union[str, List[Tuple[str, str, str]]]:
    k = os.environ.get('SUNO_KEY')
    if k.startswith('"'):
        k = k[1:-1]
    print(k)
    cookies = parse_cookie(k)

    raw_res = requests.get(
        "https://clerk.suno.com/v1/environment?__clerk_framework_hint=nextjs&__clerk_framework_version=14.2.0&_clerk_js_version=4.72.0-snapshot.vc141245",
        timeout=60,
        headers={
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Origin": "https://suno.com",
            "Referrer": "https://suno.com",
        },
        cookies=cookies
    )

    if raw_res.status_code != 200:
        return f"<api_error>\nFailed to initialize with Suno API:\n({raw_res.status_code}) {raw_res.text}\n</api_error>"

    cookies.update(get_cookies_as_dict(raw_res))

    raw_res = requests.get(
        "https://clerk.suno.com/v1/client?_clerk_js_version=4.72.0-snapshot.vc141245",
        timeout=60,
        headers={
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Origin": "https://suno.com",
            "Referrer": "https://suno.com",
        },
        cookies=cookies
    )

    if raw_res.status_code != 200:
        return f"<api_error>\nFailed to authenticate with Suno API:\n({raw_res.status_code}) {raw_res.text}\n</api_error>"
    
    print("Init Auth: ", raw_res.json())
    
    sessions = raw_res.json()["response"]["sessions"]
    sess = None
    sess_exp = 0
    for session in sessions:
        if session["status"] != "active":
            continue
        if session["expire_at"] > sess_exp:
            sess = session["id"]
            sess_exp = session["expire_at"]
    
    if sess is None:
        return f"<api_error>\nFailed to authenticate with Suno API:\nno active sessions\n</api_error>"
    
    cookies.update(get_cookies_as_dict(raw_res))

    raw_res = requests.post(
        f"https://clerk.suno.com/v1/client/sessions/{sess}/tokens?_clerk_js_version=4.72.0-snapshot.vc141245",
        json={
            "_clerk_js_version": "4.72.0-snapshot.vc141245"
        },
        timeout=60,
        headers={
            "Cookie": os.environ.get('SUNO_KEY'),
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Origin": "https://suno.com",
            "Referrer": "https://suno.com",
        },
    )

    if raw_res.status_code != 200:
        return f"<api_error>\nFailed to authenticate with Suno API:\n({raw_res.status_code}) {raw_res.text}\n</api_error>"
    
    key = raw_res.json()["jwt"]

    p = {"gpt_description_prompt": params.prompt[:200],"mv":"chirp-v3-0","prompt":"","make_instrumental":params.instrumental}
    raw_res = requests.post(
        "https://studio-api.suno.ai/api/generate/v2/",
        json=p,
        headers={
            "Authorization": f"Bearer {key}",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        },
        timeout=60,
    )

    if raw_res.status_code != 200:
        return f"<api_error>\nFailed to generate song from Suno API:\n({raw_res.status_code}) {raw_res.text}\n</api_error>"

    res = SunoResponse.parse_obj(raw_res.json())

    print("Started song gen: ", [x.id for x in res.clips])

    failures = 0
    for i in range(15):
        print("Checking Status: ", i)
        raw_res = requests.get(
            "https://studio-api.suno.ai/api/feed/?ids=" + ",".join([x.id for x in res.clips]),
            headers={
                "Authorization": f"Bearer {key}",
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            },
            timeout=60,
        )

        if raw_res.status_code != 200:
            if failures > 3:
                return f"<api_error>\nFailed to retrieve song from Suno API:\n({raw_res.status_code}) {raw_res.text}\n</api_error>"

            failures += 1
            time.sleep(10)
            continue
    
        print(raw_res.json())

        clips = [Clip.parse_obj(x) for x in raw_res.json()]

        all_completed = all(clip.status == "error" for clip in clips)
        if all_completed:
            return f"<api_error>\nFailed to retrieve song from Suno API:\n({clip[0].error_type}) {clip[0].error_message}\n</api_error>"
        
        # Check if all clips are completed
        all_completed = all(clip.status == "streaming" for clip in clips)
        if all_completed:
            audio = []
            for clip in clips:
                print("Downloadindg audio: ", clip.audio_url)
                raw_res = requests.get(
                    clip.audio_url,
                    headers={
                        "Authorization": f"Bearer {key}",
                        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                    },
                    timeout=60,
                    stream=True,
                )
                if raw_res.status_code != 200:
                    return f"<api_error>\nFailed to retrieve complete song from Suno API:\n({raw_res.status_code}) {raw_res.text}\n</api_error>"
                
                audio.append(base64.b64encode(raw_res.content).decode("utf-8"))

            return [(x.title, audio[i], x.metadata.prompt) for i, x in enumerate(clips)]

        time.sleep(10)
    
    return f"<api_error>\nFailed to retrieve song from Suno API:\ntimed out waiting on the server\n</api_error>"


def parse_cookie(cookie_string):
    cookie = SimpleCookie()
    cookie.load(cookie_string)
    
    # Extracting cookies into a dictionary
    cookies_dict = {key: morsel.value for key, morsel in cookie.items()}
    return cookies_dict


def get_cookies_as_dict(response):
    # Accessing the cookies from the response
    cookies = response.cookies
    
    # Converting cookies to a dictionary
    cookies_dict = {name: value for name, value in cookies.items()}
    return cookies_dict


if __name__ == '__main__':
    out = generate_music(SunoParams(prompt="a song about gigo the code platform", instrumental=False))
    print(out)