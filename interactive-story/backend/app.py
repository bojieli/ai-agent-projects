from flask import Flask, request, jsonify, send_from_directory, Response
import uuid
import httpx
import requests
import json
import random
import os
import sys
from queue import Queue
import asyncio
import re
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# OpenAI API Key
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
if not OPENAI_API_KEY or OPENAI_API_KEY == "<token>":
    print("错误: OPENAI_API_KEY 环境变量未设置或未正确配置。请设置 OPENAI_API_KEY 环境变量！")
    sys.exit(1)

app = Flask(__name__, static_folder="../frontend", static_url_path="")

# 全局内存存储游戏会话（仅用于演示，不适合生产环境）
sessions = {}

# 定义用于调试日志的队列
debug_queue = Queue()

def debug_log(message, msg_type="log"):
    # 以 JSON 格式发送调试日志，包含日志类型和内容
    payload = json.dumps({"type": msg_type, "log": message})
    debug_queue.put(payload)

# SSE 调试日志流，实时推送 debug 消息到前端
@app.route("/debug_stream")
def debug_stream():
    def event_stream():
        while True:
            # 消息已经是 JSON 格式字符串，直接发送给客户端
            message = debug_queue.get()
            yield f"data: {message}\n\n"
    return Response(event_stream(), mimetype="text/event-stream")

# 配置 API Token 和各 API URL
SILICONFLOW_API_KEY = os.environ.get("SILICONFLOW_API_KEY")
if not SILICONFLOW_API_KEY or SILICONFLOW_API_KEY == "<token>":
    print("错误: SILICONFLOW_API_KEY 环境变量未设置或未正确配置。请设置 SILICONFLOW_API_KEY 环境变量！")
    sys.exit(1)

## 引入官方 DeepSeek R1 API 的密钥
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
if not DEEPSEEK_API_KEY or DEEPSEEK_API_KEY == "<token>":
    print("错误: DEEPSEEK_API_KEY 环境变量未设置或未正确配置。请设置 DEEPSEEK_API_KEY 环境变量！")
    sys.exit(1)

TRANSCRIPTION_URL = "https://api.siliconflow.cn/v1/audio/transcriptions"
TTS_URL = "https://api.siliconflow.cn/v1/audio/speech"
IMAGE_GEN_URL = "https://api.siliconflow.cn/v1/images/generations"
TEXT_GEN_URL = "https://api.siliconflow.cn/v1/chat/completions"

# 新增 robust_json_parse 用于健壮解析 JSON 字符串
def robust_json_parse(text):
    try:
        return json.loads(text)
    except Exception as e:
        # 尝试使用正则表达式提取 markdown code block 中的 JSON 内容
        m = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", text)
        if m:
            json_text = m.group(1)
            try:
                return json.loads(json_text)
            except Exception as e2:
                print("Failed parsing after extracting code block:", e2)
        # 若正则提取不成功，则尝试手动查找 JSON 数组或对象
        stripped = text.strip()
        if stripped.startswith("```"):
            const_lines = stripped.splitlines()
            if len(const_lines) >= 3:
                stripped = "\n".join(const_lines[1:-1])
        for char in ['{', '[']:
            if char in stripped:
                try:
                    end_char = "}" if char == "{" else "]"
                    start = stripped.index(char)
                    end = stripped.rindex(end_char) + 1
                    possible_json = stripped[start:end]
                    return json.loads(possible_json)
                except Exception as e3:
                    continue
        print("robust_json_parse failed:", e)
        raise e

# 加载 stories.json 中的故事数据
stories_path = os.path.join(os.path.dirname(__file__), "stories.json")
with open(stories_path, "r", encoding="utf-8") as f:
    stories_data = json.load(f)

async def generate_text_async_stream(prompt, model=None):
    """Streaming version that yields tokens"""
    if not model:
        model = "openai/o3-mini"  # Default to OpenAI o3-mini
        
    if model.startswith("openai/"):
        payload = {
            "model": model.replace("openai/", ""),
            "messages": [{"role": "user", "content": prompt}],
            "stream": True,
            "max_tokens": 4096,
        }
        headers = {
            "Authorization": "Bearer " + OPENAI_API_KEY,
            "Content-Type": "application/json"
        }
        async for token in try_provider_http_stream("https://api.openai.com/v1/chat/completions", payload, headers):
            yield token
        return
    elif model == "deepseek-ai/DeepSeek-R1":
        providers = ["doubao", "siliconflow", "deepseek_official"]
        last_exception = None
        for provider in providers:
            try:
                if provider == "doubao":
                    async for token in try_provider_doubao_stream(prompt, model="ep-20250206131705-gtthc"):
                        yield token
                    return
                elif provider == "siliconflow":
                    payload = {
                        "model": "deepseek-ai/DeepSeek-R1",
                        "messages": [{"role": "user", "content": prompt}],
                        "stream": True,
                        "max_tokens": 8192,
                    }
                    headers = {
                        "Authorization": "Bearer " + SILICONFLOW_API_KEY,
                        "Content-Type": "application/json"
                    }
                    async for token in try_provider_http_stream(TEXT_GEN_URL, payload, headers):
                        yield token
                    return
                elif provider == "deepseek_official":
                    payload = {
                        "model": "deepseek-ai/DeepSeek-R1",
                        "messages": [{"role": "user", "content": prompt}],
                        "stream": True,
                        "max_tokens": 8192,
                    }
                    payload["model"] = "deepseek-reasoner"
                    headers = {
                        "Authorization": "Bearer " + DEEPSEEK_API_KEY,
                        "Content-Type": "application/json"
                    }
                    async for token in try_provider_http_stream("https://api.deepseek.com/v1/chat/completions", payload, headers):
                        yield token
                    return
            except Exception as e:
                last_exception = e
                debug_log(f"Provider {provider} failed: {e}", "log")
        raise Exception("All providers failed for deepseek-ai/DeepSeek-R1: " + str(last_exception))
    elif model == "deepseek-ai/DeepSeek-V3":
        try:
            async for token in try_provider_doubao_stream(prompt, model="ep-20250206203431-bql9h"):
                yield token
            return
        except Exception as e:
            debug_log(f"Doubao provider failed for DeepSeek V3: {e}", "log")
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": True,
                "max_tokens": 4096,
            }
            headers = {
                "Authorization": "Bearer " + SILICONFLOW_API_KEY,
                "Content-Type": "application/json"
            }
            async for token in try_provider_http_stream(TEXT_GEN_URL, payload, headers):
                yield token
    else:
        raise ValueError(f"不支持的模型: {model}")

async def generate_text_async(prompt, model):
    """Non-streaming version that returns the complete response"""
    final_result = ""
    async for token in generate_text_async_stream(prompt, model):
        final_result += token
    return {"content": final_result.strip(), "intermediate_reasoning": ""}

def generate_text(prompt, model=None):
    if model is None:
        model = "openai/o3-mini"  # Default to OpenAI o3-mini
    return asyncio.run(generate_text_async(prompt, model))

async def try_provider_http_stream(api_url, payload, headers):
    """Stream version that yields tokens"""
    final_result = ""
    accumulated_intermediate = ""
    first_chunk_received = False
    start_time = asyncio.get_running_loop().time()
    first_token_time = None
    token_count = 0

    async with httpx.AsyncClient(timeout=None) as client:
        async with client.stream("POST", api_url, json=payload, headers=headers) as response:
            debug_log("HTTP响应状态码: " + str(response.status_code) + " " + api_url)
            if response.status_code == 400:
                error_body = await response.aread()
                raise Exception("HTTP 400: " + error_body.decode())
            async for chunk in response.aiter_text():
                if not first_chunk_received:
                    elapsed = asyncio.get_running_loop().time() - start_time
                    if elapsed > 10:
                        raise TimeoutError("TTFT > 10 seconds")
                    first_chunk_received = True
                if not chunk:
                    continue
                for line in chunk.splitlines():
                    line = line.strip()
                    if line.startswith("data:"):
                        line = line[len("data:"):].strip()
                    if not line or line == "[DONE]" or "keep-alive" in line.lower():
                        continue
                    try:
                        delta = robust_json_parse(line)
                        for choice in delta.get("choices", []):
                            message_delta = choice.get("delta", {})
                            if message_delta.get("reasoning_content"):
                                accumulated_intermediate += message_delta["reasoning_content"]
                                debug_log(accumulated_intermediate, "intermediate")
                            if message_delta.get("content"):
                                token = message_delta["content"]
                                final_result += token
                                token_count += 1

                                # Record first token time and TTFT
                                if first_token_time is None:
                                    first_token_time = asyncio.get_running_loop().time()
                                    ttft = first_token_time - start_time
                                    debug_log(f"TTFT: {ttft:.3f}s", "log")

                                debug_log(final_result, "answer")
                                yield token
                    except Exception as e:
                        debug_log("Error parsing delta: " + str(e) + ". Full response: " + line)

    # Calculate and log metrics
    end_time = asyncio.get_running_loop().time()
    total_latency = end_time - start_time
    if first_token_time and token_count > 0:
        tpot = (end_time - first_token_time) / token_count
        debug_log(
            f"Metrics - Total tokens: {token_count}, TPOT: {tpot:.3f}s/token, Total latency: {total_latency:.3f}s", 
            "log"
        )
    else:
        debug_log(f"Metrics - Total latency: {total_latency:.3f}s", "log")

async def try_provider_http(api_url, payload, headers):
    """Non-stream version that returns the complete response"""
    final_result = ""
    accumulated_intermediate = ""
    async for token in try_provider_http_stream(api_url, payload, headers):
        final_result += token
    return {"content": final_result.strip(), "intermediate_reasoning": accumulated_intermediate}

async def try_provider_doubao_stream(prompt, model):
    payload = {
         "model": model,
         "messages": [
             {"role": "user", "content": prompt}
         ],
         "stream": True,
         "max_tokens": 8192,
    }
    headers = {
         "Authorization": "Bearer " + os.environ.get("ARK_API_KEY"),
         "Content-Type": "application/json"
    }
    api_url = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
    async for token in try_provider_http_stream(api_url, payload, headers):
        yield token

async def try_provider_doubao(prompt, model):
    """Non-stream version that returns the complete response"""
    final_result = ""
    async for token in try_provider_doubao_stream(prompt, model):
        final_result += token
    return {"content": final_result.strip(), "intermediate_reasoning": ""}

def generate_image(prompt):
    """
    调用图片生成 API，根据生成响应提取第一张图片的 URL。
    """
    payload = {
         "model": "deepseek-ai/Janus-Pro-7B",
         "prompt": prompt,
         "seed": random.randint(0, 9999999999)
    }
    headers = {
         "Authorization": "Bearer " + SILICONFLOW_API_KEY,
         "Content-Type": "application/json"
    }
    response = requests.post(IMAGE_GEN_URL, json=payload, headers=headers)
    if response.status_code == 200:
         result = response.json()
         images = result.get("images", [])
         if images and isinstance(images, list) and images[0].get("url"):
              return images[0]["url"]
         else:
              return "暂无图片"
    else:
         return "暂无图片"


def text_to_speech(text, voice="fishaudio/fish-speech-1.5:alex"):
    payload = {
        "model": "fishaudio/fish-speech-1.5",
        "input": text,
        "voice": voice,
        "response_format": "mp3",
        "sample_rate": 32000,
        "stream": True,
        "speed": 1,
        "gain": 0
    }
    headers = {
        "Authorization": "Bearer " + SILICONFLOW_API_KEY,
        "Content-Type": "application/json"
    }
    try:
        response = requests.post(TTS_URL, json=payload, headers=headers)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print("文字转语音 API 调用失败：", e)
        return "语音输出失败"


def transcribe_audio(file_path):
    files = {
        'file': ('audio.wav', open(file_path, 'rb'), 'audio/wav'),
        'model': (None, 'FunAudioLLM/SenseVoiceSmall')
    }
    headers = {
        "Authorization": "Bearer " + SILICONFLOW_API_KEY
    }
    try:
        response = requests.post(TRANSCRIPTION_URL, files=files, headers=headers)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print("语音转文字 API 调用失败：", e)
        return ""


def extract_novel_info(chapter_text):
    for story in stories_data.get("stories", []):
        if story.get("content") == chapter_text and "extracted_info" in story:
            debug_log("加载缓存提取信息")
            return story["extracted_info"]

    # 未找到缓存，则调用 AI 生成提取信息
    prompt = (
        "请从下面的章节内容中提取主要剧情背景和角色名称以及角色特征。"
        "请严格以 JSON 格式返回，不包含任何额外的说明文字。返回的 JSON 对象必须包含键 "
        "\"background\" 和 \"characters\"，其中 characters 为一个列表，每个元素包含 \"name\" 和 \"description\"。\n章节内容：\n"
        + chapter_text
    )
    result = generate_text(prompt, model="deepseek-ai/DeepSeek-R1")
    try:
        info = robust_json_parse(result["content"])
        # 保存角色提取过程的中间推理，将键名改为 extracted_intermediate_reasoning
        info["extracted_intermediate_reasoning"] = result["intermediate_reasoning"]
    except Exception as e:
        print("解析小说信息错误，错误：", e)
        print("解析小说信息响应：", result["content"])
        info = {
            "background": result["content"],
            "characters": [],
            "extracted_intermediate_reasoning": result["intermediate_reasoning"]
        }

    # 新增：如果该章节已存在，则更新；否则新增记录到 stories_data
    found = False
    for story in stories_data.get("stories", []):
        if story.get("content") == chapter_text:
            story["extracted_info"] = info
            found = True
            break
    if not found:
        new_story = {"content": chapter_text, "extracted_info": info}
        stories_data.setdefault("stories", []).append(new_story)

    with open(stories_path, "w", encoding="utf-8") as f:
        json.dump(stories_data, f, ensure_ascii=False, indent=2)

    return info


def generate_levels(chapter_text, extracted_info=None):
    # 检查 stories_data 中是否已有关卡生成信息（这里通过章节内容完全匹配）
    for story in stories_data.get("stories", []):
        if story.get("content") == chapter_text and "generated_levels" in story:
            debug_log("加载缓存关卡信息", "log")
            return story["generated_levels"]

    debug_log("开始生成关卡", "log")

    # 获取角色信息（若存在），并转换成 JSON 字符串附加到 prompt 中
    characters_info = ""
    if extracted_info and extracted_info.get("characters"):
         characters_info = "角色信息：" + json.dumps(extracted_info.get("characters"), ensure_ascii=False) + "\n"

    prompt = (
        "请根据下面的章节内容以及提供的角色信息设计出若干个关卡，每个关卡包含关卡描述和通关条件，每个关卡都用一段话描述。"
        "请严格以 JSON 数组格式返回，不包含任何额外的说明文字。数组中的每个元素应为一个对象，格式为 "
        "{\"level\": <数字>, \"description\": \"关卡剧情描述\", \"pass_condition\": \"通关条件描述\"}。\n" +
        characters_info +
        "章节内容：\n" + chapter_text
    )
    result = generate_text(prompt, model="deepseek-ai/DeepSeek-R1")
    try:
        levels = robust_json_parse(result["content"])
        if not isinstance(levels, list):
            levels = []
    except Exception as e:
        print("关卡生成失败，错误：", e)
        print("关卡生成响应：", result["content"])
        levels = []

    debug_log("关卡生成结果: " + json.dumps(levels, ensure_ascii=False), "final")

    # 将生成的关卡信息保存到对应的 story 对象中，方便下次直接加载而无需重新生成
    for story in stories_data.get("stories", []):
        if story.get("content") == chapter_text:
            story["generated_levels"] = levels
            break

    # 写回更新后的 stories.json 文件
    with open(stories_path, "w", encoding="utf-8") as f:
        json.dump(stories_data, f, ensure_ascii=False, indent=2)

    return levels


def evaluate_level(pass_condition, user_response, chat_history, overall_plot):
    prompt = (
        f"请严格根据以下关卡通关条件判断用户的回答是否满足要求。用户的回答必须明确体现出完成了通关条件中描述的任务。\n"
        f"关卡通关条件：{pass_condition}\n"
        f"用户回答：{user_response}\n"
        f"整体剧情：{overall_plot}\n"
        f"聊天记录：{chat_history}\n"
        "请仔细分析用户回答是否确实完成了通关条件要求的任务。如果用户回答过于简单或模糊，不能明确判断是否完成任务，则应该判定为未通过。\n"
        "请直接回复\"通过\"或\"未通过\"，不要包含其他内容。"
    )
    result = generate_text(prompt)
    # 严格匹配完整的"通过"二字
    if result["content"].strip() == "通过":
        return True, result["content"]
    else:
        return False, result["content"]


@app.route("/")
def index():
    return app.send_static_file("index.html")


@app.route("/create_game", methods=["POST"])
def create_game():
    try:
        data = request.get_json()
        chapter_text = data.get("chapter_text", "").strip()
        if not chapter_text:
            return jsonify({"error": "章节内容为空"}), 400

        # 提取小说信息（包含背景、角色、以及中间推理过程）
        extracted_info = extract_novel_info(chapter_text)
        # 生成关卡信息，同时传入提取后的角色信息
        levels = generate_levels(chapter_text, extracted_info)

        # 创建一个游戏会话，同时保存生成的角色信息到 session
        session_id = str(uuid.uuid4())
        sessions[session_id] = {
            "extracted_info": extracted_info,
            "characters": extracted_info.get("characters", []),
            "levels": levels,
            "current_level_index": 0,
            "chat_history": "",
            "overall_plot": extracted_info.get("background", "")
        }
        debug_log("游戏创建成功，会话ID: " + session_id, "log")
        # 判断该章节是否已在 stories_data 中（标记为已生成）
        story_generated = any(story.get("content") == chapter_text and "extracted_info" in story for story in stories_data.get("stories", []))
        return jsonify({
            "session_id": session_id,
            "characters": extracted_info.get("characters", []),
            "story_generated": story_generated,
            "message": "游戏创建成功"
        })
    except Exception as e:
        debug_log("Error in create_game: " + str(e), "log")
        return jsonify({"error": "游戏创建失败: " + str(e)}), 500


@app.route("/select_character", methods=["POST"])
def select_character():
    data = request.get_json()
    session_id = data.get("session_id")
    character_index = data.get("character_index")
    if session_id not in sessions:
        return jsonify({"error": "无效的 session_id"}), 400
    session = sessions[session_id]
    characters = session["characters"]
    if character_index is None or character_index < 0 or character_index >= len(characters):
        return jsonify({"error": "无效的角色选择"}), 400

    session["user_role"] = characters[character_index]["name"]
    return jsonify({"message": f"你选择的角色是 {session['user_role']}"})

@app.route("/get_level", methods=["POST"])
def get_level():
    data = request.get_json()
    session_id = data.get("session_id")
    if session_id not in sessions:
        return jsonify({"error": "无效的 session_id"}), 400

    session = sessions[session_id]
    current_index = session["current_level_index"]
    levels = session["levels"]
    
    if current_index >= len(levels):
        return jsonify({"message": "游戏结束", "game_over": True})

    level = levels[current_index]  # 先获取当前关卡
    
    # 获取 AI 角色
    user_role = session["user_role"]
    available_roles = [c for c in session["characters"] if c['name'] != user_role]
    ai_role = random.choice(available_roles)["name"] if available_roles else "旁白"
    
    # 检查是否已经生成过图片
    if "level_images" not in session:
        session["level_images"] = {}
    
    # 先检查 stories.json 中是否有缓存的图片
    for story in stories_data.get("stories", []):
        if "generated_levels" in story and len(story["generated_levels"]) > current_index:
            cached_level = story["generated_levels"][current_index]
            if "level_image" in cached_level and cached_level["level_image"].startswith("http"):
                level["level_image"] = cached_level["level_image"]
                session["level_images"][current_index] = cached_level["level_image"]
                return jsonify({
                    "level_number": level.get("level"),
                    "description": level.get("description"),
                    "pass_condition": level.get("pass_condition"),
                    "level_image": level["level_image"],
                    "ai_role": ai_role,
                    "game_over": False
                })
    
    # 如果已经生成过图片，直接返回缓存的图片 URL
    if current_index in session["level_images"]:
        level["level_image"] = session["level_images"][current_index]
    else:
        # 异步生成图片
        level_image_prompt = f"根据关卡描述生成一张背景图片的描述。描述：{level.get('description')}"
        level["level_image"] = "图片生成中..."
        import threading
        def generate_image_background(level, prompt, session, current_index):
             image_url = generate_image(prompt)
             level["level_image"] = image_url
             # 保存生成的图片 URL 到会话中
             session["level_images"][current_index] = image_url
             # 同时保存到 stories.json 中
             for story in stories_data.get("stories", []):
                 if "generated_levels" in story and len(story["generated_levels"]) > current_index:
                     story["generated_levels"][current_index]["level_image"] = image_url
                     with open(stories_path, "w", encoding="utf-8") as f:
                         json.dump(stories_data, f, ensure_ascii=False, indent=2)
             debug_log("图片生成完成，URL: " + image_url)
        threading.Thread(
            target=generate_image_background,
            args=(level, level_image_prompt, session, current_index),
            daemon=True
        ).start()

    return jsonify({
        "level_number": level.get("level"),
        "description": level.get("description"),
        "pass_condition": level.get("pass_condition"),
        "level_image": level["level_image"],
        "ai_role": ai_role,
        "game_over": False
    })


@app.route("/submit_response", methods=["POST"])
def submit_response():
    data = request.get_json()
    session_id = data.get("session_id")
    user_response = data.get("user_response", "")
    if session_id not in sessions:
        return jsonify({"error": "无效的 session_id"}), 400

    session = sessions[session_id]
    current_index = session["current_level_index"]
    levels = session["levels"]

    if current_index >= len(levels):
        return jsonify({"message": "游戏已经结束"}), 400
    
    level = levels[current_index]
    overall_plot = session["overall_plot"]
    chat_history = session["chat_history"]

    passed, evaluation_feedback = evaluate_level(
        level.get("pass_condition"),
        user_response,
        chat_history,
        overall_plot
    )
    
    # 记录用户回应到聊天历史
    session["chat_history"] += f"\n用户：{user_response}\n"
    session["chat_history"] += f"系统评价：{evaluation_feedback}\n"
    
    if passed:
        session["current_level_index"] += 1
        message = f"恭喜，你通过了关卡 {level.get('level')}！"
    else:
        message = "关卡未通过，请继续尝试。"

    return jsonify({
        "passed": passed,
        "evaluation_feedback": evaluation_feedback,
        "message": message,
        "current_level_index": session["current_level_index"],
        "total_levels": len(levels)
    })


@app.route("/random_story", methods=["GET"])
def random_story():
    if "stories" in stories_data and stories_data["stories"]:
        story = random.choice(stories_data["stories"])
        return jsonify(story)
    else:
        return jsonify({"error": "没有找到故事"}), 404


@app.route("/stream_level_dialogue", methods=["GET"])
def stream_level_dialogue():
    """
    流式返回当前关卡的 AI 对话，每个 token 以 SSE 格式发送。
    调用文本生成 API，并实时提取对话 token。
    """
    session_id = request.args.get("session_id")
    if not session_id or session_id not in sessions:
        return Response("data: 无效的 session_id\n\n", mimetype="text/event-stream")

    session = sessions[session_id]
    current_index = session["current_level_index"]
    levels = session["levels"]

    if current_index >= len(levels):
        return Response("data: 游戏结束\n\n", mimetype="text/event-stream")

    level = levels[current_index]
    overall_plot = session["overall_plot"]
    chat_history = session["chat_history"]
    user_role = session["user_role"]
    available_roles = [c for c in session["characters"] if c['name'] != user_role]
    ai_role = random.choice(available_roles)["name"] if available_roles else "旁白"

    dialogue_prompt = (
        f"请以{ai_role}的身份，根据整体剧情、关卡描述和聊天历史，对用户的回答进行回应并引导用户继续尝试。\n"
        f"整体剧情：{overall_plot}\n"
        f"关卡描述：{level.get('description')}\n"
        f"通关条件：{level.get('pass_condition')}\n"
        f"聊天历史：=== BEGIN CHAT HISTORY ===\n{chat_history if chat_history else '无'}\n=== END CHAT HISTORY ===\n"
        "请发表一句话。"
    )

    # 记录 AI 请求的 prompt 到调试日志
    debug_log("stream_level_dialogue:\n" + dialogue_prompt, "log")

    async def generate_stream():
        async for token in generate_text_async_stream(dialogue_prompt, "deepseek-ai/DeepSeek-V3"):
            yield f"data: {token}\n\n"

    gen = generate_stream()
    return Response(
         sync_generate_stream(gen),
         mimetype="text/event-stream",
         headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )

@app.route("/list_stories", methods=["GET"])
def list_stories():
    stories_list = []
    for story in stories_data.get("stories", []):
         content = story.get("content", "")
         title = story.get("title", "").strip() or "无标题"
         author = story.get("author", "").strip() or "未知作者"
         excerpt = content[:50] + ("..." if len(content) > 50 else "")
         stories_list.append({
             "id": len(stories_list),  # Use current index as id
             "title": title,
             "author": author,
             "excerpt": excerpt,
             "content": content,
             "generated": "extracted_info" in story
         })
    return jsonify(stories_list)


def sync_generate_stream(async_gen):
    """
    将异步生成器 async_gen 转换为同步生成器，以便通过 WSGI 服务器流式发送。
    """
    from queue import Queue
    import threading
    q = Queue()

    def run():
        async def main():
            async for token in async_gen:
                q.put(token)
        asyncio.run(main())
        q.put(None)

    threading.Thread(target=run, daemon=True).start()
    while True:
        token = q.get()
        if token is None:
            break
        yield token


@app.route("/update_chat_history", methods=["POST"])
def update_chat_history():
    data = request.get_json()
    session_id = data.get("session_id")
    message = data.get("message")
    
    if not session_id or session_id not in sessions:
        return jsonify({"error": "无效的 session_id"}), 400
        
    if not message:
        return jsonify({"error": "消息不能为空"}), 400
        
    session = sessions[session_id]
    session["chat_history"] += f"\n{message}\n"
    
    return jsonify({"message": "聊天历史更新成功"})


if __name__ == "__main__":
    app.run(debug=True, port=8888, threaded=True)
