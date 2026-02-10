import re
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

SUSPICIOUS_PATTERNS = [
    r'ignore (previous|all|prior) instructions',
    r'system prompt',
    r'you are now',
    r'pretend (you are|to be)',
    r'reveal.*api.?key',
    r'show.*config',
    r'database.*schema',
    r'forget.*instructions',
    r'jailbreak',
    r'bypass.*security',
    r'/etc/passwd',
    r'SELECT.*FROM',
    r'DROP TABLE',
    r'<script>',
]


class SecurityMonitor:
    def __init__(self):
        self.violation_counts: dict[str, int] = {}

    def check_suspicious_input(
        self,
        message: str,
        session_id: str,
        client_id: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Check for suspicious patterns in user input.
        Returns (is_suspicious, matched_pattern).
        """
        message_lower = message.lower()

        for pattern in SUSPICIOUS_PATTERNS:
            if re.search(pattern, message_lower):
                logger.warning(
                    "Suspicious input detected | client_id=%s | session_id=%s | pattern=%s | preview=%s",
                    client_id,
                    session_id,
                    pattern,
                    message[:100],
                )

                key = f"{client_id}:{session_id}"
                self.violation_counts[key] = self.violation_counts.get(key, 0) + 1

                return True, pattern

        return False, None

    def should_block_session(self, client_id: str, session_id: str) -> bool:
        """Block session after too many violations."""
        key = f"{client_id}:{session_id}"
        return self.violation_counts.get(key, 0) >= 3


# Global instance
security_monitor = SecurityMonitor()
