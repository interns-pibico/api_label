"""Text translation via MyMemory public API (free, no key required)."""

import asyncio

import httpx

_MYMEMORY_URL = "https://api.mymemory.translated.net/get"
_MAX_CHARS = 450  # MyMemory free tier limit per request


async def _translate_chunk(client: httpx.AsyncClient, chunk: str, langpair: str) -> str:
    resp = await client.get(
        _MYMEMORY_URL,
        params={"q": chunk, "langpair": langpair},
        timeout=8.0,
    )
    resp.raise_for_status()
    data = resp.json()
    translated = data.get("responseData", {}).get("translatedText", "")
    if translated and data.get("responseStatus") == 200:
        return translated
    return chunk


async def translate_text(text: str, source_lang: str, target_lang: str) -> str:
    """Translate text using MyMemory. Falls back to original on any error."""
    if not text or source_lang == target_lang:
        return text

    langpair = f"{source_lang}|{target_lang}"

    # Split into comma-separated chunks if text exceeds limit
    if len(text) <= _MAX_CHARS:
        chunks = [text]
    else:
        chunks = []
        current = ""
        for part in text.split(","):
            candidate = f"{current}, {part.strip()}" if current else part.strip()
            if len(candidate) > _MAX_CHARS:
                if current:
                    chunks.append(current)
                current = part.strip()
            else:
                current = candidate
        if current:
            chunks.append(current)

    try:
        async with httpx.AsyncClient() as client:
            results = await asyncio.gather(
                *[_translate_chunk(client, chunk, langpair) for chunk in chunks],
                return_exceptions=True,
            )
        parts = []
        for result in results:
            if isinstance(result, Exception):
                return text  # any failure → return original
            parts.append(result)
        return ", ".join(parts) if len(parts) > 1 else parts[0]
    except Exception:
        return text


# Fields in regulatory_data that contain translatable user text
_TRANSLATABLE_FIELDS = ["ingredients", "allergens", "best_before", "storage_conditions"]


async def translate_regulatory_data(rd: dict, source_lang: str, target_lang: str) -> dict:
    """Return a copy of regulatory_data with text fields translated."""
    if source_lang == target_lang:
        return rd

    fields = {f: rd[f] for f in _TRANSLATABLE_FIELDS if rd.get(f) and isinstance(rd[f], str)}
    if not fields:
        return rd

    results = await asyncio.gather(
        *[translate_text(v, source_lang, target_lang) for v in fields.values()],
        return_exceptions=True,
    )

    translated = dict(rd)
    for field, result in zip(fields.keys(), results):
        if not isinstance(result, Exception):
            translated[field] = result

    return translated
