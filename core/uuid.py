import os
import time
import uuid


def uuid7() -> uuid.UUID:
    """Generate a UUIDv7 (RFC 9562).

    Layout (128 bits): 48-bit unix timestamp in milliseconds, version 7,
    12 bits ``rand_a``, variant ``0b10``, and 62 bits ``rand_b``.

    Time-ordered primary keys reduce index fragmentation compared to UUIDv4.
    """
    unix_ts_ms = int(time.time() * 1000) & 0xFFFFFFFFFFFF  # 48 bits
    rand = os.urandom(10)  # 80 bits

    rand_a = (rand[0] << 4) | (rand[1] >> 4)  # 12 bits
    rand_b = int.from_bytes(rand[2:], "big") & ((1 << 62) - 1)  # 62 bits

    value = (unix_ts_ms << 80) | (7 << 76) | (rand_a << 64) | (2 << 62) | rand_b
    return uuid.UUID(int=value)
