def get_cudo_pricing(total_price,disk_size)->float:
    if disk_size is None:
        disk_size=1
    price_per_disk=float(0.00012)
    updated_price=total_price-price_per_disk+(price_per_disk*disk_size)
    return updated_price