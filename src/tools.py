# src/tools.py
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from pathlib import Path
import pdfplumber
import chromadb
from chromadb.utils import embedding_functions

class MassBalanceInput(BaseModel):
    raw_materials: dict[str, float] = Field(
        description="Словарь исходного сырья, где ключ — название, значение — масса в кг. Пример: {'Ethylene': 1000, 'Catalyst': 5}"
    )
    products: dict[str, float] = Field(
        description="Словарь полученных продуктов, где ключ — название, значение — масса в кг. Пример: {'Polyethylene': 950, 'Waste': 45}"
    )
    expected_yield: float = Field(
        description="Ожидаемый выход целевого продукта в долях от 0 до 1. Пример: 0.95"
    )

class ProcessCalculatorTool(BaseTool):
    name: str = "process_calculator"
    description: str = (
        "Проверяет материальный баланс химического или промышленного процесса. "
        "Сравнивает массу сырья и продуктов, рассчитывает ошибку невязки баланса и фактический выход."
    )
    args_schema: type[BaseModel] = MassBalanceInput

    def _run(self, raw_materials: dict[str, float], products: dict[str, float], expected_yield: float) -> str:
        total_input = sum(raw_materials.values())
        total_output = sum(products.values())
        
        if total_input == 0:
            return "❌ Ошибка: Масса исходного сырья равна нулю."
            
        if total_output > total_input:
            return (
                f"❌ КРИТИЧЕСКАЯ ОШИБКА ФИЗИКИ: Масса продуктов ({total_output:.2f} кг) превышает "
                f"массу сырья ({total_input:.2f} кг). Нарушен закон сохранения массы. Проект физически нереализуем."
            )
            
        mass_balance_error = abs(total_input - total_output) / total_input * 100
        main_product_name = max(products, key=products.get)
        main_product_mass = products[main_product_name]
        actual_yield = main_product_mass / total_input
        
        report = (
            f"=== АНАЛИЗ МАТЕРИАЛЬНОГО БАЛАНСА ===\n\n"
            f"Вход сырья (всего): {total_input:.2f} кг\n"
            f"Выход продуктов (всего): {total_output:.2f} кг\n"
            f"Ошибка невязки баланса: {mass_balance_error:.2f}%\n"
            f"Целевой продукт: {main_product_name} ({main_product_mass:.2f} кг)\n"
            f"Фактический выход: {actual_yield:.2%}\n"
            f"Ожидаемый выход: {expected_yield:.2%}\n"
            f"Отклонение от плана: {abs(actual_yield - expected_yield):.2%}\n\n"
            f"=== ВЕРДИКТ ===\n"
        )
        
        if mass_balance_error > 5.0:
            report += f"❌ КРИТИЧЕСКАЯ ОШИБКА: Нарушен закон сохранения массы (невязка {mass_balance_error:.2f}% > 5%)."
        elif abs(actual_yield - expected_yield) > 0.1:
            report += "⚠️ ВНИМАНИЕ: Фактический выход значительно отличается от заявленного плана."
        else:
            report += "✅ Баланс сошелся в пределах нормы."
            
        return report

class DocumentSearchInput(BaseModel):
    query: str = Field(
        description="Ключевое слово или фраза для поиска в документе. Если нужно прочитать документ целиком, передайте '*'"
    )
    file_path: str = Field(
        default="data/01_raw/TEO_project_example.pdf",
        description="Путь к конкретному PDF-файлу для анализа"
    )

class DocumentSearchTool(BaseTool):
    name: str = "document_search"
    description: str = "Постранично извлекает текст и таблицы из указанного PDF-файла."
    args_schema: type[BaseModel] = DocumentSearchInput

    def _run(self, query: str, file_path: str) -> str:
        path = Path(file_path)
        
        # Защита от системных файлов метаданных Windows
        if ":Zone.Identifier" in str(path):
            return "❌ Ошибка: Файл метаданных Zone.Identifier. Используйте путь к самому PDF."
        if not path.exists():
            return f"❌ Ошибка: Файл {file_path} не найден."

        extracted_data = []
        try:
            with pdfplumber.open(path) as pdf:
                for idx, page in enumerate(pdf.pages):
                    page_num = idx + 1
                    text = page.extract_text() or ""
                    tables = page.extract_tables() or []
                    
                    # 1. Проверяем совпадение в обычном тексте
                    text_match = (query == "*" or query.lower() in text.lower())
                    
                    # 2. НОВОЕ: Проверяем совпадение ВНУТРИ таблиц (если в тексте не нашли)
                    table_match = False
                    if not text_match and query != "*":
                        for table in tables:
                            for row in table:
                                if row and any(query.lower() in str(cell).lower() for cell in row if cell):
                                    table_match = True
                                    break
                            if table_match:
                                break
                                
                    # Если нашли хоть где-то — забираем страницу
                    if text_match or table_match:
                        page_output = f"=== СТРАНИЦА {page_num} ===\n"
                        if text:
                            page_output += f"【 Текст страницы 】:\n{text}\n"
                        
                        if tables:
                            page_output += "\n【 Обнаруженные таблицы 】:\n"
                            for table in tables:
                                if not table:
                                    continue
                                for i, row in enumerate(table):
                                    # 3. НОВОЕ: Очищаем ячейки и экранируем символ "|" внутри текста
                                    clean_row = [
                                        str(cell).replace('\n', ' ').replace('|', '/').strip() if cell is not None else "" 
                                        for cell in row
                                    ]
                                    page_output += f"| {' | '.join(clean_row)} |\n"
                                    
                                    # 4. НОВОЕ: Добавляем Markdown-разделитель после первой строки (заголовка)
                                    if i == 0:
                                        page_output += f"| {' | '.join(['---'] * len(clean_row))} |\n"
                                page_output += "\n"
                        
                        extracted_data.append(page_output)
            
            if not extracted_data:
                return f"🔍 По запросу '{query}' в документе {path.name} ничего не найдено. Попробуйте расширить запрос."
            
            full_response = "\n".join(extracted_data)
            
            # Защитный лимит на объем токенов
            if len(full_response) > 15000:
                return full_response[:15000] + "\n\n... [Данные обрезаны из-за лимита объема страницы] ..."
                
            return full_response

        except Exception as e:
            return f"❌ Ошибка при парсинге PDF-документа: {str(e)}"

class RegulatorySearchInput(BaseModel):
    query: str = Field(description="Ключевое слово или номер ГОСТа для поиска.")
    directory_path: str = Field(default="data/01_raw/normative_base/", description="Базовая папка с нормативными актами.")
    category: str = Field(default="*", description="Категория (01_construction ... 08_energy) или '*' для всех.")

class RegulatorySearchTool(BaseTool):
    name: str = "regulatory_search"
    description: str = "Ищет информацию по PDF-файлам в указанной категории нормативной базы."
    args_schema: type[BaseModel] = RegulatorySearchInput

    def _run(self, query: str, directory_path: str = "data/01_raw/normative_base/", category: str = "*") -> str:
        path = Path(directory_path)
        if not path.exists():
            return f"❌ Папка {directory_path} не найдена."
        
        if category == "*":
            search_paths = [path] + list(path.glob("*/"))
        else:
            category_path = path / category
            if not category_path.exists():
                return f"❌ Категория '{category}' не найдена."
            search_paths = [category_path]
            
        pdf_files = list(set([f for p in search_paths for f in p.glob("*.pdf")]))
        if not pdf_files:
            return f"❌ В категории '{category}' нет PDF-файлов."
            
        extracted_data = []
        for pdf_file in pdf_files:
            if "TEO" in pdf_file.name or "example" in pdf_file.name:
                continue
            try:
                with pdfplumber.open(pdf_file) as pdf:
                    for idx, page in enumerate(pdf.pages):
                        text = page.extract_text() or ""
                        if query.lower() in text.lower():
                            category_name = pdf_file.parent.name if pdf_file.parent != path else "root"
                            page_output = f"=== КАТЕГОРИЯ: {category_name} | ФАЙЛ: {pdf_file.name} | СТРАНИЦА {idx+1} ===\n{text}\n\n"
                            extracted_data.append(page_output)
            except Exception as e:
                extracted_data.append(f"⚠️ Ошибка чтения {pdf_file.name}: {e}\n")
                
        if not extracted_data:
            return f"🔍 По запросу '{query}' ничего не найдено."
            
        full_response = "\n".join(extracted_data)
        if len(full_response) > 15000:
            return full_response[:15000] + "\n\n... [Обрезано] ..."
        return full_response

class SemanticSearchInput(BaseModel):
    query: str = Field(description="Семантический запрос для поиска по базе знаний.")
    top_k: int = Field(default=3, description="Количество фрагментов для возврата.")

class SemanticSearchTool(BaseTool):
    name: str = "semantic_search"
    description: str = "Инструмент семантического поиска (RAG) по ChromaDB."
    args_schema: type[BaseModel] = SemanticSearchInput

    def _run(self, query: str, top_k: int = 3) -> str:
        db_dir = "data/vector_db"
        if not Path(db_dir).exists():
            return "❌ Ошибка: Векторная БД не найдена. Запустите `python src/ingest.py`."
        try:
            default_ef = embedding_functions.DefaultEmbeddingFunction()
            client = chromadb.PersistentClient(path=db_dir)
            collection = client.get_collection(name="due_diligence_docs", embedding_function=default_ef)
            results = collection.query(query_texts=[query], n_results=top_k)
            if not results['documents'][0]:
                return f"🔍 По запросу '{query}' ничего не найдено."
            output = f"🧠 Результаты:\n\n"
            for i, doc in enumerate(results['documents'][0]):
                source = results['metadatas'][0][i]['source']
                output += f"--- Фрагмент {i+1} ({source}) ---\n{doc.strip()}\n\n"
            return output
        except Exception as e:
            return f"❌ Ошибка ChromaDB: {str(e)}"

class EnergyBalanceInput(BaseModel):
    installed_capacity_mw: float = Field(description="Установленная мощность в МВт.")
    hours_per_year: int = Field(default=8760, description="Часов в году.")
    claimed_kium: float = Field(description="Заявленный КИУМ (от 0 до 1).")
    claimed_generation_mwh: float = Field(description="Заявленная выработка в МВт·ч.")
    energy_source: str = Field(default="solar", description="Тип: solar, wind, thermal, hydro")

class EnergyBalanceCalculatorTool(BaseTool):
    name: str = "energy_balance_calculator"
    description: str = "Проверяет энергетический баланс и КИУМ для проектов ВИЭ."
    args_schema: type[BaseModel] = EnergyBalanceInput

    def _run(self, installed_capacity_mw: float, hours_per_year: int, 
             claimed_kium: float, claimed_generation_mwh: float, 
             energy_source: str = "solar") -> str:
        max_kium_limits = {"solar": 0.25, "wind": 0.35, "thermal": 0.85, "hydro": 0.50}
        max_kium = max_kium_limits.get(energy_source, 0.50)
        
        theoretical_max = installed_capacity_mw * hours_per_year
        realistic_generation = theoretical_max * claimed_kium
        
        kium_check = "✅" if claimed_kium <= max_kium else "❌"
        kium_status = "норма" if claimed_kium <= max_kium else f"ПРЕВЫШАЕТ МАКСИМУМ ({max_kium*100:.0f}%)"
        
        generation_diff = abs(claimed_generation_mwh - realistic_generation) / realistic_generation * 100 if realistic_generation > 0 else 0
        generation_check = "✅" if generation_diff < 5 else "❌"
        
        report = (
            f"=== ЭНЕРГЕТИЧЕСКИЙ БАЛАНС ===\n"
            f"Мощность: {installed_capacity_mw} МВт\n"
            f"КИУМ: {claimed_kium*100:.1f}% {kium_check} ({kium_status})\n"
            f"Макс. КИУМ для {energy_source}: {max_kium*100:.0f}%\n"
            f"Реалистичная выработка: {realistic_generation:,.0f} МВт·ч\n"
            f"Заявленная выработка: {claimed_generation_mwh:,.0f} МВт·ч\n"
            f"Расхождение: {generation_diff:.1f}% {generation_check}\n\n"
        )
        
        if claimed_kium > max_kium:
            report += f"❌ КРИТИЧЕСКАЯ ОШИБКА ФИЗИКИ: КИУМ {claimed_kium*100:.1f}% невозможен!"
        elif generation_diff > 10:
            report += f"⚠️ ВНИМАНИЕ: Выработка не соответствует расчетной."
        else:
            report += "✅ Баланс корректен."
        return report
