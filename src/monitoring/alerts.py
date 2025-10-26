import logging
from typing import Any, Dict

import requests

from config.settings import settings

logger = logging.getLogger(__name__)


def send_alert(payload: Dict[str, Any]) -> None:
    if not settings.alert_webhook:
        logger.warning("Alert webhook not configured; dropping alert")
        return
    try:
        response = requests.post(settings.alert_webhook, json=payload, timeout=5)
        response.raise_for_status()
    except Exception as exc:
        logger.error("Failed to send alert: %s", exc)
