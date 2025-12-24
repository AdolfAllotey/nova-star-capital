def calculate_average_volume(volumes):
    """
    Calcule la moyenne des volumes fournis.

    Args:
        volumes (list[float]): liste des volumes

    Returns:
        float: volume moyen ou 0 si liste vide
    """
    if not volumes:
        return 0.0
    return sum(volumes) / len(volumes)

def normalize_volume(volume, max_volume):
    """
    Normalise un volume par rapport au volume max donné.

    Args:
        volume (float): volume à normaliser
        max_volume (float): volume maximal de référence

    Returns:
        float: volume normalisé entre 0 et 1
    """
    if max_volume <= 0:
        return 0.0
    return volume / max_volume

def filter_high_volume_tokens(token_volumes, threshold=0.5):
    """
    Filtre les tokens dont le volume normalisé est supérieur au seuil.

    Args:
        token_volumes (dict): dict token->volume
        threshold (float): seuil minimum (0-1)

    Returns:
        list: tokens filtrés
    """
    max_vol = max(token_volumes.values()) if token_volumes else 0
    return [token for token, vol in token_volumes.items() if normalize_volume(vol, max_vol) >= threshold]