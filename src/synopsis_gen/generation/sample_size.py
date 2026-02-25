import math

def be_sample_size_2x2(cv_intra: float, power: float = 0.8, alpha: float = 0.05, gmr: float = 0.95) -> int:
    cv_intra = max(1e-6, float(cv_intra))
    power = float(power)
    alpha = float(alpha)
    gmr = float(gmr)

    sw = math.sqrt(math.log(cv_intra**2 + 1.0))
    theta = math.log(1.25)
    delta = max(theta - abs(math.log(gmr)), 1e-6)

    try:
        from statistics import NormalDist
        z = NormalDist()
        z_alpha = z.inv_cdf(1 - alpha)
        z_beta = z.inv_cdf(power)
    except Exception:
        z_alpha = 1.6448536269514722
        z_beta = 0.8416212335729143

    n_per_seq = 2 * ((z_alpha + z_beta) * sw / delta) ** 2
    n_total = int(math.ceil(n_per_seq) * 2)
    if n_total % 2 != 0:
        n_total += 1
    return max(n_total, 12)

def apply_dropout(n_total: int, dropout: float) -> int:
    dropout = min(max(float(dropout), 0.0), 0.6)
    n = int(math.ceil(n_total / max(1.0 - dropout, 1e-6)))
    if n % 2 != 0:
        n += 1
    return n