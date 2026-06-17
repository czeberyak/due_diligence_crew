import os
from pathlib import Path
from dotenv import load_dotenv
from crewai import Crew, Process, LLM  # ✅ Импортируем LLM из CrewAI
from agents import DueDiligenceCrewAgents
from tasks import DueDiligenceCrewTasks

load_dotenv()

def run_due_diligence_council(document_path: str):
    """Запускает иерархический консилиум по одному документу"""
    
    print(f"--- [OpenRouter] Менеджер распределяет задачи для: {document_path} ---")
    
    # ✅ СОЗДАЕМ LLM ПРАВИЛЬНО через CrewAI
    llm = LLM(
        model="openai/gpt-4o-mini",  # Работает с OpenRouter
        # Альтернативы:
        # model="google/gemini-2.0-flash-exp:free"
        # model="microsoft/phi-3-mini-128k-instruct:free"
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENROUTER_API_KEY"),
        temperature=0.2,
        max_tokens=2000
    )
    
    # Создание агентов с ОТКЛЮЧЕННОЙ памятью
    agents_factory = DueDiligenceCrewAgents()
    
    auditor = agents_factory.safety_auditor_agent()
    auditor.llm = llm  # ✅ Передаем объект LLM
    auditor.memory = False
    auditor.allow_delegation = True
    
    engineer = agents_factory.process_engineer_agent()
    engineer.llm = llm
    engineer.memory = False
    engineer.allow_delegation = True
    
    investor = agents_factory.investment_analyst_agent()
    investor.llm = llm
    investor.memory = False
    investor.allow_delegation = False
    
    # Создание задач
    tasks_factory = DueDiligenceCrewTasks()
    
    safety_task = tasks_factory.safety_audit_task(auditor, document_path)
    process_task = tasks_factory.process_validation_task(engineer, document_path)
    final_task = tasks_factory.financial_translation_task(
        investor, 
        [safety_task, process_task]
    )
    
    # Формирование команды
    crew = Crew(
        agents=[auditor, engineer, investor],
        tasks=[safety_task, process_task, final_task],
        process=Process.hierarchical,
        manager_llm=llm,  # ✅ Передаем объект LLM (не строку!)
        verbose=True,
        memory=False
    )
    
    # Запуск
    result = crew.kickoff()
    return result

if __name__ == "__main__":
    print("=== Запуск Иерархического Консилиума на OpenRouter ===")
    
    doc = "data/01_raw/TEO_project_example.pdf"
    
    if not Path(doc).exists():
        print(f"❌ Файл не найден: {doc}")
        print("Создаю пустой файл для теста...")
        Path(doc).touch()
        print(f"✅ Создан: {doc}")
    
    try:
        final_report = run_due_diligence_council(doc)
        print("\n" + "="*60)
        print("🏆 ИТОГОВОЕ ЗАКЛЮЧЕНИЕ КОНСИЛИУМА:")
        print("="*60)
        print(final_report)
    except Exception as e:
        print(f"\n❌ Ошибка выполнения: {e}")