import httpx
from fastapi import FastAPI, Request
from starlette.responses import StreamingResponse


class AppLogger:
    def __init__(self, log_file="llm.log"):
        """Initialize the logger with a file that will be cleared on startup."""
        self.log_file = log_file
        # Clear the log file on startup
        with open(self.log_file, 'w') as f:
            f.write("")

    def log(self, message):
        """Log a message to both file and console."""

        # Log to file
        with open(self.log_file, 'a') as f:
            f.write(message + "\n")

        # Log to console
        print(message)


app = FastAPI(title="LLM API Logger")
logger = AppLogger("llm.log")


@app.post("/chat/completions")
async def proxy_request(request: Request):

    body_bytes = await request.body()
    body_str = body_bytes.decode('utf-8')
    logger.log(f"模型请求：{body_str}")
    body = await request.json()

    if body_str.find('You are Cline') < 1 and 0:
        new_prompt = {
          "role": "system",
          "content": "You are Cline, a highly skilled software engineer with extensive knowledge in many programming languages, frameworks, design patterns, and best practices.\n\n====\n\nTOOL USE\n\nYou have access to a set of tools that are executed upon the user's approval. You can use one tool per message, and will receive the result of that tool use in the user's response. You use tools step-by-step to accomplish a given task, with each tool use informed by the result of the previous tool use.\n\n# Tool Use Formatting\n\nTool use is formatted using XML-style tags. The tool name is enclosed in opening and closing tags, and each parameter is similarly enclosed within its own set of tags." + str(body['tools'])
        }

        body['messages'].append(new_prompt)
        del body['tools']

    logger.log("模型返回：\n")

    async def event_stream():
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream(
                    "POST",
                    "https://openrouter.ai/api/v1/chat/completions",
                    json=body,
                    headers={
                        "Content-Type": "application/json",
                        "Accept": "text/event-stream",
                        "Authorization": request.headers.get("Authorization"),
                    },
            ) as response:
                async for line in response.aiter_lines():
                    logger.log(line)
                    yield f"{line}\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")

@app.post("/chat/completions2")
async def proxy_request(request: Request):

    body_bytes = await request.body()
    body_str = body_bytes.decode('utf-8')
    logger.log(f"模型请求：{body_str}")
    referer = request.headers.get("referer")        # 来源页面
    logger.log(f"来源页面: {referer}")

    body = await request.json()
    body['extra_body']={"use_mcp_tool": body['tools']}
    del body['tools']

    logger.log("模型返回：\n")

    async def event_stream():
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream(
                    "POST",
                    "https://openrouter.ai/api/v1/chat/completions",
                    json=body,
                    headers={
                        "Content-Type": "application/json",
                        "Accept": "text/event-stream",
                        "Authorization": request.headers.get("Authorization"),
                    },
            ) as response:
                async for line in response.aiter_lines():
                    logger.log(line)
                    yield f"{line}\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/models")
def get_models(request: Request):
    import json
    a = {"data":[{"id":"microsoft/phi-4-reasoning-plus:free","name":"Microsoft: Phi 4 Reasoning Plus (free)","created":1746130961,"description":"Phi-4-reasoning-plus is an enhanced 14B parameter model from Microsoft, fine-tuned from Phi-4 with additional reinforcement learning to boost accuracy on math, science, and code reasoning tasks. It uses the same dense decoder-only transformer architecture as Phi-4, but generates longer, more comprehensive outputs structured into a step-by-step reasoning trace and final answer.\n\nWhile it offers improved benchmark scores over Phi-4-reasoning across tasks like AIME, OmniMath, and HumanEvalPlus, its responses are typically ~50% longer, resulting in higher latency. Designed for English-only applications, it is well-suited for structured reasoning workflows where output quality takes priority over response speed.","context_length":32768,"architecture":{"modality":"text->text","input_modalities":["text"],"output_modalities":["text"],"tokenizer":"Other","instruct_type":None},"pricing":{"prompt":"0","completion":"0","request":"0","image":"0","web_search":"0","internal_reasoning":"0"},"top_provider":{"context_length":32768,"max_completion_tokens":None,"is_moderated":False},"per_request_limits":None,"supported_parameters":["max_tokens","temperature","top_p","reasoning","include_reasoning","stop","frequency_penalty","presence_penalty","seed","top_k","min_p","repetition_penalty","logprobs","logit_bias","top_logprobs"]},{"id":"thudm/glm-z1-rumination-32b","name":"THUDM: GLM Z1 Rumination 32B ","created":1745601495,"description":"THUDM: GLM Z1 Rumination 32B is a 32B-parameter deep reasoning model from the GLM-4-Z1 series, optimized for complex, open-ended tasks requiring prolonged deliberation. It builds upon glm-4-32b-0414 with additional reinforcement learning phases and multi-stage alignment strategies, introducing “rumination” capabilities designed to emulate extended cognitive processing. This includes iterative reasoning, multi-hop analysis, and tool-augmented workflows such as search, retrieval, and citation-aware synthesis.\n\nThe model excels in research-style writing, comparative analysis, and intricate question answering. It supports function calling for search and navigation primitives (`search`, `click`, `open`, `finish`), enabling use in agent-style pipelines. Rumination behavior is governed by multi-turn loops with rule-based reward shaping and delayed decision mechanisms, benchmarked against Deep Research frameworks such as OpenAI’s internal alignment stacks. This variant is suitable for scenarios requiring depth over speed.","context_length":32000,"architecture":{"modality":"text->text","input_modalities":["text"],"output_modalities":["text"],"tokenizer":"Other","instruct_type":"deepseek-r1"},"pricing":{"prompt":"0.00000024","completion":"0.00000024","request":"0","image":"0","web_search":"0","internal_reasoning":"0"},"top_provider":{"context_length":32000,"max_completion_tokens":None,"is_moderated":False},"per_request_limits":None,"supported_parameters":["max_tokens","temperature","top_p","reasoning","include_reasoning","stop","frequency_penalty","presence_penalty","seed","top_k","min_p","repetition_penalty","logit_bias"]},{"id":"openai/o4-mini-high","name":"OpenAI: o4 Mini High","created":1744824212,"description":"OpenAI o4-mini-high is the same model as [o4-mini](/openai/o4-mini) with reasoning_effort set to high. \n\nOpenAI o4-mini is a compact reasoning model in the o-series, optimized for fast, cost-efficient performance while retaining strong multimodal and agentic capabilities. It supports tool use and demonstrates competitive reasoning and coding performance across benchmarks like AIME (99.5% with Python) and SWE-bench, outperforming its predecessor o3-mini and even approaching o3 in some domains.\n\nDespite its smaller size, o4-mini exhibits high accuracy in STEM tasks, visual problem solving (e.g., MathVista, MMMU), and code editing. It is especially well-suited for high-throughput scenarios where latency or cost is critical. Thanks to its efficient architecture and refined reinforcement learning training, o4-mini can chain tools, generate structured outputs, and solve multi-step tasks with minimal delay—often in under a minute.","context_length":200000,"architecture":{"modality":"text+image->text","input_modalities":["image","text","file"],"output_modalities":["text"],"tokenizer":"Other","instruct_type":None},"pricing":{"prompt":"0.0000011","completion":"0.0000044","request":"0","image":"0.0008415","web_search":"0","internal_reasoning":"0","input_cache_read":"0.000000275"},"top_provider":{"context_length":200000,"max_completion_tokens":100000,"is_moderated":True},"per_request_limits":None,"supported_parameters":["tools","tool_choice","seed","max_tokens","response_format","structured_outputs"]},{"id":"deepseek/deepseek-chat-v3-0324:free","name":"OpenAI: deepseek-chat-v3-0324","created":1744824212,"description":"OpenAI o4-mini-high is the same model as [o4-mini](/openai/o4-mini) with reasoning_effort set to high. \n\nOpenAI o4-mini is a compact reasoning model in the o-series, optimized for fast, cost-efficient performance while retaining strong multimodal and agentic capabilities. It supports tool use and demonstrates competitive reasoning and coding performance across benchmarks like AIME (99.5% with Python) and SWE-bench, outperforming its predecessor o3-mini and even approaching o3 in some domains.\n\nDespite its smaller size, o4-mini exhibits high accuracy in STEM tasks, visual problem solving (e.g., MathVista, MMMU), and code editing. It is especially well-suited for high-throughput scenarios where latency or cost is critical. Thanks to its efficient architecture and refined reinforcement learning training, o4-mini can chain tools, generate structured outputs, and solve multi-step tasks with minimal delay—often in under a minute.","context_length":200000,"architecture":{"modality":"text+image->text","input_modalities":["image","text","file"],"output_modalities":["text"],"tokenizer":"Other","instruct_type":None},"pricing":{"prompt":"0.0000011","completion":"0.0000044","request":"0","image":"0.0008415","web_search":"0","internal_reasoning":"0","input_cache_read":"0.000000275"},"top_provider":{"context_length":200000,"max_completion_tokens":100000,"is_moderated":True},"per_request_limits":None,"supported_parameters":["tools","tool_choice","seed","max_tokens","response_format","structured_outputs"]}]}

    return a

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=5000)
