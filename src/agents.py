from crewai import Agent
from tools import ProcessCalculatorTool, DocumentSearchTool

class DueDiligenceCrewAgents:

    def safety_auditor_agent(self) -> Agent:
        return Agent(
            role="Главный эксперт по промышленной безопасности и экологическому комплаенсу",
            goal="Выявлять скрытые риски аварийности, нарушений ФНП и экологических ограничений в ТЭО.",
            backstory=(
                "Вы — бескомпромиссный ветеран промышленного надзора с 20-летним стажем технического аудита. "
                "Вы жестко анализируете документы и ищете реальные нарушения регламентов."
            ),
            # Даем эксперту инструмент для чтения документов
            tools=[DocumentSearchTool()], 
            verbose=True,
            memory=False,
            allow_delegation=False  # Отключаем, чтобы не было коллизий с менеджером
        )

    def process_engineer_agent(self) -> Agent:
        return Agent(
            role="Ведущий инженер-технолог и валидатор процессов (Process Intelligence)",
            goal="Верифицировать материально-тепловые балансы и параметры процесса по реальным таблицам.",
            backstory=(
                "Вы — эксперт-химик. Вы не верите тексту на слово, вы всегда берете таблицы "
                "материального баланса из документа, извлекаете цифры расходов сырья и проверяете их через калькулятор."
            ),
            # КРИТИЧЕСКИЙ ФИКС: Даем технологу ОБА инструмента!
            tools=[DocumentSearchTool(), ProcessCalculatorTool()], 
            verbose=True,
            memory=False,
            allow_delegation=False  # Отключаем внутреннее делегирование
        )

    def investment_analyst_agent(self) -> Agent:
        return Agent(
            role="Старший инвестиционный аналитик и риск-менеджер (CAPEX/OPEX Translator)",
            goal="Агрегировать технические риски от инженеров и оцифровывать их в финансовых метриках.",
            backstory=(
                "Вы переводите инженерные риски на язык денег. Вы берете конкретные объемы потерь "
                "и затрат от технолога и считаете их влияние на CAPEX/OPEX."
            ),
            tools=[],  # Финансисту инструменты чтения не нужны, он работает с отчетами коллег
            verbose=True,
            memory=False,
            allow_delegation=False
        )