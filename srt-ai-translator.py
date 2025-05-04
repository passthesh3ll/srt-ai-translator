from g4f.client import Client
from g4f.Provider import OIVSCode
from tqdm import tqdm
import os, threading, json, pycountry, argparse, time
from colorama import init, Fore

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
    with open(output_file_path, 'w', encoding='utf-8') as f:
        for subtitle in subtitles:
            f.write(subtitle['id'] + '\n')
            f.write(subtitle['time-start'] + ' --> ' + subtitle['time-end'] + '\n')
            f.write(subtitle['translated'] + '\n\n')
def translate_subtitle(client, subtitle, input_lang, output_lang, pbar):
    max_retries = 2
    retries = 0
    while retries <= max_retries:
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": f"Translate the following sentence from {input_lang} to {output_lang}, write only the translated sentence: {subtitle['text']}"}],
                web_search=False
            )
            subtitle['translated'] = response.choices[0].message.content
            pbar.update(1)
            return
        except Exception as e:
            print(f"{Fore.YELLOW}ERR: sub {subtitle['id']} -> {e}, {Fore.GREEN}retry {retries + 1}/{max_retries + 1}")
            retries += 1
            if retries <= max_retries:
                time.sleep(5)
            else:
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
    parser = argparse.ArgumentParser(description="translate a SRT file using gpt4free.")
    parser.add_argument("input_file", help="input path for the .srt file")
    parser.add_argument("input_lang", help="input language (iso639): eng,fre,ita,jpn..")
    parser.add_argument("output_lang", help="output language (iso639): eng,fre,ita,jpn..")
    parser.add_argument("-o", "--output_file",help="custom output path for the .srt file")
    parser.add_argument("-t", "--threads",type=int,help="number of threads",default=100)
    args = parser.parse_args()

    input_file = os.path.abspath(args.input_file)
    input_lang = check_language(args.input_lang)
    output_lang = check_language(args.output_lang)
    if args.output_file is None:
        nome_base, estensione = os.path.splitext(input_file)
        output_file = nome_output = nome_base + "_" + args.output_lang + estensione
    else:
        output_file = os.path.abspath(args.input_file)
    threads_number = args.threads

    # ERROR CHECK
    if not os.path.exists(input_file):
        print(f"{Fore.RED}ERR: input file not found.")
        return 1
    if input_lang == False:
        print(f"{Fore.RED}ERR: invalid input language (iso639): eng,fre,ita,jpn..")
        return 1
    if output_lang == False:
        print(f"{Fore.RED}ERR: invalid output language (iso639): eng,fre,ita,jpn..")
        return 1
    if not (isinstance(threads_number, int) and threads_number > 0):
        print(f"{Fore.RED}ERR: invalid threads value.")
        return 1

    # SUMMARY
    print(f"Input: {Fore.BLUE}{input_file}{Fore.RESET}\nOutput:{Fore.BLUE}{output_file}{Fore.RESET}\nLanguage: {Fore.GREEN}{input_lang}{Fore.RESET}->{Fore.GREEN}{output_lang}{Fore.RESET}")

    # PARAMETERS
    file_name, file_ext = os.path.splitext(input_file)
    subtitles_list = srt_to_dict(input_file)
    client = Client(provider=OIVSCode)
    
    # TRANSLATION
    threads = []
    with tqdm(total=len(subtitles_list), desc=f"Translating ({Fore.YELLOW}{threads_number} threads{Fore.RESET})") as pbar:
        for subtitle in subtitles_list:
            thread = threading.Thread(target=translate_subtitle, args=(client,subtitle,input_lang,output_lang,pbar))
            threads.append(thread)
            thread.start()
            
            # threads_number + 1 for the main thread
            while threading.active_count() > threads_number + 1:
                pass

        # wait threads termination
        for thread in threads:
            thread.join()
            

    # FINAL SAVE
    dict_to_srt(subtitles_list, output_file)

if __name__ == "__main__":
    main()