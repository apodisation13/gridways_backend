import os
print(f"\n🔍 Loading conftest.py from: {os.path.abspath(__file__)}")

# # Переопределяем конфиг для тестов
# os.environ["CONFIG"] = "test_local"
# print("STR6 set config cron")

from lib.tests.fixtures import *
