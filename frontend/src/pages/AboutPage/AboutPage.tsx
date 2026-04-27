import './AboutPage.css'

export function AboutPage() {
  return (
    <div className="about-page">
      <div className="container">
        <div className="about-hero">
          <div className="about-logo">
            <span className="logo-letters">RC</span>
          </div>
          <h1 className="about-title">RoadCheck</h1>
          <p className="about-subtitle">
            Система автоматической оценки состояния дорожного покрытия.
            Загрузите фото с регистратора или смартфона — найдём ямы, трещины и другие заметные
            повреждения покрытия.
          </p>
        </div>

        <section className="about-section">
          <h2 className="section-title">Как это работает</h2>
          <div className="steps-grid">
            <div className="step-card">
              <div className="step-number">01</div>
              <h3 className="step-title">Загрузите фото дороги</h3>
              <p className="step-description">
                JPG или PNG до 10 МБ. Лучше всего подходят снимки сверху вниз при хорошем освещении. 
                Подходят фото с регистратора, дрона или смартфона.
              </p>
            </div>
            
            <div className="step-card">
              <div className="step-number">02</div>
              <h3 className="step-title">Нажмите «Запустить анализ»</h3>
              <p className="step-description">
                Backend запускает детекцию дефектов и возвращает координаты найденных зон. Если
                в backend подключены веса YOLOv8, анализ выполняется реальной моделью; в режиме
                разработки можно оставить mock-обработку.
              </p>
            </div>
            
            <div className="step-card step-card--wide">
              <div className="step-number">03</div>
              <h3 className="step-title">Получите результат и скачайте отчёт</h3>
              <p className="step-description">
                Список дефектов с типом, точностью и координатами. Экспорт в PDF или JSON. Все результаты сохраняются в истории.
              </p>
            </div>
          </div>
        </section>

        <section className="about-section">
          <h2 className="section-title">Типы дефектов</h2>
          <div className="defects-types">
            <div className="defect-type-card">
              <div className="defect-type-header critical">
                <span className="defect-type-icon">●</span>
                <h3>Яма (pothole)</h3>
              </div>
              <p>Разрушение верхнего слоя покрытия. Требует срочного ремонта. Опасно для транспорта.</p>
              <span className="defect-type-severity">Критично</span>
            </div>
            
            <div className="defect-type-card">
              <div className="defect-type-header warning">
                <span className="defect-type-icon">●</span>
                <h3>Трещина (crack)</h3>
              </div>
              <p>Продольные или поперечные трещины в асфальте. При отсутствии ремонта приводят к выбоинам и ямам.</p>
              <span className="defect-type-severity">Средне</span>
            </div>
            
            <div className="defect-type-card">
              <div className="defect-type-header info">
                <span className="defect-type-icon">●</span>
                <h3>Сетчатая трещина (alligator crack)</h3>
              </div>
              <p>
                Один из типов разрушения покрытия в датасете RDD2022. В интерфейсе такие случаи
                объединяются с остальными трещинами в класс <code>crack</code>.
              </p>
              <span className="defect-type-severity">Контроль</span>
            </div>
          </div>
        </section>

        <section className="about-section">
          <h2 className="section-title">Технологии</h2>
          <div className="tech-grid">
            <div className="tech-item">YOLOv8 / Ultralytics - детекция дефектов</div>
            <div className="tech-item">FastAPI - backend API</div>
            <div className="tech-item">Docker - деплой</div>
            <div className="tech-item">React + TypeScript - frontend</div>
            <div className="tech-item">PostgreSQL - хранение данных</div>
            <div className="tech-item">OpenCV - mock-анализ и предобработка</div>
          </div>
        </section>
      </div>
    </div>
  )
}
