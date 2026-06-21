import os
import sys
import argparse
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from crewai import Crew, Process, LLM
from agents import DueDiligenceCrewAgents
from tasks import DueDiligenceCrewTasks
from export_report import export_report  # ← НОВЫЙ ИМПОРТ

load_dotenv()

def run_due_diligence_council(document_path: str):
    """Запускает иерархический консилиум по одному документу"""
    print(f"\n{'='*60}")
    print(f"🚀 ЗАПУСК КОНСИЛИУМА ДЛЯ: {document_path}")
    print(f"{'='*60}\n")

    # 1. Инициализация LLM через OpenRouter
    llm = LLM(
        model="openrouter/openai/gpt-oss-120b:free", 
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENROUTER_API_KEY"),
        temperature=0.2,
        max_tokens=4000
    )

    # Создание агентов
    agents_factory = DueDiligenceCrewAgents()
    auditor = agents_factory.safety_auditor_agent()
    auditor.llm = llm
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
        manager_llm=llm,
        verbose=True,
        memory=False
    )

    # Запуск
    result = crew.kickoff()
    return result

def save_report(doc_name: str, report_content: str):
    """Сохраняет отчет в Markdown, PDF и DOCX"""
    output_dir = Path("data/02_processed")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_doc_name = Path(doc_name).stem.replace(" ", "_")
    base_path = output_dir / f"DD_Report_{safe_doc_name}_{timestamp}"
    
    # Экспорт во все форматы
    print(f"\n📄 Сохранение отчёта в форматах: Markdown, PDF, DOCX...")
    results = export_report(report_content, str(base_path), formats=['md', 'pdf', 'docx'])
    
    for fmt, path in results.items():
        if path:
            print(f"  ✅ {fmt.upper()}: {path}")
        else:
            print(f"  ⚠️ {fmt.upper()}: ошибка экспорта")
    
    return results

def main():
    parser = argparse.ArgumentParser(description="Запуск Due Diligence консилиума")
    parser.add_argument(
        "--file", 
        type=str, 
        help="Путь к конкретному PDF-файлу для анализа",
        default=None
    )
    parser.add_argument(
        "--batch", 
        action="store_true", 
        help="Запустить анализ всех PDF-файлов в папке data/01_raw/TEO/"
    )

    args = parser.parse_args()

    # Режим 1: Анализ конкретного файла
    if args.file:
        doc_path = Path(args.file)
        if not doc_path.exists():
            print(f"❌ Файл не найден: {doc_path}")
            return
        report = run_due_diligence_council(str(doc_path))
        save_report(doc_path.name, report.raw)

    # Режим 2: Пакетный анализ всех файлов в папке
    elif args.batch:
        batch_dir = Path("data/01_raw/TEO")
        if not batch_dir.exists():
            print(f"❌ Папка не найдена: {batch_dir}")
            print("Создаю папку...")
            batch_dir.mkdir(parents=True)
            return

        pdf_files = list(batch_dir.glob("*.pdf"))
        if not pdf_files:
            print(f"⚠️ В папке {batch_dir} нет PDF-файлов.")
            return

        print(f"📂 Найдено {len(pdf_files)} файлов для анализа.")
        
        for pdf_file in pdf_files:
            try:
                report = run_due_diligence_council(str(pdf_file))
                save_report(pdf_file.name, report.raw)
            except Exception as e:
                print(f"\n❌ Ошибка при анализе {pdf_file.name}: {e}")

    # Режим 3: По умолчанию (если аргументы не переданы)
    else:
        print("️ Аргументы не указаны. Используйте --file <путь> или --batch")
        print("Пример: python src/main.py --file data/01_raw/TEO/TEO_SES.pdf")
        print("Пример: python src/main.py --batch")

if __name__ == "__main__":
    main()