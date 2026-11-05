from ytmusicapi import YTMusic

# Инициализируем клиент ytmusicapi
ytmusic = YTMusic()

def _parse_duration(length_str: str) -> int:
    """Конвертирует строку формата 'M:SS' или 'H:MM:SS' в секунды."""
    if not length_str:
        return 0
    
    parts = length_str.split(":")
    try:
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        elif len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    except ValueError:
        return 0
    return 0

def get_radio_queue(video_id: str, history: list[str], limit: int = 5) -> list[dict]:
    try:
        raw_playlist = ytmusic.get_watch_playlist(videoId=video_id)
    except Exception:
        return []

    tracks = raw_playlist.get("tracks", [])
    queue = []
    recent_artists = []  # Окно из 3 последних добавленных артистов

    for track in tracks:
        if len(queue) >= limit:
            break

        t_vid = track.get("videoId")
        if not t_vid:
            continue
        
        # 1. Дедупликация: пропускаем треки, которые уже играли или уже добавлены
        if t_vid in history or any(q["video_id"] == t_vid for q in queue):
            continue

        artists = track.get("artists", [])
        artist_name = artists[0]["name"] if artists else "Unknown Artist"

        # 2. Diversity filter: 1 трек артиста на каждые 4 трека (окно размером 3)
        if artist_name in recent_artists:
            continue
        
        # Формируем трек
        thumbnails = track.get("thumbnail", [])
        thumbnail_url = thumbnails[-1]["url"] if thumbnails else ""
        
        track_dict = {
            "video_id": t_vid,
            "title": track.get("title", "Unknown Title"),
            "artist": artist_name,
            "duration_seconds": _parse_duration(track.get("length", "0:00")),
            "thumbnail_url": thumbnail_url
        }

        queue.append(track_dict)
        recent_artists.append(artist_name)
        
        # Поддерживаем размер окна
        if len(recent_artists) >= 4:
            recent_artists.pop(0)

    return queue