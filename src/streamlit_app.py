import streamlit as st
import os
import sys
from pathlib import Path
from datetime import datetime
import tempfile
import shutil

# Добавляем src в путь импортов
sys.path.append(str(Path(__file__).parent))

from main import run_due_diligence_council

# ═══════════════════════════════════════════════════════════════
# КОНФИГУРАЦИЯ СТРАНИЦЫ
# ═══════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Due Diligence Crew",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ═══════════════════════════════════════════════════════════════
# КАСТОМНЫЕ СТИЛИ (CSS)
# ═══════════════════════════════════════════════════════════════
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    .status-box {
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .status-running {
        background-color: #fff3cd;
        border-left: 4px solid #ffc107;
    }
    .status-success {
        background-color: #d4edda;
        border-left: 4px solid #28a745;
    }
    .status-error {
        background-color: #f8d7da;
        border-left: 4px solid #dc3545;
    }
    .report-container {
        background-color: #f8f9fa;
        padding: 1.5rem;
        border-radius: 0.5rem;
        border: 1px solid #dee2e6;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem;
        border-radius: 0.5rem;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
# ИНИЦИАЛИЗАЦИЯ SESSION STATE
# ═══════════════════════════════════════════════════════════════
if "report" not in st.session_state:
    st.session_state.report = None
if "is_running" not in st.session_state:
    st.session_state.is_running = False
if "logs" not in st.session_state:
    st.session_state.logs = []

# ═══════════════════════════════════════════════════════════════
# ЗАГОЛОВОК
# ═══════════════════════════════════════════════════════════════
st.markdown('<div class="main-header">🏭 Due Diligence Crew</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">AI-консилиум для автоматизированного аудита ТЭО</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
# САЙДБАР — НАСТРОЙКИ
# ═══════════════════════════════════════════════════════════════
with st.sidebar:
    st.header("⚙️ Настройки")
    
    # Выбор типа проекта
    project_type = st.selectbox(
        "Тип проекта",
        ["Химическая промышленность", "Энергетика (СЭС/ВЭС)", "Строительство", "Металлургия", "Пищевая промышленность"],
        help="Тип проекта влияет на выбор категорий нормативной базы"
    )
    
    # Выбор модели LLM
    llm_model = st.selectbox(
        "Модель LLM",
        ["openrouter/openai/gpt-oss-120b:free", "openrouter/anthropic/claude-3.5-sonnet", "openrouter/google/gemini-pro-1.5"],
        help="Модель для всех агентов консилиума"
    )
    
    # Температура
    temperature = st.slider("Температура (креативность)", 0.0, 1.0, 0.2, 0.1)
    
    st.divider()
    
    # Информация о системе
    st.header("📊 Статус системы")
    
    # Проверка наличия нормативной базы
    normative_dir = Path("data/01_raw/normative_base")
    if normative_dir.exists():
        categories = [d.name for d in normative_dir.iterdir() if d.is_dir()]
        st.success(f"✅ Нормативная база: {len(categories)} категорий")
        for cat in categories:
            pdf_count = len(list((normative_dir / cat).glob("*.pdf")))
            st.caption(f"  • {cat}: {pdf_count} файлов")
    else:
        st.warning("⚠️ Нормативная база не найдена")
    
    # Проверка TEO папки
    teo_dir = Path("data/01_raw/TEO")
    if teo_dir.exists():
        teo_count = len(list(teo_dir.glob("*.pdf")))
        st.info(f"📁 ТЭО в базе: {teo_count} файлов")
    
    st.divider()
    
    # История запусков
    st.header("📜 История")
    processed_dir = Path("data/02_processed")
    if processed_dir.exists():
        reports = sorted(processed_dir.glob("*.md"), reverse=True)[:5]
        if reports:
            for report in reports:
                st.caption(f"• {report.stem.replace('DD_Report_', '')}")
        else:
            st.caption("Нет сохраненных отчетов")

# ═══════════════════════════════════════════════════════════════
# ОСНОВНАЯ ОБЛАСТЬ — ЗАГРУЗКА ФАЙЛА
# ═══════════════════════════════════════════════════════════════
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("📄 Загрузка ТЭО")
    
    uploaded_file = st.file_uploader(
        "Перетащите PDF-файл ТЭО сюда или нажмите для выбора",
        type=["pdf"],
        help="Поддерживаются только PDF-файлы с технико-экономическим обоснованием"
    )
    
    if uploaded_file:
        st.success(f"✅ Загружен файл: {uploaded_file.name} ({uploaded_file.size / 1024:.1f} КБ)")
        
        # Показываем превью первой страницы (если возможно)
        with st.expander("👁️ Предпросмотр файла"):
            st.info("Файл готов к анализу. Нажмите 'Запустить консилиум' для начала аудита.")

with col2:
    st.subheader("📈 Метрики")
    
    # Метрики (пока заглушки)
    st.metric("Обработано ТЭО", "0", "0")
    st.metric("Среднее время анализа", "—", "—")
    st.metric("Выявлено рисков", "—", "—")

# ═══════════════════════════════════════════════════════════════
# КНОПКА ЗАПУСКА
# ═══════════════════════════════════════════════════════════════
st.divider()

run_button = st.button(
    "🚀 Запустить консилиум",
    type="primary",
    use_container_width=True,
    disabled=not uploaded_file or st.session_state.is_running
)

if run_button and uploaded_file:
    st.session_state.is_running = True
    st.session_state.logs = []
    st.session_state.report = None
    
    # Создаем временный файл для PDF
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(uploaded_file.getbuffer())
        tmp_path = tmp_file.name
    
    try:
        # Копируем в папку TEO для сохранения
        teo_dir = Path("data/01_raw/TEO")
        teo_dir.mkdir(parents=True, exist_ok=True)
        final_path = teo_dir / uploaded_file.name
        shutil.copy(tmp_path, final_path)
        
        # Запускаем консилиум
        with st.spinner("⏳ Консилиум анализирует документ... Это может занять 2-5 минут."):
            # Создаем контейнер для логов
            log_container = st.container()
            
            # Запускаем анализ (упрощенная версия без перехвата логов)
            result = run_due_diligence_council(str(final_path))
            
            # Сохраняем отчет
            st.session_state.report = result.raw
            
            # Сохраняем в файл
            processed_dir = Path("data/02_processed")
            processed_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_filename = f"DD_Report_{Path(uploaded_file.name).stem}_{timestamp}.md"
            report_path = processed_dir / report_filename
            
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(result.raw)
            
            st.session_state.logs.append(f"✅ Отчет сохранен: {report_path}")
    
    except Exception as e:
        st.error(f"❌ Ошибка при анализе: {str(e)}")
        st.session_state.logs.append(f"❌ Ошибка: {str(e)}")
    
    finally:
        # Удаляем временный файл
        os.unlink(tmp_path)
        st.session_state.is_running = False
        st.rerun()

# ═══════════════════════════════════════════════════════════════
# ОТОБРАЖЕНИЕ ЛОГОВ
# ═══════════════════════════════════════════════════════════════
if st.session_state.logs:
    st.subheader("📋 Логи выполнения")
    for log in st.session_state.logs:
        if "✅" in log:
            st.success(log)
        elif "" in log:
            st.error(log)
        else:
            st.info(log)

# ═══════════════════════════════════════════════════════════════
# ОТОБРАЖЕНИЕ ОТЧЕТА
# ═══════════════════════════════════════════════════════════════
if st.session_state.report:
    st.divider()
    st.subheader(" Итоговый отчет Due Diligence")
    
    # Кнопка скачивания
    st.download_button(
        label="⬇️ Скачать отчет (Markdown)",
        data=st.session_state.report,
        file_name=f"DD_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
        mime="text/markdown",
        use_container_width=True
    )
    
    # Отображение отчета
    with st.expander("👁️ Просмотр отчета", expanded=True):
        st.markdown('<div class="report-container">', unsafe_allow_html=True)
        st.markdown(st.session_state.report)
        st.markdown('</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
# ФУТЕР
# ═══════════════════════════════════════════════════════════════
st.divider()
st.markdown("""
<div style="text-align: center; color: #666; font-size: 0.9rem;">
    <p>🏭 Due Diligence Crew v2.0 | Powered by CrewAI + OpenRouter</p>
    <p>Разработано для автоматизированного аудита инвестиционных ТЭО</p>
</div>
""", unsafe_allow_html=True)