# Extra Audio Effects

Ниже еще несколько JSON-схем сверх уже существующих `ghost`, `robot` и `breathing`.

Все схемы запускаются через `run_audio_sim.py`, поэтому путь к входному файлу не надо зашивать в JSON:

```bash
./.venv/bin/python run_audio_sim.py input.mp3 examples/audio_identity_passthrough.json clean.wav --sample-rate 16000 --peak-voltage 1.0
./.venv/bin/python run_audio_sim.py input.mp3 examples/audio_polarity_bloom.json bloom.wav --sample-rate 8000
./.venv/bin/python run_audio_sim.py input.mp3 examples/audio_syllable_freeze.json freeze.wav --sample-rate 8000
./.venv/bin/python run_audio_sim.py input.mp3 examples/audio_talking_bloom.json talk.wav --sample-rate 8000
./.venv/bin/python run_audio_sim.py input.mp3 examples/audio_speech_soft_drive.json drive.wav --sample-rate 8000
./.venv/bin/python run_audio_sim.py input.mp3 examples/audio_speech_grit_asym.json grit.wav --sample-rate 16000
```

## 0. Identity Passthrough

Файл: `examples/audio_identity_passthrough.json`

Это проверочный прозрачный тракт:

- `Audio File Source -> Audio Sink`
- без диодов;
- без конденсаторов;
- без выпрямления;
- без клиппинга.
- `channel = left`
- `normalize = false`

Если на нем речь не слышна, проблема уже не в эффекте, а в параметрах запуска.

Для максимально прозрачного режима:

```bash
./.venv/bin/python run_audio_sim.py speech.mp3 examples/audio_identity_passthrough.json /tmp/identity.wav --sample-rate 16000 --peak-voltage 1.0
```

Важно:

- для речи не надо насильно жать все в `8000 Hz`, если цель сохранить разборчивость;
- `--peak-voltage 1.0` и `OUT_IDENTITY.output_gain = 1.0` дают почти прозрачный тракт;
- в текущем виде это **моно-тракт одного канала**, а не сохранение исходного stereo 1:1;
- `mp3 -> wav` не будет побайтно тем же файлом, но схемного искажения здесь быть не должно.

## 1. Polarity Bloom

Файл: `examples/audio_polarity_bloom.json`

Что делает:

- почти убивает одну полярность волны;
- другую полярность пропускает через диод и слегка растягивает конденсатором;
- подмешивает очень тонкий dry-сигнал, чтобы звук не распадался полностью.

Что слышно:

- музыка становится ярче, злее и более “электрической”;
- атаки как будто выпирают вперед;
- низ и симметрия волны ломаются, из-за чего звук делается кривым и цепким.

Что крутить:

- `R_DRY`: чем больше, тем сильнее исчезает “убитая” полярность;
- `C_BLOOM`: чем больше, тем шире и липче пики;
- `R_LEAK`: скорость отпускания после вспышки;
- `OUT_BLOOM.output_gain`: финальный уровень.

Для музыки удобно начать так:

```bash
./.venv/bin/python run_audio_sim.py "examples/audio_assets/Bit Bit Loop.mp3" examples/audio_polarity_bloom.json /tmp/polarity-bloom.wav --sample-rate 8000 --peak-voltage 1.4
```

## 2. Syllable Freeze

Файл: `examples/audio_syllable_freeze.json`

Что делает:

- ловит вершины через диод;
- долго держит их на `C_HOLD`;
- очень осторожно возвращает немного dry-сигнала;
- на выходе слоги начинают тянуться, а паузы заполняются хвостом предыдущего звука.

Что особенно интересно на речи:

- согласные становятся менее важными, чем гласные хвосты;
- фразы начинают звучать как будто через странный речевой компрессор-призрак;
- возникает ощущение, что “период” звука стал длиннее, хотя это не настоящий time-stretch.

Что крутить:

- `C_HOLD`: длина заморозки;
- `R_RELEASE`: как медленно схема отпускает прошлый слог;
- `R_WET`: сколько замороженной огибающей впрыснуть в выход;
- `R_DRY`: сколько исходной разборчивости оставить;
- `OUT_FREEZE.output_gain`: общий уровень.

Для речи удобно начать так:

```bash
./.venv/bin/python run_audio_sim.py speech.mp3 examples/audio_syllable_freeze.json /tmp/syllable-freeze.wav --sample-rate 8000 --peak-voltage 1.2
```

## Как выбирать

- Если хочется “сломать” музыку и перекосить саму форму волны: `audio_polarity_bloom.json`
- Если хочется странно вытянуть слоги и сделать голос почти призрачным: `audio_syllable_freeze.json`
- Если хочется странно, но чтобы речь все еще читалась: `audio_talking_bloom.json`
- Если хочется максимально сохранить речь и просто сделать ее грубее и плотнее: `audio_speech_soft_drive.json`
- Если хочется сделать голос еще грубее и добавить асимметричную хриплость: `audio_speech_grit_asym.json`

## 3. Talking Bloom

Файл: `examples/audio_talking_bloom.json`

Что делает:

- оставляет сильный прямой голосовой канал;
- поверх него добавляет мягкую envelope-ветку;
- слегка подчеркивает гласные и хвосты, но не выжигает согласные полностью.

Что слышно:

- речь остается различимой;
- голос становится чуть более “радио-странным”, мягким и воздушным;
- на музыке получается легкий сонный налет, а не полный развал формы.

Что крутить:

- `R_DRY`: меньше значение = больше разборчивости;
- `R_WET`: меньше значение = сильнее странный wet-слой;
- `C_ENV`: длиннее память хвоста;
- `R_RELEASE`: скорость отпускания;
- `OUT_TALK.output_gain`: общий уровень.

Стартовая команда для речи:

```bash
./.venv/bin/python run_audio_sim.py speech.mp3 examples/audio_talking_bloom.json /tmp/talking-bloom.wav --sample-rate 8000 --peak-voltage 1.1
```

## 4. Speech Soft Drive

Файл: `examples/audio_speech_soft_drive.json`

Почему он лучше сохраняет речь:

- здесь нет замены сигнала одной огибающей;
- основной тракт остается прямым и двуполярным;
- эффект добавляется через мягкий симметричный клиппинг `Varistor`;
- согласные и быстрые переходы не исчезают полностью, поэтому слова остаются понятнее.

Что слышно:

- голос становится плотнее, грубее и немного “радио-перегруженным”;
- пики поджимаются;
- речь остается гораздо более читаемой, чем в `syllable_freeze`.

Что крутить:

- `V_CLIP.clamp_voltage_v`: ниже значение = сильнее перегруз;
- `V_CLIP.dynamic_resistance_ohm`: ниже значение = жестче клиппинг;
- `R_DRIVE`: больше значение = мягче обработка;
- `C_EDGE`: больше значение = мягче верх и меньше рези;
- `OUT_DRIVE.output_gain`: выходной уровень.

Стартовая команда:

```bash
./.venv/bin/python run_audio_sim.py speech.mp3 examples/audio_speech_soft_drive.json /tmp/speech-soft-drive.wav --sample-rate 8000 --peak-voltage 1.0
```

## 5. Speech Grit Asym

Файл: `examples/audio_speech_grit_asym.json`

Это более грубый голосовой shaper:

- основная речь остается в прямом тракте;
- `Varistor` мягко сжимает обе полуволны;
- `D_POS` и `D_NEG` режут их несимметрично;
- из-за асимметрии голос становится более хриплым и зернистым, но не должен разваливаться в одну огибающую.

Что слышно:

- голос грубее и суше, чем в `audio_speech_soft_drive.json`;
- согласные сильнее цепляются;
- появляется ощущение рваной атаки и более злой середины.

Что крутить:

- `D_POS.forward_drop_v`: ниже = больше грубого положительного клиппинга;
- `D_NEG.forward_drop_v`: ниже = сильнее ломается отрицательная полуволна;
- `V_SOFT.clamp_voltage_v`: ниже = сильнее общий перегруз;
- `R_DRIVE`: больше = мягче и чище;
- `C_EDGE`: больше = меньше песка наверху;
- `OUT_GRIT.output_gain`: общий уровень.

Стартовая команда:

```bash
./.venv/bin/python run_audio_sim.py speech.mp3 examples/audio_speech_grit_asym.json /tmp/speech-grit.wav --sample-rate 16000 --peak-voltage 1.0
```

## Как снимать графики и метрики

Для сравнения входа и выхода есть отдельный анализатор: `examples/audio_compare_analysis.py`

Пример:

```bash
./.venv/bin/python examples/audio_compare_analysis.py speech.mp3 /tmp/speech-grit.wav /tmp/speech-grit-analysis --sample-rate 16000 --normalize-input
```

Он сохраняет:

- `comparison.png`
- `metrics.json`

Что именно на них смотреть и как сравнивать пресеты, описано в `examples/audio_analysis_guide.md`.
