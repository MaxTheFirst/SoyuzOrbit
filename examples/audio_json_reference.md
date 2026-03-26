# Audio JSON Reference

Этот файл описывает все `audio_*.json`-схемы, которые сейчас лежат в `examples/`.

Если нужен не каталог пресетов, а физика базовых элементов ядра, см. `examples/audio_component_physics.md`.

На момент составления справочника в каталоге `examples` есть 22 аудио-JSON:

- `audio_identity_passthrough.json`
- `audio_wave_controls.json`
- `audio_music_fx_rack.json`
- `audio_ghost_envelope.json`
- `audio_polarity_bloom.json`
- `audio_syllable_freeze.json`
- `audio_talking_bloom.json`
- `audio_speech_soft_drive.json`
- `audio_speech_grit_asym.json`
- `audio_robot_gate.json`
- `audio_breathing_mix.json`
- `audio_lyric_radio_crunch.json`
- `audio_vocal_stutter_mix.json`
- `audio_vocal_halo_smear.json`
- `audio_five_band_notch.json`
- `audio_bass_boost_low_shelf.json`
- `audio_redplate_distortion.json`
- `audio_crystal_delay_smear.json`
- `audio_bitcrusher_hold_matrix.json`
- `audio_speech_telephone_bandpass.json`
- `audio_speech_robot_bitcrush.json`
- `audio_speech_megaphone_distortion.json`

## 1. Общие правила для всех аудио-схем

### 1.1. Что именно делает `run_audio_sim.py`

При запуске через:

```bash
./.venv/bin/python run_audio_sim.py input.mp3 examples/some_audio.json out.wav --sample-rate 16000 --peak-voltage 1.0
```

происходит следующее:

- входной файл декодируется и подается в `Audio File Source`;
- `--sample-rate` задает реальную частоту дискретизации симуляции;
- `dt_s` при таком запуске берется как `1 / sample_rate`;
- длительность берется из входного файла, если не указан `--duration`;
- `--peak-voltage` переопределяет амплитуду `Audio File Source`;
- если в схеме несколько `Audio Sink`, нужен `--sink`;
- если в схеме несколько `Audio File Source`, нужен `--source`.

Важно:

- `settings.dt_s` и `settings.duration_s` внутри JSON удобны для GUI и прямого запуска проекта как схемы;
- в `run_audio_sim.py` они не являются главным источником правды, потому что CLI выставляет свои значения.

### 1.2. Что значат общие аудио-параметры

У `Audio File Source`:

- `file_path`: обычно пустой в JSON, потому что путь подставляет `run_audio_sim.py`;
- `internal_resistance_ohm`: внутреннее сопротивление источника;
- `peak_voltage_v`: амплитуда входного сигнала в вольтах;
- `channel`: какой канал брать из исходного файла;
- `normalize`: нормализовать ли входной файл при загрузке;
- `target_sample_rate_hz`: целевая частота для ресемплинга.

У `Audio Sink`:

- `output_gain`: масштабирует снимаемый выход;
- `dc_block`: убирает медленную DC-составляющую перед записью;
- `input_resistance_ohm`: входная нагрузка на схему.

### 1.3. Практические правила по `sample-rate`

- `8000 Hz`: лоу-фай режим, эффекты грубее, речь и верх теряются быстрее.
- `16000 Hz`: хороший базовый режим для речи и большинства новых пресетов.
- `22050 Hz` и выше: лучше для более прозрачной или более детальной обработки.

Если цель именно сохранить разборчивость речи, лучше стартовать не с `8000`, а с `16000`.

### 1.4. Что смотреть в графиках

В GUI и в `examples/audio_compare_analysis.py` особенно полезны:

- `Аудио: напряжение вход/выход`
- `Аудио: zoom формы волны`
- `Аудио: огибающая`
- `Аудио: спектр`
- `Аудио: transfer cloud`

Быстрое правило:

- если меняется в основном спектр, это ближе к фильтру;
- если облако `input -> output` изгибается, это нелинейность;
- если сильно меняется огибающая и хвосты, это memory-эффект;
- если в zoom появляются ступени, это sample/hold-подобный эффект.

### 1.5. Как получить `comparison.png` и `metrics.json`

Пример:

```bash
./.venv/bin/python run_audio_sim.py input.mp3 examples/audio_speech_grit_asym.json /tmp/grit.wav --sample-rate 16000 --peak-voltage 1.0
./.venv/bin/python examples/audio_compare_analysis.py input.mp3 /tmp/grit.wav /tmp/grit-analysis --sample-rate 16000 --normalize-input
```

На выходе будут:

- `/tmp/grit-analysis/comparison.png`
- `/tmp/grit-analysis/metrics.json`

## 2. Категории схем

Чтобы не потеряться, полезно разделить все JSON на пять групп:

- Базовые и учебные: `identity`, `wave_controls`, `music_fx_rack`
- Envelope и memory-эффекты: `ghost`, `syllable_freeze`, `talking_bloom`, `breathing_mix`, `crystal_delay_smear`
- Нелинейное окрашивание голоса и музыки: `speech_soft_drive`, `speech_grit_asym`, `lyric_radio_crunch`, `redplate_distortion`, `vocal_halo_smear`
- Ритмическое и clocked-искажение: `robot_gate`, `vocal_stutter_mix`, `bitcrusher_hold_matrix`
- Речевые специальные FX: `speech_telephone_bandpass`, `speech_robot_bitcrush`, `speech_megaphone_distortion`
- Спектральная формовка: `polarity_bloom`, `five_band_notch`, `bass_boost_low_shelf`

## 3. Полный справочник по каждому JSON

## 3.1. `audio_identity_passthrough.json`

Назначение:

- максимально прозрачный контрольный тракт;
- нужен как базовая точка сравнения перед любым эффектом.

Тракт:

- `Audio File Source -> Audio Sink`
- без промежуточных пассивных или нелинейных компонентов.

Ключевые параметры:

- `channel = left`
- `normalize = false`
- `target_sample_rate_hz = 16000`
- `OUT_IDENTITY.output_gain = 1.0`
- `OUT_IDENTITY.dc_block = false`

Что получится:

- на слух схема не должна вносить заметного тембрального искажения;
- это не побайтная копия файла, особенно если вход был `mp3`;
- это прозрачный моно-тракт выбранного канала.

Когда использовать:

- если нужно проверить, что проблема не в симуляторе, а в эффекте;
- если нужно сравнивать остальные пресеты относительно нейтрального режима.

Что крутить:

- обычно ничего;
- если нужен другой канал, менять `channel`;
- если нужен другой уровень, менять `--peak-voltage` или `output_gain`.

Выход:

- `OUT_IDENTITY`

Команда:

```bash
./.venv/bin/python run_audio_sim.py input.mp3 examples/audio_identity_passthrough.json /tmp/identity.wav --sample-rate 16000 --peak-voltage 1.0
```

## 3.2. `audio_wave_controls.json`

Назначение:

- учебный двухканальный набор для сравнения простейших линейных преобразований формы;
- это не один эффект, а две параллельные тестовые ветки.

Тракт:

- вход делится в `J_SPLIT`;
- верхняя ветка: `R_MUFFLE -> C_MUFFLE -> OUT_MUFFLE`
- нижняя ветка: `R_RAISE_SERIES -> OUT_BOOST`

Что делает каждая ветка:

- `OUT_MUFFLE`: простой RC low-pass, который приглушает быстрые колебания и верх;
- `OUT_BOOST`: почти прямой тракт с меньшим последовательным сопротивлением и повышенным `output_gain`.

Ключевые параметры:

- `R_MUFFLE = 3300 Ом`
- `C_MUFFLE = 68 нФ`
- `R_RAISE_SERIES = 220 Ом`
- `OUT_BOOST.output_gain = 1.85`

Что получится:

- `OUT_MUFFLE` дает мягкую, более приглушенную форму;
- `OUT_BOOST` дает более громкий и прямой сигнал;
- схема полезна как самый простой учебный A/B по линейной обработке.

Когда использовать:

- чтобы быстро показать разницу между RC-сглаживанием и простым усилением;
- чтобы смотреть на базовые графики без нелинейностей.

Что крутить:

- `R_MUFFLE` и `C_MUFFLE`: частота среза приглушенной ветки;
- `R_RAISE_SERIES`: насколько жестко отделить boost-ветку от источника;
- `OUT_BOOST.output_gain`: общий уровень второй ветки.

Выходы:

- `OUT_MUFFLE`
- `OUT_BOOST`

Команды:

```bash
./.venv/bin/python run_audio_sim.py input.mp3 examples/audio_wave_controls.json /tmp/muffle.wav --sample-rate 8000 --sink OUT_MUFFLE
./.venv/bin/python run_audio_sim.py input.mp3 examples/audio_wave_controls.json /tmp/boost.wav --sample-rate 8000 --sink OUT_BOOST
```

## 3.3. `audio_music_fx_rack.json`

Назначение:

- компактный учебный rack с четырьмя выходами;
- нужен, чтобы сравнивать несколько простых физических операций на одном и том же входе.

Тракт:

- вход делится в `J_SPLIT`;
- из него выходят четыре ветки:
- `OUT_GAIN`: прямой gain;
- `OUT_MUTE`: почти полное подавление через огромный верхний резистор и жесткий шунт;
- `OUT_SMOOTH`: RC-сглаживание;
- `OUT_PEAK`: диод + capacitor peak/envelope branch.

Что делает каждый выход:

- `OUT_GAIN`: просто более громкий прямой сигнал;
- `OUT_MUTE`: почти полная тишина;
- `OUT_SMOOTH`: сглаженная волна с приглушенными быстрыми изменениями;
- `OUT_PEAK`: не обычный звук, а форма, близкая к огибающей/растянутым пикам.

Ключевые параметры:

- `OUT_GAIN.output_gain = 1.8`
- `R_MUTE_TOP = 1e9 Ом`
- `R_MUTE_SHUNT = 1 Ом`
- `R_SMOOTH = 1800 Ом`, `C_SMOOTH = 22 мкФ`
- `D_PEAK.forward_drop_v = 0.32`
- `C_PEAK = 68 мкФ`, `R_PEAK = 1200 Ом`

Когда использовать:

- как демонстрационный стенд;
- как быстрый способ показать разницу между gain, mute, smoothing и peak capture.

Что крутить:

- для `OUT_SMOOTH`: `R_SMOOTH`, `C_SMOOTH`
- для `OUT_PEAK`: `D_PEAK`, `C_PEAK`, `R_PEAK`
- для `OUT_GAIN`: `output_gain`

Выходы:

- `OUT_GAIN`
- `OUT_MUTE`
- `OUT_SMOOTH`
- `OUT_PEAK`

Команды:

```bash
./.venv/bin/python run_audio_sim.py input.mp3 examples/audio_music_fx_rack.json /tmp/gain.wav --sample-rate 8000 --sink OUT_GAIN
./.venv/bin/python run_audio_sim.py input.mp3 examples/audio_music_fx_rack.json /tmp/mute.wav --sample-rate 8000 --sink OUT_MUTE
./.venv/bin/python run_audio_sim.py input.mp3 examples/audio_music_fx_rack.json /tmp/smooth.wav --sample-rate 8000 --sink OUT_SMOOTH
./.venv/bin/python run_audio_sim.py input.mp3 examples/audio_music_fx_rack.json /tmp/peak.wav --sample-rate 8000 --sink OUT_PEAK
```

## 3.4. `audio_ghost_envelope.json`

Назначение:

- превратить музыку или речь в призрачную пульсирующую огибающую;
- это intentionally destructive envelope-эффект.

Тракт:

- `D_PEAK -> C_HOLD -> R_RELEASE -> OUT_GHOST`

Ключевые параметры:

- `D_PEAK.forward_drop_v = 0.28`
- `C_HOLD = 120 мкФ`
- `R_RELEASE = 5600 Ом`
- `OUT_GHOST.output_gain = 3.2`

Что получится:

- на выходе слышно не саму форму сигнала, а в основном ее медленную амплитудную оболочку;
- ударные и слоги становятся вспышками;
- детали исходной артикуляции почти пропадают.

Когда использовать:

- для экспериментальных “призрачных” текстур;
- для изучения envelope follower на простейшей схеме.

Что крутить:

- `C_HOLD`: длина хвоста;
- `R_RELEASE`: скорость отпускания;
- `output_gain`: слышимость эффекта.

Выход:

- `OUT_GHOST`

Команда:

```bash
./.venv/bin/python run_audio_sim.py input.mp3 examples/audio_ghost_envelope.json /tmp/ghost.wav --sample-rate 8000 --peak-voltage 1.0
```

## 3.5. `audio_polarity_bloom.json`

Назначение:

- агрессивно перекосить симметрию волны;
- превратить один полупериод в доминирующий “bloom”.

Тракт:

- слабый dry-канал через `R_DRY`;
- отдельная положительная ветка через `D_POS -> C_BLOOM -> R_LEAK -> R_BLOOM`;
- легкий tilt через `C_TILT`;
- суммирование в `J_MIX`.

Ключевые параметры:

- `R_DRY = 47000 Ом`
- `D_POS.forward_drop_v = 0.24`
- `C_BLOOM = 6.8 мкФ`
- `R_LEAK = 3300 Ом`
- `R_BLOOM = 1200 Ом`
- `OUT_BLOOM.output_gain = 2.4`

Что получится:

- одна полярность становится доминирующей;
- атаки начинают выпирать;
- звук становится перекошенным, злым и “электрическим”.

Когда использовать:

- для музыкального разрушения симметрии;
- если нужен эффект “сломанный аналоговый удар”.

Что крутить:

- `R_DRY`: сколько исходного двуполярного сигнала оставить;
- `C_BLOOM`: насколько долго держать вспышку;
- `R_LEAK`: скорость отпускания;
- `R_BLOOM`: сколько wet-ветки реально попадает в выход.

Выход:

- `OUT_BLOOM`

Команда:

```bash
./.venv/bin/python run_audio_sim.py input.mp3 examples/audio_polarity_bloom.json /tmp/bloom.wav --sample-rate 8000 --peak-voltage 1.4
```

## 3.6. `audio_syllable_freeze.json`

Назначение:

- растянуть слоги и превратить речь в “замороженную” огибающую;
- эффект сильно снижает разборчивость.

Тракт:

- `D_HOLD -> C_HOLD -> R_RELEASE`
- смешивание wet и dry через `R_WET` и `R_DRY`
- дополнительное сглаживание через `C_SHAVE`

Ключевые параметры:

- `C_HOLD = 180 мкФ`
- `R_RELEASE = 12000 Ом`
- `R_WET = 1800 Ом`
- `R_DRY = 12000 Ом`
- `C_SHAVE = 47 нФ`
- `OUT_FREEZE.output_gain = 2.6`

Что получится:

- гласные и громкие части тянутся;
- согласные и быстрая структура речи теряются;
- на выходе слышна скорее “пульсация слога”, чем нормальная речь.

Когда использовать:

- если нужен максимально странный речевой эффект;
- если хочется исследовать, как envelope branch ломает разборчивость.

Что крутить:

- `C_HOLD`: длина заморозки;
- `R_RELEASE`: длина отпускания;
- `R_WET`: сколько frozen-слоя подмешать;
- `R_DRY`: сколько оставить исходной речи.

Выход:

- `OUT_FREEZE`

Команда:

```bash
./.venv/bin/python run_audio_sim.py speech.mp3 examples/audio_syllable_freeze.json /tmp/freeze.wav --sample-rate 8000 --peak-voltage 1.2
```

## 3.7. `audio_talking_bloom.json`

Назначение:

- более мягкая версия envelope-подмешивания, где речь еще остается слышимой;
- это компромисс между странностью и разборчивостью.

Тракт:

- сильный dry через `R_DRY`
- envelope-ветка через `D_ENV -> C_ENV -> R_RELEASE -> R_WET`
- легкий high-end через `C_AIR`

Ключевые параметры:

- `R_DRY = 1500 Ом`
- `C_ENV = 33 мкФ`
- `R_RELEASE = 4700 Ом`
- `R_WET = 8200 Ом`
- `C_AIR = 10 нФ`
- `OUT_TALK.output_gain = 1.9`

Что получится:

- голос остается различимым;
- появляется мягкий bloom на гласных и хвостах;
- результат намного более пригоден для речи, чем `syllable_freeze`.

Когда использовать:

- если нужна “странная”, но еще читаемая речь;
- если хочется мягкого dream-like слоя без полного развала артикуляции.

Что крутить:

- уменьшать `R_DRY`, если нужна еще большая разборчивость;
- уменьшать `R_WET`, если хочется больше bloom;
- уменьшать `C_ENV`, если хвост слишком длинный.

Выход:

- `OUT_TALK`

Команда:

```bash
./.venv/bin/python run_audio_sim.py speech.mp3 examples/audio_talking_bloom.json /tmp/talking-bloom.wav --sample-rate 8000 --peak-voltage 1.1
```

## 3.8. `audio_speech_soft_drive.json`

Назначение:

- сделать голос грубее и плотнее, но сохранить слова;
- это базовый “речь слышна, но есть перегруз”.

Тракт:

- `R_DRIVE` подает сигнал в `J_OUT`;
- `Varistor V_CLIP` мягко ограничивает пики;
- `C_EDGE + R_EDGE` слегка подшлифовывают верх;
- выход снимается через `OUT_DRIVE`.

Ключевые параметры:

- `R_DRIVE = 1500 Ом`
- `V_CLIP.clamp_voltage_v = 0.58`
- `V_CLIP.dynamic_resistance_ohm = 14 Ом`
- `C_EDGE = 4.7 нФ`
- `R_EDGE = 68000 Ом`
- `OUT_DRIVE.output_gain = 1.75`

Что получится:

- симметричный мягкий drive;
- пики поджимаются;
- голос становится плотнее, но не распадается в одну огибающую.

Когда использовать:

- как первый речевой drive-пресет;
- как стартовую точку перед `speech_grit_asym`.

Что крутить:

- `clamp_voltage_v`: ниже = жестче;
- `dynamic_resistance_ohm`: ниже = более резкий перегруз;
- `R_DRIVE`: больше = чище;
- `C_EDGE`: больше = мягче верх.

Выход:

- `OUT_DRIVE`

Команда:

```bash
./.venv/bin/python run_audio_sim.py speech.mp3 examples/audio_speech_soft_drive.json /tmp/soft-drive.wav --sample-rate 8000 --peak-voltage 1.0
```

## 3.9. `audio_speech_grit_asym.json`

Назначение:

- сделать голос грубее, суше и более хриплым за счет асимметрии полуволн;
- это более злой вариант речевого drive.

Тракт:

- `R_DRIVE -> J_OUT`
- `Varistor V_SOFT` поджимает обе полуволны;
- `D_POS` и `D_NEG` режут их по-разному;
- `R_LEAK` и `C_EDGE` стабилизируют и подтачивают верх.

Ключевые параметры:

- `R_DRIVE = 1500 Ом`
- `V_SOFT.clamp_voltage_v = 0.72`
- `D_POS.forward_drop_v = 0.34`
- `D_NEG.forward_drop_v = 0.55`
- `R_LEAK = 82000 Ом`
- `C_EDGE = 3.3 нФ`
- `OUT_GRIT.output_gain = 1.45`

Что получится:

- более выраженная асимметрия, чем в `soft_drive`;
- сильнее слышна шероховатость;
- речь обычно еще остается читаемой, но уже заметно более “рваной”.

Когда использовать:

- если `soft_drive` слишком мягкий;
- если нужен gritty voice, а не просто saturator.

Что крутить:

- `D_POS` и `D_NEG`: степень асимметрии;
- `V_SOFT.clamp_voltage_v`: общий уровень saturation;
- `R_DRIVE`: мягкость атаки;
- `C_EDGE`: количество песка на верхах.

Выход:

- `OUT_GRIT`

Команда:

```bash
./.venv/bin/python run_audio_sim.py speech.mp3 examples/audio_speech_grit_asym.json /tmp/grit.wav --sample-rate 16000 --peak-voltage 1.0
```

## 3.10. `audio_robot_gate.json`

Назначение:

- сделать механическую рубку сигнала;
- это простой gated/chopped эффект на MOSFET.

Тракт:

- прямой сигнал идет через `R_FEED` в `J_OUT`;
- `MOSFET M_SHUNT` периодически шунтирует этот узел на землю;
- открытием MOSFET управляет `Pulse Generator CLK`.

Ключевые параметры:

- `R_FEED = 820 Ом`
- `M_SHUNT.threshold_v = 2.8`
- `M_SHUNT.rds_on_ohm = 0.25`
- `CLK.period_s = 0.075`
- `CLK.duty_cycle = 0.36`
- `OUT_ROBOT.output_gain = 1.9`

Что получится:

- слова и музыка режутся на окна;
- тишина между окнами очень заметна;
- эффект похож на broken sampler или hard radio gate.

Когда использовать:

- для грубого ритмического chopping;
- для изучения clocked MOSFET-шунта на аудио.

Что крутить:

- `period_s`: скорость рубки;
- `duty_cycle`: длина заглушения;
- `R_FEED`: глубина шунта;
- `output_gain`: итоговый уровень.

Выход:

- `OUT_ROBOT`

Команда:

```bash
./.venv/bin/python run_audio_sim.py input.mp3 examples/audio_robot_gate.json /tmp/robot.wav --sample-rate 8000 --peak-voltage 1.0
```

## 3.11. `audio_breathing_mix.json`

Назначение:

- заставить сигнал “дышать” собственной огибающей;
- это dry/wet envelope feedback по ощущениям, но через простую физическую схему.

Тракт:

- dry идет через `R_DRY`;
- wet строится через `D_ENV -> C_ENV -> R_ENV_RELEASE -> R_WET`;
- потом все смешивается в `J_MIX`;
- `C_SHAVE` сглаживает верх.

Ключевые параметры:

- `R_DRY = 2200 Ом`
- `C_ENV = 82 мкФ`
- `R_ENV_RELEASE = 6800 Ом`
- `R_WET = 4700 Ом`
- `C_SHAVE = 22 нФ`
- `OUT_BREATH.output_gain = 1.8`

Что получится:

- громкие фразы начинают “вспухать”;
- тихие участки могут звучать более полыми;
- общий звук начинает качаться собственной амплитудой.

Когда использовать:

- для музыкально-странной, но не totally broken обработки;
- для демонстрации envelope-памяти с dry-подмешиванием.

Что крутить:

- `C_ENV`: длина памяти;
- `R_ENV_RELEASE`: скорость отпускания;
- `R_DRY` и `R_WET`: баланс прямого и envelope-канала;
- `C_SHAVE`: мягкость верхнего края.

Выход:

- `OUT_BREATH`

Команда:

```bash
./.venv/bin/python run_audio_sim.py input.mp3 examples/audio_breathing_mix.json /tmp/breath.wav --sample-rate 8000 --peak-voltage 1.0
```

## 3.12. `audio_lyric_radio_crunch.json`

Назначение:

- вытянуть вокал вперед и сделать его узким, сухим и радио-грязным;
- лучше сохраняет слова, чем чистые envelope-эффекты.

Тракт:

- high-pass ветка через `C_HP` и `R_HP_GND`;
- dry-сигнал через `R_DRY`;
- wet подмешивается через `R_WET`;
- на выходе стоит асимметричный diode clip и мягкий `Varistor`.

Ключевые параметры:

- `C_HP = 150 нФ`
- `R_HP_GND = 3300 Ом`
- `R_DRY = 4700 Ом`
- `R_WET = 2200 Ом`
- `D_POS = 0.34 В`
- `D_NEG = 0.58 В`
- `V_SOFT.clamp_voltage_v = 0.88`
- `OUT_RADIO.output_gain = 1.65`

Что получится:

- низ подсушивается;
- середина и присутствие вокала выходят вперед;
- появляется умеренная асимметричная хриплость.

Когда использовать:

- для треков, где есть и слова, и музыка;
- если нужен “радио/телефон/узкий передний вокал”.

Что крутить:

- `C_HP`, `R_HP_GND`: сколько низа срезать;
- `D_POS`, `D_NEG`: характер клиппинга;
- `R_DRY`, `R_WET`: баланс intelligibility и crunch;
- `V_SOFT`: плотность saturation.

Выход:

- `OUT_RADIO`

Команда:

```bash
./.venv/bin/python run_audio_sim.py input.mp3 examples/audio_lyric_radio_crunch.json /tmp/radio.wav --sample-rate 16000 --peak-voltage 1.0
```

## 3.13. `audio_vocal_stutter_mix.json`

Назначение:

- ритмически рубить голос и музыку, но не убивать их полностью;
- это музыкальнее, чем `robot_gate`.

Тракт:

- dry идет через `R_DRY`;
- wet-ветка через `R_CHOP_FEED` попадает в `J_CHOP`;
- `M_STUTTER` рубит этот узел под управлением `CLK`;
- результат возвращается через `R_WET_MIX`;
- `C_POP` смягчает щелчки.

Ключевые параметры:

- `R_DRY = 2200 Ом`
- `R_CHOP_FEED = 560 Ом`
- `M_STUTTER.rds_on_ohm = 0.12`
- `CLK.period_s = 0.094`
- `CLK.duty_cycle = 0.42`
- `R_WET_MIX = 2400 Ом`
- `C_POP = 15 нФ`
- `OUT_STUTTER.output_gain = 1.7`

Что получится:

- речь и вокал заикаются ритмически;
- но постоянный dry-канал не дает тексту исчезнуть полностью;
- эффект хорошо читается на припевах и речевых фрагментах.

Когда использовать:

- если нужен broken sampler feel без полного hard mute;
- если хочется ритмической структуры поверх нормальной разборчивости.

Что крутить:

- `period_s`: темп стуттера;
- `duty_cycle`: длина разрыва;
- `R_DRY`: сколько понятности оставить;
- `R_WET_MIX`: сколько chopped-ветки вернуть в выход.

Выход:

- `OUT_STUTTER`

Команда:

```bash
./.venv/bin/python run_audio_sim.py input.mp3 examples/audio_vocal_stutter_mix.json /tmp/stutter.wav --sample-rate 16000 --peak-voltage 1.0
```

## 3.14. `audio_vocal_halo_smear.json`

Назначение:

- дать вокалу размытый halo и мягкое “расширение”;
- это более атмосферный, чем агрессивный пресет.

Тракт:

- dry через `R_DRY`;
- smear-ветка через `R_SMEAR_IN -> C_SMEAR -> R_SMEAR_MIX`;
- air-ветка через `C_AIR -> R_AIR_GND -> R_AIR_MIX`;
- суммирование в `J_OUT` и легкая склейка через `V_GLUE`.

Ключевые параметры:

- `R_DRY = 2200 Ом`
- `R_SMEAR_IN = 3300 Ом`
- `C_SMEAR = 4.7 мкФ`
- `R_SMEAR_MIX = 4700 Ом`
- `C_AIR = 82 нФ`
- `R_AIR_GND = 4700 Ом`
- `R_AIR_MIX = 8200 Ом`
- `V_GLUE.clamp_voltage_v = 1.05`
- `OUT_HALO.output_gain = 1.55`

Что получится:

- вокруг слов появляется мягкий ореол;
- вокал кажется чуть шире и чуть более сновидческим;
- музыка не ломается грубо.

Когда использовать:

- для dream-like вокального слоя;
- если нужен эффект атмосферы, а не грубого искажения.

Что крутить:

- `C_SMEAR`: длина размазывания;
- `R_SMEAR_MIX`: количество smear;
- `C_AIR`, `R_AIR_GND`, `R_AIR_MIX`: количество воздуха;
- `V_GLUE`: насколько плотно все склеить.

Выход:

- `OUT_HALO`

Команда:

```bash
./.venv/bin/python run_audio_sim.py input.mp3 examples/audio_vocal_halo_smear.json /tmp/halo.wav --sample-rate 16000 --peak-voltage 1.0
```

## 3.15. `audio_five_band_notch.json`

Назначение:

- многополосно подавить несколько зон верхней середины и верха;
- показать, как параллельные `LC`-ловушки выедают определенные диапазоны.

Тракт:

- вход идет через `R_IN` в `J_OUT`;
- от этого узла в землю уходят пять `L + C` веток;
- сверху дополнительно стоит `C_TOP_SHAVE`.

Ключевые параметры:

- `R_IN = 680 Ом`
- `L_NOTCH_1..5 = 6.8 мГн, 2.7 мГн, 1.2 мГн, 0.47 мГн, 0.2 мГн`
- `C_NOTCH_1..5 = 4.7 мкФ`
- `C_TOP_SHAVE = 4.7 нФ`
- `OUT_NOTCH.output_gain = 1.75`

Что получится:

- часть “лохматого” высокочастотного содержимого будет поглощаться;
- спектр станет неровным с несколькими провалами;
- форма волны станет спокойнее и менее резкой.

Когда использовать:

- для учебного исследования notch-логики;
- для экспериментов с многополосным подавлением.

Что крутить:

- `L_NOTCH_*` и `C_NOTCH_*`: положение провалов;
- сопротивления катушек: ширина и добротность;
- `R_IN`: глубина общей связи с источником;
- `output_gain`: компенсация уровня.

Выход:

- `OUT_NOTCH`

Команда:

```bash
./.venv/bin/python run_audio_sim.py input.mp3 examples/audio_five_band_notch.json /tmp/notch.wav --sample-rate 16000 --peak-voltage 1.0
```

## 3.16. `audio_bass_boost_low_shelf.json`

Назначение:

- поднять низ и low-mid без жесткого разрушения верха;
- это low-shelf-подобный пассивный/суммирующий пресет.

Тракт:

- dry идет через `R_DRY`;
- bass-ветка через `L_SUB -> C_SUB -> R_SUB_MIX`;
- body-ветка через `L_BODY -> C_BODY -> R_BODY_MIX`;
- `C_AIR_SHAVE` немного держит верх в рамках.

Ключевые параметры:

- `R_DRY = 8200 Ом`
- `L_SUB = 12 мГн`, `C_SUB = 8.2 мкФ`
- `R_SUB_MIX = 2200 Ом`
- `L_BODY = 4.7 мГн`, `C_BODY = 4.7 мкФ`
- `R_BODY_MIX = 3300 Ом`
- `OUT_BASS.output_gain = 2.0`

Что получится:

- длинные низкие волны станут доминировать сильнее;
- верх останется, но будет восприниматься тоньше;
- спектр станет заметно более басовым.

Когда использовать:

- для музыкальных треков, где нужен акцент на низ;
- для демонстрации low-shelf-подобного поведения без op-amp EQ.

Что крутить:

- `L_SUB`, `C_SUB`: самый низ;
- `L_BODY`, `C_BODY`: тело и низкая середина;
- `R_SUB_MIX`, `R_BODY_MIX`: количество каждой низкой ветки;
- `R_DRY`: сколько оставить исходного верха.

Выход:

- `OUT_BASS`

Команда:

```bash
./.venv/bin/python run_audio_sim.py input.mp3 examples/audio_bass_boost_low_shelf.json /tmp/bass.wav --sample-rate 16000 --peak-voltage 1.0
```

## 3.17. `audio_redplate_distortion.json`

Назначение:

- жесткий музыкальный перегруз с плоскими вершинами и богатой асимметрией;
- это самый “агрессивный” nonlinear shaper в наборе.

Тракт:

- `R_DRIVE` вталкивает сигнал в `J_CLIP`;
- `V_SOFT` поджимает общий уровень;
- `D_POS` и `D_NEG` режут полуволны несимметрично;
- `C_SPARK` подтачивает самый злой верх;
- `R_LEAK` стабилизирует узел.

Ключевые параметры:

- `R_DRIVE = 390 Ом`
- `V_SOFT.clamp_voltage_v = 0.62`
- `V_SOFT.dynamic_resistance_ohm = 9 Ом`
- `D_POS = 0.28 В`
- `D_NEG = 0.48 В`
- `C_SPARK = 6.8 нФ`
- `R_LEAK = 56000 Ом`
- `OUT_REDPLATE.output_gain = 1.6`

Что получится:

- вершины заметно обрезаются;
- добавляется много гармоник;
- тембр становится резким, плотным и агрессивным.

Когда использовать:

- для гитароподобного перегруза;
- для примера жесткой нелинейности на графиках.

Что крутить:

- `R_DRIVE`: глубина вгона в клиппинг;
- `clamp_voltage_v`: уровень сжатия;
- `D_POS`, `D_NEG`: характер асимметрии;
- `C_SPARK`: острота верхнего края.

Выход:

- `OUT_REDPLATE`

Команда:

```bash
./.venv/bin/python run_audio_sim.py input.mp3 examples/audio_redplate_distortion.json /tmp/redplate.wav --sample-rate 16000 --peak-voltage 1.0
```

## 3.18. `audio_crystal_delay_smear.json`

Назначение:

- дать echo-like и reverb-like шлейф через каскад `RC`-памяти;
- это аналоговый smear, а не идеальный цифровой delay.

Тракт:

- dry через `R_DRY`;
- три последовательных tap-узла:
- `R_TAP1 -> C_TAP1`
- `R_TAP2 -> C_TAP2`
- `R_TAP3 -> C_TAP3`
- каждый tap подмешивается обратно через `R_MIX1`, `R_MIX2`, `R_MIX3`;
- `C_SHIMMER` слегка прибирает стеклянный верх.

Ключевые параметры:

- `R_DRY = 3900 Ом`
- `R_TAP1/2/3 = 1200, 2200, 3300 Ом`
- `C_TAP1/2/3 = 2.2, 3.3, 4.7 мкФ`
- `R_MIX1/2/3 = 12000, 8200, 5600 Ом`
- `C_SHIMMER = 4.7 нФ`
- `OUT_DELAY.output_gain = 1.9`

Что получится:

- на атаках и согласных появится хвост;
- огибающая будет спадать дольше;
- ощущение будет ближе к “кристаллическому смазу”, чем к точному delay line.

Когда использовать:

- для атмосферной обработки;
- для изучения RC memory ladder и временного размазывания сигнала.

Что крутить:

- `R_TAP*` и `C_TAP*`: длина каждого хвоста;
- `R_MIX*`: вклад каждого tap в финальный выход;
- `R_DRY`: сколько прямой атаки оставить;
- `C_SHIMMER`: контроль верха.

Выход:

- `OUT_DELAY`

Команда:

```bash
./.venv/bin/python run_audio_sim.py input.mp3 examples/audio_crystal_delay_smear.json /tmp/crystal.wav --sample-rate 16000 --peak-voltage 1.0
```

## 3.19. `audio_bitcrusher_hold_matrix.json`

Назначение:

- получить грубую ступенчатую, цифровато-ломаную волну;
- это bitcrusher-like эффект через clocked hold/reset.

Тракт:

- сигнал медленно заряжает `J_HOLD` через `R_FEED`;
- `C_HOLD` удерживает текущее значение;
- `R_DROOP` дает контролируемое провисание;
- `Pulse Generator CLK` периодически открывает `M_RESET`;
- `M_RESET` кратко сбрасывает hold-узел в землю.

Ключевые параметры:

- `R_FEED = 3300 Ом`
- `C_HOLD = 0.68 мкФ`
- `R_DROOP = 68000 Ом`
- `CLK.period_s = 0.0018`
- `CLK.duty_cycle = 0.28`
- `CLK.pulse_width_s = 0.0005`
- `M_RESET.threshold_v = 2.2`
- `M_RESET.rds_on_ohm = 0.22`
- `OUT_CRUSH.output_gain = 6.0`

Что получится:

- форма становится кусочной и ступенчатой;
- появляются clocked-артефакты и ощущение грубой дискретизации;
- это не математический ADC, а физическая hold/reset-аппроксимация bitcrusher-поведения.

Когда использовать:

- если нужен агрессивный lo-fi digital feel;
- если хочется сравнивать nonlinear distortion против clocked/held degradation.

Что крутить:

- `CLK.period_s`: грубость по времени;
- `pulse_width_s` и `duty_cycle`: жесткость и длительность reset;
- `C_HOLD`: инертность ступени;
- `R_FEED`: насколько быстро узел догоняет вход;
- `R_DROOP`: сколько сползания между reset-импульсами.

Выход:

- `OUT_CRUSH`

Команда:

```bash
./.venv/bin/python run_audio_sim.py input.mp3 examples/audio_bitcrusher_hold_matrix.json /tmp/crush.wav --sample-rate 16000 --peak-voltage 1.0
```

## 3.20. `audio_speech_telephone_bandpass.json`

Назначение:

- дать узнаваемый телефонный или intercom-эффект на речи;
- это чистый band-pass без добавочной нелинейности.

Тракт:

- `C_HP` последовательно вырезает низ;
- `R_HP_GND` задает нижнюю границу;
- `R_LP + C_LP` формируют верхнюю границу полосы;
- сигнал снимается с `OUT_PHONE`.

Ключевые параметры:

- `C_HP = 68 нФ`
- `R_HP_GND = 3300 Ом`
- `R_LP = 1800 Ом`
- `C_LP = 33 нФ`
- `OUT_PHONE.output_gain = 4.0`

Что получится:

- низ и верх заметно исчезнут;
- останется в основном средний речевой диапазон;
- голос станет похож на старый проводной телефон, переговорную панель или домофон.

Когда использовать:

- если нужен максимально узнаваемый “телефон” без перегруза;
- если нужно показать band-pass на речи без примеси других эффектов.

Что крутить:

- `C_HP`, `R_HP_GND`: нижняя граница полезной полосы;
- `R_LP`, `C_LP`: верхняя граница;
- `output_gain`: компенсация уровня после фильтрации.

Выход:

- `OUT_PHONE`

Команда:

```bash
./.venv/bin/python run_audio_sim.py speech.mp3 examples/audio_speech_telephone_bandpass.json /tmp/phone.wav --sample-rate 16000 --peak-voltage 1.0
```

## 3.21. `audio_speech_robot_bitcrush.json`

Назначение:

- роботизировать речь через узкую полосу и clocked hold/reset-деградацию;
- это речевой bitcrusher-подобный пресет.

Тракт:

- `C_HP` и `R_HP_GND` сначала оставляют в основном средне-речевой диапазон;
- дальше `R_FEED + C_HOLD` формируют hold-узел;
- `R_DROOP` позволяет узлу сползать между циклами;
- `CLK` открывает `M_RESET`, периодически сбрасывая узел в землю;
- `OUT_ROBO` снимает уже ломаную, ступенчатую версию речи.

Ключевые параметры:

- `C_HP = 82 нФ`
- `R_HP_GND = 2200 Ом`
- `R_FEED = 2700 Ом`
- `C_HOLD = 0.47 мкФ`
- `R_DROOP = 56000 Ом`
- `CLK.period_s = 0.0016`
- `CLK.duty_cycle = 0.3`
- `CLK.pulse_width_s = 0.00048`
- `OUT_ROBO.output_gain = 20.0`

Что получится:

- речь потеряет плавность и естественные микропереходы;
- появится цифровой хруст и роботический характер;
- тембр будет ближе к старому игровому цифровому голосу, чем к обычному lo-fi.

Когда использовать:

- если нужен именно “robot voice”, а не просто ступенчатость;
- если хочется сравнить чистый band-pass против band-pass плюс clocked degradation.

Что крутить:

- `CLK.period_s`: грубость временной дискретизации;
- `pulse_width_s` и `duty_cycle`: сила reset;
- `C_HOLD`: инертность ступени;
- `R_FEED`: скорость добора входного сигнала;
- `R_DROOP`: насколько быстро ступень сползает.

Выход:

- `OUT_ROBO`

Команда:

```bash
./.venv/bin/python run_audio_sim.py speech.mp3 examples/audio_speech_robot_bitcrush.json /tmp/robo.wav --sample-rate 16000 --peak-voltage 1.0
```

## 3.22. `audio_speech_megaphone_distortion.json`

Назначение:

- сделать речь агрессивной, металлической и мегафонной;
- это band-limited distortion, а не просто фильтр.

Тракт:

- `C_HP` и `R_HP_GND` отрезают низ;
- `R_DRIVE` подает уже суженный сигнал в `J_CLIP`;
- `C_LP` ограничивает верх и держит полосу узкой;
- `V_CLIP`, `D_POS`, `D_NEG` формируют асимметричный перегруз;
- `R_LEAK` стабилизирует узел;
- `OUT_MEGA` снимает готовый мегафонный голос.

Ключевые параметры:

- `C_HP = 100 нФ`
- `R_HP_GND = 1800 Ом`
- `R_DRIVE = 680 Ом`
- `V_CLIP.clamp_voltage_v = 0.76`
- `D_POS = 0.32 В`
- `D_NEG = 0.52 В`
- `C_LP = 68 нФ`
- `R_LEAK = 33000 Ом`
- `OUT_MEGA.output_gain = 4.5`

Что получится:

- голос станет пробивным, узкополосным и жестким;
- пики гласных будут срезаться;
- добавятся новые гармоники, дающие характер мегафона или громкоговорителя.

Когда использовать:

- если нужен полицейский мегафон, вокзальный громкоговоритель или shouting PA;
- если нужно наглядно показать разницу между чистым band-pass и band-pass плюс клиппинг.

Что крутить:

- `C_HP`, `R_HP_GND`: степень отрезания низа;
- `R_DRIVE` и `C_LP`: жесткость и ширина полосы;
- `V_CLIP`, `D_POS`, `D_NEG`: характер и асимметрия перегруза;
- `output_gain`: итоговый уровень.

Выход:

- `OUT_MEGA`

Команда:

```bash
./.venv/bin/python run_audio_sim.py speech.mp3 examples/audio_speech_megaphone_distortion.json /tmp/mega.wav --sample-rate 16000 --peak-voltage 1.0
```

## 4. Как выбирать схему под задачу

Если нужна почти прозрачная проверка:

- `audio_identity_passthrough.json`

Если нужен учебный стенд с несколькими выходами:

- `audio_wave_controls.json`
- `audio_music_fx_rack.json`

Если нужна странная огибающая и разрушение разборчивости:

- `audio_ghost_envelope.json`
- `audio_syllable_freeze.json`

Если нужна странность, но речь еще должна жить:

- `audio_talking_bloom.json`
- `audio_speech_soft_drive.json`
- `audio_speech_grit_asym.json`

Если нужен вокальный или lyric-ориентированный эффект для трека:

- `audio_lyric_radio_crunch.json`
- `audio_vocal_stutter_mix.json`
- `audio_vocal_halo_smear.json`

Если нужен жесткий музыкальный FX:

- `audio_robot_gate.json`
- `audio_redplate_distortion.json`
- `audio_bitcrusher_hold_matrix.json`

Если нужен узнаваемый речевой спецэффект:

- `audio_speech_telephone_bandpass.json`
- `audio_speech_robot_bitcrush.json`
- `audio_speech_megaphone_distortion.json`

Если нужен акцент на спектральной обработке:

- `audio_five_band_notch.json`
- `audio_bass_boost_low_shelf.json`

Если нужен хвост и smear во времени:

- `audio_breathing_mix.json`
- `audio_crystal_delay_smear.json`

## 5. Что сравнивать между схемами

Полезные пары:

- `identity` против любой другой схемы: насколько схема вообще ушла от нейтрального тракта;
- `speech_soft_drive` против `speech_grit_asym`: мягкий drive против асимметричной хриплости;
- `robot_gate` против `vocal_stutter_mix`: hard chop против музыкального chopped-mix;
- `ghost_envelope` против `syllable_freeze`: чистая огибающая против замороженной слоговой массы;
- `redplate_distortion` против `bitcrusher_hold_matrix`: клиппинг против ступенчатой деградации;
- `speech_telephone_bandpass` против `speech_megaphone_distortion`: чистая узкая полоса против узкой полосы с перегрузом;
- `speech_robot_bitcrush` против `bitcrusher_hold_matrix`: специализированная роботизация речи против более общего clocked lo-fi;
- `five_band_notch` против `bass_boost_low_shelf`: многополосное подавление против подъема низа;
- `breathing_mix` против `crystal_delay_smear`: envelope pumping против RC-smear хвостов.
