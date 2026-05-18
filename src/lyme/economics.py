"""Economic superiority: local vs cloud cost comparison."""

CLOUD_PRICING = {
    "claude_sonnet": {"input_per_m": 3.0, "output_per_m": 15.0, "model": "Claude 3.5 Sonnet"},
    "claude_haiku": {"input_per_m": 0.25, "output_per_m": 1.25, "model": "Claude 3.5 Haiku"},
    "gpt4o": {"input_per_m": 2.50, "output_per_m": 10.0, "model": "GPT-4o"},
    "gpt4o_mini": {"input_per_m": 0.15, "output_per_m": 0.60, "model": "GPT-4o mini"},
}

LOCAL_PRICING = {
    "local_7b": {"hardware_cost": 2000, "watts": 150, "tokens_per_sec": 40, "model": "7B local (e.g., Qwen2.5-Coder)"},
    "local_13b": {"hardware_cost": 3500, "watts": 250, "tokens_per_sec": 25, "model": "13B local"},
    "local_70b": {"hardware_cost": 8000, "watts": 500, "tokens_per_sec": 10, "model": "70B local (quantized)"},
}


class EconomicReport:
    def __init__(self):
        self._results = {}

    def compare(self, monthly_tokens: int = 10_000_000, local_config: str = "local_7b",
                cloud_model: str = "claude_sonnet", hardware_amort_years: int = 3,
                dev_salary_monthly: float = 15000, dev_time_savings_pct: float = 30) -> dict:
        local = LOCAL_PRICING[local_config]
        cloud = CLOUD_PRICING[cloud_model]

        cloud_monthly = self._cloud_cost(monthly_tokens, cloud)
        local_hw_amort = local["hardware_cost"] / (hardware_amort_years * 12)
        local_energy = self._energy_cost(local["watts"], monthly_tokens / local["tokens_per_sec"])
        local_total = local_hw_amort + local_energy

        dev_savings = dev_salary_monthly * (dev_time_savings_pct / 100)
        cloud_dev_savings = dev_salary_monthly * (dev_time_savings_pct / 100 * 0.8)

        self._results = {
            "comparison": {
                "cloud_monthly_cost": round(cloud_monthly, 2),
                "local_monthly_cost": round(local_total, 2),
                "monthly_savings": round(cloud_monthly - local_total, 2),
                "annual_savings": round((cloud_monthly - local_total) * 12, 2),
                "savings_pct": round((1 - local_total / max(cloud_monthly, 0.01)) * 100, 1),
            },
            "cloud": {
                "model": cloud["model"],
                "monthly_api_cost": round(cloud_monthly, 2),
            },
            "local": {
                "model": local["model"],
                "hardware_cost": local["hardware_cost"],
                "monthly_amortization": round(local_hw_amort, 2),
                "monthly_energy": round(local_energy, 2),
                "monthly_total": round(local_total, 2),
                "break_even_months": round(local["hardware_cost"] / max(cloud_monthly - local_total, 0.01), 1),
            },
            "developer_productivity": {
                "monthly_dev_cost": dev_salary_monthly,
                "time_savings_pct": dev_time_savings_pct,
                "monthly_dev_savings_cloud": round(cloud_dev_savings, 2),
                "monthly_dev_savings_local": round(dev_savings, 2),
                "local_advantage_vs_cloud_dev": round(dev_savings - cloud_dev_savings, 2),
            },
            "energy": {
                "watts": local["watts"],
                "monthly_kwh": round(local["watts"] * (monthly_tokens / local["tokens_per_sec"]) / 3600 / 1000, 2),
                "monthly_cost": round(local_energy, 2),
            },
            "params": {
                "monthly_tokens": monthly_tokens,
                "hardware_amort_years": hardware_amort_years,
            },
        }
        return self._results

    def _cloud_cost(self, tokens: int, pricing: dict) -> float:
        input_tokens = tokens * 0.75
        output_tokens = tokens * 0.25
        input_cost = (input_tokens / 1_000_000) * pricing["input_per_m"]
        output_cost = (output_tokens / 1_000_000) * pricing["output_per_m"]
        return input_cost + output_cost

    def _energy_cost(self, watts: int, runtime_seconds: float, rate_per_kwh: float = 0.12) -> float:
        kwh = watts * runtime_seconds / 3600 / 1000
        return kwh * rate_per_kwh

    def get_report_text(self) -> str:
        if not self._results:
            return "Run compare() first."
        r = self._results
        lines = []
        lines.append("=" * 55)
        lines.append("  LYME ECONOMIC ANALYSIS")
        lines.append("=" * 55)
        c = r["comparison"]
        lines.append(f"  Cloud:  ${c['cloud_monthly_cost']:>8.2f}/mo  ({r['cloud']['model']})")
        lines.append(f"  Local:  ${c['local_monthly_cost']:>8.2f}/mo  ({r['local']['model']})")
        lines.append(f"  Save:   ${c['monthly_savings']:>8.2f}/mo  ({c['savings_pct']}%)")
        lines.append(f"  Annual: ${c['annual_savings']:>8.2f}/yr")
        lines.append("")
        lines.append(f"  Hardware:  ${r['local']['hardware_cost']}")
        lines.append(f"  Break-even: {r['local']['break_even_months']} months")
        lines.append(f"  Energy:    ${r['local']['monthly_energy']}/mo ({r['energy']['watts']}W)")
        lines.append("")
        lines.append("  Developer Productivity:")
        lines.append(f"    Dev cost:     ${r['developer_productivity']['monthly_dev_cost']}/mo")
        lines.append(f"    Time savings: {r['developer_productivity']['time_savings_pct']}%")
        lines.append(f"    Local saves:  ${r['developer_productivity']['local_advantage_vs_cloud_dev']}/mo vs cloud API")
        lines.append("=" * 55)
        return "\n".join(lines)
