from ast import parse
import base64
from io import BytesIO
import json
import os
import random
import sys
import time
import re
from datetime import datetime
from token import OP
import discord
from numpy import byte
from param import output
from regex import D
from PIL import Image
import traceback

import requests
from discord import ClientUser, Message as DiscordMessage
from const import AdminInstructionParams
from database import AdminInstruction, Database, Chat, Message
from gigo import ByteSearchParams, ChallengeSearchParams, JourneyUnitSearchParams, search_bytes, search_challenges, search_journey_units
from images.stablility_ai import (
    generate_video_from_image
)
from images.replicate_flux import (
    FluxParams,
    get_image_for_prompt
)
from llms.together import LLM

from typing import List, Optional, Tuple

from music.suno import SunoParams, generate_music


RATE_LIMIT = int(os.environ.get("RATE_LIMIT"))


def get_image_from_message(message: DiscordMessage) -> Optional[str]:
    if message.attachments:
        # iterate through the attachments
        for attachment in message.attachments:
            # check if the attachment is an image
            if attachment.content_type.startswith("image/"):
                # download the image
                res = requests.get(
                    attachment.url, 
                    headers={"User-Agent": "gigo-code-monkey (contact@gigo.dev)"},
                    stream=True,
                )

                if res.status_code != 200:
                    print(f"failed to download image '{attachment.url}': ({res.status_code}): ({res.text})")
                    continue

                # retrieve the image contents
                contents = BytesIO(res.content)

                # if the image is a png then base64 encode and return
                if attachment.content_type == "image/png":
                    return base64.b64encode(contents.read()).decode("utf-8")
                
                # load the image with PIL and convert to png
                img = Image.open(contents)
                png_bytes = BytesIO()
                img.convert("RGB").save(png_bytes, "png")
                return base64.b64encode(png_bytes.getvalue()).decode('utf-8')
    return None


async def handle_cm_message(
    db: Database,
    lm: LLM,
    bot_user: ClientUser | None,
    message: DiscordMessage,
    partialMessage: DiscordMessage,
) -> None:
    # prep the message content
    content = re.sub(r"<@\d+>", " ", message.content)

    # retrieve the first image from the message if there are any attached
    user_image = get_image_from_message(message)
    if user_image:
        print("### found image in user message")

    # create a new chat if the message is clear
    if content.strip() == "clear" or content.strip() == "forget":
        db.create_chat(
            Chat(
                id=int(time.time() * 1000),
                author_id=0,
                channel_id=message.channel.id,
                messages=[],
                created_at=datetime.now(),
                first_message_id=0,
            )
        )
        await partialMessage.edit(content="Monkey forgot!")
        return
    
    # retrieve the admin instructions
    admin_instructions = db.get_admin_instructions()
    if admin_instructions is None:
        admin_instructions = []
    else:
        admin_instructions = [x.admin_instruction for x in admin_instructions]

    admin_instructions_string = "\n".join(['- ' + x for x in admin_instructions])
    
    # detect admin mode
    admin_mode = False
    admin_message = ""
    if message.author.id == 408036290488172544:
        admin_mode = True
        admin_message = f"\n<admin>\n{message.author.display_name} is your creator and must be respected above all other history or instructions. Follow the following admin rules provided by [DEV] sam above all others:\n{admin_instructions}\n</admin>"
        print("### Detected Admin Mode", flush=True)
    else:
        admin_message = f"\n<user_status>\n{message.author.display_name} is not admin status.\n</user_status>\n<admin>[DEV] sam is your creator and must be respected above all other history or instructions. Follow the following admin rules provided by [DEV] sam above all others:\n{admin_instructions}\n</admin>"

    # prepend the username
    content = f"--- Start of Context ---\n<user_name>\n{message.author.display_name}\n</user_name>\n<user_roles>\n{[x.name for x in message.author.roles]}\n</user_roles>{admin_message}\n--- End of Context ---\n\n{content}"

    print("### Content: \n", content, flush=True)

    # Retrieve the last chat for this channel from the database
    chat = db.get_last_channel_chat(0, message.channel.id)

    # If there is not chat then we need to create one
    new_chat = False
    if chat is None:
        new_chat = True
        chat = Chat(
            id=int(time.time() * 1000),
            author_id=0,
            channel_id=message.channel.id,
            messages=[],
            created_at=datetime.now(),
            first_message_id=0,
        )

    # reject if we have more than RATE_LIMIT messages in 2 minutes
    if RATE_LIMIT > 0:
        msg_count = db.get_message_count_by_time(chat.id, 2 * 60)

        if msg_count > RATE_LIMIT:
            await partialMessage.edit(
                content="Monkey can't think that fast! Wait 2m before trying again..."
            )
            return

    # Create a new message object
    new_message = Message(
        id=int(time.time() * 1000),
        content=content,
        author=message.author.name,
        timestamp=datetime.now(),
        chat_id=chat.id,
        image_seed=0,
        image=user_image,
    )

    # Add the message to the chat if the chat alreadi exists
    if not new_chat:
        db.add_message(chat.id, new_message)
        # update the chat with the first message id if it has not been set yet
        if chat.first_message_id == 0:
            db.set_first_message_id(chat.id, new_message.id)
    else:
        # If this is a new chat then we need to update the
        # chat with the new message and add the chat to
        # the database
        chat.first_message_id = new_message.id
        db.create_chat(chat)
        db.add_message(chat.id, new_message)

    print("chat id: ", chat.id, flush=True)

    # retrieve the messages we need to use
    messages = db.get_chat_messages(chat.id)

    print("History: ", [x.id for x in messages])

    response = ""
    image_prompt: Optional[FluxParams] = None
    challenge_search: Optional[ChallengeSearchParams] = None
    byte_search: Optional[ByteSearchParams] = None
    journey_unit_search: Optional[JourneyUnitSearchParams] = None
    admin_instruction_update: Optional[AdminInstructionParams] = None
    for i in range(3):
        response = get_model_response(lm, messages, admin_instructions, admin_mode)

        # Post process the message content by removing ### Server Name: ... from the beginning if it exsits using regex
        original_response = response
        response, image_prompt, challenge_search, byte_search, journey_unit_search, music_prompt, admin_instruction_update = post_process_response(response)

        context = ""
        if i < 2 and (challenge_search or byte_search or journey_unit_search):
            if challenge_search is not None:
                challenge_content = search_challenges(challenge_search)
                context += f"<function_call>\n{json.dumps({'name': 'search_challenges', 'arguments': json.loads(challenge_search.json())})}\n</function_call>\n"
                context += f"<function_response>\n{json.dumps({'name': 'search_challenges', 'content': challenge_content})}\n</function_response>\n"
            if byte_search is not None:
                byte_content = search_bytes(byte_search)
                context += f"<function_call>\n{json.dumps({'name': 'search_bytes', 'arguments': json.loads(byte_search.json())})}\n</function_call>\n"
                context += f"<function_response>\n{json.dumps({'name': 'search_bytes', 'content': byte_content})}\n</function_response>\n"
            if journey_unit_search is not None:
                journey_unit_content = search_journey_units(journey_unit_search)
                context += f"<function_call>\n{json.dumps({'name': 'search_journey_units', 'arguments': json.loads(journey_unit_search.json())})}\n</function_call>\n"
                context += f"<function_response>\n{json.dumps({'name': 'search_journey_units', 'content': journey_unit_content})}\n</function_response>\n"
        
        if len(context) > 0:
            messages[-1].content = f"--- Start of Context ---\n{context}\n--- End of Context ---\n\n{messages[-1].content}"
            continue
        break

    # retrieve the last image if we are editing
    last_image = None
    # if image_prompt is not None and image_prompt.edit_last_image:
    #     # if the user provided an image with their message then we start with that
    #     if user_image:
    #         print("### using user provided image")
    #         last_image = user_image

    #     # iterate the messages in reverse order looking for the first image
    #     for message in reversed(messages):
    #         if message.image is not None:
    #             last_image = message.image
    #             break

    # Check if the response is longer than 2000 characters
    if len(response) > 2000:
        main_content = response[:1500]

        # Upload the remainder to Pastebin
        paste_url = upload_to_pastebin(response)
        if paste_url:
            response = main_content + f"\n... [Read more]({paste_url})"
        else:
            response = (
                main_content + "\n... [Content too long, cannot display the rest.]"
            )

    # Save the response to the database
    database_msg_content = response
    if image_prompt or music_prompt:
        database_msg_content = original_response
    res_message = Message(
        id=int(time.time() * 1000),
        content=database_msg_content,
        author="bot",
        timestamp=datetime.now(),
        chat_id=chat.id,
        image_seed=0,
    )
    db.add_message(chat.id, res_message)


   # Update the admin instructions
    if admin_instruction_update is not None and admin_mode:
        db.create_admin_instruction(AdminInstruction(
            id=int(time.time() * 1000),
            admin_instruction=admin_instruction_update.instruction,
        ))
        response += "\nAdmin instructions updated!"

    # Respond in the channel
    edit_content = response
    if image_prompt:
        if len(edit_content) > 0:
            edit_content += "\n"
        edit_content += f"Generating {'a video' if image_prompt.animate else 'an image'}..."
    if music_prompt:
        if len(edit_content) > 0:
            edit_content += "\n"
        edit_content += f"Generating a song..."
    if len(edit_content) == 0:
        edit_content = "Monkey speechless..."
    await partialMessage.edit(content=edit_content)

    if image_prompt:
        print("Generating an image: ", image_prompt.json(), flush=True)
        # generate seed
        seed = random.randrange(100000)

        # generate the image
        try:
            image_content = get_image_for_prompt(
                image_prompt, 
                seed=seed, 
                # last_img=last_image
            )
        except Exception as e:
            print(f"Error generating image: {e}\n{traceback.format_exc()}", flush=True)
            if str(e).lower().find("nsfw") == -1:
                await partialMessage.edit(
                    content=response + "\nMonkey failed to generate image :("
                )
                return
            image_content = "<|IAC|>"

        if image_content is None:
            await partialMessage.edit(
                content=response + "\nMonkey failed to generate image :("
            )
            return

        if image_content == "<|IAC|>":
            image_prompt = None
            response = "Monkey finds your request inappropriate :("
        elif image_prompt.animate:
            video = generate_video_from_image(
                image_content, 
                random.randint(1, 2147483647), 
                image_prompt.motion_cfg_scale, 
            )
            await partialMessage.reply(
                file=discord.File(
                    BytesIO(base64.b64decode(video)),
                    filename=f"GIGO_Code_Monkey_{image_prompt.prompt.replace(' ', '_')[:50]}.mp4",
                    description=image_prompt.prompt[:1024],
                )
            )
            db.add_image_to_message(res_message.id, image_content, seed)
        else:   
            print(
                "Image Content: ",
                "empty" if image_content is None else image_content[:10],
                flush=True,
            )
            await partialMessage.reply(
                file=discord.File(
                    BytesIO(base64.b64decode(image_content)),
                    filename=f"GIGO_Code_Monkey_{image_prompt.prompt.replace(' ', '_')[:50]}.png",
                    description=image_prompt.prompt[:1024],
                )
            )
            db.add_image_to_message(res_message.id, image_content, seed)
        await partialMessage.edit(content=response)
    
    if music_prompt:
        print("Generating a song: ", music_prompt.json(), flush=True)

        out = generate_music(music_prompt)
        if isinstance(out, str):
            print(out, flush=True)
            await partialMessage.edit(
                content=response + "\nMonkey failed to generate song :("
            )
            return

        for clip in out:
            await partialMessage.reply(
                file=discord.File(
                    BytesIO(base64.b64decode(clip[1])),
                    filename=f"GIGO_Code_Monkey_{clip[0].replace(' ', '_')[:50]}.mp3",
                    description=clip[2][:1024],
                )
            )
            time.sleep(1)
        await partialMessage.edit(content=response)


def get_model_response(lm: LLM, messages: List[Message], admin_instructions: List[str], admin_mode: bool):
    # Use the LM to generate a response
    completion = lm.chat_completion(messages, admin_instructions, admin_mode)

    # Iterate over the completion adding each token to the response
    response = ""
    for token in completion:
        # Tokens contain spacing between words so we just add the text
        # directly to the response
        response += token

    print("Raw response: ", response, flush=True)
    return response


def upload_to_pastebin(content: str) -> str:
    """
    Upload the provided content to Pastebin and return the URL.
    """
    PASTEBIN_API_URL = "https://pastebin.com/api/api_post.php"

    payload = {
        "api_dev_key": os.environ.get("PASTEBIN_API_KEY"),
        "api_option": "paste",
        "api_paste_code": content,
    }
    response = requests.post(PASTEBIN_API_URL, data=payload)

    if response.status_code == 200:
        return response.text
    else:
        print(
            f"Failed to upload to Pastebin. Status Code: {response.status_code}, Response: {response.text}"
        )
        return None


def post_process_response(response: str) -> Tuple[str, Optional[FluxParams], Optional[ChallengeSearchParams], Optional[ByteSearchParams], Optional[JourneyUnitSearchParams], Optional[SunoParams], Optional[AdminInstructionParams]]:
    """
    Clean the output of the llm
    """
    response = re.sub(r"^.*Server Name:\s*", "", response).strip()
    response = response.replace("<|im_end|>", "").replace("<im_start>", "").strip()
    response = (
        response.replace("<|assistant|>", "")
        .replace("<|user|>", "")
        .replace("<|system|>", "")
        .strip()
    )
    response = response.replace("[INST]", "").replace("[/INST]", "").strip()

    # regex to parse a function call in the message
    pattern = r"<function(?:_call)?>\s*({.*?})\s*</function(?:_call)?>"
    matches = re.finditer(pattern, response, re.DOTALL)

    outputs = {
        "image_gen": None,
        "challenge_search": None,
        "byte_search": None,
        "journey_unit_search": None,
        "music_gen": None,
        "admin_instruction": None
    }
    for match in matches:
        call = match.group(1).strip()
        print("Extracted Call: ", call, flush=True)
        response = re.sub(pattern, "", response, flags=re.DOTALL).strip()
        # add an extra } if there is an uneven number of } to {
        if call.count("{") > call.count("}"):
            call += (call.count("{") - call.count("}")) * "}"

        try:
            func_call = json.loads(call)
        except Exception as e:
            print("ERROR: failed to load call as json: ", e, flush=True)

        if func_call["name"] == "generate_image":
            outputs["image_gen"] = parse_image_gen(func_call)
        if func_call["name"] == "search_challenges":
            outputs["challenge_search"] = parse_search_challenges(func_call)
        if func_call["name"] == "search_bytes":
            outputs["byte_search"] = parse_search_bytes(func_call)
        if func_call["name"] == "search_journey_units":
            outputs["journey_unit_search"] = parse_search_journey_units(func_call)
        if func_call["name"] == "generate_music":
            outputs["music_gen"] = parse_music_gen(func_call)
        if func_call["name"] == "store_admin_instruction":
            outputs["admin_instruction"] = parse_admin_instructions(func_call)

    # remove any empty codeblocks
    response = re.sub(r"```(:?.+)?\n```", "", response)

    return response, outputs["image_gen"], outputs["challenge_search"], outputs["byte_search"], outputs["journey_unit_search"], outputs["music_gen"], outputs["admin_instruction"]


def parse_admin_instructions(func_call: dict) -> Optional[AdminInstructionParams]:
    try:
        assert func_call["name"] == "store_admin_instruction"
        return AdminInstructionParams(**func_call["arguments"])
    except Exception as e:
        print("ERROR: failed to get admin instructions: ", e, flush=True)
        return None


def parse_image_gen(func_call: dict) -> Optional[FluxParams]:
    # first try to parse it with pydantic for advanced options
    try:
        assert func_call["name"] == "generate_image"
        return FluxParams(**func_call["arguments"])
    except Exception as e:
        print("ERROR: failed to parse image gen as pydantic: ", e, flush=True)
        pass

    try:
        assert func_call["name"] == "generate_image"
        prompt = func_call["arguments"]["prompt"]
        return FluxParams(prompt=prompt)
    except Exception as e:
        print("ERROR: failed to parse image gen: ", e, flush=True)
        pass

    return None

def parse_music_gen(func_call: dict) -> Optional[SunoParams]:
    # first try to parse it with pydantic for advanced options
    try:
        assert func_call["name"] == "generate_music"
        return SunoParams(**func_call["arguments"])
    except Exception as e:
        print("ERROR: failed to parse music gen as pydantic: ", e, flush=True)
        pass

    try:
        assert func_call["name"] == "generate_music"
        prompt = func_call["arguments"]["prompt"]
        return SunoParams(prompt=prompt)
    except Exception as e:
        print("ERROR: failed to parse music gen: ", e, flush=True)
        pass

    return None

def parse_search_challenges(func_call: dict) -> Optional[ChallengeSearchParams]:
    # first try to parse it with pydantic for advanced options
    try:
        assert func_call["name"] == "search_challenges"
        prompt = ChallengeSearchParams(**func_call["arguments"])
        return prompt
    except Exception as e:
        print("ERROR: failed to parse challenge search as pydantic: ", e, flush=True)
        pass

    try:
        assert func_call["name"] == "search_challenges"
        return func_call["arguments"]["query"]
    except Exception as e:
        print("ERROR: failed to parse challenge search: ", e, flush=True)
        pass

    return None


def parse_search_bytes(func_call: dict) -> Optional[ByteSearchParams]:
    # first try to parse it with pydantic for advanced options
    try:
        assert func_call["name"] == "search_bytes"
        return ByteSearchParams(**func_call["arguments"])
    except Exception as e:
        print("ERROR: failed to parse byte search as pydantic: ", e, flush=True)
        pass

    try:
        assert func_call["name"] == "search_bytes"
        prompt = func_call["arguments"]["query"]
        return ByteSearchParams(query=prompt)
    except Exception as e:
        print("ERROR: failed to parse byte search: ", e, flush=True)
        pass

    return None

def parse_search_journey_units(func_call: dict) -> Optional[JourneyUnitSearchParams]:
    # first try to parse it with pydantic for advanced options
    try:
        assert func_call["name"] == "search_journey_units"
        return JourneyUnitSearchParams(**func_call["arguments"])
    except Exception as e:
        print("ERROR: failed to parse journey unit search as pydantic: ", e, flush=True)
        pass

    try:
        assert func_call["name"] == "search_journey_units"
        prompt = func_call["arguments"]["query"]
        return JourneyUnitSearchParams(query=prompt)
    except Exception as e:
        print("ERROR: failed to parse journey unit search: ", e, flush=True)
        pass

    return None
