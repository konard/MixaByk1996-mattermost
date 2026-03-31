import React from 'react';
import { useStore } from '../store/useStore';
import { formatCurrency, getInitials, getAvatarColor } from '../utils/helpers';

function ProcurementSlider() {
  const { procurements, selectProcurement } = useStore();

  const handleCardClick = (procurement) => {
    selectProcurement(procurement.id);
  };

  if (procurements.length === 0) {
    return (
      <section className="procurement-slider">
        <h2 className="slider-title">Активные закупки</h2>
        <div className="slider-container">
          <div className="p-md text-muted">Нет активных закупок</div>
        </div>
      </section>
    );
  }

  return (
    <section className="procurement-slider">
      <h2 className="slider-title">Активные закупки</h2>
      <div className="slider-container">
        {procurements.map((procurement) => {
          const daysLeft = procurement.deadline
            ? Math.max(0, Math.ceil((new Date(procurement.deadline) - new Date()) / (1000 * 60 * 60 * 24)))
            : null;

          return (
            <div
              key={procurement.id}
              className="procurement-card"
              onClick={() => handleCardClick(procurement)}
            >
              <div className="procurement-title">{procurement.title}</div>
              <div className="procurement-info">{procurement.city || 'Город не указан'}</div>
              <div className="procurement-progress">
                <div
                  className="procurement-progress-bar"
                  style={{ width: `${procurement.progress || 0}%` }}
                />
              </div>
              <div className="procurement-stats">
                <span>
                  {formatCurrency(procurement.current_amount)} / {formatCurrency(procurement.target_amount)}
                </span>
                {daysLeft !== null && <span>{daysLeft} дн.</span>}
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}

export default ProcurementSlider;
