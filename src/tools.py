from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from pathlib import Path  
import pdfplumber         

# ... дальше идет ваш код классов MassBalanceInput и т.д.

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