# src/ingest.py
import pdfplumber
import chromadb
from chromadb.utils import embedding_functions
from pathlib import Path

def ingest_documents(pdf_dir="data/01_raw", db_dir="data/vector_db"):
    print(f"📂 Начинаем индексацию документов из {pdf_dir}...")
    
    # Используем встроенную бесплатную модель эмбеддингов (all-MiniLM-L6-v2)
    # При первом запуске она автоматически скачается (~80 МБ)
    default_ef = embedding_functions.DefaultEmbeddingFunction()
    client = chromadb.PersistentClient(path=db_dir)
    
    # Удаляем старую коллекцию, чтобы избежать дублирования при повторном запуске
    try:
        client.delete_collection("due_diligence_docs")
    except Exception:
        pass  # Игнорируем ошибку, если коллекции еще нет
        
    collection = client.get_or_create_collection(
        name="due_diligence_docs",
        embedding_function=default_ef,
        metadata={"hnsw:space": "cosine"} # Косинусное сходство для поиска по смыслу
    )

    pdf_files = list(Path(pdf_dir).glob("*.pdf"))
    if not pdf_files:
        print("❌ PDF-файлы не найдены.")
        return

    all_chunks = []
    all_metadatas = []
    all_ids = []
    
    # Параметры нарезки текста
    chunk_size = 1000  # символов
    chunk_overlap = 200 # символов перекрытия, чтобы не терять смысл на стыках

    for pdf_path in pdf_files:
        print(f"📄 Чтение и нарезка: {pdf_path.name}")
        try:
            with pdfplumber.open(pdf_path) as pdf:
                full_text = "\n".join([page.extract_text() or "" for page in pdf.pages])
                
                # Разбиение на чанки с перекрытием
                start = 0
                while start < len(full_text):
                    end = start + chunk_size
                    chunk = full_text[start:end].strip()
                    
                    if chunk:
                        chunk_id = f"{pdf_path.stem}_{len(all_chunks)}"
                        all_chunks.append(chunk)
                        all_metadatas.append({"source": pdf_path.name})
                        all_ids.append(chunk_id)
                        
                    start += (chunk_size - chunk_overlap)
                    
        except Exception as e:
            print(f"⚠️ Ошибка при чтении {pdf_path.name}: {e}")

    if not all_chunks:
        print("❌ Не удалось извлечь текст из файлов.")
        return

    # Батч-загрузка в ChromaDB
    print(f"🧠 Векторизация и сохранение {len(all_chunks)} фрагментов...")
    batch_size = 500
    for i in range(0, len(all_chunks), batch_size):
        end = min(i + batch_size, len(all_chunks))
        collection.add(
            documents=all_chunks[i:end],
            metadatas=all_metadatas[i:end],
            ids=all_ids[i:end]
        )

    print(f"🎉 Индексация завершена! База данных сохранена в {db_dir}")

if __name__ == "__main__":
    ingest_documents()