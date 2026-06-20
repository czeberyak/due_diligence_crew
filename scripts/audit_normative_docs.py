import os
import json
from pathlib import Path
from datetime import datetime
import requests
from bs4 import BeautifulSoup

class NormativeDocsAuditor:
    """Проверка актуальности нормативных документов"""
    
    def __init__(self, base_dir="data/01_raw/normative_base"):
        self.base_dir = Path(base_dir)
        self.metadata_file = self.base_dir / "documents_metadata.json"
        self.load_metadata()
    
    def load_metadata(self):
        """Загружает метаданные документов"""
        if self.metadata_file.exists():
            with open(self.metadata_file, 'r', encoding='utf-8') as f:
                self.metadata = json.load(f)
        else:
            self.metadata = {}
    
    def save_metadata(self):
        """Сохраняет метаданные"""
        with open(self.metadata_file, 'w', encoding='utf-8') as f:
            json.dump(self.metadata, f, ensure_ascii=False, indent=2)
    
    def check_document_status(self, consultant_url):
        """
        Проверяет статус документа на Consultant.ru
        Возвращает: 'active', 'expired', 'updated'
        """
        try:
            response = requests.get(consultant_url, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Ищем статус документа (зависит от структуры Consultant.ru)
            status_div = soup.find('div', class_='document-status')
            if status_div:
                status_text = status_div.get_text().lower()
                if 'утратил силу' in status_text or 'не действует' in status_text:
                    return 'expired'
                elif 'в новой редакции' in status_text:
                    return 'updated'
            
            return 'active'
            
        except Exception as e:
            print(f"Ошибка проверки статуса: {e}")
            return 'unknown'
    
    def audit_all_documents(self):
        """Проводит аудит всех документов в базе"""
        print("🔍 Начинаю аудит нормативной базы...\n")
        
        audit_results = {
            'date': datetime.now().isoformat(),
            'total': 0,
            'active': 0,
            'expired': 0,
            'updated': 0,
            'unknown': 0,
            'files': []
        }
        
        for pdf_file in self.base_dir.rglob("*.pdf"):
            audit_results['total'] += 1
            
            rel_path = str(pdf_file.relative_to(self.base_dir))
            
            # Получаем метаданные из кэша или создаём новые
            if rel_path not in self.metadata:
                self.metadata[rel_path] = {
                    'url': None,
                    'last_checked': None,
                    'status': 'unknown'
                }
            
            # Проверяем статус (если есть URL)
            doc_url = self.metadata[rel_path].get('url')
            if doc_url:
                status = self.check_document_status(doc_url)
                self.metadata[rel_path]['status'] = status
                self.metadata[rel_path]['last_checked'] = datetime.now().isoformat()
                
                audit_results[status] += 1
                audit_results['files'].append({
                    'file': rel_path,
                    'status': status,
                    'url': doc_url
                })
                
                status_emoji = {
                    'active': '✓',
                    'expired': '✗',
                    'updated': '⚠',
                    'unknown': '?'
                }
                
                print(f"{status_emoji.get(status, '?')} {pdf_file.name}: {status}")
            else:
                print(f"? {pdf_file.name}: нет URL для проверки")
                audit_results['unknown'] += 1
        
        self.save_metadata()
        
        # Генерируем отчёт
        self.generate_audit_report(audit_results)
        
        return audit_results
    
    def generate_audit_report(self, results):
        """Генерирует отчёт об аудите"""
        report_path = self.base_dir / f"audit_report_{datetime.now().strftime('%Y%m%d')}.md"
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("# 📋 Отчёт аудита нормативной базы\n\n")
            f.write(f"**Дата проверки:** {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n")
            
            f.write("## 📊 Статистика\n\n")
            f.write(f"- Всего документов: **{results['total']}**\n")
            f.write(f"- ✅ Действуют: **{results['active']}**\n")
            f.write(f"- ⚠ Требуют обновления: **{results['updated']}**\n")
            f.write(f"- ✗ Утратили силу: **{results['expired']}**\n")
            f.write(f"- ❓ Не проверено: **{results['unknown']}**\n\n")
            
            if results['expired']:
                f.write("## ⚠️ Утратили силу (требуют замены)\n\n")
                for file_info in results['files']:
                    if file_info['status'] == 'expired':
                        f.write(f"- `{file_info['file']}`\n")
                f.write("\n")
            
            if results['updated']:
                f.write("## 🔄 Доступны новые редакции\n\n")
                for file_info in results['files']:
                    if file_info['status'] == 'updated':
                        f.write(f"- `{file_info['file']}`\n")
                f.write("\n")
        
        print(f"\n📄 Отчёт сохранён: {report_path}")


def main():
    """Точка входа для аудита"""
    auditor = NormativeDocsAuditor()
    results = auditor.audit_all_documents()
    
    print(f"\n✅ Аудит завершён!")
    print(f"   Действуют: {results['active']}")
    print(f"   Требуют обновления: {results['updated']}")
    print(f"   Утратили силу: {results['expired']}")


if __name__ == "__main__":
    main()