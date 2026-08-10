"""
OpenAI API를 활용한 자연어 경로 안내 생성

- 경로 좌표 + 화재 위치 + 층 정보를 입력으로 받아
- 사용자에게 보여줄 간결한 방향 안내를 생성한다.
- API 장애 시 로컬 direction.py fallback 사용
"""

import json
import logging
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """당신은 건물 내 화재 대피 안내 시스템입니다.
사용자의 현재 위치와 대피 경로 좌표를 받아 간결한 방향 안내를 생성합니다.

규칙:
1. 방향은 "straight", "left", "right", "slight_left", "slight_right", "back" 중 하나
2. 거리는 미터(m) 단위 정수로 반올림
3. 위험 구역 근처일 경우 경고 메시지 포함
4. 한 번에 다음 1~2 구간만 안내 (너무 많은 정보 금지)
5. 한국어로 안내

반드시 아래 JSON 형식으로만 응답하세요:
{
  "direction": "straight|left|right|slight_left|slight_right|back",
  "distance_m": <정수>,
  "instruction": "<한국어 안내 문장>",
  "warning": "<위험 경고 메시지 또는 null>",
  "next_landmark": "<다음 랜드마크 이름 또는 null>"
}"""


async def generate_ai_guidance(
    current_x: float,
    current_y: float,
    path_coords: list,
    fire_positions: list,
    floor_name: str = "알 수 없음",
) -> Optional[dict]:
    """
    OpenAI API를 호출하여 자연어 방향 안내 생성

    Returns:
        AI 생성 안내 dict 또는 None (API 실패 시)
    """
    if not settings.OPENAI_API_KEY:
        logger.warning("OPENAI_API_KEY not configured, skipping AI guidance")
        return None

    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

        # 다음 3개 waypoint만 전달 (토큰 절약)
        upcoming = path_coords[:3]
        waypoints_str = "\n".join(
            f"  - ({p['x']:.0f}, {p['y']:.0f}) [{p.get('node_type', 'path')}] {p.get('label', '')}"
            for p in upcoming
        )

        fires_str = "없음"
        if fire_positions:
            fires_str = "\n".join(
                f"  - ({f['x']:.0f}, {f['y']:.0f})" for f in fire_positions[:5]
            )

        user_message = f"""현재 위치: ({current_x:.0f}, {current_y:.0f})
층: {floor_name}

경로 waypoints (다음 구간):
{waypoints_str}

활성 화재 위치:
{fires_str}

현재 위치에서 다음 waypoint까지의 방향 안내를 생성해주세요."""

        response = await client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=200,
        )

        content = response.choices[0].message.content
        result = json.loads(content)

        # 필수 필드 검증
        if "direction" not in result or "instruction" not in result:
            logger.warning("AI response missing required fields: %s", content)
            return None

        return {
            "direction": result.get("direction", "straight"),
            "distance_m": result.get("distance_m", 0),
            "instruction": result.get("instruction", ""),
            "warning": result.get("warning"),
            "next_landmark": result.get("next_landmark"),
        }

    except ImportError:
        logger.error("openai package not installed")
        return None
    except Exception as e:
        logger.error("AI guidance generation failed: %s", str(e))
        return None
