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
    name: str = "process_calculator"  # ✅ ДОБАВЛЕНО ИМЯ (без пробелов!)
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
            
        # ✅ НОВОЕ: Защита от "создания материи из ничего"
        if total_output > total_input:
            return (
                f"❌ КРИТИЧЕСКАЯ ОШИБКА ФИЗИКИ: Масса продуктов ({total_output:.2f} кг) превышает "
                f"массу сырья ({total_input:.2f} кг). Нарушен закон сохранения массы (материя не может "
                f"возникнуть из ничего), даже если процент невязки мал. Проект физически нереализуем или "
                f"в ТЭО скрыты дополнительные неучтенные потоки сырья."
            )
            
        # Расчет невязки (ошибки) баланса согласно закону сохранения массы
        mass_balance_error = abs(total_input - total_output) / total_input * 100
        
        # Находим главный целевой продукт (максимальный по массе)
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
            report += f"❌ КРИТИЧЕСКАЯ ОШИБКА: Нарушен закон сохранения массы (невязка {mass_balance_error:.2f}% > 5%). Проект физически нереализуем или содержит подлог в цифрах."
        elif abs(actual_yield - expected_yield) > 0.1:
            report += "⚠️ ВНИМАНИЕ: Фактический выход значительно отличается от заявленного плана (отклонение > 10%). Экономика проекта под угрозой."
        else:
            report += "✅ Баланс сошелся в пределах нормы. Данные технологической схемы верифицированы."
            
        return report


class DocumentSearchInput(BaseModel):
    query: str = Field(
        description="Ключевое слово или фраза для поиска в документе (например, 'баланс', 'пропилен', 'этилбензол', 'риски'). Если нужно прочитать документ целиком, передайте '*'"
    )
    file_path: str = Field(
        default="data/01_raw/TEO_project_example.pdf", 
        description="Путь к конкретному PDF-файлу для анализа из папки data/01_raw/"
    )

class DocumentSearchTool(BaseTool):
    name: str = "document_search"
    description: str = (
        "Честный парсер проектной документации. Постранично извлекает текст и таблицы "
        "из указанного PDF-файла, фильтруя данные по ключевому слову."
    )
    args_schema: type[BaseModel] = DocumentSearchInput

    def _run(self, query: str, file_path: str) -> str:
        path = Path(file_path)
        
        # Защита от системных файлов метаданных Windows
        if ":Zone.Identifier" in str(path):
            return "❌ Ошибка: Вы попытались прочитать файл метаданных Zone.Identifier. Используйте путь к самому PDF-файлу."
            
        if not path.exists():
            return f"❌ Ошибка: Файл по пути {file_path} не найден. Проверьте имя файла в data/01_raw/"

        extracted_data = []
        
        try:
            with pdfplumber.open(path) as pdf:
                for idx, page in enumerate(pdf.pages):
                    page_num = idx + 1
                    text = page.extract_text() or ""
                    
                    # Проверяем вхождение ключевого слова (регистронезависимо) или признак полного чтения
                    if query == "*" or query.lower() in text.lower():
                        page_output = f"=== СТРАНИЦА {page_num} ===\n"
                        
                        # Добавляем текстовый контент страницы
                        if text:
                            page_output += f"【 Текст страницы 】:\n{text}\n"
                        
                        # Извлекаем таблицы — критично для материальных балансов!
                        tables = page.extract_tables()
                        if tables:
                            page_output += "\n【 Обнаруженные технологические таблицы 】:\n"
                            for table in tables:
                                for row in table:
                                    # Очищаем ячейки от None, убираем лишние переносы строк внутри ячеек
                                    clean_row = [
                                        str(cell).replace('\n', ' ').strip() if cell is not None else "" 
                                        for cell in row
                                    ]
                                    # Форматируем строку таблицы в псевдо-Markdown
                                    page_output += f"| {' | '.join(clean_row)} |\n"
                                page_output += "\n"
                        
                        extracted_data.append(page_output)
            
            if not extracted_data:
                return f"🔍 По запросу '{query}' в документе {path.name} ничего не найдено. Попробуйте расширить запрос."
            
            # Собираем финальный контекст для агента
            full_response = "\n".join(extracted_data)
            
            # Защитный лимит на объем токенов, чтобы не перегрузить контекстное окно модели
            if len(full_response) > 15000:
                return full_response[:15000] + "\n\n... [Данные обрезаны из-за лимита объема страницы] ..."
                
            return full_response

        except Exception as e:
            return f"❌ Ошибка при парсинге PDF-документа: {str(e)}"
        
class RegulatorySearchInput(BaseModel):
    query: str = Field(
        description="Ключевое слово, номер ГОСТа или фраза для поиска по базе нормативных документов (например, 'Приказ 533', 'ПДК', 'категория опасности', 'Трубопроводы')."
    )
    directory_path: str = Field(
        default="data/01_raw/",
        description="Папка, в которой лежат нормативные акты и ГОСТы."
    )

class RegulatorySearchInput(BaseModel):
    query: str = Field(
        description="Ключевое слово, номер ГОСТа, фраза или название закона для поиска по базе нормативных документов (например, 'Приказ 533', 'ПДК', 'категория опасности', 'АСУ ТП')."
    )
    directory_path: str = Field(
        default="data/01_raw/",
        description="Папка, в которой лежат нормативные акты, ГОСТы, ТУ и Приказы."
    )

class RegulatorySearchInput(BaseModel):
    query: str = Field(
        description="Ключевое слово, номер ГОСТа или фраза для поиска (например, 'ПДК', 'категория опасности', 'подключение к сетям')."
    )
    directory_path: str = Field(
        default="data/01_raw/normative_base/",
        description="Базовая папка с нормативными актами."
    )
    category: str = Field(
        default="*",
        description=(
            "Категория нормативных документов для поиска. "
            "Доступные категории: 01_construction, 02_industrial_safety, 03_ecology, "
            "04_pressure_equipment, 05_automation, 06_labor, 07_fire_safety, 08_energy. "
            "Используйте '*' для поиска по всем категориям или укажите конкретную (например, '08_energy')."
        )
    )

class RegulatorySearchTool(BaseTool):
    name: str = "regulatory_search"
    description: str = (
        "Инструмент для сверки с законодательством. Ищет информацию по PDF-файлам "
        "в указанной категории нормативной базы. Используйте для поиска реальных требований "
        "законов и сравнения их с проектом."
    )
    args_schema: type[BaseModel] = RegulatorySearchInput

    def _run(self, query: str, directory_path: str = "data/01_raw/normative_base/", category: str = "*") -> str:
        path = Path(directory_path)
        if not path.exists():
            return f"❌ Папка {directory_path} не найдена."
        
        # Определяем, какие подпапки сканировать
        if category == "*":
            # Сканируем все подпапки
            search_paths = [path] + list(path.glob("*/"))
        else:
            # Сканируем только указанную категорию
            category_path = path / category
            if not category_path.exists():
                return f"❌ Категория '{category}' не найдена в {directory_path}."
            search_paths = [category_path]
            
        # Находим все PDF в выбранных путях
        pdf_files = []
        for search_path in search_paths:
            pdf_files.extend(list(search_path.glob("*.pdf")))
        
        # Убираем дубликаты (если category="*", то path и path/* могут пересекаться)
        pdf_files = list(set(pdf_files))
        
        if not pdf_files:
            return f"❌ В категории '{category}' нет PDF-файлов."
            
        extracted_data = []
        
        for pdf_file in pdf_files:
            # Пропускаем само ТЭО (если оно случайно попало в normative_base)
            if "TEO" in pdf_file.name or "example" in pdf_file.name:
                continue
                
            try:
                with pdfplumber.open(pdf_file) as pdf:
                    for idx, page in enumerate(pdf.pages):
                        text = page.extract_text() or ""
                        # Ищем совпадение (регистронезависимо)
                        if query.lower() in text.lower():
                            # Указываем категорию в выводе
                            category_name = pdf_file.parent.name if pdf_file.parent != path else "root"
                            page_output = f"=== КАТЕГОРИЯ: {category_name} | ФАЙЛ: {pdf_file.name} | СТРАНИЦА {idx+1} ===\n"
                            page_output += f"{text}\n\n"
                            extracted_data.append(page_output)
            except Exception as e:
                extracted_data.append(f"⚠️ Ошибка чтения {pdf_file.name}: {e}\n")
                
        if not extracted_data:
            return f"🔍 По запросу '{query}' в категории '{category}' ({len(pdf_files)} файлов) ничего не найдено."
            
        full_response = "\n".join(extracted_data)
        
        # Защита от переполнения контекста
        if len(full_response) > 15000:
            return full_response[:15000] + "\n\n... [Данные обрезаны из-за лимита объема] ..."
            
        return full_response


class SemanticSearchInput(BaseModel):
    query: str = Field(
        description="Семантический запрос, суть вопроса или описание требования для поиска по базе знаний (например, 'требования к резервированию систем безопасности', 'предельно допустимые концентрации в воде')."
    )
    top_k: int = Field(
        default=3,
        description="Количество наиболее релевантных фрагментов текста для возврата (обычно 3-5)."
    )

class SemanticSearchTool(BaseTool):
    name: str = "semantic_search"
    description: str = (
        "Инструмент семантического поиска (RAG) по локальной векторной базе данных ChromaDB. "
        "Ищет по смыслу, а не по точному совпадению ключевых слов. "
        "Используйте его, чтобы найти скрытые требования, завуалированные формулировки и сложные нормативные предписания в ТЭО и законах."
    )
    args_schema: type[BaseModel] = SemanticSearchInput

    def _run(self, query: str, top_k: int = 3) -> str:
        db_dir = "data/vector_db"
        if not Path(db_dir).exists():
            return "❌ Ошибка: Векторная база данных не найдена. Сначала запустите скрипт индексации `python src/ingest.py`."

        try:
            default_ef = embedding_functions.DefaultEmbeddingFunction()
            client = chromadb.PersistentClient(path=db_dir)
            collection = client.get_collection(
                name="due_diligence_docs",
                embedding_function=default_ef
            )
            
            results = collection.query(
                query_texts=[query],
                n_results=top_k
            )
            
            if not results['documents'][0]:
                return f"🔍 По семантическому запросу '{query}' ничего не найдено."
                
            output = f"🧠 Результаты семантического поиска по запросу: '{query}'\n\n"
            for i, doc in enumerate(results['documents'][0]):
                source = results['metadatas'][0][i]['source']
                output += f"--- Фрагмент {i+1} (Источник: {source}) ---\n"
                output += doc.strip() + "\n\n"
                
            return output
            
        except Exception as e:
            return f"❌ Ошибка при обращении к векторной БД: {str(e)}"
        
class EnergyBalanceInput(BaseModel):
    installed_capacity_mw: float = Field(
        description="Установленная мощность в МВт. Пример: 50.0"
    )
    hours_per_year: int = Field(
        default=8760,
        description="Количество часов в году (обычно 8760)"
    )
    claimed_kium: float = Field(
        description="Заявленный КИУМ (коэффициент использования установленной мощности) в долях от 0 до 1. Пример: 0.15 для 15%"
    )
    claimed_generation_mwh: float = Field(
        description="Заявленная годовая выработка в МВт·ч. Пример: 65000"
    )
    energy_source: str = Field(
        default="solar",
        description="Тип источника энергии: solar, wind, thermal, hydro"
    )

class EnergyBalanceCalculatorTool(BaseTool):
    name: str = "energy_balance_calculator"
    description: str = (
        "Проверяет энергетический баланс для проектов ВИЭ (солнечные, ветровые электростанции). "
        "Рассчитывает реальную выработку на основе КИУМ и сравнивает с заявленной. "
        "Выявляет физически невозможные параметры (например, КИУМ > 25% для солнца)."
    )
    args_schema: type[BaseModel] = EnergyBalanceInput

    def _run(self, installed_capacity_mw: float, hours_per_year: int, 
             claimed_kium: float, claimed_generation_mwh: float, 
             energy_source: str = "solar") -> str:
        
        # Максимально допустимый КИУМ для разных типов генерации
        max_kium_limits = {
            "solar": 0.25,   # 25% - максимум для солнечных станций в РФ
            "wind": 0.35,    # 35% - для ветровых
            "thermal": 0.85, # 85% - для тепловых
            "hydro": 0.50    # 50% - для гидро
        }
        
        max_kium = max_kium_limits.get(energy_source, 0.50)
        
        # Расчет реальной выработки
        theoretical_max = installed_capacity_mw * hours_per_year
        realistic_generation = theoretical_max * claimed_kium
        
        # Проверка КИУМ
        kium_check = "✅" if claimed_kium <= max_kium else "❌"
        kium_status = "в пределах нормы" if claimed_kium <= max_kium else f"ПРЕВЫШАЕТ МАКСИМУМ ({max_kium*100:.0f}% для {energy_source})"
        
        # Проверка соответствия выработки
        generation_diff = abs(claimed_generation_mwh - realistic_generation) / realistic_generation * 100 if realistic_generation > 0 else 0
        generation_check = "✅" if generation_diff < 5 else "❌"
        
        report = (
            f"=== АНАЛИЗ ЭНЕРГЕТИЧЕСКОГО БАЛАНСА ===\n\n"
            f"Установленная мощность: {installed_capacity_mw} МВт\n"
            f"Заявленный КИУМ: {claimed_kium*100:.1f}% {kium_check} ({kium_status})\n"
            f"Максимально допустимый КИУМ для {energy_source}: {max_kium*100:.0f}%\n"
            f"Теоретический максимум выработки: {theoretical_max:,.0f} МВт·ч/год\n"
            f"Реалистичная выработка при КИУМ {claimed_kium*100:.1f}%: {realistic_generation:,.0f} МВт·ч/год\n"
            f"Заявленная выработка: {claimed_generation_mwh:,.0f} МВт·ч/год\n"
            f"Расхождение: {generation_diff:.1f}% {generation_check}\n\n"
            f"=== ВЕРДИКТ ===\n"
        )
        
        if claimed_kium > max_kium:
            report += (
                f"❌ КРИТИЧЕСКАЯ ОШИБКА ФИЗИКИ: Заявленный КИУМ {claimed_kium*100:.1f}% "
                f"превышает физически возможный максимум {max_kium*100:.0f}% для {energy_source}. "
                f"Это означает, что ТЭО содержит завышенные показатели выработки. "
                f"Реальная выработка будет на {((claimed_kium/max_kium - 1)*100):.0f}% ниже заявленной."
            )
        elif generation_diff > 10:
            report += f"⚠️ ВНИМАНИЕ: Заявленная выработка не соответствует расчетной (расхождение {generation_diff:.1f}%). Требуется перепроверка данных."
        else:
            report += "✅ Энергетический баланс корректен. Параметры реалистичны."
            
        return report