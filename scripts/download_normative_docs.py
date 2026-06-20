import os
import time
import requests
from pathlib import Path
from datetime import datetime
import json

class NormativeDocsDownloader:
    """
    Автоматизированное скачивание нормативных документов из Consultant.ru
    ПРИМЕЧАНИЕ: Для работы требуется активная подписка и авторизация
    """
    
    def __init__(self, base_dir="data/01_raw/normative_base"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        # Карта категорий и документов для скачивания
        self.documents_map = {
            "01_construction": [
                {"name": "Gradostroitelny_kodeks_RF", "url": "https://www.consultant.ru/document/cons_doc_LAW_51040/"},
                {"name": "SP_42.13330.2016", "url": "https://www.consultant.ru/document/cons_doc_LAW_194309/"},
            ],
            "02_industrial_safety": [
                {"name": "Prikaz_Rostekhnadzora_533", "url": "https://www.consultant.ru/document/cons_doc_LAW_374622/"},
                {"name": "FZ_116_OPBO", "url": "https://www.consultant.ru/document/cons_doc_LAW_12891/"},
            ],
            "03_ecology": [
                {"name": "FZ_7_Okhrana_okruzhayushchey_sredy", "url": "https://www.consultant.ru/document/cons_doc_LAW_2746/"},
                {"name": "FZ_89_Otkhody_proizvodstva", "url": "https://www.consultant.ru/document/cons_doc_LAW_13362/"},
            ],
            # ... добавьте остальные документы
        }
    
    def download_document(self, category, doc_info, headers=None):
        """Скачивает один документ"""
        category_dir = self.base_dir / category
        category_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = category_dir / f"{doc_info['name']}.pdf"
        
        # Проверяем, существует ли уже файл
        if file_path.exists():
            print(f"✓ {doc_info['name']} уже существует")
            return file_path
        
        try:
            # Скачивание через requests (если есть прямой доступ)
            response = requests.get(doc_info['url'], headers=headers, timeout=30)
            response.raise_for_status()
            
            with open(file_path, 'wb') as f:
                f.write(response.content)
            
            print(f"✓ Скачан: {doc_info['name']}")
            time.sleep(1)  # Задержка между запросами
            
            return file_path
            
        except Exception as e:
            print(f"✗ Ошибка скачивания {doc_info['name']}: {e}")
            return None
    
    def download_all(self, consultant_session=None):
        """Скачивает все документы из карты"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        if consultant_session:
            headers['Cookie'] = consultant_session
        
        total_docs = sum(len(docs) for docs in self.documents_map.values())
        print(f"Начинаю скачивание {total_docs} документов...\n")
        
        downloaded = 0
        for category, docs in self.documents_map.items():
            print(f"\n📁 Категория: {category}")
            for doc in docs:
                if self.download_document(category, doc, headers):
                    downloaded += 1
        
        print(f"\n✅ Готово! Скачано {downloaded} из {total_docs} документов")
        return downloaded


def main():
    """Точка входа для скачивания"""
    downloader = NormativeDocsDownloader()
    
    # Если есть сессия Consultant.ru (опционально)
    consultant_session = os.getenv("CONSULTANT_SESSION_COOKIE")
    
    downloader.download_all(consultant_session=consultant_session)


if __name__ == "__main__":
    main()