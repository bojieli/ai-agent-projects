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
API_TOKEN = os.environ.get("API_TOKEN")
if not API_TOKEN or API_TOKEN == "<token>":
    print("错误: API_TOKEN 环境变量未设置或未正确配置。请设置 API_TOKEN 环境变量！")
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
        # 尝试提取 JSON 部分：去除 markdown 格式（如 ```）和多余说明
        try:
            stripped = text.strip()
            if stripped.startswith("```"):
                const_lines = stripped.splitlines()
                if len(const_lines) >= 3:
                    stripped = "\n".join(const_lines[1:-1])
            if "{" in stripped and "}" in stripped:
                start = stripped.index("{")
                end = stripped.rindex("}") + 1
                possible_json = stripped[start:end]
                return json.loads(possible_json)
            elif "[" in stripped and "]" in stripped:
                start = stripped.index("[")
                end = stripped.rindex("]") + 1
                possible_json = stripped[start:end]
                return json.loads(possible_json)
        except Exception as e2:
            print("robust_json_parse failed:", e, e2)
        raise e

# 加载 stories.json 中的故事数据
stories_path = os.path.join(os.path.dirname(__file__), "stories.json")
with open(stories_path, "r", encoding="utf-8") as f:
    stories_data = json.load(f)

def generate_text(prompt, model=None):
    if model is None:
        model = "deepseek-ai/DeepSeek-V3"
    return asyncio.run(generate_text_async(prompt, model))

async def try_provider_http(api_url, payload, headers):
    final_result = ""
    accumulated_intermediate = ""
    first_chunk_received = False
    start_time = asyncio.get_running_loop().time()
    async with httpx.AsyncClient(timeout=None) as client:
        async with client.stream("POST", api_url, json=payload, headers=headers) as response:
            debug_log("HTTP响应状态码: " + str(response.status_code))
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
                                final_result += message_delta["content"]
                                debug_log(final_result, "final")
                    except Exception as e:
                        debug_log("Error parsing delta: " + str(e) + ". Full response: " + line)
    return {"content": final_result.strip(), "intermediate_reasoning": accumulated_intermediate}

async def try_provider_doubao(prompt):
    # 使用与 siliconflow 相同的 prompt 格式, 但采用豆包专用 model 和 API URL
    payload = {
         "model": "ep-20250206131705-gtthc",
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
    # 调用异步 HTTP 请求接口，TTFT 检查由 try_provider_http 处理
    result = await try_provider_http(api_url, payload, headers)
    debug_log("Doubao provider succeeded", "log")
    return result

async def generate_text_async(prompt, model):
    # 若请求 deepseek R1（初始生成），采用多供应商顺序
    if model == "deepseek-ai/DeepSeek-R1":
         providers = ["doubao", "siliconflow", "deepseek_official"]
         last_exception = None
         for provider in providers:
             try:
                 if provider == "doubao":
                     result = await try_provider_doubao(prompt)
                     debug_log("Doubao provider succeeded", "log")
                     return result
                 elif provider == "siliconflow":
                     # siliconflow 使用默认 TEXT_GEN_URL 与 API_TOKEN
                     payload = {
                         "model": "deepseek-ai/DeepSeek-R1",
                         "messages": [{"role": "user", "content": prompt}],
                         "stream": True,
                         "max_tokens": 8192,
                     }
                     headers = {
                         "Authorization": "Bearer " + API_TOKEN,
                         "Content-Type": "application/json"
                     }
                     result = await try_provider_http(TEXT_GEN_URL, payload, headers)
                     debug_log("Siliconflow provider succeeded", "log")
                     return result
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
                     result = await try_provider_http("https://api.deepseek.com/v1/chat/completions", payload, headers)
                     debug_log("DeepSeek official provider succeeded", "log")
                     return result
             except Exception as e:
                 last_exception = e
                 debug_log(f"Provider {provider} failed: {e}", "log")
         raise Exception("All providers failed for deepseek-ai/DeepSeek-R1: " + str(last_exception))
    else:
         # 对于其它模型（如 deepseek-ai/DeepSeek-V3），直接走 siliconflow
         payload = {
             "model": model,
             "messages": [{"role": "user", "content": prompt}],
             "stream": True,
             "max_tokens": 8192,
         }
         headers = {
             "Authorization": "Bearer " + API_TOKEN,
             "Content-Type": "application/json"
         }
         return await try_provider_http(TEXT_GEN_URL, payload, headers)


def generate_image(prompt, seed=4999999999):
    payload = {
        "model": "deepseek-ai/Janus-Pro-7B",
        "prompt": prompt,
        "seed": seed
    }
    headers = {
        "Authorization": "Bearer " + API_TOKEN,
        "Content-Type": "application/json"
    }
    debug_log("发送图片生成请求: " + json.dumps(payload, ensure_ascii=False))
    try:
        response = requests.post(IMAGE_GEN_URL, json=payload, headers=headers)
        debug_log("收到图片生成响应: " + response.text)
        response.raise_for_status()
        data = response.json()
        image_url = data.get("url", "暂无图片")
        debug_log("生成图片 URL: " + image_url)
        return image_url
    except Exception as e:
        debug_log("图片生成 API 调用失败: " + str(e))
        print("图片生成 API 调用失败：", e)
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
        "Authorization": "Bearer " + API_TOKEN,
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
        "Authorization": "Bearer " + API_TOKEN
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
        f"请根据以下关卡通关条件判断用户的回答是否满足要求。\n"
        f"关卡通关条件：{pass_condition}\n"
        f"用户回答：{user_response}\n"
        f"整体剧情：{overall_plot}\n"
        f"聊天记录：{chat_history}\n"
        "请直接回复\"通过\"或\"未通过\"。"
    )
    result = generate_text(prompt)
    if "通过" in result["content"]:
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

    level = levels[current_index]
    overall_plot = session["overall_plot"]
    chat_history = session["chat_history"]
    user_role = session["user_role"]

    available_roles = [c for c in session["characters"] if c['name'] != user_role]
    ai_role = random.choice(available_roles)["name"] if available_roles else "旁白"
    
    dialogue_prompt = (
        f"请以{ai_role}的身份，根据整体剧情和关卡描述进行发言，引导用户进行互动。\n"
        f"整体剧情：{overall_plot}\n关卡描述：{level.get('description')}\n"
        "请发表一句话。"
    )
    ai_dialogue = generate_text(dialogue_prompt)
    
    level_image_prompt = f"根据关卡描述生成一张背景图片的描述。描述：{level.get('description')}"
    level_image = generate_image(level_image_prompt)
    
    return jsonify({
        "level_number": level.get("level"),
        "description": level.get("description"),
        "pass_condition": level.get("pass_condition"),
        "level_image": level_image,
        "ai_role": ai_role,
        "ai_dialogue": ai_dialogue,
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
    
    session["chat_history"] += (
        f"\n关卡 {level.get('level')} AI发言：{evaluation_feedback}\n"
        f"用户响应：{user_response}\n"
    )
    
    if passed:
        session["current_level_index"] += 1
        message = f"恭喜，你通过了关卡 {level.get('level')}！"
    else:
        message = "关卡未通过，请重新尝试。"

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


if __name__ == "__main__":
    app.run(debug=True, port=8888, threaded=True) 