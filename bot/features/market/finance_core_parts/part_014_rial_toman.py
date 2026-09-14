# Auto-split part 14: rial_toman
def rial_toman(amount: float, to_toman: bool = True) -> str:
    if to_toman:
        return f"💵 {pn(f'{amount:,.0f}')} ریال = **{pn(f'{amount/10:,.0f}')} تومان**"
    return f"💵 {pn(f'{amount:,.0f}')} تومان = **{pn(f'{amount*10:,.0f}')} ریال**"
