"""Constants for Taipit tests."""
from __future__ import annotations

MOCK_USERNAME = "test@example.com"
MOCK_PASSWORD = "testpassword"

MOCK_TOKEN_DATA = {
    "access_token": "mock_access_token_abc123",
    "refresh_token": "mock_refresh_token_xyz789",
    "expires_in": 3600,
    "expires_at": 1700003600,
}

MOCK_METER_ID = 12345

MOCK_METERS_RESPONSE = [
    {
        "id": MOCK_METER_ID,
        "serialNumber": "SN001",
        "name": "Test Meter",
        "meterTypeId": 16,
    },
]

MOCK_METER_INFO_RESPONSE = {
    "meterTypeId": 16,
    "serialNumber": "SN001",
    "name": "Test Meter",
}

MOCK_METER_READINGS_RESPONSE = {
    "economizer": {
        "lastReading": {
            "ts_tz": 1700000000,
            "energy_a": "1234.5",
            "energy_t1_a": "800.0",
            "energy_t2_a": "300.0",
            "energy_t3_a": None,
        },
        "timezone": 3,
        "addParams": {
            "values": {
                "i": ["5.0"],
                "u": ["230.0"],
                "cos": ["0.95"],
            }
        },
    },
    "meter": {"serialNumber": "SN001", "name": "Test Meter"},
    "controller": {"id": "aabbccddeeff", "signal": 15},
}

MOCK_THREE_PHASE_READINGS_RESPONSE = {
    "economizer": {
        "lastReading": {
            "ts_tz": 1700000000,
            "energy_a": "5000.0",
            "energy_t1_a": "3000.0",
            "energy_t2_a": "1500.0",
            "energy_t3_a": "500.0",
        },
        "timezone": 3,
        "addParams": {
            "values": {
                "i": ["5.0", "4.5", "4.8"],
                "u": ["230.0", "228.0", "231.0"],
                "cos": ["0.95", "0.90", "0.92"],
            }
        },
    },
    "meter": {"serialNumber": "SN002", "name": "Three Phase Meter"},
    "controller": {"id": "112233445566", "signal": 20},
}
