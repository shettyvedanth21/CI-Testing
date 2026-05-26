from src.pdf.charts import (
    idle_cost_bar,
    offhours_cost_bar,
    overconsumption_cost_bar,
    total_energy_bar,
)


def generate_waste_pdf(payload: dict) -> bytes:
    from src.pdf.builder import generate_waste_pdf as _generate_waste_pdf

    return _generate_waste_pdf(payload)


async def async_generate_waste_pdf(payload: dict) -> bytes:
    from src.pdf.builder import async_generate_waste_pdf as _async_generate_waste_pdf

    return await _async_generate_waste_pdf(payload)


__all__ = [
    "generate_waste_pdf",
    "async_generate_waste_pdf",
    "idle_cost_bar",
    "offhours_cost_bar",
    "overconsumption_cost_bar",
    "total_energy_bar",
]
