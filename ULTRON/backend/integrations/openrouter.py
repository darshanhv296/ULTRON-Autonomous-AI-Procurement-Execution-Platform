"""
ULTRON OpenRouter & Groq AI Integration Module
Provides configurable model selection, structured JSON outputs, timeout protection,
and telemetry logging without fabricating AI responses.
"""
import json
import time
from typing import Any, Dict, Optional
import httpx

from backend.config import settings
from backend.database import db_manager


class OpenRouterClient:
    """Modular AI Client supporting OpenRouter and Groq with timeout protection."""

    OPENROUTER_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
    GROQ_ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"

    def get_status(self) -> Dict[str, Any]:
        if settings.is_groq_configured:
            return {
                "configured": True,
                "provider": "Groq",
                "model": settings.GROQ_MODEL,
                "fallback_provider": "OpenRouter" if settings.is_openrouter_configured else "Deterministic Python",
            }
        if settings.is_openrouter_configured:
            return {
                "configured": True,
                "provider": "OpenRouter",
                "model": settings.OPENROUTER_MODEL,
                "fallback_provider": "Deterministic Python",
            }
        return {
            "configured": False,
            "provider": "Deterministic Python Engine",
            "model": "ultron-deterministic-v4.8",
            "message": "Set OPENROUTER_API_KEY and OPENROUTER_MODEL in .env to enable live OpenRouter LLM calls.",
        }

    async def complete_json(
        self,
        system_prompt: str,
        user_prompt: str,
        agent_role: str = "ULTRON Reasoning Agent",
        objective_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Executes a structured JSON completion via Groq or OpenRouter with 12s timeout."""
        start_ts = time.perf_counter()

        # 1. Try Groq if configured
        if settings.is_groq_configured:
            try:
                async with httpx.AsyncClient(timeout=12.0) as client:
                    resp = await client.post(
                        self.GROQ_ENDPOINT,
                        headers={
                            "Authorization": f"Bearer {settings.GROQ_API_KEY}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": settings.GROQ_MODEL,
                            "messages": [
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": user_prompt},
                            ],
                            "temperature": 0.1,
                            "response_format": {"type": "json_object"},
                        },
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    content = data["choices"][0]["message"]["content"]
                    tokens = data.get("usage", {}).get("total_tokens", 0)
                    latency_ms = int((time.perf_counter() - start_ts) * 1000)
                    parsed = json.loads(content)
                    db_manager.log_ai_run(
                        provider="Groq",
                        model=settings.GROQ_MODEL,
                        agent_role=agent_role,
                        prompt_summary=user_prompt[:240],
                        response_summary=content[:240],
                        tokens_used=tokens,
                        latency_ms=latency_ms,
                        status="SUCCESS",
                        objective_id=objective_id,
                    )
                    return parsed
            except Exception as exc:
                db_manager.log_ai_run(
                    provider="Groq",
                    model=settings.GROQ_MODEL,
                    agent_role=agent_role,
                    prompt_summary=user_prompt[:240],
                    response_summary=f"Groq error: {str(exc)[:180]}",
                    tokens_used=0,
                    latency_ms=int((time.perf_counter() - start_ts) * 1000),
                    status="FAILED",
                    objective_id=objective_id,
                )

        # 2. Try OpenRouter if configured
        if settings.is_openrouter_configured:
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.post(
                        self.OPENROUTER_ENDPOINT,
                        headers={
                            "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                            "HTTP-Referer": settings.APP_URL,
                            "X-Title": settings.APP_NAME,
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": settings.OPENROUTER_MODEL,
                            "messages": [
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": user_prompt},
                            ],
                            "temperature": 0.1,
                        },
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    content = data["choices"][0]["message"]["content"]
                    tokens = data.get("usage", {}).get("total_tokens", 0)
                    latency_ms = int((time.perf_counter() - start_ts) * 1000)

                    # Extract JSON block if wrapped in markdown fences
                    clean_json = content.strip()
                    if "```json" in clean_json:
                        clean_json = clean_json.split("```json")[1].split("```")[0].strip()
                    elif "```" in clean_json:
                        clean_json = clean_json.split("```")[1].split("```")[0].strip()

                    parsed = json.loads(clean_json)
                    db_manager.log_ai_run(
                        provider="OpenRouter",
                        model=settings.OPENROUTER_MODEL,
                        agent_role=agent_role,
                        prompt_summary=user_prompt[:240],
                        response_summary=clean_json[:240],
                        tokens_used=tokens,
                        latency_ms=latency_ms,
                        status="SUCCESS",
                        objective_id=objective_id,
                    )
                    return parsed
            except Exception as exc:
                db_manager.log_ai_run(
                    provider="OpenRouter",
                    model=settings.OPENROUTER_MODEL,
                    agent_role=agent_role,
                    prompt_summary=user_prompt[:240],
                    response_summary=f"OpenRouter error: {str(exc)[:180]}",
                    tokens_used=0,
                    latency_ms=int((time.perf_counter() - start_ts) * 1000),
                    status="FAILED",
                    objective_id=objective_id,
                )

        return None

    async def chat_response(
        self, prompt: str, objective_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Handles AI Assistant operational queries with live database context."""
        metrics = db_manager.get_dashboard_metrics()
        sys_prompt = (
            "You are the ULTRON Autonomous Procurement & Governance Assistant. "
            "Respond concisely with accurate operational facts based on this live database telemetry: "
            f"{json.dumps(metrics)}"
        )
        start_ts = time.perf_counter()

        if settings.is_openrouter_configured or settings.is_groq_configured:
            endpoint = (
                self.GROQ_ENDPOINT if settings.is_groq_configured else self.OPENROUTER_ENDPOINT
            )
            api_key = (
                settings.GROQ_API_KEY
                if settings.is_groq_configured
                else settings.OPENROUTER_API_KEY
            )
            model = (
                settings.GROQ_MODEL
                if settings.is_groq_configured
                else settings.OPENROUTER_MODEL
            )
            provider = "Groq" if settings.is_groq_configured else "OpenRouter"
            try:
                async with httpx.AsyncClient(timeout=12.0) as client:
                    resp = await client.post(
                        endpoint,
                        headers={
                            "Authorization": f"Bearer {api_key}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": model,
                            "messages": [
                                {"role": "system", "content": sys_prompt},
                                {"role": "user", "content": prompt},
                            ],
                            "temperature": 0.2,
                        },
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    reply = data["choices"][0]["message"]["content"]
                    tokens = data.get("usage", {}).get("total_tokens", 0)
                    latency_ms = int((time.perf_counter() - start_ts) * 1000)
                    db_manager.log_ai_run(
                        provider=provider,
                        model=model,
                        agent_role="ULTRON Assistant",
                        prompt_summary=prompt[:200],
                        response_summary=reply[:200],
                        tokens_used=tokens,
                        latency_ms=latency_ms,
                        status="SUCCESS",
                        objective_id=objective_id,
                    )
                    return {
                        "reply": reply,
                        "provider": provider,
                        "model": model,
                        "tokens_used": tokens,
                        "latency_ms": latency_ms,
                    }
            except Exception as exc:
                err_note = f"{provider} API error ({str(exc)[:120]}). Using deterministic telemetry responder."
        else:
            err_note = "OpenRouter/Groq API key not configured in .env. Reporting deterministic database telemetry."

        reply = (
            f"[{err_note}]\n\n"
            f"• Total Objectives: {metrics['total_objectives']} ({metrics['completed_objectives']} Completed)\n"
            f"• Pending Governance Approvals: {metrics['pending_approvals']}\n"
            f"• Proposed Plan Pipeline: ${metrics['proposed_purchase_value']:.2f} USD\n"
            f"• Settled PayPal Sandbox Captures: ${metrics['completed_sandbox_payments_value']:.2f} USD "
            f"({metrics['completed_sandbox_payments_count']} verified captures)\n"
            f"• Database Status: {metrics['system_health']['database']}"
        )
        return {
            "reply": reply,
            "provider": "Deterministic Telemetry Engine",
            "model": "ultron-local-telemetry",
            "tokens_used": 0,
            "latency_ms": int((time.perf_counter() - start_ts) * 1000),
        }


openrouter_client = OpenRouterClient()
