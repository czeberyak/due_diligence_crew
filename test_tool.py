from src.tools import ProcessCalculatorTool

def test_calculator():
    tool = ProcessCalculatorTool()
    
    # Сценарий 1: Корректный баланс
    print("Тест 1: Валидные данные")
    res1 = tool._run(
        raw_materials={"Пропан": 1000.0, "Катализатор": 10.0},
        products={"Пропилен": 850.0, "Водород": 140.0, "Потери": 20.0},
        expected_yield=0.85
    )
    print(res1)
    
    print("\n" + "="*40 + "\n")
    
    # Сценарий 2: Нарушение закона сохранения массы (цифры «из головы»)
    print("Тест 2: Нарушение баланса")
    res2 = tool._run(
        raw_materials={"Бензол": 500.0, "Этилен": 200.0},
        products={"Этилбензол": 800.0}, # Из 700 кг сырья получили 800 кг продукта — магия
        expected_yield=0.90
    )
    print(res2)

if __name__ == "__main__":
    test_calculator()