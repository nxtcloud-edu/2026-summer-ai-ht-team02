import asyncio
import logging
from datetime import datetime

from app.models.database import SessionLocal
from app.models.location import EvacuationStatus
from app.services.location import check_stale_locations, detect_unconscious
from app.services.alert import create_unconscious_alert
from app.websocket_manager import manager
from app.config import settings

logger = logging.getLogger(__name__)


async def unconscious_check_loop():
    """주기적으로 의식 불명 감지 → 상태 전환 → WebSocket broadcast"""
    logger.info(
        "Unconscious checker started "
        f"(interval={settings.UNCONSCIOUS_CHECK_INTERVAL}s, "
        f"timeout={settings.UNCONSCIOUS_TIMEOUT_SECONDS}s)"
    )

    while True:
        await asyncio.sleep(settings.UNCONSCIOUS_CHECK_INTERVAL)

        db = SessionLocal()
        try:
            # Step 1: 위치 갱신 없는 유저 → is_moving=False
            stale_ids = check_stale_locations(
                db, timeout_seconds=settings.UNCONSCIOUS_TIMEOUT_SECONDS
            )

            # Step 2: is_moving=False인 유저 중 의식불명 판정
            for user_id in stale_ids:
                if detect_unconscious(user_id, db, settings.UNCONSCIOUS_TIMEOUT_SECONDS):
                    evac = (
                        db.query(EvacuationStatus)
                        .filter(EvacuationStatus.user_id == user_id)
                        .first()
                    )
                    if evac and evac.status != "unconscious":
                        # 상태 전환
                        evac.status = "unconscious"
                        evac.updated_at = datetime.utcnow()
                        db.commit()

                        # Alert 생성
                        create_unconscious_alert(
                            user_id=user_id,
                            floor_id=evac.last_floor_id,
                            x=evac.last_x,
                            y=evac.last_y,
                            reason="timeout",
                            db=db,
                        )

                        # WebSocket broadcast → 구조대 + 관리자
                        msg = {
                            "type": "unconscious_detected",
                            "user_id": user_id,
                            "floor_id": evac.last_floor_id,
                            "x": evac.last_x,
                            "y": evac.last_y,
                            "reason": "timeout",
                        }
                        await manager.broadcast_to_rescuers(msg)
                        await manager.broadcast_to_admins(msg)

                        logger.info(
                            f"User {user_id} detected as unconscious (timeout)"
                        )

        except Exception as e:
            logger.error(f"Unconscious checker error: {e}")
        finally:
            db.close()
