from enum import StrEnum


class EnvType(StrEnum):
    TESTING = "testing"
    PRODUCTION = "production"
    DEVELOPMENT_LOCAL = "development_local"
    TEST_LOCAL = "test_local"
