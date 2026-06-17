from crewai.tools import BaseTool
from pydantic import BaseModel, Field

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


class DocumentSearchTool(BaseTool):
    name: str = "document_search"  # ✅ ДОБАВЛЕНО ИМЯ
    description: str = "Выполняет поиск релевантной информации в загруженных документах"
    
    def _run(self, query: str) -> str:
        # Временная заглушка
        return f"🔍 Поиск по документам: '{query}'\n(Функция RAG будет добавлена позже)"