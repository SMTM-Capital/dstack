def get_cudo_pricing(total_price, disk_size) -> float:
    if disk_size is None:
        disk_size = 1
    disk_price_per_gb_per_hr = float(0.000107)  # Todo rate depends on region
    updated_price = total_price - disk_price_per_gb_per_hr + (disk_price_per_gb_per_hr * disk_size)
    return updated_price
