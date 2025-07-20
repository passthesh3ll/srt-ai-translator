# AI Subtitle Translator

A Python script to translate SubRip (.srt) subtitles using AI (g4f).

## Description

The script takes an input .srt file and translates the subtitle text from a specified input language to a specified output language, using an AI model (GPT-4) from [gpt4free](https://github.com/xtekky/gpt4free). The translation consists of two steps: initial (direct) translation and final adaptation, correcting translation errors and gender mismatches (based on characters names and entire translated text). The final translated subtitles are saved to a new .srt file.

⚠️ No API/token is needed using gpt4free. If srt-ai-translator can't connect to api may be a gpt4free's provider problem, I'll update the provider ASAP.

## Dependencies

1. Generate a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
```

2. Install Dependencies


2a. Using [**Poetry**](https://python-poetry.org/)

Install Poetry (if not already installed), e.g. on linux/mac:

```bash
curl -sSL https://install.python-poetry.org | python3 -
```

Then install dependencies:

```bash
poetry install
```

To run the script:

```bash
poetry run srt-ai-translator
```

2b. Using [**Rye**](https://rye.astral.sh/guide/installation/)

Install Rye (if not already installed), e.g. on linux/mac:

```bash
curl -sSf https://rye.astral.sh/get | bash
```

Then install dependencies:

```bash
rye sync
```
To run the script:

```bash
rye run srt-ai-translator
```


3. ffmpeg must be installed

## Usage

_(Available languages: [ISO 639-2 Codes](https://www.loc.gov/standards/iso639-2/php/code_list.php))_

**Help**:

```
$ poetry run srt-ai-translator -h

usage: srt-ai-translator.py [-h] [-o OUTPUT_FOLDER] [--demux [DEMUX]] [--delete]
                            input_path input_lang output_lang

translate SRT file(s) using gpt4free.

positional arguments:
  input_path            input path for the .srt file or folder containing .srt files
  input_lang            input language (iso639): eng,fre,ita,jpn..
  output_lang           output language (iso639): eng,fre,ita,jpn..

options:
  -h, --help            show this help message and exit
  -o, --output_folder OUTPUT_FOLDER
                        custom output folder for the .srt file(s)
  --demux [DEMUX]       automatically demux .srt from file(s) (default stream index is 0)
  --delete              delete the source .srt file after processing
```

**Translate a single subtitle**:

```bash
poetry run srt-ai-translator INPUT.srt eng ita
```

**Translate all subtitles in a folder**:

```bash
poetry run srt-ai-translator . eng ita
```

**Translate all subtitles in a folder auto-demuxing srt (stream index=0)**:

```bash
poetry run srt-ai-translator . eng ita --demux 0
```

## Screen

![image](https://i.postimg.cc/VNx3gQmP/1.png)
