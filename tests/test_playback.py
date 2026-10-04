import numpy as np
import soundfile as sf
from PySide6.QtCore import QUrl
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer


def test_qt_decodes_generated_wav(qtbot, tmp_path):
    """Verify media loading, not human-audible output or speech naturalness."""
    path = tmp_path / 'playback.wav'
    sf.write(path, np.zeros(4800), 48000, subtype='PCM_24')
    player = QMediaPlayer()
    output = QAudioOutput()
    player.setAudioOutput(output)
    player.setSource(QUrl.fromLocalFile(str(path)))
    qtbot.waitUntil(lambda: player.mediaStatus() in (QMediaPlayer.MediaStatus.LoadedMedia, QMediaPlayer.MediaStatus.InvalidMedia), timeout=15000)
    assert player.mediaStatus() == QMediaPlayer.MediaStatus.LoadedMedia
    assert player.duration() == 100
    player.stop()
