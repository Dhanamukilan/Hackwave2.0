# llm
LOCAL LLM client (per your choice): wraps a local model server, e.g. Ollama (llama3.1 / qwen2.5 / mistral) via its OpenAI-compatible /v1/chat/completions endpoint, or vLLM/text-generation-inference if you prefer higher throughput. Only ever receives retrieved/structured evidence, never raw multi-MB logs.
