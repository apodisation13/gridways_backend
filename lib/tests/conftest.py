import os
print(f"\n🔍 Loading conftest.py from: {os.path.abspath(__file__)}")


# Переопределяем конфиг для тестов
os.environ["CONFIG"] = "test_local"
print("STR14 SET CONFIG LIB")

from lib.tests.fixtures import *
