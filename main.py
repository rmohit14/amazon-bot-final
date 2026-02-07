# main.py

def calculate_discount(deal_price_str, original_price_str):
    deal_price_num = _clean_price(deal_price_str)
    original_price_num = _clean_price(original_price_str)
    discount_percent = 0

    if deal_price_num and original_price_num and original_price_num > deal_price_num:
        discount_percent = round(((original_price_num - deal_price_num) / original_price_num) * 100)

    # Fallback: use extracted discount percent if available
    if discount_percent == 0:
        dp_from_page = details.get("discount_percent")
        if isinstance(dp_from_page, int) and 0 <= dp_from_page <= 100:
            discount_percent = dp_from_page

    return discount_percent
