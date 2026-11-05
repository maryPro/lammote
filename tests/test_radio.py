import pytest
from unittest.mock import patch
from app.radio import get_radio_queue

@patch("app.radio.ytmusic.get_watch_playlist")
def test_get_radio_queue_deduplication(mock_get_playlist):
    # Мокаем ответ ytmusicapi
    mock_get_playlist.return_value = {
        "tracks": [
            {"videoId": "track1", "title": "Title 1", "artists": [{"name": "Artist A"}], "length": "3:00"},
            {"videoId": "track2", "title": "Title 2", "artists": [{"name": "Artist B"}], "length": "4:00"},
            {"videoId": "track3", "title": "Title 3", "artists": [{"name": "Artist C"}], "length": "5:00"}
        ]
    }
    
    # Передаем track2 в историю
    history = ["track2"]
    queue = get_radio_queue("track1", history, limit=5)
    
    assert len(queue) == 2
    assert queue[0]["video_id"] == "track1"
    assert queue[1]["video_id"] == "track3"
    assert queue[0]["duration_seconds"] == 180

@patch("app.radio.ytmusic.get_watch_playlist")
def test_get_radio_queue_diversity_filter(mock_get_playlist):
    # Треки, где Artist A встречается слишком часто
    mock_get_playlist.return_value = {
        "tracks": [
            {"videoId": "v1", "title": "T1", "artists": [{"name": "Artist A"}]}, # + (Окно: [A])
            {"videoId": "v2", "title": "T2", "artists": [{"name": "Artist A"}]}, # Пропуск (A в окне)
            {"videoId": "v3", "title": "T3", "artists": [{"name": "Artist B"}]}, # + (Окно: [A, B])
            {"videoId": "v4", "title": "T4", "artists": [{"name": "Artist C"}]}, # + (Окно: [A, B, C])
            {"videoId": "v5", "title": "T5", "artists": [{"name": "Artist A"}]}, # Пропуск (A еще в окне)
            {"videoId": "v6", "title": "T6", "artists": [{"name": "Artist D"}]}, # + (Окно: [B, C, D]) - A выпадает
            {"videoId": "v7", "title": "T7", "artists": [{"name": "Artist A"}]}, # + (Окно: [C, D, A]) - Снова можно
        ]
    }
    
    queue = get_radio_queue("v1", history=[], limit=5)
    
    assert len(queue) == 5
    # Проверяем, что фильтр пропустил v2 и v5
    expected_ids = ["v1", "v3", "v4", "v6", "v7"]
    result_ids = [t["video_id"] for t in queue]
    
    assert result_ids == expected_ids