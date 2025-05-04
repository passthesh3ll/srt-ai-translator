# AI Subtitle Translator

A multi-thread Python script to translate SubRip (.srt) subtitles using AI (g4f) in seconds.

## Description

The script takes an input .srt file, translates the subtitle text from a specified input language to a specified output language using an AI model (at the moment **deepseek-v3** by **Blackbox**) from [gpt4free](https://github.com/xtekky/gpt4free), and saves the translated subtitles to a new .srt file. No api/token needed.

## Dependencies

1. Generate a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
```

2. Install dependences

```bash
pip install g4f\[all\] argparse pycountry tqdm colorama
```

## Usage

**Help**:
```bash
python srt-ai-translator.py -h
```
**Translation** *(Available languages: [ISO 639-2 Codes](https://www.loc.gov/standards/iso639-2/php/code_list.php))*:
```bash
python srt-ai-translator.py input.srt eng ita
```

![image](https://i.postimg.cc/VN72nZhw/rec.gif)
