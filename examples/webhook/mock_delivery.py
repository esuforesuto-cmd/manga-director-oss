"""Exercise the notification boundary without sending a network webhook."""

import logging

from manga_director.notifications import (
    MockNotificationProvider,
    NotificationMessage,
    NotificationService,
)

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)

provider = MockNotificationProvider()
result = NotificationService(provider).send(
    NotificationMessage(event_type="PageApproved", title="Page approved", body="Page 1")
)
LOGGER.info("delivered=%s event=%s", result.success, provider.sent[0].event_type)
