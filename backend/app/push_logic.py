from app.intelligence_ws import intelligence_manager


async def broadcast_push_ready_event(
    title: str,
    description: str,
    severity: str = "watchlist",
    event_type: str = "push_ready_event",
    payload: dict | None = None,
) -> None:
    await intelligence_manager.broadcast(
        {
            "type": event_type,
            "severity": severity,
            "title": title,
            "description": description,
            "payload": payload or {},
        }
    )
