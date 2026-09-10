import math
import random
import pygame

pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)


class SoundManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_sounds()
        return cls._instance

    def _init_sounds(self):
        self.sounds = {}

        # Основные звуки (без изменений)
        self.sounds['shoot'] = self._generate_sound(880, 0.1, 0.2)
        self.sounds['hit'] = self._generate_sound(440, 0.2, 0.3)
        self.sounds['explosion'] = self._generate_sound(200, 0.5, 0.4)
        self.sounds['pickup'] = self._generate_sound(1200, 0.15, 0.3)
        self.sounds['dash'] = self._generate_sound(600, 0.2, 0.3)
        self.sounds['wall'] = self._generate_sound(300, 0.3, 0.3)
        self.sounds['repair'] = self._generate_sound(500, 0.3, 0.4)
        self.sounds['boss'] = self._generate_sound(150, 1.0, 0.5)
        self.sounds['quest'] = self._generate_sound(800, 0.3, 0.3)
        self.sounds['levelup'] = self._generate_sound(1000, 0.4, 0.4)
        self.sounds['achievement'] = self._generate_sound(1500, 0.5, 0.4)

        # НОВЫЕ ЗВУКИ (20+)
        self.sounds['shotgun'] = self._generate_sound(250, 0.2, 0.5)
        self.sounds['laser'] = self._generate_sound(1800, 0.15, 0.3)
        self.sounds['plasma'] = self._generate_sound(1400, 0.25, 0.35)
        self.sounds['rocket'] = self._generate_sound(150, 0.3, 0.5)
        self.sounds['minigun'] = self._generate_sound(700, 0.05, 0.3)
        self.sounds['flamethrower'] = self._generate_sound(300, 0.3, 0.4)
        self.sounds['ice_shot'] = self._generate_sound(2000, 0.1, 0.25)
        self.sounds['shock'] = self._generate_sound(900, 0.15, 0.35)
        self.sounds['gravity'] = self._generate_sound(100, 0.5, 0.4)
        self.sounds['teleport'] = self._generate_sound(2500, 0.3, 0.3)
        self.sounds['shield_break'] = self._generate_sound(400, 0.3, 0.4)
        self.sounds['shield_up'] = self._generate_sound(800, 0.2, 0.3)
        self.sounds['heal'] = self._generate_sound(600, 0.4, 0.3)
        self.sounds['energy_pickup'] = self._generate_sound(1300, 0.2, 0.3)
        self.sounds['scrap_pickup'] = self._generate_sound(500, 0.1, 0.2)
        self.sounds['crystal_pickup'] = self._generate_sound(2000, 0.3, 0.3)
        self.sounds['weapon_pickup'] = self._generate_sound(1600, 0.4, 0.35)
        self.sounds['enemy_death'] = self._generate_sound(300, 0.3, 0.35)
        self.sounds['boss_roar'] = self._generate_sound(100, 1.5, 0.6)
        self.sounds['door_open'] = self._generate_sound(500, 0.3, 0.3)
        self.sounds['door_locked'] = self._generate_sound(200, 0.2, 0.3)
        self.sounds['hazard'] = self._generate_sound(350, 0.2, 0.3)
        self.sounds['meteor'] = self._generate_sound(120, 0.8, 0.5)
        self.sounds['thunder'] = self._generate_sound(60, 1.0, 0.6)
        self.sounds['rain_ambient'] = self._generate_noise(0.5, 0.1)
        self.sounds['wind'] = self._generate_noise(1.0, 0.15)
        self.sounds['acid_burn'] = self._generate_sound(200, 0.2, 0.25)
        self.sounds['drone_summon'] = self._generate_sound(1100, 0.4, 0.3)
        self.sounds['drone_attack'] = self._generate_sound(750, 0.15, 0.3)
        self.sounds['mutation'] = self._generate_sound(500, 0.6, 0.4)
        self.sounds['crafting'] = self._generate_sound(900, 0.3, 0.3)
        self.sounds['shop_buy'] = self._generate_sound(1000, 0.2, 0.3)
        self.sounds['shop_sell'] = self._generate_sound(800, 0.2, 0.25)
        self.sounds['quest_complete'] = self._generate_sound(1200, 0.5, 0.4)
        self.sounds['story_event'] = self._generate_sound(700, 0.8, 0.35)
        self.sounds['phoenix_alarm'] = self._generate_sound(400, 1.0, 0.5)
        self.sounds['genesis_voice'] = self._generate_sound(120, 1.5, 0.4)
        self.sounds['player_death'] = self._generate_sound(250, 1.0, 0.5)
        self.sounds['respawn'] = self._generate_sound(800, 0.6, 0.4)
        self.sounds['combo_break'] = self._generate_sound(300, 0.3, 0.3)
        self.sounds['critical_hit'] = self._generate_sound(1500, 0.1, 0.4)

        # Новые жуткие звуки для атмосферы
        self.sounds['evil_laugh'] = self._generate_laugh(duration=1.5, pitch=0.7)
        self.sounds['mechanical_laugh'] = self._generate_laugh(duration=2.0, pitch=1.1)
        self.sounds['whisper'] = self._generate_whisper(duration=1.5)
        self.sounds['glitch'] = self._generate_glitch(duration=0.3)
        self.sounds['heartbeat'] = self._generate_heartbeat(duration=1.2)

        # Музыка
        self.music_channel = pygame.mixer.Channel(0)
        self.current_music = None
        self.music_volume = 0.4

        # Инициализация музыки
        self._init_music()

    def _generate_sound(self, frequency: float, duration: float, volume: float = 0.3) -> pygame.mixer.Sound:
        """Генерация звука с затуханием."""
        sample_rate = 22050
        n_samples = int(sample_rate * duration)
        arr = []
        for i in range(n_samples):
            t = i / sample_rate
            # Затухание
            envelope = 1 - (i / n_samples) ** 0.5
            value = int(volume * envelope * 32767 * math.sin(2 * math.pi * frequency * t))
            arr.append(value & 0xff)
            arr.append((value >> 8) & 0xff)
        return pygame.mixer.Sound(buffer=bytes(arr))

    def _generate_noise(self, duration: float, volume: float = 0.2) -> pygame.mixer.Sound:
        """Генерация шума (для дождя, ветра)."""
        sample_rate = 22050
        n_samples = int(sample_rate * duration)
        arr = []
        for i in range(n_samples):
            envelope = 1 - (i / n_samples) ** 0.3
            value = int(volume * envelope * 32767 * random.uniform(-1, 1))
            arr.append(value & 0xff)
            arr.append((value >> 8) & 0xff)
        return pygame.mixer.Sound(buffer=bytes(arr))

    def _generate_laugh(self, duration=1.5, pitch=1.0):
        """Синтезированный смех."""
        sample_rate = 22050
        n_samples = int(sample_rate * duration)
        arr = []
        syllable_duration = 0.12 * pitch
        pause_duration = 0.06 * pitch

        for i in range(n_samples):
            t = i / sample_rate
            local_t = t % (syllable_duration + pause_duration)
            if local_t < syllable_duration:
                base_freq = 400 * pitch + (i % 3) * 100
                freq = base_freq * (1 + 0.3 * math.sin(local_t * 30))
                env = math.sin(math.pi * local_t / syllable_duration)
                wave = math.sin(2 * math.pi * freq * local_t)
                wave = math.tanh(0.5 * wave)  # лёгкое искажение
                value = wave * env
            else:
                value = 0.0

            global_env = 1.0 if t < duration - 0.2 else max(0.0, (duration - t) / 0.2)
            final = int(32767 * 0.6 * value * global_env)
            arr.append(final & 0xff)
            arr.append((final >> 8) & 0xff)

        return pygame.mixer.Sound(buffer=bytes(arr))

    def _generate_whisper(self, duration=1.5):
        """Шёпот."""
        sample_rate = 22050
        n_samples = int(sample_rate * duration)
        arr = []
        for i in range(n_samples):
            t = i / sample_rate
            noise = random.uniform(-1, 1)
            env = 0.5 + 0.5 * math.sin(2 * math.pi * 0.5 * t)
            value = 0.3 * noise * env
            arr.append(int(value * 32767) & 0xff)
            arr.append((int(value * 32767) >> 8) & 0xff)
        return pygame.mixer.Sound(buffer=bytes(arr))

    def _generate_glitch(self, duration=0.3):
        """Цифровой сбой."""
        sample_rate = 22050
        n_samples = int(sample_rate * duration)
        arr = []
        for i in range(n_samples):
            t = i / sample_rate
            if random.random() < 0.7:
                freq = random.randint(100, 4000)
            else:
                freq = 200
            envelope = 1 - (i / n_samples)
            value = int(0.4 * envelope * 32767 * random.uniform(-1, 1) * math.sin(2 * math.pi * freq * t))
            arr.append(value & 0xff)
            arr.append((value >> 8) & 0xff)
        return pygame.mixer.Sound(buffer=bytes(arr))

    def _generate_heartbeat(self, duration=1.2):
        """Двойной удар сердца."""
        sample_rate = 22050
        n_samples = int(sample_rate * duration)
        arr = []
        beat_times = [0.0, 0.25, 0.5, 0.75]
        for i in range(n_samples):
            t = i / sample_rate
            value = 0.0
            for bt in beat_times:
                if t >= bt and t < bt + 0.1:
                    freq = 60
                    env = math.sin(math.pi * (t - bt) / 0.1)
                    value += math.sin(2 * math.pi * freq * (t - bt)) * env
            final = int(0.7 * 32767 * value)
            arr.append(final & 0xff)
            arr.append((final >> 8) & 0xff)
        return pygame.mixer.Sound(buffer=bytes(arr))

    def _init_music(self):
        """Инициализация фоновой музыки."""
        self.music_tracks = {
            'menu': self._generate_music_track(90, 'calm'),
            'combat': self._generate_music_track(120, 'intense'),
            'exploration': self._generate_music_track(70, 'ambient'),
            'boss': self._generate_music_track(140, 'epic'),
        }

    def _generate_music_track(self, bpm: int, mood: str = 'calm') -> pygame.mixer.Sound:
        """Генерация фоновой музыки (оригинальная, без изменений)."""
        sample_rate = 22050
        duration = 8.0  # 8 секунд
        n_samples = int(sample_rate * duration)
        arr = []

        beat_duration = 60.0 / bpm
        notes = {
            'calm': [261.63, 293.66, 329.63, 392.00, 440.00, 523.25],  # До-мажор
            'intense': [220.00, 277.18, 329.63, 440.00, 554.37],  # Минор
            'ambient': [196.00, 246.94, 293.66, 349.23],  # Медленные
            'epic': [164.81, 196.00, 246.94, 293.66, 329.63, 392.00],  # Эпичные
        }
        note_freqs = notes.get(mood, notes['calm'])

        for i in range(n_samples):
            t = i / sample_rate

            # Мелодия
            note_index = int(t / beat_duration) % len(note_freqs)
            note_freq = note_freqs[note_index]

            # Основная нота
            value = math.sin(2 * math.pi * note_freq * t)

            # Басовый тон
            bass = math.sin(2 * math.pi * note_freq / 2 * t) * 0.5

            # Гармоника
            harmonic = math.sin(2 * math.pi * note_freq * 2 * t) * 0.3

            # Смешивание
            mixed = value + bass + harmonic

            # Огибающая
            envelope = 0.7 + 0.3 * math.sin(math.pi * t / beat_duration)

            # Громкость зависит от настроения
            if mood == 'combat' or mood == 'epic':
                volume = 0.5
            else:
                volume = 0.35

            final = int(volume * envelope * 32767 * mixed / 3)
            arr.append(final & 0xff)
            arr.append((final >> 8) & 0xff)

        return pygame.mixer.Sound(buffer=bytes(arr))

    def play(self, name: str):
        """Воспроизведение звука."""
        if name in self.sounds:
            self.sounds[name].play()

    def play_music(self, track_name: str = 'exploration'):
        """Воспроизведение фоновой музыки."""
        if track_name in self.music_tracks:
            if self.current_music != track_name:
                self.current_music = track_name
                self.music_channel.stop()
                self.music_channel.play(self.music_tracks[track_name], loops=-1)
                self.music_channel.set_volume(self.music_volume)

    def stop_music(self):
        """Остановка музыки."""
        self.music_channel.stop()
        self.current_music = None

    def set_music_volume(self, volume: float):
        """Установка громкости музыки."""
        self.music_volume = max(0.0, min(1.0, volume))
        self.music_channel.set_volume(self.music_volume)

    def set_volume(self, volume: float):
        """Установка общей громкости."""
        for sound in self.sounds.values():
            sound.set_volume(volume)