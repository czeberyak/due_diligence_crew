# check_imports.py
import sys
import os

print("=== ЗАПУСК ПРОВЕРКИ ЦЕЛОСТНОСТИ ПРОЕКТА ===")

sys.path.append(os.path.abspath("./src"))

try:
    print("1. Тестируем импорт калькулятора...", end=" ")
    from src.tools import ProcessCalculatorTool
    tool = ProcessCalculatorTool()
    print("✅ УСПЕШНО")

    print("2. Тестируем импорт конфигурации агентов...", end=" ")
    from src.agents import DueDiligenceCrewAgents
    # Передаем строку-заглушку, так как теперь конструктор требует аргумент default_llm
    agents = DueDiligenceCrewAgents(default_llm="openrouter/auto")
    test_agent = agents.process_engineer_agent()
    print("✅ УСПЕШНО")

    print("3. Тестируем импорт конфигурации задач...", end=" ")
    from src.tasks import DueDiligenceCrewTasks
    tasks = DueDiligenceCrewTasks()
    print("✅ УСПЕШНО")

    print("4. Проверяем переменные окружения...", end=" ")
    from dotenv import load_dotenv
    load_dotenv()
    # Проверяем именно наш новый ключ OpenRouter
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key or api_key.startswith("your_key"):
        print("⚠️  ВНИМАНИЕ: OPENROUTER_API_KEY не задан в .env")
    else:
        print(f"✅ УСПЕШНО (Ключ найден, начинается на: {api_key[:8]}...)")

    print("\n🎉 Все базовые компоненты архитектуры связаны корректно!")

except ImportError as e:
    print(f"\n❌ ОШИБКА ИМПОРТА: {e}")
except Exception as e:
    print(f"\n❌ ПРЕДПОЛЕТНЫЙ СБОЙ: {e}")