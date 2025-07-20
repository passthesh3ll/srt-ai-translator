import os, json, pycountry, argparse, time, subprocess, tempfile, shutil
from g4f.client import Client
from g4f.Provider import Blackbox
from tqdm import tqdm
from colorama import init, Fore, Style

def srt_to_dict(file_path):
    subtitles = []
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    i = 0
    while i < len(lines):
        if lines[i].strip().isdigit():
            subtitle = {}
            subtitle['id'] = lines[i].strip()
            i += 1
            subtitle['time-start'], subtitle['time-end'] = lines[i].strip().split(' --> ')
            i += 1
            text_lines = []
            while i < len(lines) and lines[i].strip():
                text_lines.append(lines[i].strip())
                i += 1
            subtitle['text'] = '\n'.join(text_lines)
            subtitle['translated'] = ''
            subtitles.append(subtitle)
        i += 1

    return subtitles

def dict_to_srt(subtitles, output_file_path):
    try:
        with open(output_file_path, 'w', encoding='utf-8') as f:
            for subtitle in subtitles:
                f.write(subtitle['id'] + '\n')
                f.write(subtitle['time-start'] + ' --> ' + subtitle['time-end'] + '\n')
                f.write(subtitle['translated'] + '\n\n')
    except Exception as e:
        print(f"{Fore.RED}ERR{Fore.RESET}: {e}")

def translate_subtitle(client, subtitle, input_lang, output_lang, pbar, history):
    max_retries = 4
    retries = 0
    new_message = {
        "role": "user",
        "content": f"Considering all translated subtitles in the full chat history,\
        translate the following subtitle sentence (at timing:{subtitle['time-start']}) from {input_lang} to {output_lang}:\
        - Adapt the translated text to ensure fluency in {output_lang}.\
        - Use the context of previous translations and character names to guess implicit genders (distant subtitle timing may lead to different scenes and characters).\
        - Ensure the tone and register match the original context.\
        - Adapt the translation to sound natural when spoken, avoiding overly literal or bookish phrasing.\
        Write only the translation (e.g., don't say 'here is the translation', 'the translated version is' or similar phrases).\
        Text:{subtitle['text']}"}
    
    # Append new message to history
    history.append(new_message)
    
    # Keep history at max 30 messages (question + answer)
    if len(history) > 2*30:
        history.pop(0)
    
    while retries <= max_retries:
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=history,
                web_search=False
            )
            history.append({"role":"assistant","content":response.choices[0].message.content})
            subtitle['translated'] = response.choices[0].message.content
            pbar.update(1)
            return
        except Exception as e:
            print(f"{Fore.RED}ERR{Fore.RESET}: sub {subtitle['id']} -> {e}, retry {retries + 1}/{max_retries + 1}")
            print(f"Subtitle request: [{subtitle['text']}]")
            retries += 1
            if retries <= max_retries:
                time.sleep(5)
            else:
                print(f"{Fore.RED}ERR{Fore.RESET}: The provider can't translate")
                subtitle['translated'] = "! TRANSLATION ERROR !"
                pbar.update(1)
                return 

def check_language(lang_code):
    try:
        language = pycountry.languages.get(alpha_2=lang_code) or pycountry.languages.get(alpha_3=lang_code)
        return language.name.upper()
    except KeyError:
        return False

def main():
    # COLORAMA SETUP
    init(autoreset=True)

    # ARGUMENTS
    parser = argparse.ArgumentParser(description="translate SRT file(s) using gpt4free.")
    parser.add_argument("input_path", help="input path for the .srt file or folder containing .srt files")
    parser.add_argument("input_lang", help="input language (iso639): eng,fre,ita,jpn..")
    parser.add_argument("output_lang", help="output language (iso639): eng,fre,ita,jpn..")
    parser.add_argument("-o", "--output_folder", help="custom output folder for the .srt file(s)")
    parser.add_argument("--demux", type=int, nargs='?', const=0, help="automatically demux .srt from file(s) (default stream index is 0)")
    parser.add_argument("--delete", action='store_true', help="delete the source .srt file after processing")
    args = parser.parse_args()

    input_path = os.path.abspath(args.input_path)
    input_lang = check_language(args.input_lang)
    output_lang = check_language(args.output_lang)
    client = Client(provider=Blackbox)
        
    # ERROR CHECK
    if not os.path.exists(input_path):
        print(f"{Fore.RED}ERR{Fore.RESET}: input path not found.")
        return 1
    if input_lang == False:
        print(f"{Fore.RED}ERR{Fore.RESET}: invalid input language (iso639): eng,fre,ita,jpn..")
        return 1
    if output_lang == False:
        print(f"{Fore.RED}ERR{Fore.RESET}: invalid output language (iso639): eng,fre,ita,jpn..")
        return 1

    # PREPARE OUTPUT FOLDER
    if args.output_folder is None:
        output_folder = os.path.dirname(input_path) if os.path.isfile(input_path) else input_path
    else:
        output_folder = os.path.abspath(args.output_folder)
        if not os.path.exists(output_folder):
            print(f"{Fore.RED}ERR{Fore.RESET}: output folder does not exist.")
            return 1
    os.makedirs(output_folder, exist_ok=True)
    
    # AUTO-DEMUX .SRT
    if args.demux is not None:
        subtitle_stream_index = args.demux

        # LOAD MKV LIST
        mkv_files = []
        if os.path.isfile(input_path) and input_path.endswith('.mkv'):
            mkv_files.append(input_path)
        elif os.path.isdir(input_path):
            for file in os.listdir(input_path):
                if file.endswith('.mkv'):
                    mkv_files.append(os.path.join(input_path, file))
        mkv_files.sort()

        if not mkv_files:
            print(f"{Fore.RED}ERR{Fore.RESET}: no .mkv files found in the specified path.")
            return 1

        print(f"{Fore.YELLOW}Loaded {len(mkv_files)} MKV file/s{Fore.RESET}")

        # LOOP IN MKV FILES
        for mkv_file in mkv_files:
            
            nome_base, _ = os.path.splitext(os.path.basename(mkv_file))
            output_file = os.path.join(output_folder, f"{nome_base}_{args.output_lang}.srt")
            demuxed_srt_file = os.path.join(output_folder, f"{nome_base}_{subtitle_stream_index}.srt")

            # SUMMARY
            in_path, in_file = os.path.split(mkv_file)
            out_path, out_file = os.path.split(output_file)
            print(f"\n{Fore.YELLOW}Input MKV{Fore.RESET}: {Fore.BLUE}{in_path}{Style.BRIGHT}/{in_file}{Style.RESET_ALL}")
            if os.path.exists(output_file):
                print(f"{Fore.YELLOW}File already translated. Skipping..{Fore.RESET}")
                if args.delete and os.path.exists(demuxed_srt_file):
                    try:
                        os.remove(demuxed_srt_file)
                    except Exception as e:
                        print(f"{Fore.RED}ERR{Fore.RESET}: {e}")
                continue
            print(f"{Fore.YELLOW}Output{Fore.RESET}: {Fore.BLUE}{out_path}{Style.BRIGHT}/{out_file}{Style.RESET_ALL}")
            
            # DEMUX SRT FROM MKV
            if os.path.exists(demuxed_srt_file):
                print(f"{Fore.YELLOW}Subtitle stream already demuxed. Skipping demux..{Fore.RESET}")
            else:
                print(f"{Fore.YELLOW}Demuxing subtitle {Fore.BLUE}[{subtitle_stream_index}]{Fore.RESET}{Fore.YELLOW}..{Fore.RESET}")

                with tempfile.NamedTemporaryFile(suffix=".srt", delete=False) as tmp_srt:
                    tmp_srt_file = tmp_srt.name
                    cmd = [
                        "ffmpeg", "-y",
                        "-i", mkv_file,
                        "-map", f"0:s:{subtitle_stream_index}",
                        tmp_srt_file
                    ]
                    try:
                        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                    except subprocess.CalledProcessError:
                        print(f"{Fore.RED}ERR{Fore.RESET}: subtitle stream {Fore.RED}[{subtitle_stream_index}]{Fore.RESET} not found. Skipping MKV..")
                        continue
                shutil.move(tmp_srt_file, demuxed_srt_file)

            # LOAD SRT IN DICTIONARY
            subtitles_list = srt_to_dict(demuxed_srt_file)

            print(f"{Fore.YELLOW}Language{Fore.RESET}: {Fore.GREEN}{input_lang}{Fore.RESET}->{Fore.GREEN}{output_lang}{Fore.RESET}")
            history=[]
            with tqdm(total=len(subtitles_list), desc=f"{Fore.YELLOW}Translation{Fore.RESET}") as pbar:
                for subtitle in subtitles_list:
                    translate_subtitle(client, subtitle, input_lang, output_lang, pbar, history)

            # FINAL SAVE
            dict_to_srt(subtitles_list, output_file)
            if args.delete and os.path.exists(demuxed_srt_file):
                try:
                    os.remove(demuxed_srt_file)
                except Exception as e:
                    print(f"{Fore.RED}ERR{Fore.RESET}: {e}")
    else:

        # COLLECT SRT FILES
        srt_files = []
        if os.path.isfile(input_path) and input_path.endswith('.srt'):
            srt_files.append(input_path)
        elif os.path.isdir(input_path):
            for file in os.listdir(input_path):
                if file.endswith('.srt'):
                    srt_files.append(os.path.join(input_path, file))
        srt_files.sort()

        if not srt_files:
            print(f"{Fore.RED}ERR{Fore.RESET}: no .srt files found in the specified path.")
            return 1
        
        # PROCESS EACH SRT FILE
        print(f"{Fore.YELLOW}Loaded {len(srt_files)} SRT file/s{Fore.RESET}")
        for input_file in srt_files:
            # SET OUTPUT FILE PATH
            nome_base, estensione = os.path.splitext(os.path.basename(input_file))
            output_file = os.path.join(output_folder, f"{nome_base}_{args.output_lang}{estensione}")
            
            # SUMMARY
            in_path,in_file =os.path.split(input_file)
            out_path,out_file =os.path.split(output_file)
            print(f"\n{Fore.YELLOW}Input{Fore.RESET}: {Fore.BLUE}{in_path}{Style.BRIGHT}/{in_file}{Style.RESET_ALL}")
            if os.path.exists(output_file) or input_file.endswith(f"_{args.output_lang}{estensione}"):
                print(f"{Fore.YELLOW}File already translated. Skipping..{Fore.RESET}")
                if args.delete and os.path.exists(input_file):
                    try:
                        os.remove(input_file)
                    except Exception as e:
                        print(f"{Fore.RED}ERR{Fore.RESET}: {e}")
                continue

            print(f"{Fore.YELLOW}Output{Fore.RESET}: {Fore.BLUE}{out_path}{Style.BRIGHT}/{out_file}{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}Language{Fore.RESET}: {Fore.GREEN}{input_lang}{Fore.RESET}->{Fore.GREEN}{output_lang}{Fore.RESET}")

            # LOAD SRT IN DICTIONARY
            subtitles_list = srt_to_dict(input_file)

            # TRANSLATION
            history=[]
            with tqdm(total=len(subtitles_list), desc=f"{Fore.YELLOW}Translation{Fore.RESET}") as pbar:
                for subtitle in subtitles_list:
                    translate_subtitle(client, subtitle, input_lang, output_lang, pbar, history)

            # FINAL SAVE
            dict_to_srt(subtitles_list, output_file)
            if args.delete and os.path.exists(input_file):
                try:
                    os.remove(input_file)
                except Exception as e:
                    print(f"{Fore.RED}ERR{Fore.RESET}: {e}")

if __name__ == "__main__":
    main()