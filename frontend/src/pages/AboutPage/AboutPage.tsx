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
            Загрузите фото с регистратора или смартфона — найдём ямы, трещины и выбоины за секунды.
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
                Модель YOLOv8 обработает изображение за 300-500 мс. На фото появятся цветные рамки вокруг каждого найденного дефекта.
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
                <h3>Выбоина (minor)</h3>
              </div>
              <p>Небольшие углубления и неровности. Меньше всего разрушение — лёгкий ремонт.</p>
              <span className="defect-type-severity">Легко</span>
            </div>
          </div>
        </section>

        <section className="about-section">
          <h2 className="section-title">Технологии</h2>
          <div className="tech-grid">
            <div className="tech-item">YOLOv8 - детекция дефектов</div>
            <div className="tech-item">FastAPI - backend API</div>
            <div className="tech-item">Docker - деплой</div>
            <div className="tech-item">React + TypeScript - frontend</div>
            <div className="tech-item">PostgreSQL - хранение данных</div>
            <div className="tech-item">Redis - кэширование</div>
          </div>
        </section>
      </div>
    </div>
  )
}