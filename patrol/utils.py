import math

POS_RONDA_LATITUDE  = -0.474271
POS_RONDA_LONGITUDE = 117.140290
RADIUS_ABSEN_METER  = 4000


def hitung_jarak_meter(lat1, lon1, lat2, lon2):
    R    = 6_371_000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a    = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def validasi_lokasi(latitude, longitude):
    jarak = hitung_jarak_meter(
        POS_RONDA_LATITUDE, POS_RONDA_LONGITUDE,
        float(latitude), float(longitude)
    )
    return jarak <= RADIUS_ABSEN_METER, round(jarak, 1)